from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Set

from sqlalchemy.orm import Session

from app.models import DeviceToken, Driver, Notification


def upsert_device_token(
    db: Session,
    *,
    user_id: int,
    token: str,
    platform: Optional[str] = None,
) -> DeviceToken:
    existing = db.query(DeviceToken).filter(DeviceToken.token == token).first()
    now = datetime.now(timezone.utc)

    if existing:
        existing.user_id = user_id
        existing.platform = platform
        existing.is_active = True
        existing.last_seen_at = now
        existing.updated_at = now
        db.commit()
        db.refresh(existing)
        return existing

    device_token = DeviceToken(
        user_id=user_id,
        token=token,
        platform=platform,
        is_active=True,
        last_seen_at=now,
    )
    db.add(device_token)
    db.commit()
    db.refresh(device_token)
    return device_token


def create_notification(
    db: Session,
    *,
    title: str,
    body: str,
    notification_type: str,
    user_id: Optional[int] = None,
    driver_id: Optional[int] = None,
    data: Optional[Dict[str, Any]] = None,
) -> Notification:
    notification = Notification(
        user_id=user_id,
        driver_id=driver_id,
        title=title,
        message=body,
        body=body,
        data=data,
        notification_type=notification_type,
        is_read=False,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def resolve_target_user_ids(
    db: Session,
    *,
    user_id: Optional[int],
    driver_id: Optional[int],
) -> Set[int]:
    target_user_ids: Set[int] = set()
    if user_id:
        target_user_ids.add(user_id)
    if driver_id:
        driver = db.query(Driver).filter(Driver.id == driver_id).first()
        if driver and driver.user_id:
            target_user_ids.add(driver.user_id)
    return target_user_ids


def get_active_tokens_for_user_ids(db: Session, user_ids: Set[int]) -> List[DeviceToken]:
    if not user_ids:
        return []
    return (
        db.query(DeviceToken)
        .filter(DeviceToken.user_id.in_(user_ids), DeviceToken.is_active == True)
        .all()
    )
