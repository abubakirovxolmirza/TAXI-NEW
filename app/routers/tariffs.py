from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.auth import get_current_superadmin, get_current_user
from app.database import get_db
from app.models import SystemSettings, Tariff, User

router = APIRouter(prefix="/api/tariffs", tags=["Tariffs"])


def _setting_key(tariff: Tariff) -> str:
    return f"tariff_active_{tariff.value}"


def _parse_bool(raw: Optional[str], default: bool = True) -> bool:
    if raw is None:
        return default
    normalized = raw.strip().lower()
    return normalized in {"1", "true", "yes", "on"}


class TariffStatusItem(BaseModel):
    tariff: Tariff
    is_active: bool
    updated_at: Optional[datetime] = None


class TariffStatusUpdate(BaseModel):
    is_active: bool = Field(..., description="Tariff active status")


@router.get("", response_model=List[TariffStatusItem])
@router.get("/", response_model=List[TariffStatusItem], include_in_schema=False)
def get_tariff_statuses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    del current_user
    keys = [_setting_key(tariff) for tariff in Tariff]
    settings_rows = (
        db.query(SystemSettings)
        .filter(SystemSettings.setting_key.in_(keys))
        .all()
    )
    by_key = {row.setting_key: row for row in settings_rows}

    result: List[TariffStatusItem] = []
    for tariff in Tariff:
        row = by_key.get(_setting_key(tariff))
        result.append(
            TariffStatusItem(
                tariff=tariff,
                is_active=_parse_bool(row.setting_value if row else None, default=True),
                updated_at=row.updated_at if row else None,
            )
        )
    return result


@router.get("/{tariff}", response_model=TariffStatusItem)
def get_single_tariff_status(
    tariff: Tariff,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    del current_user
    key = _setting_key(tariff)
    row = db.query(SystemSettings).filter(SystemSettings.setting_key == key).first()
    return TariffStatusItem(
        tariff=tariff,
        is_active=_parse_bool(row.setting_value if row else None, default=True),
        updated_at=row.updated_at if row else None,
    )


@router.patch("/{tariff}/status", response_model=TariffStatusItem)
@router.put("/{tariff}/status", response_model=TariffStatusItem, include_in_schema=False)
def update_tariff_status(
    tariff: Tariff,
    payload: TariffStatusUpdate,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db),
):
    key = _setting_key(tariff)
    row = db.query(SystemSettings).filter(SystemSettings.setting_key == key).first()

    if not row:
        row = SystemSettings(
            setting_key=key,
            setting_value=str(payload.is_active).lower(),
            description=f"Tariff availability flag for {tariff.value}",
            updated_by=current_user.id,
        )
        db.add(row)
    else:
        row.setting_value = str(payload.is_active).lower()
        row.updated_by = current_user.id

    db.commit()
    db.refresh(row)

    return TariffStatusItem(
        tariff=tariff,
        is_active=_parse_bool(row.setting_value, default=True),
        updated_at=row.updated_at,
    )
