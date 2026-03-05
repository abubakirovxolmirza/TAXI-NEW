import shutil
import time
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from app.auth import get_current_admin, get_current_driver, get_current_superadmin
from app.config import settings
from app.database import get_db
from app.models import Driver, DriverPhotoControl, DriverPhotoControlStatus, SystemSettings, User
from app.schemas import (
    DriverPhotoControlCheckResponse,
    DriverPhotoControlIntervalUpdate,
    DriverPhotoControlResponse,
    DriverPhotoControlReviewRequest,
    DriverPhotoControlSubmitRequest,
    DriverPhotoControlToggleRequest,
    DriverPhotoControlUploadResponse,
)

router = APIRouter(prefix="/api/driver-photo-controls", tags=["Driver Photo Controls"])

PHOTO_CONTROL_INTERVAL_SETTING_KEY = "driver_photo_control_interval_days"
DEFAULT_PHOTO_CONTROL_INTERVAL_DAYS = 15
WINDOW_START_HOUR = 8
WINDOW_END_HOUR = 16
UZBEKISTAN_TZ = timezone(timedelta(hours=5))


def _get_interval_days(db: Session) -> int:
    setting = db.query(SystemSettings).filter(
        SystemSettings.setting_key == PHOTO_CONTROL_INTERVAL_SETTING_KEY
    ).first()
    if not setting:
        return DEFAULT_PHOTO_CONTROL_INTERVAL_DAYS
    try:
        parsed = int(setting.setting_value)
    except (TypeError, ValueError):
        return DEFAULT_PHOTO_CONTROL_INTERVAL_DAYS
    return parsed if parsed > 0 else DEFAULT_PHOTO_CONTROL_INTERVAL_DAYS


def _within_working_hours() -> bool:
    now_uz = datetime.now(UZBEKISTAN_TZ)
    return WINDOW_START_HOUR <= now_uz.hour < WINDOW_END_HOUR


def _get_driver_or_404(user: User) -> Driver:
    driver = user.driver_profile
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver profile not found",
        )
    return driver


def _latest_control(db: Session, driver_id: int) -> Optional[DriverPhotoControl]:
    return (
        db.query(DriverPhotoControl)
        .filter(DriverPhotoControl.driver_id == driver_id)
        .order_by(DriverPhotoControl.created_at.desc())
        .first()
    )


def _calculate_due(
    *,
    driver: Driver,
    latest: Optional[DriverPhotoControl],
    interval_days: int,
) -> tuple[bool, str, Optional[datetime]]:
    if latest is None:
        if driver.control:
            return False, "active", None
        return True, "first_time", None

    if latest.status == DriverPhotoControlStatus.PENDING:
        return False, "pending_approval", None

    if not driver.control:
        if latest.status == DriverPhotoControlStatus.REJECTED:
            return True, "rejected", None
        return True, "required", None

    if latest.status == DriverPhotoControlStatus.REJECTED:
        return True, "rejected", None

    base_time = latest.approved_at or latest.created_at
    if base_time is None:
        return False, "active", None

    next_due_at = base_time + timedelta(days=interval_days)
    return False, "active", next_due_at


@router.get("/me/check", response_model=DriverPhotoControlCheckResponse)
def check_my_photo_control(
    current_user: User = Depends(get_current_driver),
    db: Session = Depends(get_db),
):
    driver = _get_driver_or_404(current_user)
    interval_days = _get_interval_days(db)
    latest = _latest_control(db, driver.id)
    required, status_label, next_due_at = _calculate_due(
        driver=driver,
        latest=latest,
        interval_days=interval_days,
    )

    return {
        "required": required,
        "can_submit_now": required,
        "window_start_hour": WINDOW_START_HOUR,
        "window_end_hour": WINDOW_END_HOUR,
        "interval_days": interval_days,
        "status": status_label,
        "latest": latest,
        "next_due_at": next_due_at,
    }


@router.post("/upload", response_model=DriverPhotoControlUploadResponse)
def upload_photo_control_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_driver),
):
    driver = _get_driver_or_404(current_user)

    allowed_types = {"image/jpeg", "image/png", "image/jpg", "image/webp"}
    if file.content_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only JPEG, PNG, JPG and WEBP images are allowed",
        )

    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > settings.MAX_UPLOAD_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB",
        )

    upload_dir = Path(settings.UPLOAD_DIR) / "driver_photocontrols" / str(driver.id)
    upload_dir.mkdir(parents=True, exist_ok=True)

    extension = file.filename.split(".")[-1].lower() if file.filename and "." in file.filename else "jpg"
    filename = f"pc_{driver.id}_{int(time.time() * 1000)}.{extension}"
    file_path = upload_dir / filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    relative_path = f"uploads/driver_photocontrols/{driver.id}/{filename}"
    return {
        "message": "Photo uploaded successfully",
        "file_path": relative_path,
    }


@router.post("/me/submit", response_model=DriverPhotoControlResponse, status_code=status.HTTP_201_CREATED)
def submit_my_photo_control(
    payload: DriverPhotoControlSubmitRequest,
    current_user: User = Depends(get_current_driver),
    db: Session = Depends(get_db),
):
    driver = _get_driver_or_404(current_user)
    interval_days = _get_interval_days(db)
    latest = _latest_control(db, driver.id)

    required, status_label, next_due_at = _calculate_due(
        driver=driver,
        latest=latest,
        interval_days=interval_days,
    )

    if status_label == "pending_approval":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Latest photo control is still pending approval",
        )
    if not required:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Photo control is not due yet. Next due: {next_due_at.isoformat() if next_due_at else 'n/a'}",
        )
    control = DriverPhotoControl(
        driver_id=driver.id,
        front_image=payload.front_image,
        back_image=payload.back_image,
        front_salon=payload.front_salon,
        back_salon=payload.back_salon,
        trunk_image=payload.trunk_image,
        status=DriverPhotoControlStatus.PENDING,
    )
    db.add(control)
    db.commit()
    db.refresh(control)
    return control


@router.get("/pending", response_model=list[DriverPhotoControlResponse])
def list_pending_photo_controls(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    controls = (
        db.query(DriverPhotoControl)
        .filter(DriverPhotoControl.status == DriverPhotoControlStatus.PENDING)
        .order_by(DriverPhotoControl.created_at.desc())
        .all()
    )
    return controls


@router.post("/{control_id}/review", response_model=DriverPhotoControlResponse)
def review_photo_control(
    control_id: int,
    payload: DriverPhotoControlReviewRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    control = db.query(DriverPhotoControl).filter(DriverPhotoControl.id == control_id).first()
    if not control:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Photo control not found",
        )
    if control.status != DriverPhotoControlStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending controls can be reviewed",
        )

    if payload.approved:
        control.status = DriverPhotoControlStatus.APPROVED
        control.approved_at = datetime.now(timezone.utc)
        control.rejection_reason = None
        if control.driver:
            control.driver.control = True
    else:
        control.status = DriverPhotoControlStatus.REJECTED
        control.approved_at = None
        control.rejection_reason = (payload.rejection_reason or "").strip()
        if control.driver:
            control.driver.control = False

    db.commit()
    db.refresh(control)
    return control


@router.get("/settings/interval-days")
def get_photo_control_interval_days(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    return {"days": _get_interval_days(db)}


@router.put("/settings/interval-days")
def update_photo_control_interval_days(
    payload: DriverPhotoControlIntervalUpdate,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db),
):
    setting = db.query(SystemSettings).filter(
        SystemSettings.setting_key == PHOTO_CONTROL_INTERVAL_SETTING_KEY
    ).first()

    if not setting:
        setting = SystemSettings(
            setting_key=PHOTO_CONTROL_INTERVAL_SETTING_KEY,
            setting_value=str(payload.days),
            description="Days between required driver photo controls",
            updated_by=current_user.id,
        )
        db.add(setting)
    else:
        setting.setting_value = str(payload.days)
        setting.updated_by = current_user.id

    db.commit()
    return {"days": payload.days}


@router.put("/drivers/{driver_id}/control")
def update_driver_control_flag(
    driver_id: int,
    payload: DriverPhotoControlToggleRequest,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db),
):
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found",
        )

    driver.control = payload.control
    db.commit()
    return {"driver_id": driver_id, "control": payload.control}
