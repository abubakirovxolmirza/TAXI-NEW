from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User, Bonus, UserRole
from app.schemas import BonusCreate, BonusUpdate, BonusResponse
from app.auth import get_current_user

router = APIRouter(prefix="/api/bonuses", tags=["Bonuses"])


@router.post("/", response_model=BonusResponse, status_code=status.HTTP_201_CREATED)
async def create_bonus(
    bonus_data: BonusCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new bonus configuration (Admin only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create bonus configurations"
        )
    
    bonus = Bonus(
        bonus_percent=bonus_data.bonus_percent,
        description=bonus_data.description,
        is_active=bonus_data.is_active
    )
    db.add(bonus)
    db.commit()
    db.refresh(bonus)
    
    return bonus


@router.get("/", response_model=List[BonusResponse])
async def get_all_bonuses(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all bonus configurations (Admin only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view bonus configurations"
        )
    
    bonuses = db.query(Bonus).offset(skip).limit(limit).all()
    return bonuses


@router.get("/active", response_model=BonusResponse)
async def get_active_bonus(
    db: Session = Depends(get_db)
):
    """Get the active bonus configuration (Public endpoint)"""
    bonus = db.query(Bonus).filter(Bonus.is_active == True).first()
    
    if not bonus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active bonus configuration found"
        )
    
    return bonus


@router.get("/{bonus_id}", response_model=BonusResponse)
async def get_bonus(
    bonus_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific bonus configuration (Admin only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view bonus configurations"
        )
    
    bonus = db.query(Bonus).filter(Bonus.id == bonus_id).first()
    
    if not bonus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bonus configuration not found"
        )
    
    return bonus


@router.put("/{bonus_id}", response_model=BonusResponse)
async def update_bonus(
    bonus_id: int,
    bonus_data: BonusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a bonus configuration (Admin only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update bonus configurations"
        )
    
    bonus = db.query(Bonus).filter(Bonus.id == bonus_id).first()
    
    if not bonus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bonus configuration not found"
        )
    
    # Update fields if provided
    if bonus_data.bonus_percent is not None:
        bonus.bonus_percent = bonus_data.bonus_percent
    if bonus_data.description is not None:
        bonus.description = bonus_data.description
    if bonus_data.is_active is not None:
        bonus.is_active = bonus_data.is_active
    
    db.commit()
    db.refresh(bonus)
    
    return bonus


@router.delete("/{bonus_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_bonus(
    bonus_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a bonus configuration (Admin only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete bonus configurations"
        )
    
    bonus = db.query(Bonus).filter(Bonus.id == bonus_id).first()
    
    if not bonus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bonus configuration not found"
        )
    
    db.delete(bonus)
    db.commit()
    
    return None
