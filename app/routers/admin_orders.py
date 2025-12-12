from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List, Optional
from datetime import datetime, timezone
from app.database import get_db
from app.models import (
    User, TaxiOrder, DeliveryOrder, OrderStatus, 
    Driver, Region, District
)
from app.schemas import (
    TaxiOrderResponse, TaxiOrderUpdate,
    DeliveryOrderResponse, DeliveryOrderUpdate,
    OrderCancellation
)
from app.auth import get_current_admin
from app.utils import create_notification, apply_service_fee_refund

router = APIRouter(prefix="/api/admin/orders", tags=["Admin - Orders"])


# Taxi Orders Management
@router.get("/taxi", response_model=List[TaxiOrderResponse])
def get_all_taxi_orders(
    status: Optional[OrderStatus] = None,
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all taxi orders with optional filtering (Admin only)"""
    query = db.query(TaxiOrder).order_by(TaxiOrder.created_at.desc())
    
    if status:
        query = query.filter(TaxiOrder.status == status)
    
    orders = query.limit(limit).offset(offset).all()
    return orders


@router.get("/taxi/{order_id}", response_model=TaxiOrderResponse)
def get_taxi_order_details(
    order_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific taxi order (Admin only)"""
    order = db.query(TaxiOrder).filter(TaxiOrder.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taxi order not found"
        )
    
    return order


@router.put("/taxi/{order_id}", response_model=TaxiOrderResponse)
def update_taxi_order(
    order_id: int,
    order_data: TaxiOrderUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update a taxi order (Admin only)"""
    order = db.query(TaxiOrder).filter(TaxiOrder.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taxi order not found"
        )
    
    # Update fields
    update_data = order_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(order, key, value)
    
    order.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(order)
    
    # Notify user about update
    create_notification(
        db=db,
        title="Order Updated",
        message=f"Your taxi order #{order.id} has been updated by admin.",
        notification_type="order_updated",
        user_id=order.user_id
    )
    
    # Notify driver if assigned
    if order.driver_id:
        create_notification(
            db=db,
            title="Order Updated",
            message=f"Taxi order #{order.id} has been updated by admin.",
            notification_type="order_updated",
            driver_id=order.driver_id
        )
    
    return order


@router.post("/taxi/{order_id}/cancel")
def cancel_taxi_order_admin(
    order_id: int,
    cancellation_data: OrderCancellation,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Cancel a taxi order (Admin only)"""
    order = db.query(TaxiOrder).filter(TaxiOrder.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taxi order not found"
        )
    
    if order.status == OrderStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is already cancelled"
        )
    
    if order.status == OrderStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel a completed order"
        )
    
    # Handle refund if order was accepted
    if order.status == OrderStatus.ACCEPTED and order.driver_id:
        apply_service_fee_refund(db, order.driver_id, order.service_fee)
    
    order.status = OrderStatus.CANCELLED
    order.cancellation_reason = cancellation_data.cancellation_reason + " (Admin cancelled)"
    order.cancelled_at = datetime.now(timezone.utc)
    
    db.commit()
    
    # Notify user
    create_notification(
        db=db,
        title="Order Cancelled",
        message=f"Your taxi order #{order.id} has been cancelled by admin. Reason: {cancellation_data.cancellation_reason}",
        notification_type="order_cancelled",
        user_id=order.user_id
    )
    
    # Notify driver if assigned
    if order.driver_id:
        create_notification(
            db=db,
            title="Order Cancelled",
            message=f"Taxi order #{order.id} has been cancelled by admin.",
            notification_type="order_cancelled",
            driver_id=order.driver_id
        )
    
    return {"success": True, "message": "Order cancelled successfully"}


@router.delete("/taxi/{order_id}")
def delete_taxi_order(
    order_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Permanently delete a taxi order (Admin only) - USE WITH CAUTION"""
    order = db.query(TaxiOrder).filter(TaxiOrder.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taxi order not found"
        )
    
    # Only allow deletion of cancelled orders
    if order.status != OrderStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only delete cancelled orders. Please cancel the order first."
        )
    
    db.delete(order)
    db.commit()
    
    return {"success": True, "message": f"Taxi order #{order_id} deleted permanently"}


# Delivery Orders Management
@router.get("/delivery", response_model=List[DeliveryOrderResponse])
def get_all_delivery_orders(
    status: Optional[OrderStatus] = None,
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all delivery orders with optional filtering (Admin only)"""
    query = db.query(DeliveryOrder).order_by(DeliveryOrder.created_at.desc())
    
    if status:
        query = query.filter(DeliveryOrder.status == status)
    
    orders = query.limit(limit).offset(offset).all()
    return orders


@router.get("/delivery/{order_id}", response_model=DeliveryOrderResponse)
def get_delivery_order_details(
    order_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get detailed information about a specific delivery order (Admin only)"""
    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery order not found"
        )
    
    return order


@router.put("/delivery/{order_id}", response_model=DeliveryOrderResponse)
def update_delivery_order(
    order_id: int,
    order_data: DeliveryOrderUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update a delivery order (Admin only)"""
    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery order not found"
        )
    
    # Update fields
    update_data = order_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(order, key, value)
    
    order.updated_at = datetime.now(timezone.utc)
    
    db.commit()
    db.refresh(order)
    
    # Notify user about update
    create_notification(
        db=db,
        title="Order Updated",
        message=f"Your delivery order #{order.id} has been updated by admin.",
        notification_type="order_updated",
        user_id=order.user_id
    )
    
    # Notify driver if assigned
    if order.driver_id:
        create_notification(
            db=db,
            title="Order Updated",
            message=f"Delivery order #{order.id} has been updated by admin.",
            notification_type="order_updated",
            driver_id=order.driver_id
        )
    
    return order


@router.post("/delivery/{order_id}/cancel")
def cancel_delivery_order_admin(
    order_id: int,
    cancellation_data: OrderCancellation,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Cancel a delivery order (Admin only)"""
    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery order not found"
        )
    
    if order.status == OrderStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is already cancelled"
        )
    
    if order.status == OrderStatus.COMPLETED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel a completed order"
        )
    
    # Handle refund if order was accepted
    if order.status == OrderStatus.ACCEPTED and order.driver_id:
        apply_service_fee_refund(db, order.driver_id, order.service_fee)
    
    order.status = OrderStatus.CANCELLED
    order.cancellation_reason = cancellation_data.cancellation_reason + " (Admin cancelled)"
    order.cancelled_at = datetime.now(timezone.utc)
    
    db.commit()
    
    # Notify user
    create_notification(
        db=db,
        title="Order Cancelled",
        message=f"Your delivery order #{order.id} has been cancelled by admin. Reason: {cancellation_data.cancellation_reason}",
        notification_type="order_cancelled",
        user_id=order.user_id
    )
    
    # Notify driver if assigned
    if order.driver_id:
        create_notification(
            db=db,
            title="Order Cancelled",
            message=f"Delivery order #{order.id} has been cancelled by admin.",
            notification_type="order_cancelled",
            driver_id=order.driver_id
        )
    
    return {"success": True, "message": "Order cancelled successfully"}


@router.delete("/delivery/{order_id}")
def delete_delivery_order(
    order_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Permanently delete a delivery order (Admin only) - USE WITH CAUTION"""
    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery order not found"
        )
    
    # Only allow deletion of cancelled orders
    if order.status != OrderStatus.CANCELLED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Can only delete cancelled orders. Please cancel the order first."
        )
    
    db.delete(order)
    db.commit()
    
    return {"success": True, "message": f"Delivery order #{order_id} deleted permanently"}
