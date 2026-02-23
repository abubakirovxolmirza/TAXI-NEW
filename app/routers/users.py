from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth import get_current_user
from app.database import get_db
from app.models import DeviceToken, User
from app.schemas import (
    DeviceTokenActionResponse,
    DeviceTokenDeleteRequest,
    DeviceTokenResponse,
    DeviceTokenUpsertRequest,
)

router = APIRouter(prefix="/api/users", tags=["Users"])


@router.post("/device-token", response_model=DeviceTokenActionResponse, status_code=status.HTTP_200_OK)
def upsert_device_token(
    payload: DeviceTokenUpsertRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    existing = db.query(DeviceToken).filter(DeviceToken.token == payload.token).first()
    now = datetime.now(timezone.utc)

    if existing:
        existing.user_id = current_user.id
        existing.platform = payload.platform
        existing.is_active = True
        existing.last_seen_at = now
        existing.updated_at = now
        db.commit()
        db.refresh(existing)
        return {
            "success": True,
            "message": "Device token updated",
            "device_token": existing,
        }

    device_token = DeviceToken(
        user_id=current_user.id,
        token=payload.token,
        platform=payload.platform,
        is_active=True,
        last_seen_at=now,
    )
    db.add(device_token)
    db.commit()
    db.refresh(device_token)

    return {
        "success": True,
        "message": "Device token registered",
        "device_token": device_token,
    }


@router.delete("/device-token", response_model=DeviceTokenActionResponse)
def deactivate_device_token(
    payload: DeviceTokenDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    device_token = (
        db.query(DeviceToken)
        .filter(
            DeviceToken.token == payload.token,
            DeviceToken.user_id == current_user.id,
            DeviceToken.is_active == True,
        )
        .first()
    )
    if not device_token:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active device token not found",
        )

    device_token.is_active = False
    device_token.updated_at = datetime.now(timezone.utc)
    db.commit()
    db.refresh(device_token)

    return {
        "success": True,
        "message": "Device token deactivated",
        "device_token": device_token,
    }
