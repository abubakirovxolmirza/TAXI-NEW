import asyncio
import json
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, Tuple, Union, TYPE_CHECKING
import uuid

import redis
from sqlalchemy.orm import Session

from app.auth import get_password_hash
from app.config import settings
from app.models import (
    BalanceTransaction,
    Driver,
    Language,
    Notification,
    Pricing,
    SystemSettings,
    User,
    UserRole,
)
from app.websocket import manager

if TYPE_CHECKING:
    from app.models import TaxiOrder, DeliveryOrder

# Default platform service fee percentage (fallback if not set in DB)
DEFAULT_SERVICE_FEE_PERCENTAGE = Decimal("10.00")  # 10%
MONEY_QUANTIZE = Decimal("0.01")


def _quantize_money(value: Decimal) -> Decimal:
    """Round monetary values to 2 decimal places using bankers-friendly rounding."""
    return value.quantize(MONEY_QUANTIZE, rounding=ROUND_HALF_UP)


def get_or_create_guest_user(db: Session, telephone: str, username: str) -> User:
    """
    Get existing user by telephone or create a new guest user.
    This allows orders to be created without authentication.
    """
    # Try to find existing user by telephone
    user = db.query(User).filter(User.telephone == telephone).first()
    
    if user:
        return user
    
    # Create new guest user
    # Generate random password for guest users
    random_password = str(uuid.uuid4())
    
    guest_user = User(
        telephone=telephone,
        name=username,
        hashed_password=get_password_hash(random_password),
        role=UserRole.USER,
        language=Language.UZ_LATIN,
        is_active=True
    )
    
    db.add(guest_user)
    db.commit()
    db.refresh(guest_user)
    
    return guest_user


def get_service_fee_percentage(db: Session) -> Decimal:
    """
    Get current service fee percentage from database settings
    Returns: Decimal percentage (e.g., 10.00 for 10%)
    """
    setting = db.query(SystemSettings).filter(
        SystemSettings.setting_key == "service_fee_percentage"
    ).first()
    
    if setting:
        return Decimal(setting.setting_value)
    return DEFAULT_SERVICE_FEE_PERCENTAGE


def calculate_service_fee(price: Decimal, db: Session) -> Tuple[Decimal, Decimal]:
    """
    Calculate service fee and driver earnings
    Returns: (service_fee, driver_earnings)
    """
    price = _quantize_money(price)
    service_fee_percentage = get_service_fee_percentage(db)
    service_fee = _quantize_money((price * service_fee_percentage) / Decimal("100.00"))
    driver_earnings = _quantize_money(price - service_fee)
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
    
    total_passengers = passengers if passengers and passengers > 0 else 1

    if not pricing:
        # Default pricing if not set (per passenger)
        return _quantize_money(Decimal("50000.00") * Decimal(total_passengers))

    base_price = pricing.base_price or Decimal("0.00")

    # Apply discount based on passengers
    discount = Decimal("0.00")
    if total_passengers == 1:
        discount = pricing.discount_1_passenger or Decimal("0.00")
    elif total_passengers == 2:
        discount = pricing.discount_2_passengers or Decimal("0.00")
    elif total_passengers == 3:
        discount = pricing.discount_3_passengers or Decimal("0.00")
    elif total_passengers >= 4:
        discount = pricing.discount_full_car or Decimal("0.00")

    effective_multiplier = (Decimal("100.00") - discount) / Decimal("100.00")
    total_price = base_price * effective_multiplier * Decimal(total_passengers)
    if total_price < Decimal("0.00"):
        total_price = Decimal("0.00")

    return _quantize_money(total_price)


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
        return _quantize_money(Decimal("30000.00"))

    return _quantize_money(pricing.base_price or Decimal("0.00"))


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
    driver_id: Optional[int] = None,
    driver_status_payload: Optional[dict] = None,
) -> Notification:
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
    _dispatch_notification_event(notification)
    if driver_status_payload:
        target_user_id = (
            driver_status_payload.get("user_id")
            or user_id
            or getattr(notification.driver, "user_id", None)
        )
        payload_status = driver_status_payload.get("status")
        if target_user_id and payload_status:
            dispatch_driver_status_event(
                user_id=target_user_id,
                status=payload_status,
                title=driver_status_payload.get("title", title),
                message=driver_status_payload.get("message", message),
                driver_id=driver_status_payload.get("driver_id", driver_id),
                application_id=driver_status_payload.get("application_id"),
            )
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


def _normalize_order_type(order_type: str) -> str:
    normalized = (order_type or "order").strip().lower()
    if normalized not in {"taxi", "delivery"}:
        return "order"
    return normalized


def _service_fee_description(order_type: str, order_id: int) -> str:
    order_label = _normalize_order_type(order_type)
    return f"Service fee for {order_label} order #{order_id}"


def _service_fee_refund_description(order_type: str, order_id: int) -> str:
    order_label = _normalize_order_type(order_type)
    return f"Service fee refund for {order_label} order #{order_id}"


def apply_service_fee_charge(
    db: Session,
    order: Union["TaxiOrder", "DeliveryOrder"],
    order_type: str,
) -> Optional[Tuple[Decimal, int]]:
    """Deduct the platform service fee from the driver's balance."""
    driver_id = getattr(order, "driver_id", None)
    if not driver_id:
        return None

    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        return None

    fee_amount = getattr(order, "service_fee", None)
    if fee_amount is None or fee_amount <= Decimal("0"):
        return None

    description = _service_fee_description(order_type, order.id)
    existing_charge = db.query(BalanceTransaction).filter(
        BalanceTransaction.driver_id == driver.id,
        BalanceTransaction.transaction_type == "debit",
        BalanceTransaction.description == description,
    ).first()
    if existing_charge:
        return None

    driver.balance = (driver.balance or Decimal("0")) - fee_amount
    transaction = BalanceTransaction(
        driver_id=driver.id,
        amount=fee_amount,
        transaction_type="debit",
        description=description,
    )
    db.add(transaction)
    db.flush()

    return fee_amount, driver.id


def apply_service_fee_refund(
    db: Session,
    order: Union["TaxiOrder", "DeliveryOrder"],
    order_type: str,
) -> Optional[Tuple[Decimal, int]]:
    """Refund a previously charged service fee back to the driver."""
    driver_id = getattr(order, "driver_id", None)
    if not driver_id:
        return None

    driver = db.query(Driver).filter(Driver.id == driver_id).first()
    if not driver:
        return None

    fee_amount = getattr(order, "service_fee", None)
    if fee_amount is None or fee_amount <= Decimal("0"):
        return None

    description = _service_fee_description(order_type, order.id)
    charge_exists = db.query(BalanceTransaction).filter(
        BalanceTransaction.driver_id == driver.id,
        BalanceTransaction.transaction_type == "debit",
        BalanceTransaction.description == description,
    ).first()
    if not charge_exists:
        return None

    refund_description = _service_fee_refund_description(order_type, order.id)
    existing_refund = db.query(BalanceTransaction).filter(
        BalanceTransaction.driver_id == driver.id,
        BalanceTransaction.transaction_type == "refund",
        BalanceTransaction.description == refund_description,
    ).first()
    if existing_refund:
        return None

    driver.balance = (driver.balance or Decimal("0")) + fee_amount
    transaction = BalanceTransaction(
        driver_id=driver.id,
        amount=fee_amount,
        transaction_type="refund",
        description=refund_description,
    )
    db.add(transaction)
    db.flush()

    return fee_amount, driver.id


def _serialize_notification(notification: Notification) -> dict:
    created_at = notification.created_at
    if not isinstance(created_at, datetime):
        created_at = datetime.now(timezone.utc)
    return {
        "id": notification.id,
        "title": notification.title,
        "message": notification.message,
        "type": notification.notification_type,
        "notification_type": notification.notification_type,
        "is_read": notification.is_read,
        "created_at": created_at.isoformat(),
    }


def _dispatch_notification_event(notification: Notification):
    event_payload = _serialize_notification(notification)
    driver_user_id: Optional[int] = None
    if notification.driver_id:
        try:
            driver = notification.driver
        except Exception:
            driver = None
        if driver and driver.user_id:
            driver_user_id = driver.user_id

    target_user_id = notification.user_id or driver_user_id
    if not target_user_id and not notification.driver_id:
        return

    event = {
        "type": "notification",
        "event": "notification_created",
        "notification": event_payload,
    }
    if target_user_id:
        event["user_id"] = target_user_id
    if notification.driver_id:
        event["driver_id"] = notification.driver_id

    _dispatch_realtime_event(
        user_id=target_user_id,
        user_payload=event,
        driver_id=notification.driver_id,
        driver_payload=event if notification.driver_id else None,
    )


def dispatch_driver_status_event(
    *,
    user_id: int,
    status: str,
    title: str,
    message: str,
    driver_id: Optional[int] = None,
    application_id: Optional[int] = None,
):
    """Push driver status update to a specific user via WebSocket."""
    normalized_status = status.lower().strip()
    if not user_id or not normalized_status:
        return

    timestamp_token = int(datetime.now(timezone.utc).timestamp() * 1_000_000)
    event_id = f"driver_status:{user_id}:{timestamp_token}"
    base_payload = {
        "type": "driver_status",
        "status": normalized_status,
        "title": title,
        "message": message,
        "user_id": user_id,
        "event_id": event_id,
    }
    if driver_id is not None:
        base_payload["driver_id"] = driver_id
    if application_id is not None:
        base_payload["application_id"] = application_id

    user_payload = dict(base_payload)
    user_payload["channel"] = "user"

    driver_payload = None
    if driver_id is not None:
        driver_payload = dict(base_payload)
        driver_payload["channel"] = "driver"

    _dispatch_realtime_event(
        user_id=user_id,
        user_payload=user_payload,
        driver_id=driver_id,
        driver_payload=driver_payload,
        broadcast_user=True,
    )


def _dispatch_realtime_event(
    *,
    user_id: Optional[int],
    user_payload: Optional[dict],
    driver_id: Optional[int] = None,
    driver_payload: Optional[dict] = None,
    broadcast_user: bool = False,
):
    """Send realtime payloads either via active manager loop or Redis fallback."""
    if not user_payload and not driver_payload:
        return

    loop = getattr(manager, "_loop", None)
    if loop:
        async def _send():
            tasks = []
            if user_id and user_payload:
                tasks.append(manager.send_to_user(user_id, user_payload))
            if broadcast_user and user_payload:
                tasks.append(manager.broadcast_to_all_users(user_payload))
            if driver_id and driver_payload:
                tasks.append(manager.send_to_driver(driver_id, driver_payload))
            if tasks:
                await asyncio.gather(*tasks, return_exceptions=True)

        manager.submit_background_task(_send())
        return

    _publish_realtime_via_redis(
        user_id=user_id,
        user_payload=user_payload,
        driver_id=driver_id,
        driver_payload=driver_payload,
        broadcast_user=broadcast_user,
    )


def _publish_realtime_via_redis(
    *,
    user_id: Optional[int],
    user_payload: Optional[dict],
    driver_id: Optional[int],
    driver_payload: Optional[dict],
    broadcast_user: bool,
):
    """Fallback dispatcher used when websocket manager loop is unavailable."""
    redis_url = settings.REDIS_URL
    if not redis_url:
        return

    client = None
    try:
        client = redis.Redis.from_url(
            redis_url,
            encoding="utf-8",
            decode_responses=True,
        )
    except Exception as exc:
        print(f"Redis fallback connection error: {exc}")
        return

    def _publish(channel: str, payload: dict):
        try:
            client.publish(channel, json.dumps(payload))
        except Exception as exc:
            print(f"Redis fallback publish error: {exc}")

    try:
        if user_payload:
            if user_id:
                _publish("users_channel", {"user_id": user_id, "message": user_payload})
            if broadcast_user:
                _publish("users_channel", user_payload)
        if driver_payload and driver_id:
            _publish(
                "drivers_channel",
                {"driver_id": driver_id, "message": driver_payload},
            )
    finally:
        if client:
            try:
                client.close()
            except Exception:
                pass
