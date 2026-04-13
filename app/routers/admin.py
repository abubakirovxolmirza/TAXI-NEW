from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, extract, or_, case
from sqlalchemy.exc import IntegrityError
from typing import List, Optional
from datetime import datetime, date, timezone, timedelta
from decimal import Decimal
from app.database import get_db
from app.models import (
    User,
    Driver,
    DriverApplication,
    ApplicationStatus,
    Tariff,
    UserRole,
    TaxiOrder,
    DeliveryOrder,
    OrderStatus,
    Pricing,
    DistrictPricing,
    BalanceTransaction,
    Notification,
    Feedback,
    SystemSettings,
    Rating,
    Permission,
    DeviceToken,
    DriverPhotoControl,
    OrderAcceptanceHistory,
    TopUpTransaction,
)
from app.schemas import (
    DriverApplicationResponse, DriverApplicationReview,
    DriverResponse, PricingCreate, PricingUpdate, PricingResponse,
    PricingBulkAdjustRequest, PricingBulkAdjustResponse,
    BalanceAdd, BalanceTransactionResponse, BroadcastMessage,
    FeedbackResponse, UserResponse, UserRoleUpdate,
    FeedbackReplyRequest,
    BonusBallUpdate, BonusBallUserResponse,
    ServiceFeeUpdate, ServiceFeeResponse, SystemSettingResponse,
    DriverVipUpdate, DriverBrendUpdate, DriverTariffUpdate, DriverControlUpdate, DriverBlockRequest,
    ActiveDriverStatsResponse, ActiveDriverStatsItem,
)
from app.auth import get_current_admin, get_current_superadmin
from app.utils import (
    create_notification,
    get_service_fee_percentage,
    dispatch_driver_status_event,
)
from app.localization import get_notification_message

router = APIRouter(prefix="/api/admin", tags=["Admin"])


def _build_user_delete_blockers(db: Session, user_id: int) -> List[str]:
    blockers: List[str] = []

    user_taxi_orders = db.query(func.count(TaxiOrder.id)).filter(TaxiOrder.user_id == user_id).scalar() or 0
    if user_taxi_orders:
        blockers.append(f"{user_taxi_orders} taxi orders")

    user_delivery_orders = (
        db.query(func.count(DeliveryOrder.id)).filter(DeliveryOrder.user_id == user_id).scalar() or 0
    )
    if user_delivery_orders:
        blockers.append(f"{user_delivery_orders} delivery orders")

    user_ratings = db.query(func.count(Rating.id)).filter(Rating.user_id == user_id).scalar() or 0
    if user_ratings:
        blockers.append(f"{user_ratings} ratings")

    driver = db.query(Driver).filter(Driver.user_id == user_id).first()
    if driver:
        driver_ratings = db.query(func.count(Rating.id)).filter(Rating.driver_id == driver.id).scalar() or 0
        if driver_ratings:
            blockers.append(f"{driver_ratings} driver ratings")

        driver_transactions = (
            db.query(func.count(BalanceTransaction.id))
            .filter(BalanceTransaction.driver_id == driver.id)
            .scalar()
            or 0
        )
        if driver_transactions:
            blockers.append(f"{driver_transactions} balance transactions")

        driver_topups = db.query(func.count(TopUpTransaction.id)).filter(TopUpTransaction.driver_id == driver.id).scalar() or 0
        if driver_topups:
            blockers.append(f"{driver_topups} top-up transactions")

        driver_acceptance_history = (
            db.query(func.count(OrderAcceptanceHistory.id))
            .filter(OrderAcceptanceHistory.driver_id == driver.id)
            .scalar()
            or 0
        )
        if driver_acceptance_history:
            blockers.append(f"{driver_acceptance_history} order acceptance history records")

    return blockers


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
    
    driver_status_event = None

    if review_data.approved:
        # Approve application and create or update driver profile
        application.status = ApplicationStatus.APPROVED

        existing_driver = (
            db.query(Driver)
            .filter(Driver.user_id == application.user_id)
            .first()
        )

        if existing_driver:
            existing_driver.full_name = application.full_name
            existing_driver.region_id = application.region_id
            existing_driver.car_model = application.car_model
            existing_driver.car_number = application.car_number
            existing_driver.license_photo = application.license_photo
            existing_driver.car_photo = application.car_photo
            existing_driver.tex_pas = application.tex_pas
            existing_driver.is_blocked = False
            driver_record = existing_driver
        else:
            driver_record = Driver(
                user_id=application.user_id,
                full_name=application.full_name,
                region_id=application.region_id,
                car_model=application.car_model,
                car_number=application.car_number,
                license_photo=application.license_photo,
                car_photo=application.car_photo,
                tex_pas=application.tex_pas
            )
            db.add(driver_record)
            db.flush()
        
        # Update user role to driver
        user = db.query(User).filter(User.id == application.user_id).first()
        if user:
            user.role = UserRole.DRIVER

        approval_notification = get_notification_message("application_approved")
        approval_title = approval_notification["title"]
        approval_message = approval_notification["message"]

        driver_status_event = {
            "status": "approved",
            "title": approval_title,
            "message": approval_message,
            "driver_id": driver_record.id,
            "application_id": application.id,
        }

        # Notify user
        create_notification(
            db=db,
            title=approval_title,
            message=approval_message,
            notification_type="application_approved",
            user_id=application.user_id,
            driver_status_payload=driver_status_event,
        )
    else:
        # Reject application
        application.status = ApplicationStatus.REJECTED
        application.rejection_reason = review_data.rejection_reason

        rejection_reason = review_data.rejection_reason or "Sabab ko'rsatilmagan"
        rejection_notification = get_notification_message(
            "application_rejected",
            reason=rejection_reason,
        )
        rejection_title = rejection_notification["title"]
        rejection_message = rejection_notification["message"]

        driver_status_event = {
            "status": "rejected",
            "title": rejection_title,
            "message": rejection_message,
            "driver_id": None,
            "application_id": application.id,
        }

        # Notify user
        create_notification(
            db=db,
            title=rejection_title,
            message=rejection_message,
            notification_type="application_rejected",
            user_id=application.user_id,
            driver_status_payload=driver_status_event,
        )
    
    application.reviewed_by = current_user.id
    application.reviewed_at = datetime.now(timezone.utc)
    
    db.commit()

    return {
        "success": True,
        "message": "Application reviewed successfully",
        "status": application.status
    }


@router.get("/users", response_model=List[UserResponse])
def get_all_users(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of users to return"),
    offset: int = Query(0, ge=0, description="Number of users to skip"),
    name: Optional[str] = Query(None, description="Filter by user name"),
    telephone: Optional[str] = Query(None, description="Filter by phone number"),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get users with optional pagination and filtering."""
    query = db.query(User)

    if name:
        query = query.filter(User.name.ilike(f"%{name.strip()}%"))

    if telephone:
        query = query.filter(User.telephone.ilike(f"%{telephone.strip()}%"))

    users = (
        query
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return users


@router.get("/users/admins", response_model=List[UserResponse])
def get_all_admin_users(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of admins to return"),
    offset: int = Query(0, ge=0, description="Number of admins to skip"),
    name: Optional[str] = Query(None, description="Filter by admin name"),
    telephone: Optional[str] = Query(None, description="Filter by admin phone number"),
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db),
):
    """Get admin users only (SUPERADMIN only)."""
    query = db.query(User).filter(User.role == UserRole.ADMIN)

    if name:
        query = query.filter(User.name.ilike(f"%{name.strip()}%"))

    if telephone:
        query = query.filter(User.telephone.ilike(f"%{telephone.strip()}%"))

    admins = (
        query
        .order_by(User.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return admins


@router.get("/users/bonus-ball", response_model=List[BonusBallUserResponse])
def get_all_bonus_ball(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get bonus balances for all users (with driver info when available)"""
    users = (
        db.query(User)
        .options(joinedload(User.driver_profile))
        .order_by(User.created_at.desc())
        .all()
    )
    return users


@router.get("/users/{user_id}", response_model=UserResponse)
def get_user_by_id(
    user_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get user details by user ID (admin/superadmin only)."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    return user


@router.put("/users/{user_id}/bonus-ball", response_model=BonusBallUserResponse)
def update_bonus_ball(
    user_id: int,
    bonus_data: BonusBallUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update a user's bonus balance"""
    user = (
        db.query(User)
        .options(joinedload(User.driver_profile))
        .filter(User.id == user_id)
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    user.bonus_ball = bonus_data.bonus_ball
    db.commit()
    db.refresh(user)
    return user


@router.get("/drivers", response_model=List[DriverResponse])
def get_all_drivers(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of drivers to return"),
    offset: int = Query(0, ge=0, description="Number of drivers to skip"),
    name: Optional[str] = Query(None, description="Filter by driver name"),
    telephone: Optional[str] = Query(None, description="Filter by driver phone number"),
    car_number: Optional[str] = Query(None, description="Filter by car number"),
    brend: Optional[bool] = Query(None, description="Filter by brend flag"),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get drivers with optional pagination and filtering."""
    query = db.query(Driver).options(joinedload(Driver.user))

    if name:
        name_value = name.strip()
        query = query.filter(
            or_(
                Driver.full_name.ilike(f"%{name_value}%"),
                User.name.ilike(f"%{name_value}%"),
            )
        )

    if telephone:
        query = query.filter(User.telephone.ilike(f"%{telephone.strip()}%"))

    if car_number:
        query = query.filter(Driver.car_number.ilike(f"%{car_number.strip()}%"))

    if brend is not None:
        query = query.filter(Driver.brend == brend)

    drivers = (
        query
        .join(User, Driver.user_id == User.id)
        .order_by(Driver.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return drivers


@router.get("/drivers/blocked", response_model=List[DriverResponse])
def get_blocked_drivers(
    limit: int = Query(50, ge=1, le=500, description="Maximum number of blocked drivers to return"),
    offset: int = Query(0, ge=0, description="Number of blocked drivers to skip"),
    name: Optional[str] = Query(None, description="Filter by driver name"),
    telephone: Optional[str] = Query(None, description="Filter by driver phone number"),
    car_number: Optional[str] = Query(None, description="Filter by car number"),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get blocked drivers with their block reasons (ADMIN or SUPERADMIN only)."""
    query = (
        db.query(Driver)
        .options(joinedload(Driver.user))
        .join(User, Driver.user_id == User.id)
        .filter(Driver.is_blocked == True)
    )

    if name:
        name_value = name.strip()
        query = query.filter(
            or_(
                Driver.full_name.ilike(f"%{name_value}%"),
                User.name.ilike(f"%{name_value}%"),
            )
        )

    if telephone:
        query = query.filter(User.telephone.ilike(f"%{telephone.strip()}%"))

    if car_number:
        query = query.filter(Driver.car_number.ilike(f"%{car_number.strip()}%"))

    blocked_drivers = (
        query
        .order_by(Driver.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return blocked_drivers


@router.get("/drivers/{driver_id}", response_model=DriverResponse)
def get_driver_by_id(
    driver_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get a driver by ID (ADMIN or SUPERADMIN only)."""
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found"
        )
    return driver


@router.put("/drivers/{driver_id}/vip", response_model=DriverResponse)
def update_driver_vip(
    driver_id: int,
    update_data: DriverVipUpdate,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db),
):
    """Update driver's VIP status with expiration in days (SUPERADMIN only)."""
    driver = db.query(Driver).filter(Driver.id == driver_id).first()

    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found"
        )

    if update_data.vip:
        driver.vip = True
        driver.vip_expires_at = datetime.now(timezone.utc) + timedelta(days=update_data.vip_days)
    else:
        driver.vip = False
        driver.vip_expires_at = None

    db.commit()
    db.refresh(driver)

    return driver


@router.put("/drivers/{driver_id}/brend", response_model=DriverResponse)
def update_driver_brend(
    driver_id: int,
    update_data: DriverBrendUpdate,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db),
):
    """Update driver's brend flag (SUPERADMIN only)."""
    driver = db.query(Driver).filter(Driver.id == driver_id).first()

    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found"
        )

    driver.brend = update_data.brend
    db.commit()
    db.refresh(driver)
    return driver


@router.put("/drivers/{driver_id}/tariff", response_model=DriverResponse)
def update_driver_tariff(
    driver_id: int,
    update_data: DriverTariffUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Update driver's tariff (ADMIN or SUPERADMIN only)."""
    driver = db.query(Driver).filter(Driver.id == driver_id).first()

    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found"
        )

    driver.tariff = update_data.tariff
    db.commit()
    db.refresh(driver)
    return driver


@router.put("/drivers/{driver_id}/control", response_model=DriverResponse)
def update_driver_control(
    driver_id: int,
    update_data: DriverControlUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Update driver's photo-control flag (ADMIN or SUPERADMIN only)."""
    driver = db.query(Driver).filter(Driver.id == driver_id).first()

    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found"
        )

    driver.control = update_data.control
    db.commit()
    db.refresh(driver)
    return driver


@router.post("/drivers/{driver_id}/block")
def block_driver(
    driver_id: int,
    block_data: DriverBlockRequest,
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
    driver.block_reason = block_data.reason.strip()
    db.commit()
    
    # Notify driver
    notification = get_notification_message("account_blocked")
    notify_message = f"{notification['message']} Sabab: {driver.block_reason}"
    create_notification(
        db=db,
        title=notification["title"],
        message=notify_message,
        notification_type="account_blocked",
        driver_id=driver_id
    )
    
    return {
        "success": True,
        "message": "Driver blocked successfully",
        "driver_id": driver_id,
        "reason": driver.block_reason,
    }


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
    driver.block_reason = None
    db.commit()
    
    # Notify driver
    notification = get_notification_message("account_unblocked")
    create_notification(
        db=db,
        title=notification["title"],
        message=notification["message"],
        notification_type="account_unblocked",
        driver_id=driver_id
    )
    
    return {"success": True, "message": "Driver unblocked successfully"}


@router.delete("/drivers/{driver_id}")
def delete_driver(
    driver_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete a driver (but keep the associated user account)"""
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver not found"
        )
    
    # Guardrails: do not delete if there is historical data that must be preserved
    existing_rating = db.query(Rating.id).filter(Rating.driver_id == driver_id).first()
    if existing_rating:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Driver has ratings and cannot be deleted. Please archive/disable instead.",
        )
    
    existing_transactions = (
        db.query(BalanceTransaction.id)
        .filter(BalanceTransaction.driver_id == driver_id)
        .first()
    )
    if existing_transactions:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Driver has balance transactions and cannot be deleted. Please archive/disable instead.",
        )
    
    # Detach nullable relationships to avoid FK violations (orders, notifications)
    db.query(TaxiOrder).filter(TaxiOrder.driver_id == driver_id).update(
        {TaxiOrder.driver_id: None}, synchronize_session=False
    )
    db.query(DeliveryOrder).filter(DeliveryOrder.driver_id == driver_id).update(
        {DeliveryOrder.driver_id: None}, synchronize_session=False
    )
    db.query(Notification).filter(Notification.driver_id == driver_id).delete(
        synchronize_session=False
    )
    
    # Get associated user info before deletion
    user_id = driver.user_id
    user = db.query(User).filter(User.id == user_id).first()
    
    # Delete the driver profile
    db.delete(driver)
    db.commit()
    
    # Update user role back to regular user
    if user:
        user.role = UserRole.USER
        db.commit()
        
        # Notify user that driver profile was deleted
        notification = get_notification_message("driver_profile_deleted")
        create_notification(
            db=db,
            title=notification["title"],
            message=notification["message"],
            notification_type="driver_deleted",
            user_id=user_id
        )
    
    return {
        "success": True,
        "message": "Driver profile deleted successfully. Associated user account remains active.",
        "driver_id": driver_id,
        "user_id": user_id
    }


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
    notification = get_notification_message("balance_added", amount=balance_data.amount)
    create_notification(
        db=db,
        title=notification["title"],
        message=notification["message"],
        notification_type="balance_added",
        driver_id=balance_data.driver_id
    )
    
    return transaction


@router.get("/drivers/balance/history")
def get_balance_history(
    driver_id: Optional[int] = None,
    transaction_type: Optional[str] = None,
    limit: Optional[int] = 100,
    offset: Optional[int] = 0,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """
    Get balance transaction history with detailed information.
    Shows which admin added money, to which driver, amount, and when.
    """
    query = db.query(BalanceTransaction).order_by(BalanceTransaction.created_at.desc())
    
    # Filter by driver if specified
    if driver_id:
        query = query.filter(BalanceTransaction.driver_id == driver_id)
    
    # Filter by transaction type if specified
    if transaction_type:
        if transaction_type not in ["credit", "debit", "refund"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid transaction_type. Must be 'credit', 'debit', or 'refund'"
            )
        query = query.filter(BalanceTransaction.transaction_type == transaction_type)
    
    transactions = query.limit(limit).offset(offset).all()
    
    # Build detailed response with admin and driver info
    result = []
    for transaction in transactions:
        driver = db.query(Driver).filter(Driver.id == transaction.driver_id).first()
        admin = db.query(User).filter(User.id == transaction.admin_id).first() if transaction.admin_id else None
        
        result.append({
            "id": transaction.id,
            "driver_id": transaction.driver_id,
            "driver_name": driver.full_name if driver else "Unknown",
            "amount": str(transaction.amount),
            "transaction_type": transaction.transaction_type,
            "description": transaction.description,
            "admin_id": transaction.admin_id,
            "admin_name": admin.name if admin else "System",
            "created_at": transaction.created_at
        })
    
    return {
        "total": len(result),
        "transactions": result
    }


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
        Pricing.tariff == pricing_data.tariff,
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
    if pricing.service_type == "delivery" and update_data.get("tariff") not in (None, Tariff.STANDARD):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Delivery pricing supports only standard tariff"
        )
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


@router.get("/delivery-pricing", response_model=List[PricingResponse])
def get_all_delivery_pricing(
    from_region_id: Optional[int] = Query(None, description="Filter by source region"),
    to_region_id: Optional[int] = Query(None, description="Filter by destination region"),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get all active delivery pricing configurations."""
    query = db.query(Pricing).filter(
        Pricing.is_active == True,
        Pricing.service_type == "delivery",
    )

    if from_region_id is not None:
        query = query.filter(Pricing.from_region_id == from_region_id)
    if to_region_id is not None:
        query = query.filter(Pricing.to_region_id == to_region_id)

    pricing = query.all()
    return pricing


@router.put("/delivery-pricing/{pricing_id}", response_model=PricingResponse)
def update_delivery_pricing(
    pricing_id: int,
    pricing_data: PricingUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Update a delivery pricing row by ID."""
    pricing = db.query(Pricing).filter(Pricing.id == pricing_id).first()

    if not pricing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pricing not found",
        )
    if pricing.service_type != "delivery":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This pricing is not delivery service type",
        )

    update_data = pricing_data.dict(exclude_unset=True)
    if update_data.get("tariff") not in (None, Tariff.STANDARD):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Delivery pricing supports only standard tariff",
        )

    for key, value in update_data.items():
        setattr(pricing, key, value)

    db.commit()
    db.refresh(pricing)
    return pricing


@router.delete("/pricing/{pricing_id}")
def delete_pricing_by_id(
    pricing_id: int,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Delete a specific pricing by ID"""
    pricing = db.query(Pricing).filter(Pricing.id == pricing_id).first()
    
    if not pricing:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Pricing not found"
        )
    
    db.delete(pricing)
    db.commit()
    
    return {
        "success": True,
        "message": f"Pricing with ID {pricing_id} deleted successfully"
    }


@router.delete("/pricing")
def delete_all_pricing(
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db)
):
    """Delete all pricing records (SUPERADMIN only)"""
    deleted_count = db.query(Pricing).delete()
    db.commit()
    
    return {
        "success": True,
        "message": f"All pricing deleted successfully. Total deleted: {deleted_count}"
    }


def _adjust_price_value(value: Optional[Decimal], amount: Decimal, operation: str) -> Optional[Decimal]:
    if value is None:
        return None
    if operation == "add":
        return value + amount
    updated_value = value - amount
    if updated_value < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Price adjustment would produce negative values",
        )
    return updated_value


def _apply_bulk_price_adjustment(
    db: Session,
    *,
    service_type: str,
    operation: str,
    amount: Decimal,
) -> tuple[int, int]:
    region_pricing = db.query(Pricing).filter(
        Pricing.service_type == service_type,
        Pricing.is_active == True,
    ).all()
    district_pricing = db.query(DistrictPricing).filter(
        DistrictPricing.service_type == service_type,
        DistrictPricing.is_active == True,
    ).all()

    for row in region_pricing:
        row.base_price = _adjust_price_value(row.base_price, amount, operation)
        row.front_seat_price = _adjust_price_value(row.front_seat_price, amount, operation)
        row.back_seat_price = _adjust_price_value(row.back_seat_price, amount, operation)

    for row in district_pricing:
        row.base_price = _adjust_price_value(row.base_price, amount, operation)
        row.front_seat_price = _adjust_price_value(row.front_seat_price, amount, operation)
        row.back_seat_price = _adjust_price_value(row.back_seat_price, amount, operation)

    return len(region_pricing), len(district_pricing)


@router.post("/pricing/taxi/adjust", response_model=PricingBulkAdjustResponse)
def bulk_adjust_taxi_pricing(
    payload: PricingBulkAdjustRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Bulk add/subtract amount from all active taxi pricing (region + district)."""
    try:
        region_count, district_count = _apply_bulk_price_adjustment(
            db,
            service_type="taxi",
            operation=payload.operation,
            amount=payload.amount,
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise

    return {
        "success": True,
        "service_type": "taxi",
        "operation": payload.operation,
        "amount": payload.amount,
        "updated_region_pricing_count": region_count,
        "updated_district_pricing_count": district_count,
    }


@router.post("/pricing/delivery/adjust", response_model=PricingBulkAdjustResponse)
def bulk_adjust_delivery_pricing(
    payload: PricingBulkAdjustRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Bulk add/subtract amount from all active delivery pricing (region + district)."""
    try:
        region_count, district_count = _apply_bulk_price_adjustment(
            db,
            service_type="delivery",
            operation=payload.operation,
            amount=payload.amount,
        )
        db.commit()
    except HTTPException:
        db.rollback()
        raise

    return {
        "success": True,
        "service_type": "delivery",
        "operation": payload.operation,
        "amount": payload.amount,
        "updated_region_pricing_count": region_count,
        "updated_district_pricing_count": district_count,
    }


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
    today = datetime.now(timezone.utc).date()
    
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


@router.get("/drivers/active/stats", response_model=ActiveDriverStatsResponse)
def get_active_drivers_statistics(
    period: str = Query("daily", pattern="^(daily|monthly|yearly)$"),
    limit: int = Query(10, ge=1, le=200, description="Number of drivers to return"),
    include_blocked: bool = Query(False, description="Include blocked drivers in ranking"),
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Get most active drivers by period with acceptance, completion, cancellation, and revenue stats."""
    now = datetime.now(timezone.utc)
    today = now.date()
    if period == "daily":
        start_date = today
    elif period == "monthly":
        start_date = today.replace(day=1)
    else:  # yearly
        start_date = today.replace(month=1, day=1)

    start_dt = datetime.combine(start_date, datetime.min.time(), tzinfo=timezone.utc)
    end_dt = now

    taxi_stats = db.query(
        TaxiOrder.driver_id.label("driver_id"),
        func.count(TaxiOrder.id).label("accepted_orders"),
        func.coalesce(func.sum(case((TaxiOrder.status == OrderStatus.COMPLETED, 1), else_=0)), 0).label("completed_orders"),
        func.coalesce(func.sum(case((TaxiOrder.status == OrderStatus.CANCELLED, 1), else_=0)), 0).label("cancelled_orders"),
        func.coalesce(
            func.sum(case((TaxiOrder.status == OrderStatus.COMPLETED, TaxiOrder.driver_earnings), else_=0)),
            0,
        ).label("revenue"),
    ).filter(
        TaxiOrder.driver_id.isnot(None),
        TaxiOrder.accepted_at.isnot(None),
        TaxiOrder.created_at >= start_dt,
        TaxiOrder.created_at <= end_dt,
    ).group_by(TaxiOrder.driver_id).all()

    delivery_stats = db.query(
        DeliveryOrder.driver_id.label("driver_id"),
        func.count(DeliveryOrder.id).label("accepted_orders"),
        func.coalesce(func.sum(case((DeliveryOrder.status == OrderStatus.COMPLETED, 1), else_=0)), 0).label("completed_orders"),
        func.coalesce(func.sum(case((DeliveryOrder.status == OrderStatus.CANCELLED, 1), else_=0)), 0).label("cancelled_orders"),
        func.coalesce(
            func.sum(case((DeliveryOrder.status == OrderStatus.COMPLETED, DeliveryOrder.driver_earnings), else_=0)),
            0,
        ).label("revenue"),
    ).filter(
        DeliveryOrder.driver_id.isnot(None),
        DeliveryOrder.accepted_at.isnot(None),
        DeliveryOrder.created_at >= start_dt,
        DeliveryOrder.created_at <= end_dt,
    ).group_by(DeliveryOrder.driver_id).all()

    aggregated: dict[int, dict] = {}

    for row in list(taxi_stats) + list(delivery_stats):
        driver_id = int(row.driver_id)
        if driver_id not in aggregated:
            aggregated[driver_id] = {
                "accepted_orders": 0,
                "completed_orders": 0,
                "cancelled_orders": 0,
                "revenue": Decimal("0.00"),
            }
        aggregated[driver_id]["accepted_orders"] += int(row.accepted_orders or 0)
        aggregated[driver_id]["completed_orders"] += int(row.completed_orders or 0)
        aggregated[driver_id]["cancelled_orders"] += int(row.cancelled_orders or 0)
        aggregated[driver_id]["revenue"] += Decimal(str(row.revenue or 0))

    if not aggregated:
        return {
            "period": period,
            "start_date": start_dt,
            "end_date": end_dt,
            "drivers": [],
        }

    drivers_query = db.query(Driver).options(joinedload(Driver.user)).filter(Driver.id.in_(aggregated.keys()))
    if not include_blocked:
        drivers_query = drivers_query.filter(Driver.is_blocked == False)
    drivers = drivers_query.all()

    result: List[ActiveDriverStatsItem] = []
    for driver in drivers:
        stats = aggregated.get(driver.id)
        if not stats:
            continue
        accepted_orders = int(stats["accepted_orders"])
        completed_orders = int(stats["completed_orders"])
        cancelled_orders = int(stats["cancelled_orders"])
        revenue = Decimal(str(stats["revenue"]))
        total_orders = accepted_orders

        completion_rate = Decimal("0.00")
        cancellation_rate = Decimal("0.00")
        if total_orders > 0:
            completion_rate = (Decimal(completed_orders) * Decimal("100") / Decimal(total_orders)).quantize(Decimal("0.01"))
            cancellation_rate = (Decimal(cancelled_orders) * Decimal("100") / Decimal(total_orders)).quantize(Decimal("0.01"))

        avg_revenue = Decimal("0.00")
        if completed_orders > 0:
            avg_revenue = (revenue / Decimal(completed_orders)).quantize(Decimal("0.01"))

        result.append(
            ActiveDriverStatsItem(
                driver_id=driver.id,
                full_name=driver.full_name,
                telephone=driver.telephone,
                car_number=driver.car_number,
                tariff=driver.tariff,
                rating=driver.rating or Decimal("0.00"),
                balance=driver.balance or Decimal("0.00"),
                accepted_orders=accepted_orders,
                completed_orders=completed_orders,
                cancelled_orders=cancelled_orders,
                total_orders=total_orders,
                revenue=revenue.quantize(Decimal("0.01")),
                completion_rate=completion_rate,
                cancellation_rate=cancellation_rate,
                avg_revenue_per_completed=avg_revenue,
            )
        )

    result.sort(
        key=lambda item: (
            item.accepted_orders,
            item.completed_orders,
            item.revenue,
        ),
        reverse=True,
    )

    return {
        "period": period,
        "start_date": start_dt,
        "end_date": end_dt,
        "drivers": result[:limit],
    }


@router.get("/feedback", response_model=List[FeedbackResponse])
def get_feedback(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all feedback"""
    feedback = (
        db.query(Feedback)
        .options(joinedload(Feedback.user))
        .order_by(Feedback.created_at.desc())
        .all()
    )
    return feedback


@router.post("/feedback/{feedback_id}/reply", response_model=FeedbackResponse)
def reply_feedback(
    feedback_id: int,
    payload: FeedbackReplyRequest,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db),
):
    """Reply to feedback, send notification to user, and mark feedback as reviewed."""
    feedback = (
        db.query(Feedback)
        .options(joinedload(Feedback.user))
        .filter(Feedback.id == feedback_id)
        .first()
    )
    if not feedback:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Feedback not found",
        )
    if not feedback.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This feedback has no user_id. Cannot send in-app notification.",
        )

    feedback.is_reviewed = True
    create_notification(
        db=db,
        title="Talab va taklifingizga javob keldi",
        message=payload.message,
        notification_type="feedback_reply",
        user_id=feedback.user_id,
    )
    db.refresh(feedback)
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
    notification = get_notification_message("admin_access_granted")
    create_notification(
        db=db,
        title=notification["title"],
        message=notification["message"],
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
    driver_record = (
        db.query(Driver)
        .filter(Driver.user_id == user.id)
        .first()
    )
    driver_id = driver_record.id if driver_record else None
    driver_status_event = None
    if old_role == UserRole.DRIVER and role_data.role != UserRole.DRIVER:
        driver_status_event = {
            "status": "revoked",
            "title": "Driver access revoked",
            "message": "Your driver privileges have been revoked by the administrator.",
        }
    elif old_role != UserRole.DRIVER and role_data.role == UserRole.DRIVER:
        driver_status_event = {
            "status": "approved",
            "title": "Driver access granted",
            "message": "You have been granted driver privileges by the administrator.",
        }

    notification_message = (
        f"Your role has been changed from {old_role.value} to {role_data.role.value}."
    )
    notification = get_notification_message("role_updated", message=notification_message)
    create_notification(
        db=db,
        title=notification["title"],
        message=notification["message"],
        notification_type="role_updated",
        user_id=role_data.user_id,
        driver_id=driver_id,
        driver_status_payload=driver_status_event,
    )

    return user


@router.post("/users/{user_id}/deactivate")
def deactivate_user(
    user_id: int,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db)
):
    """Deactivate/soft delete a user (superadmin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent deactivating own account
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot deactivate your own account"
        )
    
    user.is_active = False
    db.commit()
    
    # Notify user
    notification = get_notification_message("account_deactivated")
    create_notification(
        db=db,
        title=notification["title"],
        message=notification["message"],
        notification_type="account_deactivated",
        user_id=user_id
    )
    
    return {
        "success": True,
        "message": f"User {user.name} has been deactivated",
        "user_id": user_id
    }


@router.post("/users/{user_id}/activate")
def activate_user(
    user_id: int,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db)
):
    """Activate a deactivated user (superadmin only)"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    user.is_active = True
    db.commit()
    
    # Notify user
    notification = get_notification_message("account_activated")
    create_notification(
        db=db,
        title=notification["title"],
        message=notification["message"],
        notification_type="account_activated",
        user_id=user_id
    )
    
    return {
        "success": True,
        "message": f"User {user.name} has been activated",
        "user_id": user_id
    }


@router.delete("/users/{user_id}")
def delete_user_permanently(
    user_id: int,
    current_user: User = Depends(get_current_superadmin),
    db: Session = Depends(get_db)
):
    """Permanently delete a user (superadmin only) - USE WITH CAUTION"""
    user = db.query(User).filter(User.id == user_id).first()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Prevent deleting own account
    if user.id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot delete your own account"
        )

    blockers = _build_user_delete_blockers(db, user_id)
    if blockers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "User cannot be permanently deleted because related historical records exist: "
                + ", ".join(blockers)
                + ". Deactivate this user instead."
            ),
        )
    
    user_name = user.name
    user_telephone = user.telephone

    try:
        driver = db.query(Driver).filter(Driver.user_id == user_id).first()
        if driver:
            db.query(TaxiOrder).filter(TaxiOrder.driver_id == driver.id).update(
                {TaxiOrder.driver_id: None},
                synchronize_session=False,
            )
            db.query(DeliveryOrder).filter(DeliveryOrder.driver_id == driver.id).update(
                {DeliveryOrder.driver_id: None},
                synchronize_session=False,
            )
            db.query(Notification).filter(Notification.driver_id == driver.id).delete(
                synchronize_session=False
            )
            db.query(DriverPhotoControl).filter(DriverPhotoControl.driver_id == driver.id).delete(
                synchronize_session=False
            )
            db.delete(driver)

        # Clear nullable references to this user from historical records.
        db.query(TaxiOrder).filter(TaxiOrder.bonus_user_id == user_id).update(
            {TaxiOrder.bonus_user_id: None}, synchronize_session=False
        )
        db.query(TaxiOrder).filter(TaxiOrder.cancelled_by_user_id == user_id).update(
            {TaxiOrder.cancelled_by_user_id: None}, synchronize_session=False
        )
        db.query(DeliveryOrder).filter(DeliveryOrder.bonus_user_id == user_id).update(
            {DeliveryOrder.bonus_user_id: None}, synchronize_session=False
        )
        db.query(DeliveryOrder).filter(DeliveryOrder.cancelled_by_user_id == user_id).update(
            {DeliveryOrder.cancelled_by_user_id: None}, synchronize_session=False
        )
        db.query(DriverApplication).filter(DriverApplication.reviewed_by == user_id).update(
            {DriverApplication.reviewed_by: None}, synchronize_session=False
        )
        db.query(BalanceTransaction).filter(BalanceTransaction.admin_id == user_id).update(
            {BalanceTransaction.admin_id: None}, synchronize_session=False
        )
        db.query(Feedback).filter(Feedback.user_id == user_id).update(
            {Feedback.user_id: None}, synchronize_session=False
        )
        db.query(SystemSettings).filter(SystemSettings.updated_by == user_id).update(
            {SystemSettings.updated_by: None}, synchronize_session=False
        )
        db.query(Notification).filter(Notification.user_id == user_id).delete(
            synchronize_session=False
        )

        # Delete records directly owned by this user.
        db.query(DeviceToken).filter(DeviceToken.user_id == user_id).delete(
            synchronize_session=False
        )
        db.query(Permission).filter(Permission.user_id == user_id).delete(
            synchronize_session=False
        )
        db.query(DriverApplication).filter(DriverApplication.user_id == user_id).delete(
            synchronize_session=False
        )

        db.delete(user)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "User cannot be permanently deleted because related records still reference this user. "
                "Deactivate this user instead."
            ),
        )
    
    return {
        "success": True,
        "message": f"User {user_name} ({user_telephone}) has been permanently deleted",
        "user_id": user_id
    }


@router.post("/users/{user_id}/reset-password")
def reset_user_password(
    user_id: int,
    new_password: str,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Reset user password (admin or superadmin)"""
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
    notification = get_notification_message("password_reset")
    create_notification(
        db=db,
        title=notification["title"],
        message=notification["message"],
        notification_type="password_reset",
        user_id=user_id
    )
    
    return {"success": True, "message": "Password reset successfully"}


@router.get("/settings/service-fee", response_model=ServiceFeeResponse)
def get_service_fee(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get current service fee percentage"""
    service_fee_percentage = get_service_fee_percentage(db)
    
    setting = db.query(SystemSettings).filter(
        SystemSettings.setting_key == "service_fee_percentage"
    ).first()
    
    return {
        "service_fee_percentage": service_fee_percentage,
        "updated_at": setting.updated_at if setting else None,
        "updated_by": setting.updated_by if setting else None
    }


@router.put("/settings/service-fee", response_model=ServiceFeeResponse)
def update_service_fee(
    fee_data: ServiceFeeUpdate,
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Update service fee percentage"""
    setting = db.query(SystemSettings).filter(
        SystemSettings.setting_key == "service_fee_percentage"
    ).first()
    
    if setting:
        # Update existing setting
        setting.setting_value = str(fee_data.service_fee_percentage)
        setting.updated_by = current_user.id
        setting.updated_at = datetime.now(timezone.utc)
    else:
        # Create new setting
        setting = SystemSettings(
            setting_key="service_fee_percentage",
            setting_value=str(fee_data.service_fee_percentage),
            description="Platform service fee percentage",
            updated_by=current_user.id
        )
        db.add(setting)
    
    db.commit()
    db.refresh(setting)
    
    return {
        "service_fee_percentage": Decimal(setting.setting_value),
        "updated_at": setting.updated_at,
        "updated_by": setting.updated_by
    }


@router.get("/settings", response_model=List[SystemSettingResponse])
def get_all_settings(
    current_user: User = Depends(get_current_admin),
    db: Session = Depends(get_db)
):
    """Get all system settings"""
    settings = db.query(SystemSettings).all()
    return settings
