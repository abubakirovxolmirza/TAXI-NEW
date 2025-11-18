"""
Background tasks for order management
"""
import asyncio
from datetime import datetime, timedelta, timezone
from sqlalchemy.orm import Session
from app.database import SessionLocal
from app.models import TaxiOrder, DeliveryOrder, OrderStatus
from app.utils import create_notification
from app.websocket import manager


async def check_unconfirmed_orders():
    """
    Background task to check for unconfirmed orders and return them to pending state
    Runs every minute to check for orders that were accepted but not confirmed within 15 minutes
    """
    while True:
        try:
            db: Session = SessionLocal()
            
            # Get current time
            current_time = datetime.now(timezone.utc)
            expiration_time = current_time - timedelta(minutes=15)
            
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
                    create_notification(
                        db=db,
                        title="Order Expired",
                        message=f"Taxi order #{order.id} confirmation time has expired (15 minutes). The order has been returned to the pool.",
                        notification_type="order_expired",
                        driver_id=old_driver_id
                    )
                
                # Notify all drivers that order is available again
                await manager.broadcast_to_all_drivers({
                    "type": "order_returned",
                    "order_id": order.id,
                    "order_type": "taxi",
                    "reason": "Confirmation time expired (automatic)"
                })
                
                # Notify user
                create_notification(
                    db=db,
                    title="Order Status Update",
                    message=f"Your taxi order #{order.id} is now available for other drivers.",
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
                    create_notification(
                        db=db,
                        title="Order Expired",
                        message=f"Delivery order #{order.id} confirmation time has expired (15 minutes). The order has been returned to the pool.",
                        notification_type="order_expired",
                        driver_id=old_driver_id
                    )
                
                # Notify all drivers that order is available again
                await manager.broadcast_to_all_drivers({
                    "type": "order_returned",
                    "order_id": order.id,
                    "order_type": "delivery",
                    "reason": "Confirmation time expired (automatic)"
                })
                
                # Notify user
                create_notification(
                    db=db,
                    title="Order Status Update",
                    message=f"Your delivery order #{order.id} is now available for other drivers.",
                    notification_type="order_status_update",
                    user_id=order.user_id
                )
                
                print(f"[TASK] Delivery order #{order.id} returned to pending (confirmation expired)")
            
            db.close()
            
        except Exception as e:
            print(f"[TASK ERROR] Error checking unconfirmed orders: {str(e)}")
            if 'db' in locals():
                db.close()
        
        # Wait 1 minute before next check
        await asyncio.sleep(60)


def start_background_tasks():
    """Start all background tasks"""
    asyncio.create_task(check_unconfirmed_orders())
    print("[TASKS] Background tasks started")
