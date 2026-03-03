from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import Driver, User, UserRole
from app.repositories.notifications_repo import upsert_device_token
from app.schemas import DeviceRegisterRequest, DeviceTokenActionResponse

router = APIRouter(prefix="/api/devices", tags=["Devices"])


@router.post("/register", response_model=DeviceTokenActionResponse, status_code=status.HTTP_200_OK)
def register_device(
    payload: DeviceRegisterRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    resolved_user_id = payload.user_id

    if payload.driver_id is not None:
        driver = db.query(Driver).filter(Driver.id == payload.driver_id).first()
        if not driver:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Driver not found",
            )
        if resolved_user_id is not None and resolved_user_id != driver.user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="user_id does not match driver_id owner",
            )
        resolved_user_id = driver.user_id

    if resolved_user_id is None:
        resolved_user_id = current_user.id

    if resolved_user_id != current_user.id and current_user.role not in {UserRole.ADMIN, UserRole.SUPERADMIN}:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not allowed to register token for another user",
        )

    device_token = upsert_device_token(
        db=db,
        user_id=resolved_user_id,
        token=payload.token,
        platform=payload.platform,
    )
    return {
        "success": True,
        "message": "Device token registered",
        "device_token": device_token,
    }
