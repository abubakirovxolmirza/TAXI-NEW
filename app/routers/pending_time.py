from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User, SystemSettings, TaxiOrder, DeliveryOrder, UserRole, OrderStatus
from app.schemas import PendingTimeUpdate, TaxiOrderResponse, DeliveryOrderResponse
from app.auth import get_current_user

router = APIRouter(prefix="/api/pending-time", tags=["Pending Time Management"])


@router.get("/")
async def get_pending_time_setting(
    db: Session = Depends(get_db)
):
    """Get the current pending time setting"""
    setting = db.query(SystemSettings).filter(
        SystemSettings.setting_key == "public_order_pending_time"
    ).first()
    
    if not setting:
        # Return default
        return {
            "setting_key": "public_order_pending_time",
            "setting_value": "15",
            "description": "Time in minutes before order becomes public (default)"
        }
    
    return {
        "setting_key": setting.setting_key,
        "setting_value": setting.setting_value,
        "description": setting.description,
        "updated_at": setting.updated_at
    }


@router.put("/")
async def update_pending_time_setting(
    pending_time_data: PendingTimeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update the global pending time setting (Admin only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update pending time settings"
        )
    
    setting = db.query(SystemSettings).filter(
        SystemSettings.setting_key == "public_order_pending_time"
    ).first()
    
    if not setting:
        # Create new setting
        setting = SystemSettings(
            setting_key="public_order_pending_time",
            setting_value=str(pending_time_data.pending_time),
            description="Time in minutes before order becomes public",
            updated_by=current_user.id
        )
        db.add(setting)
    else:
        # Update existing setting
        setting.setting_value = str(pending_time_data.pending_time)
        setting.updated_by = current_user.id
    
    db.commit()
    db.refresh(setting)
    
    return {
        "message": "Pending time updated successfully",
        "setting_key": setting.setting_key,
        "setting_value": setting.setting_value,
        "updated_at": setting.updated_at
    }


@router.put("/taxi/{order_id}")
async def update_taxi_order_pending_time(
    order_id: int,
    pending_time_data: PendingTimeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update pending time for a specific taxi order (Admin only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update order pending time"
        )
    
    order = db.query(TaxiOrder).filter(TaxiOrder.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Taxi order not found"
        )
    
    order.pending_time = pending_time_data.pending_time
    db.commit()
    db.refresh(order)
    
    return {
        "message": "Order pending time updated successfully",
        "order_id": order.id,
        "pending_time": order.pending_time
    }


@router.put("/delivery/{order_id}")
async def update_delivery_order_pending_time(
    order_id: int,
    pending_time_data: PendingTimeUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update pending time for a specific delivery order (Admin only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update order pending time"
        )
    
    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Delivery order not found"
        )
    
    order.pending_time = pending_time_data.pending_time
    db.commit()
    db.refresh(order)
    
    return {
        "message": "Order pending time updated successfully",
        "order_id": order.id,
        "pending_time": order.pending_time
    }
