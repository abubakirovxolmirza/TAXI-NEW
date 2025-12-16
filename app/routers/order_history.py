from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import List, Optional
from app.database import get_db
from app.models import User, OrderAcceptanceHistory, UserRole
from app.schemas import OrderAcceptanceHistoryResponse
from app.auth import get_current_user

router = APIRouter(prefix="/api/order-acceptance-history", tags=["Order Acceptance History"])


@router.get("/", response_model=List[OrderAcceptanceHistoryResponse])
async def get_history(
    driver_id: Optional[int] = None,
    order_type: Optional[str] = None,  # "taxi" or "delivery"
    order_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get order acceptance history across all orders (Admin only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view order acceptance history"
        )

    query = db.query(OrderAcceptanceHistory)

    if driver_id:
        query = query.filter(OrderAcceptanceHistory.driver_id == driver_id)

    if order_type == "taxi":
        query = query.filter(OrderAcceptanceHistory.taxi_order_id.isnot(None))
        if order_id:
            query = query.filter(OrderAcceptanceHistory.taxi_order_id == order_id)
    elif order_type == "delivery":
        query = query.filter(OrderAcceptanceHistory.delivery_order_id.isnot(None))
        if order_id:
            query = query.filter(OrderAcceptanceHistory.delivery_order_id == order_id)
    elif order_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order_type. Must be 'taxi' or 'delivery'"
        )
    elif order_id:
        # If order_id provided without type, match either taxi or delivery entries
        query = query.filter(
            or_(
                OrderAcceptanceHistory.taxi_order_id == order_id,
                OrderAcceptanceHistory.delivery_order_id == order_id,
            )
        )

    history = query.order_by(OrderAcceptanceHistory.created_at.desc()).all()
    return history


@router.get("/driver/{driver_id}", response_model=List[OrderAcceptanceHistoryResponse])
async def get_driver_history(
    driver_id: int,
    order_type: Optional[str] = None,  # "taxi" or "delivery"
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get order acceptance history for a specific driver (Admin only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view order acceptance history"
        )
    
    query = db.query(OrderAcceptanceHistory).filter(
        OrderAcceptanceHistory.driver_id == driver_id
    )
    
    if order_type == "taxi":
        query = query.filter(OrderAcceptanceHistory.taxi_order_id.isnot(None))
    elif order_type == "delivery":
        query = query.filter(OrderAcceptanceHistory.delivery_order_id.isnot(None))
    
    history = query.order_by(OrderAcceptanceHistory.created_at.desc()).all()
    
    return history


@router.get("/order/taxi/{order_id}", response_model=List[OrderAcceptanceHistoryResponse])
async def get_taxi_order_history(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all drivers who received a specific taxi order (Admin only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view order acceptance history"
        )
    
    history = db.query(OrderAcceptanceHistory).filter(
        OrderAcceptanceHistory.taxi_order_id == order_id
    ).order_by(OrderAcceptanceHistory.created_at.desc()).all()
    
    return history


@router.get("/order/delivery/{order_id}", response_model=List[OrderAcceptanceHistoryResponse])
async def get_delivery_order_history(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all drivers who received a specific delivery order (Admin only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view order acceptance history"
        )
    
    history = db.query(OrderAcceptanceHistory).filter(
        OrderAcceptanceHistory.delivery_order_id == order_id
    ).order_by(OrderAcceptanceHistory.created_at.desc()).all()
    
    return history
