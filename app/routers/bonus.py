from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import User, UserRole, Bonus
from app.schemas import BonusCreate, BonusUpdate, BonusResponse
from app.auth import get_current_user

router = APIRouter(prefix="/api/bonus", tags=["Bonus"])


@router.post("/", response_model=BonusResponse, status_code=status.HTTP_201_CREATED)
def create_bonus(
    bonus_data: BonusCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Create a new bonus percentage record (Admin/Superadmin only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can create bonus records"
        )
    
    new_bonus = Bonus(
        bonus_percent=bonus_data.bonus_percent,
        description=bonus_data.description,
        is_active=True
    )
    
    db.add(new_bonus)
    db.commit()
    db.refresh(new_bonus)
    
    return new_bonus


@router.get("/", response_model=List[BonusResponse])
def get_all_bonuses(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all bonus records (Admin/Superadmin only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view bonus records"
        )
    
    bonuses = db.query(Bonus).order_by(Bonus.created_at.desc()).all()
    return bonuses


@router.get("/active", response_model=BonusResponse)
def get_active_bonus(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get the active bonus percentage"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view bonus records"
        )
    
    bonus = db.query(Bonus).filter(Bonus.is_active == True).first()
    
    if not bonus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active bonus found"
        )
    
    return bonus


@router.get("/{bonus_id}", response_model=BonusResponse)
def get_bonus(
    bonus_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get a specific bonus record (Admin/Superadmin only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view bonus records"
        )
    
    bonus = db.query(Bonus).filter(Bonus.id == bonus_id).first()
    
    if not bonus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bonus not found"
        )
    
    return bonus


@router.put("/{bonus_id}", response_model=BonusResponse)
def update_bonus(
    bonus_id: int,
    bonus_update: BonusUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Update a bonus record (Admin/Superadmin only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can update bonus records"
        )
    
    bonus = db.query(Bonus).filter(Bonus.id == bonus_id).first()
    
    if not bonus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bonus not found"
        )
    
    if bonus_update.bonus_percent is not None:
        bonus.bonus_percent = bonus_update.bonus_percent
    
    if bonus_update.description is not None:
        bonus.description = bonus_update.description
    
    if bonus_update.is_active is not None:
        bonus.is_active = bonus_update.is_active
    
    db.commit()
    db.refresh(bonus)
    
    return bonus


@router.delete("/{bonus_id}", status_code=status.HTTP_200_OK)
def delete_bonus(
    bonus_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a bonus record (Admin/Superadmin only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete bonus records"
        )
    
    bonus = db.query(Bonus).filter(Bonus.id == bonus_id).first()
    
    if not bonus:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Bonus not found"
        )
    
    db.delete(bonus)
    db.commit()
    
    return {"message": "Bonus deleted successfully", "id": bonus_id}
