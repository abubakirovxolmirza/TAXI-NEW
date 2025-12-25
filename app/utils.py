import asyncio
import json
import urllib.parse
import urllib.request
from datetime import datetime, timezone, timedelta
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
    District,
    Language,
    Notification,
    OrderAcceptanceHistory,
    Pricing,
    Region,
    SystemSettings,
    User,
    UserRole,
)
from app.websocket import manager
from app.localization import get_notification_message

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
    passengers: int,
    seat_type: Optional[str] = None,
    from_district_id: Optional[int] = None,
    to_district_id: Optional[int] = None
) -> Decimal:
    """Calculate taxi price with district-level pricing support (district > region > default)"""
    from app.models import SeatType, DistrictPricing
    
    total_passengers = passengers if passengers and passengers > 0 else 1
    pricing = None
    
    # Try district-level pricing first (if both districts provided)
    if from_district_id and to_district_id:
        pricing = db.query(DistrictPricing).filter(
            DistrictPricing.from_district_id == from_district_id,
            DistrictPricing.to_district_id == to_district_id,
            DistrictPricing.service_type == "taxi",
            DistrictPricing.is_active == True
        ).first()
    
    # Fallback to region-level pricing
    if not pricing:
        pricing = db.query(Pricing).filter(
            Pricing.from_region_id == from_region_id,
            Pricing.to_region_id == to_region_id,
            Pricing.service_type == "taxi",
            Pricing.is_active == True
        ).first()

    if not pricing:
        # Default pricing if not set (per passenger)
        return _quantize_money(Decimal("50000.00") * Decimal(total_passengers))

    # Determine seat type if not provided
    if seat_type is None:
        # Default to BACK (rear) seat for all cases, including single passenger
        # Front seat should only be used when explicitly requested
        seat_type = SeatType.BACK
    
    # Convert string to SeatType if needed
    if isinstance(seat_type, str):
        seat_type = SeatType(seat_type)

    # Check for seat-specific pricing
    base_price = pricing.base_price or Decimal("0.00")
    
    if seat_type == SeatType.FRONT and pricing.front_seat_price:
        base_price = pricing.front_seat_price
    elif seat_type == SeatType.BACK and pricing.back_seat_price:
        base_price = pricing.back_seat_price

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
    to_region_id: int,
    from_district_id: Optional[int] = None,
    to_district_id: Optional[int] = None
) -> Decimal:
    """Calculate delivery price with district-level pricing support (district > region > default)"""
    from app.models import DistrictPricing
    
    pricing = None
    
    # Try district-level pricing first (if both districts provided)
    if from_district_id and to_district_id:
        pricing = db.query(DistrictPricing).filter(
            DistrictPricing.from_district_id == from_district_id,
            DistrictPricing.to_district_id == to_district_id,
            DistrictPricing.service_type == "delivery",
            DistrictPricing.is_active == True
        ).first()
    
    # Fallback to region-level pricing
    if not pricing:
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


def record_order_acceptance_history(
    db: Session,
    driver_id: Optional[int],
    order_type: str,
    order_id: int,
    action: str,
):
    """
    Persist an acceptance history entry for either taxi or delivery orders.
    The caller is responsible for committing the session.
    """
    if not driver_id or not action or order_type not in {"taxi", "delivery"}:
        return None

    history = OrderAcceptanceHistory(
        driver_id=driver_id,
        taxi_order_id=order_id if order_type == "taxi" else None,
        delivery_order_id=order_id if order_type == "delivery" else None,
        action=action,
        received_at=datetime.now(timezone.utc),
    )
    db.add(history)
    return history


def get_last_history_driver_id(db: Session, order_type: str, order_id: int) -> Optional[int]:
    """Return the latest driver_id that interacted with this order in history."""
    if order_type not in {"taxi", "delivery"}:
        return None

    query = db.query(OrderAcceptanceHistory.driver_id)
    if order_type == "taxi":
        query = query.filter(OrderAcceptanceHistory.taxi_order_id == order_id)
    else:
        query = query.filter(OrderAcceptanceHistory.delivery_order_id == order_id)

    latest = query.order_by(OrderAcceptanceHistory.created_at.desc()).first()
    if not latest:
        return None
    return latest.driver_id


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


def calculate_and_apply_bonus(db: Session, order: Union["TaxiOrder", "DeliveryOrder"]) -> Optional[Decimal]:
    """
    Calculate bonus based on order price and active bonus percentage.
    Add bonus to the bonus_user if specified.
    
    Returns: The bonus amount added (or None if no bonus_user_id)
    """
    from app.models import Bonus
    
    # Check if bonus_user_id is set
    if not order.bonus_user_id:
        return None
    
    # Get the active bonus configuration
    bonus_config = db.query(Bonus).filter(Bonus.is_active == True).first()
    
    if not bonus_config:
        # No active bonus configuration
        return None
    
    # Get the bonus user
    bonus_user = db.query(User).filter(User.id == order.bonus_user_id).first()
    
    if not bonus_user:
        # Bonus user not found
        return None
    
    # Calculate bonus amount
    bonus_percent = bonus_config.bonus_percent
    total_price = order.price
    bonus_amount = _quantize_money((total_price * bonus_percent) / Decimal("100.00"))
    
    # Add bonus to user's bonus_ball
    bonus_user.bonus_ball = _quantize_money(bonus_user.bonus_ball + bonus_amount)
    
    db.commit()
    
    # Create notification for bonus user
    notification = get_notification_message("bonus_earned", amount=bonus_amount, order_id=order.id)
    create_notification(
        db=db,
        title=notification["title"],
        message=notification["message"],
        notification_type="bonus_earned",
        user_id=bonus_user.id
    )
    
    return bonus_amount


def _telegram_enabled() -> bool:
    return bool(settings.TELEGRAM_ORDER_BOT_TOKEN and settings.TELEGRAM_ORDER_CHANNEL_ID)


def _telegram_api_request(method: str, payload: dict) -> Optional[dict]:
    if not _telegram_enabled():
        return None
    token = settings.TELEGRAM_ORDER_BOT_TOKEN
    url = f"https://api.telegram.org/bot{token}/{method}"
    data = urllib.parse.urlencode(payload).encode("utf-8")
    request = urllib.request.Request(url, data=data)
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            content = response.read().decode("utf-8")
            return json.loads(content)
    except Exception as exc:
        print(f"Telegram API error: {exc}")
        return None


def _resolve_region_name(db: Session, region_id: Optional[int]) -> str:
    if not region_id:
        return "-"
    region = db.query(Region).filter(Region.id == region_id).first()
    if not region:
        return str(region_id)
    return region.name_uz_latin or str(region_id)


def _resolve_district_name(db: Session, district_id: Optional[int]) -> str:
    if not district_id:
        return "-"
    district = db.query(District).filter(District.id == district_id).first()
    if not district:
        return str(district_id)
    return district.name_uz_latin or str(district_id)


def _build_order_telegram_message(
    db: Session,
    order: Union["TaxiOrder", "DeliveryOrder"],
    order_type: str,
    status_label: str,
    driver: Optional[Driver] = None,
) -> str:
    def _format_price(value) -> str:
        try:
            amount = int(value)
            formatted = format(amount, ",").replace(",", " ")
            return f"{formatted} so'm"
        except Exception:
            return f"{value} so'm"

    def _format_schedule(dt: datetime) -> str:
        """Format datetime in Uzbekistan timezone (UTC+5) for Telegram messages"""
        try:
            # Define Uzbekistan timezone (UTC+5)
            uzbekistan_tz = timezone(timedelta(hours=5))
            
            # Convert to Uzbekistan timezone
            # If datetime is naive, assume it's already in UTC
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            
            local_dt = dt.astimezone(uzbekistan_tz)
            
            months = [
                "yanvar",
                "fevral",
                "mart",
                "aprel",
                "may",
                "iyun",
                "iyul",
                "avgust",
                "sentabr",
                "oktabr",
                "noyabr",
                "dekabr",
            ]
            month_name = months[local_dt.month - 1] if 1 <= local_dt.month <= 12 else local_dt.strftime("%b")
            return f"{local_dt.day:02d}-{month_name} {local_dt.year} • {local_dt:%H:%M}"
        except Exception:
            # Fallback to a simple readable format if conversion fails
            try:
                return f"{dt.day:02d}.{dt.month:02d}.{dt.year} • {dt.hour:02d}:{dt.minute:02d}"
            except Exception:
                return str(dt)

    from_region = _resolve_region_name(db, order.from_region_id)
    to_region = _resolve_region_name(db, order.to_region_id)
    from_district = _resolve_district_name(db, order.from_district_id)
    to_district = _resolve_district_name(db, order.to_district_id)
    
    # Format scheduled time in a human-readable way
    if order.scheduled_datetime:
        reja_vaqt = _format_schedule(order.scheduled_datetime)
    else:
        # Fallback to date and time strings if scheduled_datetime is not available
        reja_vaqt = f"{order.date} • {order.time_start}-{order.time_end}"
    
    lines: list[str] = []
    if order_type == "taxi":
        lines.extend(
            [
                "🚖 *YANGI TAKSI BUYURTMA*",
                "",
                "👤 *Mijoz:*",
                f"{order.username}",
                "",
                "📍 *Yo'nalish:*",
                f"{from_region}, {from_district} ➡️ {to_region}, {to_district}",
                "",
                f"👥 *Yo'lovchilar soni:* {order.passengers} ta",
                "",
                "⏰ *Reja vaqt:*",
                reja_vaqt,
                "",
                "💰 *Narx:*",
                _format_price(order.price),
            ]
        )
    else:
        item_type = getattr(order.item_type, "value", order.item_type)
        lines.extend(
            [
                "📦 *YANGI YETKAZIB BERISH BUYURTMA*",
                "",
                "👤 *Jo'natuvchi:*",
                f"{order.username}",
                "",
                "📍 *Yo'nalish:*",
                f"{from_region}, {from_district} ➡️ {to_region}, {to_district}",
                "",
                f"🧾 *Yuk turi:* {item_type}",
                "",
                "⏰ *Reja vaqt:*",
                reja_vaqt,
                "",
                "💰 *Narx:*",
                _format_price(order.price),
            ]
        )
    if order.note:
        lines.extend(["", f"📝 *Izoh:* {order.note}"])
    # Only show driver information for orders that have been accepted (not in PENDING status)
    # This prevents showing empty/incorrect driver fields for newly created orders
    from app.models import OrderStatus
    if driver and order.status != OrderStatus.PENDING:
        driver_phone = driver.user.telephone if driver.user else "-"
        lines.extend(
            [
                "",
                f"🚗 *Haydovchi:* {driver.full_name}",
                f"📞 *Haydovchi tel:* {driver_phone}",
                f"🚙 *Avto:* {driver.car_model} {driver.car_number}",
            ]
        )
    return "\n".join(lines)


def _send_telegram_message(text: str) -> Optional[int]:
    payload = {
        "chat_id": settings.TELEGRAM_ORDER_CHANNEL_ID,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    response = _telegram_api_request("sendMessage", payload)
    if not response or not response.get("ok"):
        return None
    result = response.get("result") or {}
    return result.get("message_id")


def _edit_telegram_message(message_id: int, text: str) -> bool:
    payload = {
        "chat_id": settings.TELEGRAM_ORDER_CHANNEL_ID,
        "message_id": message_id,
        "text": text,
        "parse_mode": "Markdown",
        "disable_web_page_preview": True,
    }
    response = _telegram_api_request("editMessageText", payload)
    return bool(response and response.get("ok"))


async def send_order_telegram_message(
    db: Session,
    order: Union["TaxiOrder", "DeliveryOrder"],
    order_type: str,
    status_label: str,
    driver: Optional[Driver] = None,
) -> Optional[int]:
    if not _telegram_enabled():
        return None
    message = _build_order_telegram_message(db, order, order_type, status_label, driver)
    return await asyncio.to_thread(_send_telegram_message, message)


async def update_order_telegram_message(
    db: Session,
    order: Union["TaxiOrder", "DeliveryOrder"],
    order_type: str,
    status_label: str,
    driver: Optional[Driver] = None,
) -> Optional[int]:
    if not _telegram_enabled():
        return None
    message = _build_order_telegram_message(db, order, order_type, status_label, driver)
    message_id = getattr(order, "telegram_message_id", None)
    if message_id:
        updated = await asyncio.to_thread(_edit_telegram_message, message_id, message)
        if updated:
            return message_id
    return await asyncio.to_thread(_send_telegram_message, message)
