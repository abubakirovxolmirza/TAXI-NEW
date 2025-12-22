from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List
from app.database import get_db
from app.models import Permission, User
from app.schemas import PermissionCreate, PermissionResponse, PermissionUpdate
from app.auth import get_current_admin

router = APIRouter(prefix="/api/permissions", tags=["Permissions"])


@router.post("/", response_model=PermissionResponse, status_code=status.HTTP_201_CREATED)
def create_permission(
    permission_data: PermissionCreate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Create permissions for a user (Admin only)."""
    user = db.query(User).filter(User.id == permission_data.user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    existing = db.query(Permission).filter(Permission.user_id == permission_data.user_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Permissions already exist for this user",
        )

    permission = Permission(**permission_data.dict())
    db.add(permission)
    db.commit()
    db.refresh(permission)
    return permission


@router.get("/", response_model=List[PermissionResponse])
def list_permissions(
    skip: int = 0,
    limit: int = 100,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """List all permissions (Admin only)."""
    return db.query(Permission).offset(skip).limit(limit).all()


@router.get("/user/{user_id}", response_model=PermissionResponse)
def get_permission_for_user(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get permissions for a specific user (Admin only)."""
    permission = db.query(Permission).filter(Permission.user_id == user_id).first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permissions not found for this user",
        )
    return permission


@router.get("/{permission_id}", response_model=PermissionResponse)
def get_permission(
    permission_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get a permission record by id (Admin only)."""
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permissions not found",
        )
    return permission


@router.put("/{permission_id}", response_model=PermissionResponse)
def update_permission(
    permission_id: int,
    permission_data: PermissionUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Update a permission record (Admin only)."""
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permissions not found",
        )

    update_data = permission_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(permission, key, value)

    db.commit()
    db.refresh(permission)
    return permission


@router.delete("/{permission_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_permission(
    permission_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Delete a permission record (Admin only)."""
    permission = db.query(Permission).filter(Permission.id == permission_id).first()
    if not permission:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Permissions not found",
        )

    db.delete(permission)
    db.commit()
    return None
