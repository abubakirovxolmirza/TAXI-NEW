from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import and_, or_, func
from typing import List, Optional
from datetime import datetime, timedelta, timezone
from app.database import get_db
from app.models import User, TaxiOrder, OrderStatus, Driver
from app.schemas import TaxiOrderCreate, TaxiOrderResponse, OrderCancellation
from app.auth import get_current_user
from app.utils import calculate_taxi_price, notify_all_drivers, create_notification, calculate_service_fee
from app.websocket import manager, convert_decimal_to_float

router = APIRouter(prefix="/api/taxi-orders", tags=["Taxi Orders"])


@router.post("/", response_model=TaxiOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_taxi_order(
    order_data: TaxiOrderCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new taxi order"""
    # Calculate price
    price = calculate_taxi_price(
        db=db,
        from_region_id=order_data.from_region_id,
        to_region_id=order_data.to_region_id,
        passengers=order_data.passengers
    )
    
    # Calculate service fee and driver earnings
    service_fee, driver_earnings = calculate_service_fee(price, db)
    
    # Create order
    new_order = TaxiOrder(
        user_id=current_user.id,
        username=order_data.username,
        telephone=order_data.telephone,
        from_region_id=order_data.from_region_id,
        from_district_id=order_data.from_district_id,
        to_region_id=order_data.to_region_id,
        to_district_id=order_data.to_district_id,
        pickup_latitude=order_data.pickup_latitude,
        pickup_longitude=order_data.pickup_longitude,
        pickup_address=order_data.pickup_address,
        passengers=order_data.passengers,
        is_mail_delivery=order_data.is_mail_delivery,
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
        title="New Taxi Order",
        message=f"New taxi order from region {order_data.from_region_id} to {order_data.to_region_id}"
    )
    
    # Broadcast to all drivers via WebSocket
    import asyncio
    order_data_dict = {
        "id": new_order.id,
        "type": "taxi",
        "from_region_id": new_order.from_region_id,
        "to_region_id": new_order.to_region_id,
        "passengers": new_order.passengers,
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


@router.get("/", response_model=List[TaxiOrderResponse])
def get_all_taxi_orders(
    status_filter: Optional[OrderStatus] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all taxi orders"""
    query = db.query(TaxiOrder)
    
    if status_filter:
        query = query.filter(TaxiOrder.status == status_filter)
    
    orders = query.order_by(TaxiOrder.created_at.desc()).all()
    return orders


@router.get("/active", response_model=List[TaxiOrderResponse])
def get_active_taxi_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get active taxi orders (pending or accepted)"""
    orders = db.query(TaxiOrder).filter(
        TaxiOrder.user_id == current_user.id,
        TaxiOrder.status.in_([OrderStatus.PENDING, OrderStatus.ACCEPTED])
    ).order_by(TaxiOrder.created_at.desc()).all()
    
    return orders


@router.get("/history", response_model=List[TaxiOrderResponse])
def get_taxi_order_history(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get completed and cancelled taxi orders"""
    orders = db.query(TaxiOrder).filter(
        TaxiOrder.user_id == current_user.id,
        TaxiOrder.status.in_([OrderStatus.COMPLETED, OrderStatus.CANCELLED])
    ).order_by(TaxiOrder.completed_at.desc()).all()
    
    return orders


@router.get("/{order_id}", response_model=TaxiOrderResponse)
def get_taxi_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get taxi order details"""
    order = db.query(TaxiOrder).filter(TaxiOrder.id == order_id).first()
    
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


@router.post("/cancel", response_model=TaxiOrderResponse)
def cancel_taxi_order(
    cancellation: OrderCancellation,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel a taxi order"""
    order = db.query(TaxiOrder).filter(TaxiOrder.id == cancellation.order_id).first()
    
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
                message=f"Taxi order #{order.id} has been cancelled. Reason: {cancellation.cancellation_reason}",
                notification_type="order_cancelled",
                driver_id=driver.id
            )
            
            # Process refund (add balance back to driver if needed)
            # This would be implemented based on your business logic
    
    # Notify user
    create_notification(
        db=db,
        title="Order Cancelled",
        message=f"Your taxi order #{order.id} has been cancelled successfully.",
        notification_type="order_cancelled",
        user_id=current_user.id
    )
    
    return order
