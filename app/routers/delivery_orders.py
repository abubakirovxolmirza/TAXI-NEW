from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from app.database import get_db
from app.models import User, DeliveryOrder, OrderStatus, Driver, UserRole
from app.schemas import DeliveryOrderCreate, DeliveryOrderResponse, OrderCancellation, BulkDeleteRequest
from app.auth import get_current_user
from app.utils import calculate_delivery_price, notify_all_drivers, create_notification, calculate_service_fee
from app.websocket import manager

router = APIRouter(prefix="/api/delivery-orders", tags=["Delivery Orders"])


@router.post("/", response_model=DeliveryOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_delivery_order(
    order_data: DeliveryOrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new delivery order"""
    # Calculate price
    price = calculate_delivery_price(
        db=db,
        from_region_id=order_data.from_region_id,
        to_region_id=order_data.to_region_id
    )
    
    # Calculate service fee and driver earnings
    service_fee, driver_earnings = calculate_service_fee(price, db)
    
    # Create order
    new_order = DeliveryOrder(
        user_id=current_user.id,
        username=order_data.username,
        sender_telephone=order_data.sender_telephone,
        receiver_telephone=order_data.receiver_telephone,
        from_region_id=order_data.from_region_id,
        from_district_id=order_data.from_district_id,
        to_region_id=order_data.to_region_id,
        to_district_id=order_data.to_district_id,
        pickup_latitude=order_data.pickup_latitude,
        pickup_longitude=order_data.pickup_longitude,
        pickup_address=order_data.pickup_address,
        dropoff_latitude=order_data.dropoff_latitude,
        dropoff_longitude=order_data.dropoff_longitude,
        dropoff_address=order_data.dropoff_address,
        item_type=order_data.item_type,
        date=order_data.date,
        time_start=order_data.time_start,
        time_end=order_data.time_end,
        scheduled_datetime=order_data.scheduled_datetime,
        price=price,
        service_fee=service_fee,
        driver_earnings=driver_earnings,
        note=order_data.note,
        status=OrderStatus.PENDING
    )
    
    db.add(new_order)
    db.commit()
    db.refresh(new_order)
    
    # Notify all drivers via database
    notify_all_drivers(
        db=db,
        title="New Delivery Order",
        message=f"New delivery order from region {order_data.from_region_id} to {order_data.to_region_id}"
    )
    
    # Broadcast to all drivers via WebSocket
    import asyncio
    order_data_dict = {
        "id": new_order.id,
        "type": "delivery",
        "from_region_id": new_order.from_region_id,
        "to_region_id": new_order.to_region_id,
        "item_type": new_order.item_type.value,
        "price": float(new_order.price),
        "service_fee": float(new_order.service_fee),
        "driver_earnings": float(new_order.driver_earnings),
        "date": new_order.date,
        "time_start": new_order.time_start,
        "time_end": new_order.time_end,
        "scheduled_datetime": new_order.scheduled_datetime.isoformat() if new_order.scheduled_datetime else None,
        "created_at": new_order.created_at.isoformat()
    }
    asyncio.create_task(manager.broadcast_to_all_drivers({
        "type": "new_order",
        "order": order_data_dict
    }))
    
    return new_order


@router.get("/", response_model=List[DeliveryOrderResponse])
def get_all_delivery_orders(
    status_filter: Optional[OrderStatus] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all delivery orders"""
    query = db.query(DeliveryOrder)
    
    if status_filter:
        query = query.filter(DeliveryOrder.status == status_filter)
    
    orders = query.order_by(DeliveryOrder.created_at.desc()).all()
    return orders


@router.get("/active", response_model=List[DeliveryOrderResponse])
def get_active_delivery_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get active delivery orders (pending or accepted)"""
    orders = db.query(DeliveryOrder).filter(
        DeliveryOrder.user_id == current_user.id,
        DeliveryOrder.status.in_([OrderStatus.PENDING, OrderStatus.ACCEPTED])
    ).order_by(DeliveryOrder.created_at.desc()).all()
    
    return orders


@router.get("/history", response_model=List[DeliveryOrderResponse])
def get_delivery_order_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get completed and cancelled delivery orders"""
    orders = db.query(DeliveryOrder).filter(
        DeliveryOrder.user_id == current_user.id,
        DeliveryOrder.status.in_([OrderStatus.COMPLETED, OrderStatus.CANCELLED])
    ).order_by(DeliveryOrder.completed_at.desc()).all()
    
    return orders


@router.get("/{order_id}", response_model=DeliveryOrderResponse)
def get_delivery_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get delivery order details"""
    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if user owns the order or is the assigned driver
    if order.user_id != current_user.id:
        if current_user.driver_profile and order.driver_id != current_user.driver_profile.id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this order"
            )
    
    return order


@router.delete("/{order_id}", status_code=status.HTTP_200_OK)
def delete_delivery_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a delivery order (only for cancelled or completed orders)"""
    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Allow order owner, admin, or superadmin to delete
    is_owner = order.user_id == current_user.id
    is_admin_or_superadmin = current_user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]
    
    if not (is_owner or is_admin_or_superadmin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this order"
        )
    
    # Only allow deleting cancelled or completed orders
    if order.status not in [OrderStatus.CANCELLED, OrderStatus.COMPLETED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only cancelled or completed orders can be deleted"
        )
    
    # Delete the order
    db.delete(order)
    db.commit()
    
    return {
        "message": "Order deleted successfully",
        "order_id": order_id
    }


@router.post("/bulk-delete", status_code=status.HTTP_200_OK)
def bulk_delete_delivery_orders(
    delete_request: BulkDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete multiple delivery orders at once (only for cancelled or completed orders)"""
    
    # Check if user is admin or superadmin
    is_admin_or_superadmin = current_user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]
    
    deleted_orders = []
    failed_orders = []
    
    for order_id in delete_request.order_ids:
        order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()
        
        if not order:
            failed_orders.append({
                "order_id": order_id,
                "reason": "Order not found"
            })
            continue
        
        # Allow order owner, admin, or superadmin to delete
        is_owner = order.user_id == current_user.id
        
        if not (is_owner or is_admin_or_superadmin):
            failed_orders.append({
                "order_id": order_id,
                "reason": "Not authorized to delete this order"
            })
            continue
        
        # Only allow deleting cancelled or completed orders
        if order.status not in [OrderStatus.CANCELLED, OrderStatus.COMPLETED]:
            failed_orders.append({
                "order_id": order_id,
                "reason": "Only cancelled or completed orders can be deleted"
            })
            continue
        
        # Delete the order
        db.delete(order)
        deleted_orders.append(order_id)
    
    db.commit()
    
    return {
        "message": f"Successfully deleted {len(deleted_orders)} order(s)",
        "deleted_orders": deleted_orders,
        "failed_orders": failed_orders,
        "total_requested": len(delete_request.order_ids),
        "total_deleted": len(deleted_orders),
        "total_failed": len(failed_orders)
    }


@router.delete("/delete-all", status_code=status.HTTP_200_OK)
def delete_all_delivery_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete all delivery orders (Admin/Superadmin only)"""
    
    # Only admin or superadmin can delete all orders
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete all orders"
        )
    
    # Get all delivery orders
    all_orders = db.query(DeliveryOrder).all()
    total_orders = len(all_orders)
    
    if total_orders == 0:
        return {
            "message": "No orders to delete",
            "total_deleted": 0
        }
    
    # Delete all orders
    db.query(DeliveryOrder).delete()
    db.commit()
    
    return {
        "message": f"Successfully deleted all delivery orders",
        "total_deleted": total_orders
    }


@router.post("/cancel", response_model=DeliveryOrderResponse)
def cancel_delivery_order(
    cancellation: OrderCancellation,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel a delivery order"""
    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == cancellation.order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this order"
        )
    
    if order.status not in [OrderStatus.PENDING, OrderStatus.ACCEPTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending or accepted orders can be cancelled"
        )
    
    # Update order status
    order.status = OrderStatus.CANCELLED
    order.cancellation_reason = cancellation.cancellation_reason
    order.cancelled_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(order)
    
    # Notify driver if order was accepted
    if order.driver_id:
        driver = db.query(Driver).filter(Driver.id == order.driver_id).first()
        if driver:
            create_notification(
                db=db,
                title="Order Cancelled",
                message=f"Delivery order #{order.id} has been cancelled. Reason: {cancellation.cancellation_reason}",
                notification_type="order_cancelled",
                driver_id=driver.id
            )
    
    # Notify user
    create_notification(
        db=db,
        title="Order Cancelled",
        message=f"Your delivery order #{order.id} has been cancelled successfully.",
        notification_type="order_cancelled",
        user_id=current_user.id
    )
    
    return order
