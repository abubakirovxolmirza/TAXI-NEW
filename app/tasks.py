"""
Background tasks for order management
"""
import asyncio
from datetime import datetime, timedelta, timezone
from pathlib import Path
from sqlalchemy.orm import Session
from app.config import settings
from app.database import SessionLocal
from app.models import (
    TaxiOrder,
    DeliveryOrder,
    Driver,
    OrderStatus,
    DriverPhotoControl,
    DriverPhotoControlStatus,
    SystemSettings,
)
from app.utils import (
    create_notification,
    get_seat_visibility_timeout_minutes,
    get_uzbek_time,
    send_new_order_push_to_working_drivers,
)
from app.localization import get_notification_message
from app.websocket import manager
from app.routers.driver import (
    _broadcast_order_to_eligible_drivers,
    _serialize_pending_order_for_driver,
)

# Uzbekistan timezone (UTC+5)
UZBEKISTAN_TZ = timezone(timedelta(hours=5))
PHOTO_CONTROL_INTERVAL_SETTING_KEY = "driver_photo_control_interval_days"
DEFAULT_PHOTO_CONTROL_INTERVAL_DAYS = 15


async def check_unconfirmed_orders():
    """
    Background task to check for unconfirmed orders and return them to pending state
    Runs every minute to check for orders that were accepted but not confirmed within the configured timeout
    """
    while True:
        try:
            db: Session = SessionLocal()
            
            # Get current time in Uzbekistan timezone
            current_time = get_uzbek_time()
            
            # Get configurable timeout (default: 15 minutes)
            timeout_minutes = get_seat_visibility_timeout_minutes(db)
            expiration_time = current_time - timedelta(minutes=timeout_minutes)
            
            # Find taxi orders that are accepted but not confirmed and expired
            expired_taxi_orders = db.query(TaxiOrder).filter(
                TaxiOrder.status == OrderStatus.ACCEPTED,
                TaxiOrder.is_confirmed == False,
                TaxiOrder.accepted_at <= expiration_time
            ).all()
            
            # Find delivery orders that are accepted but not confirmed and expired
            expired_delivery_orders = db.query(DeliveryOrder).filter(
                DeliveryOrder.status == OrderStatus.ACCEPTED,
                DeliveryOrder.is_confirmed == False,
                DeliveryOrder.accepted_at <= expiration_time
            ).all()

            # Find taxi orders that are pending but held (previewed) for too long
            held_taxi_orders = db.query(TaxiOrder).filter(
                TaxiOrder.status == OrderStatus.PENDING,
                TaxiOrder.is_confirmed == True,
                TaxiOrder.accepted_at <= expiration_time
            ).all()

            # Find delivery orders that are pending but held (previewed) for too long
            held_delivery_orders = db.query(DeliveryOrder).filter(
                DeliveryOrder.status == OrderStatus.PENDING,
                DeliveryOrder.is_confirmed == True,
                DeliveryOrder.accepted_at <= expiration_time
            ).all()
            
            # Process expired taxi orders
            for order in expired_taxi_orders:
                old_driver_id = order.driver_id
                
                # Return to pending state
                order.driver_id = None
                order.status = OrderStatus.PENDING
                order.accepted_at = None
                order.is_confirmed = False
                
                db.commit()
                db.refresh(order)
                
                # Notify the driver who lost the order
                if old_driver_id:
                    notification = get_notification_message("order_expired", order_id=order.id, order_type="taksi")
                    create_notification(
                        db=db,
                        title=notification["title"],
                        message=notification["message"],
                        notification_type="order_expired",
                        driver_id=old_driver_id
                    )
                
                # Notify all drivers that order is available again
                await _broadcast_order_to_eligible_drivers(
                    {
                        "type": "order_returned",
                        "order_id": order.id,
                        "order_type": "taxi",
                        "reason": "Confirmation time expired (automatic)",
                        "driver_id": old_driver_id,
                        "order": _serialize_pending_order_for_driver(order, "taxi"),
                    },
                    order.id,
                    "taxi",
                )
                
                # Notify user
                notification = get_notification_message("order_expired_user", order_id=order.id, order_type="taksi")
                create_notification(
                    db=db,
                    title=notification["title"],
                    message=notification["message"],
                    notification_type="order_status_update",
                    user_id=order.user_id
                )
                
                print(f"[TASK] Taxi order #{order.id} returned to pending (confirmation expired)")
            
            # Process expired delivery orders
            for order in expired_delivery_orders:
                old_driver_id = order.driver_id
                
                # Return to pending state
                order.driver_id = None
                order.status = OrderStatus.PENDING
                order.accepted_at = None
                order.is_confirmed = False
                
                db.commit()
                db.refresh(order)
                
                # Notify the driver who lost the order
                if old_driver_id:
                    notification = get_notification_message("order_expired", order_id=order.id, order_type="yetkazib berish")
                    create_notification(
                        db=db,
                        title=notification["title"],
                        message=notification["message"],
                        notification_type="order_expired",
                        driver_id=old_driver_id
                    )
                
                # Notify all drivers that order is available again
                await _broadcast_order_to_eligible_drivers(
                    {
                        "type": "order_returned",
                        "order_id": order.id,
                        "order_type": "delivery",
                        "reason": "Confirmation time expired (automatic)",
                        "driver_id": old_driver_id,
                        "order": _serialize_pending_order_for_driver(order, "delivery"),
                    },
                    order.id,
                    "delivery",
                )
                
                # Notify user
                notification = get_notification_message("order_status_update", order_id=order.id, order_type="yetkazib berish")
                create_notification(
                    db=db,
                    title=notification["title"],
                    message=notification["message"],
                    notification_type="order_status_update",
                    user_id=order.user_id
                )
                
                print(f"[TASK] Delivery order #{order.id} returned to pending (confirmation expired)")

            # Process taxi orders that were held in preview for too long
            for order in held_taxi_orders:
                old_driver_id = order.driver_id

                # Return to pending state
                order.driver_id = None
                order.status = OrderStatus.PENDING
                order.accepted_at = None
                order.is_confirmed = False

                db.commit()
                db.refresh(order)

                # Notify the driver who lost the hold
                if old_driver_id:
                    notification = get_notification_message("order_released", order_id=order.id, order_type="taksi")
                    create_notification(
                        db=db,
                        title=notification["title"],
                        message=notification["message"],
                        notification_type="order_expired",
                        driver_id=old_driver_id
                    )

                # Notify all drivers that order is available again
                await _broadcast_order_to_eligible_drivers(
                    {
                        "type": "order_returned",
                        "order_id": order.id,
                        "order_type": "taxi",
                        "reason": "Preview hold expired (automatic)",
                        "driver_id": old_driver_id,
                        "order": _serialize_pending_order_for_driver(order, "taxi"),
                    },
                    order.id,
                    "taxi",
                )

                # Notify user
                notification = get_notification_message("order_status_update", order_id=order.id, order_type="taksi")
                create_notification(
                    db=db,
                    title=notification["title"],
                    message=notification["message"],
                    notification_type="order_status_update",
                    user_id=order.user_id
                )

                print(f"[TASK] Taxi order #{order.id} preview hold expired and returned to pending")

            # Process delivery orders that were held in preview for too long
            for order in held_delivery_orders:
                old_driver_id = order.driver_id

                # Return to pending state
                order.driver_id = None
                order.status = OrderStatus.PENDING
                order.accepted_at = None
                order.is_confirmed = False

                db.commit()
                db.refresh(order)

                # Notify the driver who lost the hold
                if old_driver_id:
                    notification = get_notification_message("order_released", order_id=order.id, order_type="yetkazib berish")
                    create_notification(
                        db=db,
                        title=notification["title"],
                        message=notification["message"],
                        notification_type="order_expired",
                        driver_id=old_driver_id
                    )

                # Notify all drivers that order is available again
                await _broadcast_order_to_eligible_drivers(
                    {
                        "type": "order_returned",
                        "order_id": order.id,
                        "order_type": "delivery",
                        "reason": "Preview hold expired (automatic)",
                        "driver_id": old_driver_id,
                        "order": _serialize_pending_order_for_driver(order, "delivery"),
                    },
                    order.id,
                    "delivery",
                )

                # Notify user
                notification = get_notification_message("order_status_update", order_id=order.id, order_type="yetkazib berish")
                create_notification(
                    db=db,
                    title=notification["title"],
                    message=notification["message"],
                    notification_type="order_status_update",
                    user_id=order.user_id
                )

                print(f"[TASK] Delivery order #{order.id} preview hold expired and returned to pending")
            
            db.close()
            
        except Exception as e:
            print(f"[TASK ERROR] Error checking unconfirmed orders: {str(e)}")
            if 'db' in locals():
                db.close()
        
        # Wait 1 minute before next check
        await asyncio.sleep(60)


async def check_pending_orders_for_public():
    """
    Background task to check pending orders and make them public after pending_time expires
    Runs every 5 seconds to check for orders that should become public
    """
    while True:
        try:
            db: Session = SessionLocal()
            
            # Get current time
            current_time = datetime.now(timezone.utc)
            # Mark orders as not new when their own pending_time (minutes) expires.
            taxi_new_orders = db.query(TaxiOrder).filter(
                TaxiOrder.is_new == True,
                TaxiOrder.pending_time.isnot(None),
            ).all()
            delivery_new_orders = db.query(DeliveryOrder).filter(
                DeliveryOrder.is_new == True,
                DeliveryOrder.pending_time.isnot(None),
            ).all()

            new_flags_changed = False
            for order in taxi_new_orders:
                if (current_time - order.created_at).total_seconds() >= (order.pending_time * 60):
                    order.is_new = False
                    new_flags_changed = True
            for order in delivery_new_orders:
                if (current_time - order.created_at).total_seconds() >= (order.pending_time * 60):
                    order.is_new = False
                    new_flags_changed = True

            if new_flags_changed:
                db.commit()
            
            # Find taxi orders that are pending, not public, and have expired pending_time
            taxi_orders_to_make_public = db.query(TaxiOrder).filter(
                TaxiOrder.status == OrderStatus.PENDING,
                TaxiOrder.public_order == False,
                TaxiOrder.driver_id == None,  # No driver assigned yet
                TaxiOrder.pending_time.isnot(None)
            ).all()
            
            # Find delivery orders that are pending, not public, and have expired pending_time
            delivery_orders_to_make_public = db.query(DeliveryOrder).filter(
                DeliveryOrder.status == OrderStatus.PENDING,
                DeliveryOrder.public_order == False,
                DeliveryOrder.driver_id == None,  # No driver assigned yet
                DeliveryOrder.pending_time.isnot(None)
            ).all()
            
            # Process taxi orders
            for order in taxi_orders_to_make_public:
                # Check if pending_time (minutes) has expired
                time_elapsed = (current_time - order.created_at).total_seconds()
                
                if time_elapsed >= (order.pending_time * 60):
                    # Make order public
                    order.public_order = True
                    db.commit()
                    db.refresh(order)
                    
                    # Notify user
                    notification = get_notification_message("order_now_public", order_id=order.id, order_type="taksi")
                    create_notification(
                        db=db,
                        title=notification["title"],
                        message=notification["message"],
                        notification_type="order_public",
                        user_id=order.user_id
                    )
                    
                    # Broadcast to all drivers
                    await manager.broadcast_to_all_drivers({
                        "type": "order_now_public",
                        "order_id": order.id,
                        "order_type": "taxi",
                        "order": _serialize_pending_order_for_driver(order, "taxi")
                    })
                    send_new_order_push_to_working_drivers(
                        db,
                        order_id=order.id,
                        order_type="taxi",
                        brend_only=False,
                    )
                    
                    print(f"[TASK] Taxi order #{order.id} is now public after {order.pending_time} minutes")
            
            # Process delivery orders
            for order in delivery_orders_to_make_public:
                # Check if pending_time (minutes) has expired
                time_elapsed = (current_time - order.created_at).total_seconds()
                
                if time_elapsed >= (order.pending_time * 60):
                    # Make order public
                    order.public_order = True
                    db.commit()
                    db.refresh(order)
                    
                    # Notify user
                    notification = get_notification_message("order_now_public", order_id=order.id, order_type="yetkazib berish")
                    create_notification(
                        db=db,
                        title=notification["title"],
                        message=notification["message"],
                        notification_type="order_public",
                        user_id=order.user_id
                    )
                    
                    # Broadcast to all drivers
                    await manager.broadcast_to_all_drivers({
                        "type": "order_now_public",
                        "order_id": order.id,
                        "order_type": "delivery",
                        "order": _serialize_pending_order_for_driver(order, "delivery")
                    })
                    send_new_order_push_to_working_drivers(
                        db,
                        order_id=order.id,
                        order_type="delivery",
                        brend_only=False,
                    )
                    
                    print(f"[TASK] Delivery order #{order.id} is now public after {order.pending_time} minutes")
            
            db.close()
            
        except Exception as e:
            print(f"[TASK ERROR] Error checking pending orders for public: {str(e)}")
            if 'db' in locals():
                db.close()
        
        # Wait 5 seconds before next check
        await asyncio.sleep(5)


async def check_expired_driver_vip():
    """
    Background task to disable VIP for drivers whose VIP period has ended.
    Runs every minute.
    """
    while True:
        try:
            db: Session = SessionLocal()
            current_time = datetime.now(timezone.utc)

            expired_vip_drivers = db.query(Driver).filter(
                Driver.vip == True,
                Driver.vip_expires_at.isnot(None),
                Driver.vip_expires_at <= current_time
            ).all()

            if expired_vip_drivers:
                for driver in expired_vip_drivers:
                    driver.vip = False
                    driver.vip_expires_at = None
                db.commit()
                print(f"[TASK] Disabled VIP for {len(expired_vip_drivers)} expired driver(s)")

            db.close()
        except Exception as e:
            print(f"[TASK ERROR] Error checking expired driver VIP: {str(e)}")
            if 'db' in locals():
                db.close()

        await asyncio.sleep(60)


def _photo_control_interval_days(db: Session) -> int:
    setting = db.query(SystemSettings).filter(
        SystemSettings.setting_key == PHOTO_CONTROL_INTERVAL_SETTING_KEY
    ).first()
    if not setting:
        return DEFAULT_PHOTO_CONTROL_INTERVAL_DAYS
    try:
        value = int(setting.setting_value)
    except (TypeError, ValueError):
        return DEFAULT_PHOTO_CONTROL_INTERVAL_DAYS
    return value if value > 0 else DEFAULT_PHOTO_CONTROL_INTERVAL_DAYS


def _is_photo_control_window(now_uz: datetime) -> bool:
    return 8 <= now_uz.hour < 16


async def check_expired_driver_photo_controls():
    """
    Background task to disable driver control after interval days from approval.
    Disabling is allowed only in Uzbekistan time window 08:00-16:00.
    """
    while True:
        db = None
        try:
            db = SessionLocal()
            now_utc = datetime.now(timezone.utc)
            now_uz = get_uzbek_time(now_utc)

            if not _is_photo_control_window(now_uz):
                await asyncio.sleep(60)
                continue

            interval_days = _photo_control_interval_days(db)
            drivers = db.query(Driver).filter(Driver.control == True).all()
            changed = 0

            for driver in drivers:
                latest_approved = (
                    db.query(DriverPhotoControl)
                    .filter(
                        DriverPhotoControl.driver_id == driver.id,
                        DriverPhotoControl.status == DriverPhotoControlStatus.APPROVED,
                    )
                    .order_by(
                        DriverPhotoControl.approved_at.desc(),
                        DriverPhotoControl.created_at.desc(),
                    )
                    .first()
                )
                if not latest_approved:
                    continue

                base_time = latest_approved.approved_at or latest_approved.created_at
                if base_time is None:
                    continue
                if base_time.tzinfo is None:
                    base_time = base_time.replace(tzinfo=timezone.utc)

                due_at = base_time + timedelta(days=interval_days)
                if now_utc >= due_at:
                    driver.control = False
                    changed += 1

            if changed:
                db.commit()
                print(f"[TASK] Disabled control for {changed} driver(s) after photo-control expiry")
            else:
                db.rollback()
        except Exception as e:
            print(f"[TASK ERROR] check_expired_driver_photo_controls: {str(e)}")
            if db is not None:
                db.rollback()
        finally:
            if db is not None:
                db.close()

        await asyncio.sleep(60)


def _resolve_upload_file_path(image_path: str) -> Path:
    candidate = Path(str(image_path).strip())
    if candidate.is_absolute():
        return candidate
    if str(candidate).startswith("uploads/"):
        return Path.cwd() / candidate
    return Path(settings.UPLOAD_DIR) / candidate


async def cleanup_expired_driver_photocontrol_images():
    """
    Delete photo-control images and DB rows after 2x configured interval.
    Runs every 6 hours.
    """
    while True:
        db: Session | None = None
        try:
            db = SessionLocal()
            interval_days = _photo_control_interval_days(db)
            cutoff = datetime.now(timezone.utc) - timedelta(days=interval_days * 2)

            expired_rows = (
                db.query(DriverPhotoControl)
                .filter(DriverPhotoControl.created_at <= cutoff)
                .all()
            )
            if expired_rows:
                for row in expired_rows:
                    for field_name in ("front_image", "back_image", "front_salon", "back_salon", "trunk_image"):
                        image_path = getattr(row, field_name, None)
                        if not image_path:
                            continue
                        file_path = _resolve_upload_file_path(image_path)
                        try:
                            if file_path.exists() and file_path.is_file():
                                file_path.unlink()
                        except Exception:
                            pass
                    db.delete(row)
                db.commit()
                print(f"[TASK] Deleted {len(expired_rows)} expired driver photo control records")
        except Exception as e:
            print(f"[TASK ERROR] cleanup_expired_driver_photocontrol_images: {str(e)}")
            if db is not None:
                db.rollback()
        finally:
            if db is not None:
                db.close()

        await asyncio.sleep(6 * 60 * 60)


def start_background_tasks():
    """Start all background tasks"""
    asyncio.create_task(check_unconfirmed_orders())
    asyncio.create_task(check_pending_orders_for_public())
    asyncio.create_task(check_expired_driver_vip())
    asyncio.create_task(check_expired_driver_photo_controls())
    asyncio.create_task(cleanup_expired_driver_photocontrol_images())
    print("[TASKS] Background tasks started")
