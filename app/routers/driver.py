from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, extract
from typing import List
from datetime import datetime, timedelta
from decimal import Decimal
import shutil
from pathlib import Path
from app.database import get_db
from app.models import (
    User, Driver, DriverApplication, ApplicationStatus, 
    TaxiOrder, DeliveryOrder, OrderStatus, UserRole
)
from app.schemas import (
    DriverApplicationCreate, DriverApplicationResponse,
    DriverUpdate, DriverResponse, DriverStatistics
)
from app.auth import get_current_user, get_current_driver
from app.utils import check_driver_can_accept_order, create_notification
from app.config import settings

router = APIRouter(prefix="/api/driver", tags=["Driver"])


@router.post("/apply", response_model=DriverApplicationResponse, status_code=status.HTTP_201_CREATED)
async def apply_as_driver(
    application_data: DriverApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Apply to become a driver"""
    # Check if user already has a driver profile
    if current_user.driver_profile:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a driver"
        )
    
    # Check if there's already a pending application
    existing_application = db.query(DriverApplication).filter(
        DriverApplication.user_id == current_user.id,
        DriverApplication.status == ApplicationStatus.PENDING
    ).first()
    
    if existing_application:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You already have a pending application"
        )
    
    # Create application
    new_application = DriverApplication(
        user_id=current_user.id,
        full_name=application_data.full_name,
        telephone=current_user.telephone,
        car_model=application_data.car_model,
        car_number=application_data.car_number,
        license_photo=application_data.license_photo,
        status=ApplicationStatus.PENDING
    )
    
    db.add(new_application)
    db.commit()
    db.refresh(new_application)
    
    # TODO: Send notification to admin via Telegram bot
    
    return new_application


@router.post("/upload-license")
async def upload_license_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """Upload driving license photo"""
    try:
        # Validate file type
        allowed_types = ["image/jpeg", "image/png", "image/jpg"]
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only JPEG and PNG images are allowed"
            )
        
        # Validate file size (max 5MB)
        file.file.seek(0, 2)  # Move to end of file
        file_size = file.file.tell()  # Get file size
        file.file.seek(0)  # Reset to beginning
        
        if file_size > settings.MAX_UPLOAD_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File size exceeds maximum allowed size of {settings.MAX_UPLOAD_SIZE / 1024 / 1024}MB"
            )
        
        # Create upload directory if not exists
        upload_dir = Path(settings.UPLOAD_DIR) / "licenses"
        upload_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate unique filename
        import time
        file_extension = file.filename.split(".")[-1] if "." in file.filename else "jpg"
        filename = f"license_{current_user.id}_{int(time.time())}.{file_extension}"
        file_path = upload_dir / filename
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Return relative path for storing in database
        relative_path = f"uploads/licenses/{filename}"
        
        return {
            "message": "License photo uploaded successfully",
            "file_path": relative_path
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error uploading file: {str(e)}"
        )


@router.get("/status")
def check_driver_status(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Check if user is a driver or has pending application"""
    if current_user.driver_profile:
        return {
            "is_driver": True,
            "driver_id": current_user.driver_profile.id,
            "status": "approved"
        }
    
    application = db.query(DriverApplication).filter(
        DriverApplication.user_id == current_user.id
    ).first()
    
    if application:
        return {
            "is_driver": False,
            "application_status": application.status,
            "application_id": application.id
        }
    
    return {
        "is_driver": False,
        "application_status": None
    }


@router.get("/profile", response_model=DriverResponse)
def get_driver_profile(
    current_user: User = Depends(get_current_driver),
    db: Session = Depends(get_db)
):
    """Get driver profile"""
    if not current_user.driver_profile:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver profile not found"
        )
    
    return current_user.driver_profile


@router.put("/profile", response_model=DriverResponse)
def update_driver_profile(
    driver_update: DriverUpdate,
    current_user: User = Depends(get_current_driver),
    db: Session = Depends(get_db)
):
    """Update driver profile"""
    driver = current_user.driver_profile
    
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver profile not found"
        )
    
    if driver_update.full_name is not None:
        driver.full_name = driver_update.full_name
    
    if driver_update.car_model is not None:
        driver.car_model = driver_update.car_model
    
    if driver_update.car_number is not None:
        driver.car_number = driver_update.car_number
    
    db.commit()
    db.refresh(driver)
    
    return driver


@router.get("/statistics", response_model=DriverStatistics)
def get_driver_statistics(
    current_user: User = Depends(get_current_driver),
    db: Session = Depends(get_db)
):
    """Get driver statistics (daily, monthly, total)"""
    driver = current_user.driver_profile
    
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver profile not found"
        )
    
    today = datetime.utcnow().date()
    month_start = today.replace(day=1)
    
    # Daily statistics
    daily_taxi = db.query(
        func.count(TaxiOrder.id).label('count'),
        func.coalesce(func.sum(TaxiOrder.price), 0).label('revenue')
    ).filter(
        TaxiOrder.driver_id == driver.id,
        TaxiOrder.status == OrderStatus.COMPLETED,
        func.date(TaxiOrder.completed_at) == today
    ).first()
    
    daily_delivery = db.query(
        func.count(DeliveryOrder.id).label('count'),
        func.coalesce(func.sum(DeliveryOrder.price), 0).label('revenue')
    ).filter(
        DeliveryOrder.driver_id == driver.id,
        DeliveryOrder.status == OrderStatus.COMPLETED,
        func.date(DeliveryOrder.completed_at) == today
    ).first()
    
    # Monthly statistics
    monthly_taxi = db.query(
        func.count(TaxiOrder.id).label('count'),
        func.coalesce(func.sum(TaxiOrder.price), 0).label('revenue')
    ).filter(
        TaxiOrder.driver_id == driver.id,
        TaxiOrder.status == OrderStatus.COMPLETED,
        func.date(TaxiOrder.completed_at) >= month_start
    ).first()
    
    monthly_delivery = db.query(
        func.count(DeliveryOrder.id).label('count'),
        func.coalesce(func.sum(DeliveryOrder.price), 0).label('revenue')
    ).filter(
        DeliveryOrder.driver_id == driver.id,
        DeliveryOrder.status == OrderStatus.COMPLETED,
        func.date(DeliveryOrder.completed_at) >= month_start
    ).first()
    
    # Total statistics
    total_taxi = db.query(
        func.count(TaxiOrder.id).label('count'),
        func.coalesce(func.sum(TaxiOrder.price), 0).label('revenue')
    ).filter(
        TaxiOrder.driver_id == driver.id,
        TaxiOrder.status == OrderStatus.COMPLETED
    ).first()
    
    total_delivery = db.query(
        func.count(DeliveryOrder.id).label('count'),
        func.coalesce(func.sum(DeliveryOrder.price), 0).label('revenue')
    ).filter(
        DeliveryOrder.driver_id == driver.id,
        DeliveryOrder.status == OrderStatus.COMPLETED
    ).first()
    
    return {
        "daily_orders": (daily_taxi.count or 0) + (daily_delivery.count or 0),
        "daily_revenue": Decimal(str(daily_taxi.revenue or 0)) + Decimal(str(daily_delivery.revenue or 0)),
        "monthly_orders": (monthly_taxi.count or 0) + (monthly_delivery.count or 0),
        "monthly_revenue": Decimal(str(monthly_taxi.revenue or 0)) + Decimal(str(monthly_delivery.revenue or 0)),
        "total_orders": (total_taxi.count or 0) + (total_delivery.count or 0),
        "total_revenue": Decimal(str(total_taxi.revenue or 0)) + Decimal(str(total_delivery.revenue or 0)),
        "current_balance": driver.balance,
        "rating": driver.rating
    }


@router.get("/orders/new")
def get_new_orders(
    from_region_id: int = None,
    to_region_id: int = None,
    current_user: User = Depends(get_current_driver),
    db: Session = Depends(get_db)
):
    """Get new pending orders for drivers"""
    driver = current_user.driver_profile
    
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver profile not found"
        )
    
    # Build query for taxi orders
    taxi_query = db.query(TaxiOrder).filter(TaxiOrder.status == OrderStatus.PENDING)
    delivery_query = db.query(DeliveryOrder).filter(DeliveryOrder.status == OrderStatus.PENDING)
    
    # Apply filters
    if from_region_id:
        taxi_query = taxi_query.filter(TaxiOrder.from_region_id == from_region_id)
        delivery_query = delivery_query.filter(DeliveryOrder.from_region_id == from_region_id)
    
    if to_region_id:
        taxi_query = taxi_query.filter(TaxiOrder.to_region_id == to_region_id)
        delivery_query = delivery_query.filter(DeliveryOrder.to_region_id == to_region_id)
    
    taxi_orders = taxi_query.order_by(TaxiOrder.created_at.desc()).all()
    delivery_orders = delivery_query.order_by(DeliveryOrder.created_at.desc()).all()
    
    return {
        "taxi_orders": [
            {
                "id": order.id,
                "type": "taxi",
                "from_region_id": order.from_region_id,
                "to_region_id": order.to_region_id,
                "passengers": order.passengers,
                "price": str(order.price),
                "date": order.date,
                "time_start": order.time_start,
                "time_end": order.time_end,
                "scheduled_datetime": order.scheduled_datetime.isoformat() if order.scheduled_datetime else None,
                "created_at": order.created_at.isoformat()
            }
            for order in taxi_orders
        ],
        "delivery_orders": [
            {
                "id": order.id,
                "type": "delivery",
                "from_region_id": order.from_region_id,
                "to_region_id": order.to_region_id,
                "item_type": order.item_type,
                "price": str(order.price),
                "date": order.date,
                "time_start": order.time_start,
                "time_end": order.time_end,
                "scheduled_datetime": order.scheduled_datetime.isoformat() if order.scheduled_datetime else None,
                "created_at": order.created_at.isoformat()
            }
            for order in delivery_orders
        ]
    }


@router.post("/orders/accept/{order_type}/{order_id}")
def accept_order(
    order_type: str,
    order_id: int,
    current_user: User = Depends(get_current_driver),
    db: Session = Depends(get_db)
):
    """Accept a taxi or delivery order"""
    driver = current_user.driver_profile
    
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver profile not found"
        )
    
    # Check if driver can accept orders
    if not check_driver_can_accept_order(db, driver.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not allowed to accept orders. Check your balance or account status."
        )
    
    # Get order based on type
    if order_type == "taxi":
        order = db.query(TaxiOrder).filter(TaxiOrder.id == order_id).first()
    elif order_type == "delivery":
        order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order type. Must be 'taxi' or 'delivery'"
        )
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is not available for acceptance"
        )
    
    # Check if order was created within last 5 minutes
    time_diff = datetime.utcnow() - order.created_at
    if time_diff > timedelta(minutes=5):
        # Return order to pending state if expired
        return {
            "success": False,
            "message": "Order acceptance time has expired (5 minutes)"
        }
    
    # Accept order
    order.driver_id = driver.id
    order.status = OrderStatus.ACCEPTED
    order.accepted_at = datetime.utcnow()
    
    db.commit()
    db.refresh(order)
    
    # Notify user
    create_notification(
        db=db,
        title="Order Accepted",
        message=f"Your {order_type} order #{order.id} has been accepted by a driver.",
        notification_type="order_accepted",
        user_id=order.user_id
    )
    
    return {
        "success": True,
        "message": "Order accepted successfully",
        "order": {
            "id": order.id,
            "type": order_type,
            "status": order.status
        }
    }


@router.post("/orders/complete/{order_type}/{order_id}")
def complete_order(
    order_type: str,
    order_id: int,
    current_user: User = Depends(get_current_driver),
    db: Session = Depends(get_db)
):
    """Mark order as completed"""
    driver = current_user.driver_profile
    
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver profile not found"
        )
    
    # Get order based on type
    if order_type == "taxi":
        order = db.query(TaxiOrder).filter(TaxiOrder.id == order_id).first()
    elif order_type == "delivery":
        order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order type"
        )
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    if order.driver_id != driver.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not assigned to this order"
        )
    
    if order.status != OrderStatus.ACCEPTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only accepted orders can be completed"
        )
    
    # Complete order
    order.status = OrderStatus.COMPLETED
    order.completed_at = datetime.utcnow()
    
    db.commit()
    db.refresh(order)
    
    # Notify user
    create_notification(
        db=db,
        title="Order Completed",
        message=f"Your {order_type} order #{order.id} has been completed. Please rate the driver.",
        notification_type="order_completed",
        user_id=order.user_id
    )
    
    return {
        "success": True,
        "message": "Order completed successfully",
        "order": {
            "id": order.id,
            "type": order_type,
            "status": order.status
        }
    }
