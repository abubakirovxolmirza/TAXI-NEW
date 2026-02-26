"""
Background tasks for order management
"""
import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import TaxiOrder, DeliveryOrder, OrderStatus, Driver
from app.utils import create_notification, get_seat_visibility_timeout_minutes, get_uzbek_time
from app.localization import get_notification_message
from app.websocket import manager
from app.routers.driver import (
    _broadcast_order_to_eligible_drivers,
    _serialize_pending_order_for_driver,
)

# Uzbekistan timezone (UTC+5)
UZBEKISTAN_TZ = timezone(timedelta(hours=5))


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
            new_order_threshold = current_time - timedelta(minutes=1)

            # Taxi orders are marked as new for 1 minute after creation.
            updated_new_flags = (
                db.query(TaxiOrder)
                .filter(
                    TaxiOrder.is_new == True,
                    TaxiOrder.created_at <= new_order_threshold,
                )
                .update({TaxiOrder.is_new: False}, synchronize_session=False)
            )
            updated_delivery_new_flags = (
                db.query(DeliveryOrder)
                .filter(
                    DeliveryOrder.is_new == True,
                    DeliveryOrder.created_at <= new_order_threshold,
                )
                .update({DeliveryOrder.is_new: False}, synchronize_session=False)
            )
            if updated_new_flags or updated_delivery_new_flags:
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
                # Check if pending_time has expired
                time_elapsed = (current_time - order.created_at).total_seconds()
                
                if time_elapsed >= order.pending_time:
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
                    
                    print(f"[TASK] Taxi order #{order.id} is now public after {order.pending_time} seconds")
            
            # Process delivery orders
            for order in delivery_orders_to_make_public:
                # Check if pending_time has expired
                time_elapsed = (current_time - order.created_at).total_seconds()
                
                if time_elapsed >= order.pending_time:
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
                    
                    print(f"[TASK] Delivery order #{order.id} is now public after {order.pending_time} seconds")
            
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


def start_background_tasks():
    """Start all background tasks"""
    asyncio.create_task(check_unconfirmed_orders())
    asyncio.create_task(check_pending_orders_for_public())
    asyncio.create_task(check_expired_driver_vip())
    print("[TASKS] Background tasks started")
