from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import Optional
from pydantic import BaseModel, Field
from app.database import get_db
from app.models import User, SystemSettings, UserRole
from app.auth import get_current_user

router = APIRouter(prefix="/api/settings", tags=["System Settings"])


class SeatVisibilityTimeoutUpdate(BaseModel):
    """Request model for updating seat visibility timeout"""
    minutes: int = Field(..., ge=1, le=120, description="Timeout in minutes (1-120)")


class SeatVisibilityTimeoutResponse(BaseModel):
    """Response model for seat visibility timeout"""
    setting_key: str
    minutes: int
    description: Optional[str] = None
    updated_at: Optional[str] = None


@router.get("/seat-visibility-timeout", response_model=SeatVisibilityTimeoutResponse)
async def get_seat_visibility_timeout(
    db: Session = Depends(get_db)
):
    """
    Get the current seat visibility timeout setting.
    
    This setting controls how long an order remains visible exclusively to a driver
    who has accepted another order on the same route before becoming visible to all drivers.
    
    Default: 15 minutes
    """
    setting = db.query(SystemSettings).filter(
        SystemSettings.setting_key == "seat_visibility_timeout_minutes"
    ).first()
    
    if not setting:
        # Return default
        return {
            "setting_key": "seat_visibility_timeout_minutes",
            "minutes": 15,
            "description": "Time in minutes before order becomes visible to all drivers (default)"
        }
    
    try:
        minutes = int(setting.setting_value)
    except (ValueError, TypeError):
        minutes = 15
    
    updated_at_str = None
    if setting.updated_at:
        updated_at_str = setting.updated_at.isoformat()
    
    return {
        "setting_key": setting.setting_key,
        "minutes": minutes,
        "description": setting.description,
        "updated_at": updated_at_str
    }


@router.put("/seat-visibility-timeout", response_model=SeatVisibilityTimeoutResponse)
async def update_seat_visibility_timeout(
    timeout_data: SeatVisibilityTimeoutUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Update the seat visibility timeout setting (Admin only).
    
    This setting controls how long an order remains visible exclusively to a driver
    who has accepted another order on the same route before becoming visible to all drivers.
    
    **Behavior:**
    - Before timeout: Order visible only to the original driver (who has an accepted order)
    - After timeout: Order becomes visible to all drivers
    
    **Parameters:**
    - minutes: Timeout duration in minutes (1-120)
    
    **Note:** Change applies immediately, no restart required.
    """
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update seat visibility timeout"
        )
    
    setting = db.query(SystemSettings).filter(
        SystemSettings.setting_key == "seat_visibility_timeout_minutes"
    ).first()
    
    if not setting:
        # Create new setting
        setting = SystemSettings(
            setting_key="seat_visibility_timeout_minutes",
            setting_value=str(timeout_data.minutes),
            description="Time in minutes before order becomes visible to all drivers",
            updated_by=current_user.id
        )
        db.add(setting)
    else:
        # Update existing setting
        setting.setting_value = str(timeout_data.minutes)
        setting.updated_by = current_user.id
    
    db.commit()
    db.refresh(setting)
    
    updated_at_str = None
    if setting.updated_at:
        updated_at_str = setting.updated_at.isoformat()
    
    return {
        "setting_key": setting.setting_key,
        "minutes": timeout_data.minutes,
        "description": setting.description,
        "updated_at": updated_at_str
    }
