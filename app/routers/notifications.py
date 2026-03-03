from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import User, Notification, DeviceToken, UserRole
from app.schemas import (
    NotificationResponse,
    NotificationSendRequest,
    NotificationSendResponse,
    NotificationBroadcastRequest,
    NotificationBroadcastResponse,
    NotificationCreateRequest,
)
from app.auth import get_current_user, get_current_admin
from app.services.fcm import send_push_to_tokens
from app.repositories.notifications_repo import (
    create_notification as repo_create_notification,
    get_active_tokens_for_user_ids,
    resolve_target_user_ids,
)

router = APIRouter(prefix="/api/notifications", tags=["Notifications"])


@router.get("/", response_model=List[NotificationResponse])
def get_my_notifications(
    user_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get current user's notifications"""
    target_user_id = current_user.id
    if user_id is not None:
        if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only admin can query notifications by user_id",
            )
        target_user_id = user_id

    # Get user notifications
    notifications = db.query(Notification).filter(
        Notification.user_id == target_user_id
    )
    
    # If user is also a driver, get driver notifications
    if current_user.driver_profile:
        driver_notifications = db.query(Notification).filter(
            Notification.driver_id == current_user.driver_profile.id
        )
        notifications = notifications.union(driver_notifications)
    
    notifications = notifications.order_by(Notification.created_at.desc()).all()
    return notifications


@router.get("/unread", response_model=List[NotificationResponse])
def get_unread_notifications(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get unread notifications"""
    notifications = db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    )
    
    # If user is also a driver, get driver notifications
    if current_user.driver_profile:
        driver_notifications = db.query(Notification).filter(
            Notification.driver_id == current_user.driver_profile.id,
            Notification.is_read == False
        )
        notifications = notifications.union(driver_notifications)
    
    notifications = notifications.order_by(Notification.created_at.desc()).all()
    return notifications


@router.post("/{notification_id}/mark-read")
def mark_notification_read(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark notification as read"""
    notification = db.query(Notification).filter(
        Notification.id == notification_id
    ).first()
    
    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notification not found"
        )
    
    # Check if notification belongs to user
    if notification.user_id != current_user.id:
        if not current_user.driver_profile or notification.driver_id != current_user.driver_profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this notification"
            )
    
    notification.is_read = True
    db.commit()
    
    return {"success": True, "message": "Notification marked as read"}


@router.post("/mark-all-read")
def mark_all_notifications_read(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Mark all notifications as read"""
    # Mark user notifications
    db.query(Notification).filter(
        Notification.user_id == current_user.id,
        Notification.is_read == False
    ).update({"is_read": True})
    
    # Mark driver notifications if applicable
    if current_user.driver_profile:
        db.query(Notification).filter(
            Notification.driver_id == current_user.driver_profile.id,
            Notification.is_read == False
        ).update({"is_read": True})
    
    db.commit()
    
    return {"success": True, "message": "All notifications marked as read"}


@router.post("/send", response_model=NotificationSendResponse)
def send_notification_to_user(
    payload: NotificationSendRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    target_user = db.query(User).filter(User.id == payload.user_id).first()
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    notification = Notification(
        user_id=payload.user_id,
        title=payload.title,
        message=payload.body,
        body=payload.body,
        data=payload.data,
        notification_type="push",
        is_read=False,
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)

    tokens = (
        db.query(DeviceToken)
        .filter(DeviceToken.user_id == payload.user_id, DeviceToken.is_active == True)
        .all()
    )
    push_result = send_push_to_tokens(
        db=db,
        device_tokens=tokens,
        title=payload.title,
        body=payload.body,
        data=payload.data,
    )

    return {
        "success": True,
        "notification": notification,
        "push": push_result,
    }


@router.post("/create", response_model=NotificationSendResponse)
def create_notification_and_push(
    payload: NotificationCreateRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    if payload.user_id is None and payload.driver_id is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_id or driver_id is required",
        )

    notification = repo_create_notification(
        db=db,
        user_id=payload.user_id,
        driver_id=payload.driver_id,
        title=payload.title,
        body=payload.body,
        notification_type=payload.type,
        data=payload.data,
    )

    target_user_ids = resolve_target_user_ids(
        db=db,
        user_id=payload.user_id,
        driver_id=payload.driver_id,
    )
    tokens = get_active_tokens_for_user_ids(db, target_user_ids)
    push_data = dict(payload.data or {})
    push_data.setdefault("type", payload.type)
    push_data.setdefault("notification_id", str(notification.id))
    push_data.setdefault("notification_type", payload.type)
    push_result = send_push_to_tokens(
        db=db,
        device_tokens=tokens,
        title=payload.title,
        body=payload.body,
        data=push_data,
        android_channel_id="high_importance_channel",
        android_sound="order_sound",
        ios_sound="default",
    )

    return {
        "success": True,
        "notification": notification,
        "push": push_result,
    }


@router.post("/broadcast", response_model=NotificationBroadcastResponse)
def broadcast_notifications(
    payload: NotificationBroadcastRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    unique_user_ids = list(dict.fromkeys(payload.user_ids))
    if not unique_user_ids:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="user_ids cannot be empty",
        )

    users = db.query(User.id).filter(User.id.in_(unique_user_ids)).all()
    existing_user_ids = {row.id for row in users}
    if not existing_user_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No valid users found",
        )

    notifications = [
        Notification(
            user_id=user_id,
            title=payload.title,
            message=payload.body,
            body=payload.body,
            data=payload.data,
            notification_type="push",
            is_read=False,
        )
        for user_id in existing_user_ids
    ]
    db.add_all(notifications)
    db.commit()

    tokens = (
        db.query(DeviceToken)
        .filter(DeviceToken.user_id.in_(existing_user_ids), DeviceToken.is_active == True)
        .all()
    )
    push_result = send_push_to_tokens(
        db=db,
        device_tokens=tokens,
        title=payload.title,
        body=payload.body,
        data=payload.data,
    )

    return {
        "success": True,
        "notifications_created": len(notifications),
        "push": push_result,
    }
