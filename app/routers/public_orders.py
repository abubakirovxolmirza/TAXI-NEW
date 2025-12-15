from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User, TaxiOrder, DeliveryOrder, OrderStatus, Driver
from app.schemas import TaxiOrderResponse, DeliveryOrderResponse
from app.auth import get_current_user

router = APIRouter(prefix="/api/public-orders", tags=["Public Orders"])


@router.get("/taxi", response_model=List[TaxiOrderResponse])
async def get_public_taxi_orders(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all public taxi orders (available to all drivers)"""
    # Check if user is a driver
    if not current_user.driver_profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can view public orders"
        )
    
    # Get all pending orders that are marked as public
    orders = db.query(TaxiOrder).filter(
        TaxiOrder.status == OrderStatus.PENDING,
        TaxiOrder.public_order == True
    ).order_by(TaxiOrder.created_at.desc()).offset(skip).limit(limit).all()
    
    return orders


@router.get("/delivery", response_model=List[DeliveryOrderResponse])
async def get_public_delivery_orders(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all public delivery orders (available to all drivers)"""
    # Check if user is a driver
    if not current_user.driver_profile:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only drivers can view public orders"
        )
    
    # Get all pending orders that are marked as public
    orders = db.query(DeliveryOrder).filter(
        DeliveryOrder.status == OrderStatus.PENDING,
        DeliveryOrder.public_order == True
    ).order_by(DeliveryOrder.created_at.desc()).offset(skip).limit(limit).all()
    
    return orders


@router.post("/taxi/{order_id}/make-public")
async def make_taxi_order_public(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually make a taxi order public (Admin only or automatic after pending_time)"""
    # Only admins can manually make orders public
    # In production, this would typically be called by a background task
    from app.models import UserRole
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can manually make orders public"
        )
    
    order = db.query(TaxiOrder).filter(TaxiOrder.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taxi order not found"
        )
    
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending orders can be made public"
        )
    
    order.public_order = True
    db.commit()
    db.refresh(order)
    
    # Broadcast to all drivers
    from app.websocket import manager
    import asyncio
    
    order_data_dict = {
        "id": order.id,
        "type": "taxi",
        "public_order": True,
        "from_region_id": order.from_region_id,
        "to_region_id": order.to_region_id,
        "passengers": order.passengers,
        "price": float(order.price),
        "driver_earnings": float(order.driver_earnings),
    }
    
    asyncio.create_task(manager.broadcast_to_all_drivers({
        "type": "order_now_public",
        "order": order_data_dict
    }))
    
    return {
        "message": "Order is now public",
        "order_id": order.id,
        "public_order": order.public_order
    }


@router.post("/delivery/{order_id}/make-public")
async def make_delivery_order_public(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Manually make a delivery order public (Admin only or automatic after pending_time)"""
    from app.models import UserRole
    
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can manually make orders public"
        )
    
    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery order not found"
        )
    
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending orders can be made public"
        )
    
    order.public_order = True
    db.commit()
    db.refresh(order)
    
    # Broadcast to all drivers
    from app.websocket import manager
    import asyncio
    
    order_data_dict = {
        "id": order.id,
        "type": "delivery",
        "public_order": True,
        "from_region_id": order.from_region_id,
        "to_region_id": order.to_region_id,
        "price": float(order.price),
        "driver_earnings": float(order.driver_earnings),
    }
    
    asyncio.create_task(manager.broadcast_to_all_drivers({
        "type": "order_now_public",
        "order": order_data_dict
    }))
    
    return {
        "message": "Order is now public",
        "order_id": order.id,
        "public_order": order.public_order
    }
