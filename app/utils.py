from decimal import Decimal
from sqlalchemy.orm import Session
from app.models import Pricing, Driver, User, Notification
from typing import Optional, Tuple

# Platform service fee percentage
SERVICE_FEE_PERCENTAGE = Decimal("8.00")  # 8%


def calculate_service_fee(price: Decimal) -> Tuple[Decimal, Decimal]:
    """
    Calculate service fee and driver earnings
    Returns: (service_fee, driver_earnings)
    """
    service_fee = (price * SERVICE_FEE_PERCENTAGE) / Decimal("100.00")
    driver_earnings = price - service_fee
    return (service_fee, driver_earnings)


def calculate_taxi_price(
    db: Session,
    from_region_id: int,
    to_region_id: int,
    passengers: int
) -> Decimal:
    """Calculate taxi price with discounts based on number of passengers"""
    pricing = db.query(Pricing).filter(
        Pricing.from_region_id == from_region_id,
        Pricing.to_region_id == to_region_id,
        Pricing.service_type == "taxi",
        Pricing.is_active == True
    ).first()
    
    if not pricing:
        # Default pricing if not set
        return Decimal("50000.00")
    
    base_price = pricing.base_price
    
    # Apply discount based on passengers
    discount = Decimal("0.00")
    if passengers == 1:
        discount = pricing.discount_1_passenger
    elif passengers == 2:
        discount = pricing.discount_2_passengers
    elif passengers == 3:
        discount = pricing.discount_3_passengers
    elif passengers == 4:
        discount = pricing.discount_full_car
    
    discount_amount = base_price * (discount / Decimal("100.00"))
    final_price = base_price - discount_amount
    
    return final_price


def calculate_delivery_price(
    db: Session,
    from_region_id: int,
    to_region_id: int
) -> Decimal:
    """Calculate delivery price"""
    pricing = db.query(Pricing).filter(
        Pricing.from_region_id == from_region_id,
        Pricing.to_region_id == to_region_id,
        Pricing.service_type == "delivery",
        Pricing.is_active == True
    ).first()
    
    if not pricing:
        # Default pricing if not set
        return Decimal("30000.00")
    
    return pricing.base_price


def update_driver_rating(db: Session, driver_id: int):
    """Recalculate driver's average rating"""
    from app.models import Rating
    
    ratings = db.query(Rating).filter(Rating.driver_id == driver_id).all()
    if ratings:
        avg_rating = sum(r.rating for r in ratings) / len(ratings)
        driver = db.query(Driver).filter(Driver.id == driver_id).first()
        if driver:
            driver.rating = Decimal(str(round(avg_rating, 2)))
            db.commit()


def create_notification(
    db: Session,
    title: str,
    message: str,
    notification_type: str,
    user_id: Optional[int] = None,
    driver_id: Optional[int] = None
):
    """Create a notification for user or driver"""
    notification = Notification(
        user_id=user_id,
        driver_id=driver_id,
        title=title,
        message=message,
        notification_type=notification_type
    )
    db.add(notification)
    db.commit()
    db.refresh(notification)
    return notification


def notify_all_drivers(db: Session, title: str, message: str):
    """Send notification to all active drivers"""
    drivers = db.query(Driver).filter(Driver.is_blocked == False).all()
    for driver in drivers:
        create_notification(
            db=db,
            title=title,
            message=message,
            notification_type="new_order",
            driver_id=driver.id
        )


def check_driver_can_accept_order(db: Session, driver_id: int) -> bool:
    """Check if driver can accept orders (not blocked)"""
    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        return False
    
    if driver.is_blocked:
        return False
    
    # Allow acceptance if balance is sufficient (can be negative for credit)
    # Minimum balance requirement removed - drivers can accept orders
    
    return True
