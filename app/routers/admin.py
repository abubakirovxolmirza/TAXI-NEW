from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func, extract
from typing import List
from datetime import datetime, date
from decimal import Decimal
from app.database import get_db
from app.models import (
    User, Driver, DriverApplication, ApplicationStatus, UserRole,
    TaxiOrder, DeliveryOrder, OrderStatus, Pricing, BalanceTransaction,
    Notification, Feedback
)
from app.schemas import (
    DriverApplicationResponse, DriverApplicationReview,
    DriverResponse, PricingCreate, PricingUpdate, PricingResponse,
    BalanceAdd, BalanceTransactionResponse, BroadcastMessage,
    FeedbackResponse, UserResponse, UserRoleUpdate
)
from app.auth import get_current_admin, get_current_superadmin
from app.utils import create_notification

router = APIRouter(prefix="/api/admin", tags=["Admin"])


@router.get("/driver-applications", response_model=List[DriverApplicationResponse])
def get_pending_applications(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all pending driver applications"""
    applications = db.query(DriverApplication).filter(
        DriverApplication.status == ApplicationStatus.PENDING
    ).order_by(DriverApplication.created_at.desc()).all()
    
    return applications


@router.post("/driver-applications/review")
def review_application(
    review_data: DriverApplicationReview,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Approve or reject a driver application"""
    application = db.query(DriverApplication).filter(
        DriverApplication.id == review_data.application_id
    ).first()
    
    if not application:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Application not found"
        )
    
    if application.status != ApplicationStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Application has already been reviewed"
        )
    
    if review_data.approved:
        # Approve application and create driver profile
        application.status = ApplicationStatus.APPROVED
        
        new_driver = Driver(
            user_id=application.user_id,
            full_name=application.full_name,
            car_model=application.car_model,
            car_number=application.car_number,
            license_photo=application.license_photo
        )
        
        db.add(new_driver)
        
        # Update user role to driver
        user = db.query(User).filter(User.id == application.user_id).first()
        if user:
            user.role = UserRole.DRIVER
        
        # Notify user
        create_notification(
            db=db,
            title="Application Approved",
            message="Congratulations! Your driver application has been approved.",
            notification_type="application_approved",
            user_id=application.user_id
        )
    else:
        # Reject application
        application.status = ApplicationStatus.REJECTED
        application.rejection_reason = review_data.rejection_reason
        
        # Notify user
        create_notification(
            db=db,
            title="Application Rejected",
            message=f"Your driver application has been rejected. Reason: {review_data.rejection_reason}",
            notification_type="application_rejected",
            user_id=application.user_id
        )
    
    application.reviewed_by = current_user.id
    application.reviewed_at = datetime.utcnow()
    
    db.commit()
    
    return {
        "success": True,
        "message": "Application reviewed successfully",
        "status": application.status
    }


@router.get("/users", response_model=List[UserResponse])
def get_all_users(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all users"""
    users = db.query(User).order_by(User.created_at.desc()).all()
    return users


@router.get("/drivers", response_model=List[DriverResponse])
def get_all_drivers(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all drivers"""
    drivers = db.query(Driver).all()
    return drivers


@router.post("/drivers/{driver_id}/block")
def block_driver(
    driver_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Block a driver"""
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found"
        )
    
    driver.is_blocked = True
    db.commit()
    
    # Notify driver
    create_notification(
        db=db,
        title="Account Blocked",
        message="Your driver account has been blocked by admin.",
        notification_type="account_blocked",
        driver_id=driver_id
    )
    
    return {"success": True, "message": "Driver blocked successfully"}


@router.post("/drivers/{driver_id}/unblock")
def unblock_driver(
    driver_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Unblock a driver"""
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found"
        )
    
    driver.is_blocked = False
    db.commit()
    
    # Notify driver
    create_notification(
        db=db,
        title="Account Unblocked",
        message="Your driver account has been unblocked.",
        notification_type="account_unblocked",
        driver_id=driver_id
    )
    
    return {"success": True, "message": "Driver unblocked successfully"}


@router.post("/drivers/balance/add", response_model=BalanceTransactionResponse)
def add_driver_balance(
    balance_data: BalanceAdd,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Add balance to driver account"""
    driver = db.query(Driver).filter(Driver.id == balance_data.driver_id).first()
    
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found"
        )
    
    # Update driver balance
    driver.balance += balance_data.amount
    
    # Create transaction record
    transaction = BalanceTransaction(
        driver_id=balance_data.driver_id,
        amount=balance_data.amount,
        transaction_type="credit",
        description=balance_data.description,
        admin_id=current_user.id
    )
    
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    
    # Notify driver
    create_notification(
        db=db,
        title="Balance Added",
        message=f"Your balance has been credited with {balance_data.amount}",
        notification_type="balance_added",
        driver_id=balance_data.driver_id
    )
    
    return transaction


@router.post("/pricing", response_model=PricingResponse, status_code=status.HTTP_201_CREATED)
def create_pricing(
    pricing_data: PricingCreate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Create pricing for a route"""
    # Check if pricing already exists
    existing = db.query(Pricing).filter(
        Pricing.from_region_id == pricing_data.from_region_id,
        Pricing.to_region_id == pricing_data.to_region_id,
        Pricing.service_type == pricing_data.service_type,
        Pricing.is_active == True
    ).first()
    
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Pricing for this route already exists"
        )
    
    new_pricing = Pricing(**pricing_data.dict())
    db.add(new_pricing)
    db.commit()
    db.refresh(new_pricing)
    
    return new_pricing


@router.put("/pricing/{pricing_id}", response_model=PricingResponse)
def update_pricing(
    pricing_id: int,
    pricing_data: PricingUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update pricing"""
    pricing = db.query(Pricing).filter(Pricing.id == pricing_id).first()
    
    if not pricing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pricing not found"
        )
    
    update_data = pricing_data.dict(exclude_unset=True)
    for key, value in update_data.items():
        setattr(pricing, key, value)
    
    db.commit()
    db.refresh(pricing)
    
    return pricing


@router.get("/pricing", response_model=List[PricingResponse])
def get_all_pricing(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all pricing configurations"""
    pricing = db.query(Pricing).filter(Pricing.is_active == True).all()
    return pricing


@router.post("/broadcast")
def broadcast_message(
    message_data: BroadcastMessage,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Broadcast message to users or drivers"""
    if message_data.target == "users":
        users = db.query(User).filter(User.is_active == True).all()
        for user in users:
            create_notification(
                db=db,
                title=message_data.title,
                message=message_data.message,
                notification_type="broadcast",
                user_id=user.id
            )
    elif message_data.target == "drivers":
        drivers = db.query(Driver).filter(Driver.is_blocked == False).all()
        for driver in drivers:
            create_notification(
                db=db,
                title=message_data.title,
                message=message_data.message,
                notification_type="broadcast",
                driver_id=driver.id
            )
    elif message_data.target == "all":
        users = db.query(User).filter(User.is_active == True).all()
        for user in users:
            create_notification(
                db=db,
                title=message_data.title,
                message=message_data.message,
                notification_type="broadcast",
                user_id=user.id
            )
        drivers = db.query(Driver).filter(Driver.is_blocked == False).all()
        for driver in drivers:
            create_notification(
                db=db,
                title=message_data.title,
                message=message_data.message,
                notification_type="broadcast",
                driver_id=driver.id
            )
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid target. Must be 'users', 'drivers', or 'all'"
        )
    
    return {"success": True, "message": "Message broadcasted successfully"}


@router.get("/orders/statistics")
def get_order_statistics(
    period: str = "daily",  # daily, monthly, yearly
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get order statistics"""
    today = datetime.utcnow().date()
    
    if period == "daily":
        start_date = today
    elif period == "monthly":
        start_date = today.replace(day=1)
    elif period == "yearly":
        start_date = today.replace(month=1, day=1)
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid period. Must be 'daily', 'monthly', or 'yearly'"
        )
    
    # Taxi orders
    taxi_stats = db.query(
        func.count(TaxiOrder.id).label('total'),
        func.count(func.nullif(TaxiOrder.status == OrderStatus.PENDING, False)).label('pending'),
        func.count(func.nullif(TaxiOrder.status == OrderStatus.ACCEPTED, False)).label('accepted'),
        func.count(func.nullif(TaxiOrder.status == OrderStatus.COMPLETED, False)).label('completed'),
        func.count(func.nullif(TaxiOrder.status == OrderStatus.CANCELLED, False)).label('cancelled'),
        func.coalesce(func.sum(TaxiOrder.price), 0).label('revenue')
    ).filter(
        func.date(TaxiOrder.created_at) >= start_date
    ).first()
    
    # Delivery orders
    delivery_stats = db.query(
        func.count(DeliveryOrder.id).label('total'),
        func.count(func.nullif(DeliveryOrder.status == OrderStatus.PENDING, False)).label('pending'),
        func.count(func.nullif(DeliveryOrder.status == OrderStatus.ACCEPTED, False)).label('accepted'),
        func.count(func.nullif(DeliveryOrder.status == OrderStatus.COMPLETED, False)).label('completed'),
        func.count(func.nullif(DeliveryOrder.status == OrderStatus.CANCELLED, False)).label('cancelled'),
        func.coalesce(func.sum(DeliveryOrder.price), 0).label('revenue')
    ).filter(
        func.date(DeliveryOrder.created_at) >= start_date
    ).first()
    
    return {
        "period": period,
        "taxi_orders": {
            "total": taxi_stats.total or 0,
            "pending": taxi_stats.pending or 0,
            "accepted": taxi_stats.accepted or 0,
            "completed": taxi_stats.completed or 0,
            "cancelled": taxi_stats.cancelled or 0,
            "revenue": str(taxi_stats.revenue or 0)
        },
        "delivery_orders": {
            "total": delivery_stats.total or 0,
            "pending": delivery_stats.pending or 0,
            "accepted": delivery_stats.accepted or 0,
            "completed": delivery_stats.completed or 0,
            "cancelled": delivery_stats.cancelled or 0,
            "revenue": str(delivery_stats.revenue or 0)
        }
    }


@router.get("/feedback", response_model=List[FeedbackResponse])
def get_feedback(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all feedback"""
    feedback = db.query(Feedback).order_by(Feedback.created_at.desc()).all()
    return feedback


@router.post("/users/add-admin", response_model=UserResponse)
def add_admin(
    user_id: int,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db)
):
    """Add admin (superadmin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.role = UserRole.ADMIN
    db.commit()
    db.refresh(user)
    
    # Notify user
    create_notification(
        db=db,
        title="Admin Access Granted",
        message="You have been granted admin privileges.",
        notification_type="role_updated",
        user_id=user_id
    )
    
    return user


@router.post("/users/update-role", response_model=UserResponse)
def update_user_role(
    role_data: UserRoleUpdate,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db)
):
    """Update user role (superadmin only)"""
    user = db.query(User).filter(User.id == role_data.user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent changing own role
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot change your own role"
        )
    
    old_role = user.role
    user.role = role_data.role
    db.commit()
    db.refresh(user)
    
    # Notify user
    create_notification(
        db=db,
        title="Role Updated",
        message=f"Your role has been changed from {old_role.value} to {role_data.role.value}.",
        notification_type="role_updated",
        user_id=role_data.user_id
    )
    
    return user


@router.post("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    new_password: str,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db)
):
    """Reset user password (superadmin only)"""
    from app.auth import get_password_hash
    
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.hashed_password = get_password_hash(new_password)
    db.commit()
    
    # Notify user
    create_notification(
        db=db,
        title="Password Reset",
        message="Your password has been reset by admin.",
        notification_type="password_reset",
        user_id=user_id
    )
    
    return {"success": True, "message": "Password reset successfully"}
