import asyncio
import shutil
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path
from typing import List, Optional, Set, Union

from fastapi import APIRouter, Body, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.encoders import jsonable_encoder
from sqlalchemy import and_, extract, func, or_
from sqlalchemy.orm import Session

from app.auth import get_current_driver, get_current_user
from app.config import settings
from app.database import get_db
from app.models import (
    ApplicationStatus,
    BalanceTransaction,
    DeliveryOrder,
    Driver,
    DriverApplication,
    OrderStatus,
    TaxiOrder,
    Tariff,
    User,
    UserRole,
)
from app.schemas import (
    BonusToBalanceConvertRequest,
    BonusToBalanceConvertResponse,
    DriverBalanceHistoryResponse,
    DriverApplicationCreate,
    DriverApplicationResponse,
    DriverResponse,
    DriverStatistics,
    DriverUpdate,
    DriverWorkStatusUpdate,
)
from app.utils import (
    apply_service_fee_charge,
    check_driver_can_accept_order,
    create_notification,
    record_order_acceptance_history,
    update_order_telegram_message,
)
from app.localization import get_notification_message
from app.websocket import manager

router = APIRouter(prefix="/api/driver", tags=["Driver"])

ACTIVE_ORDER_STATUSES = (OrderStatus.PENDING, OrderStatus.ACCEPTED)
DRIVER_CANCEL_BLOCK_TTL_SECONDS = 24 * 60 * 60  # 24 hours
DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100

# In-memory fallback store when Redis is unavailable
_driver_cancelled_orders: dict[str, dict[int, Set[int]]] = {
    "taxi": {},
    "delivery": {},
}


def _normalize_pagination(limit: Optional[int], offset: Optional[int]) -> tuple[int, int]:
    safe_limit = DEFAULT_PAGE_SIZE if limit is None or limit <= 0 else min(limit, MAX_PAGE_SIZE)
    safe_offset = 0 if offset is None or offset < 0 else offset
    return safe_limit, safe_offset


def _parse_ids_csv(raw_ids: Optional[str]) -> Set[int]:
    """Convert a comma-separated list of integer IDs into a set."""
    if not raw_ids:
        return set()
    candidates = (raw_ids or "").split(",")
    parsed: Set[int] = set()
    for item in candidates:
        try:
            value = int(item.strip())
            if value:
                parsed.add(value)
        except (TypeError, ValueError):
            continue
    return parsed


def _parse_tariffs_csv(raw_tariffs: Optional[str]) -> Set[Tariff]:
    """Convert a comma-separated list of tariff values into a set of Tariff enums."""
    if not raw_tariffs:
        return set()
    parsed: Set[Tariff] = set()
    for item in raw_tariffs.split(","):
        candidate = (item or "").strip().lower()
        if not candidate:
            continue
        try:
            parsed.add(Tariff(candidate))
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid tariff filter. Allowed values: standard, comfort, comfort_plus, business",
            )
    return parsed


def _get_local_cancelled(driver_id: int, order_type: str) -> Set[int]:
    """Fetch the local blacklist set for a driver/order_type combo."""
    if order_type not in _driver_cancelled_orders:
        _driver_cancelled_orders[order_type] = {}
    bucket = _driver_cancelled_orders[order_type]
    if driver_id not in bucket:
        bucket[driver_id] = set()
    return bucket[driver_id]


async def _add_driver_cancelled_order(driver_id: int, order_id: int, order_type: str):
    """Remember that a driver cancelled/rejected an order (Redis + in-memory fallback)."""
    try:
        order_id_int = int(order_id)
    except (TypeError, ValueError):
        return

    _get_local_cancelled(driver_id, order_type).add(order_id_int)

    if manager.redis_pool:
        try:
            key = f"driver_cancelled:{order_type}:{driver_id}"
            await manager.redis_pool.sadd(key, str(order_id_int))
            await manager.redis_pool.expire(key, DRIVER_CANCEL_BLOCK_TTL_SECONDS)
        except Exception:
            pass


async def _get_driver_cancelled_orders(driver_id: int, order_type: str) -> Set[int]:
    """Return the set of order IDs a driver has cancelled/rejected."""
    blocked = set(_get_local_cancelled(driver_id, order_type))

    if manager.redis_pool:
        try:
            key = f"driver_cancelled:{order_type}:{driver_id}"
            members = await manager.redis_pool.smembers(key)
            for item in members:
                try:
                    blocked.add(int(item))
                except (TypeError, ValueError):
                    continue
        except Exception:
            pass

    return blocked


def _should_block_driver(reason: Optional[str]) -> bool:
    """Determine if a release/reject reason should blacklist the driver from the order."""
    if not reason:
        return False
    normalized = reason.strip().lower()
    return normalized in {
        "cancel",
        "cancelled",
        "canceled",
        "driver_cancelled",
        "driver_cancelled_manual",
        "reject",
        "rejected",
        "manual",
    }


def _driver_has_accepted_order(db: Session, driver_id: int) -> bool:
    """Return True if the driver has an active order with status ACCEPTED."""
    taxi_exists = (
        db.query(TaxiOrder.id)
        .filter(
            TaxiOrder.driver_id == driver_id,
            TaxiOrder.status == OrderStatus.ACCEPTED,
        )
        .first()
    )
    if taxi_exists:
        return True
    delivery_exists = (
        db.query(DeliveryOrder.id)
        .filter(
            DeliveryOrder.driver_id == driver_id,
            DeliveryOrder.status == OrderStatus.ACCEPTED,
        )
        .first()
    )
    return bool(delivery_exists)


def _build_driver_payload(driver: Driver) -> dict:
    """Prepare driver info for websocket payloads."""
    user = driver.user
    telephone = None
    avatar = None
    if user:
        telephone = user.telephone
        avatar = user.profile_picture
    rating_value = None
    if driver.rating is not None:
        try:
            rating_value = float(driver.rating)
        except (TypeError, ValueError):
            rating_value = None
    return {
        "id": driver.id,
        "name": driver.full_name,
        "phone_number": telephone,
        "avatar": avatar,
        "car_model": driver.car_model,
        "car_number": driver.car_number,
        "tariff": _enum_value(driver.tariff),
        "rating": rating_value,
    }


async def _notify_passenger_order_status(
    order: Union[TaxiOrder, DeliveryOrder],
    order_type: str,
    status: OrderStatus,
    driver_payload: Optional[dict] = None,
):
    """Push real-time order status updates to the passenger."""
    status_value = status.value if isinstance(status, OrderStatus) else str(status)
    status_timestamp = datetime.now(timezone.utc).isoformat()
    event_type = {
        OrderStatus.ACCEPTED: "order_accepted",
        OrderStatus.COMPLETED: "order_completed",
        OrderStatus.CANCELLED: "order_cancelled",
        OrderStatus.PENDING: "order_status",
    }.get(status, "order_status")

    payload = {
        "type": "order_status",
        "event": event_type,
        "status_event": event_type,
        "status": status_value,
        "status_changed_at": status_timestamp,
        "order_id": order.id,
        "order_type": order_type,
        "user_id": order.user_id,
    }
    if driver_payload:
        payload["driver"] = driver_payload

    await asyncio.gather(
        manager.send_to_user(order.user_id, payload),
        manager.broadcast_to_all_users(payload),
    )


def _decimal_to_float(value):
    """Safely convert Decimal values to float for JSON payloads."""
    if value is None:
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _datetime_to_iso(value: Optional[datetime]) -> Optional[str]:
    return value.isoformat() if isinstance(value, datetime) else None


def _enum_value(value):
    if value is None:
        return None
    return getattr(value, "value", str(value))


def _tariff_level(tariff: Optional[Tariff]) -> int:
    level_map = {
        Tariff.STANDARD: 0,
        Tariff.COMFORT: 1,
        Tariff.COMFORT_PLUS: 2,
        Tariff.BUSINESS: 3,
    }
    return level_map.get(tariff or Tariff.STANDARD, 0)


def _allowed_taxi_tariffs_for_driver(driver_tariff: Optional[Tariff]) -> list[Tariff]:
    driver_level = _tariff_level(driver_tariff)
    all_tariffs = [Tariff.STANDARD, Tariff.COMFORT, Tariff.COMFORT_PLUS, Tariff.BUSINESS]
    return [tariff for tariff in all_tariffs if _tariff_level(tariff) <= driver_level]


def _can_driver_take_taxi_order(driver_tariff: Optional[Tariff], order_tariff: Optional[Tariff]) -> bool:
    return _tariff_level(driver_tariff) >= _tariff_level(order_tariff or Tariff.STANDARD)


def _transaction_source_label(source: str) -> str:
    labels = {
        "admin": "Admin tomonidan qo'shildi",
        "click": "Click orqali to'ldirish",
        "bonus_convert": "Bonusdan balansga o'tkazish",
        "order_fee": "Buyurtma xizmat haqi yechimi",
        "order_fee_refund": "Buyurtma xizmat haqi qaytarimi",
        "other": "Boshqa operatsiya",
    }
    return labels.get(source, labels["other"])


def _transaction_source(transaction: BalanceTransaction) -> str:
    description = (transaction.description or "").strip().lower()
    if transaction.admin_id and transaction.transaction_type == "credit":
        return "admin"
    if description.startswith("click topup"):
        return "click"
    if description == "bonus ball converted to driver balance":
        return "bonus_convert"
    if transaction.transaction_type == "debit" and description.startswith("service fee for"):
        return "order_fee"
    if transaction.transaction_type == "refund" and description.startswith("service fee refund for"):
        return "order_fee_refund"
    return "other"


def _serialize_pending_order_for_driver(order: Union[TaxiOrder, DeliveryOrder], order_type: str) -> dict:
    base = {
        "id": order.id,
        "type": order_type,
        "user_id": order.user_id,
        "driver_id": order.driver_id,
        "from_region_id": order.from_region_id,
        "from_district_id": getattr(order, "from_district_id", None),
        "to_region_id": order.to_region_id,
        "to_district_id": getattr(order, "to_district_id", None),
        "price": _decimal_to_float(order.price),
        "date": order.date,
        "time_start": order.time_start,
        "time_end": order.time_end,
        "scheduled_datetime": _datetime_to_iso(order.scheduled_datetime),
        "created_at": _datetime_to_iso(order.created_at),
        "is_confirmed": order.is_confirmed,
        "confirmed_at": _datetime_to_iso(order.confirmed_at),
        "status": _enum_value(order.status),
    }
    if isinstance(order, TaxiOrder):
        base["passengers"] = order.passengers
        base["seat_type"] = _enum_value(order.seat_type)
        base["tariff"] = _enum_value(order.tariff)
        base["is_new"] = order.is_new
    if isinstance(order, DeliveryOrder):
        base["item_type"] = _enum_value(order.item_type)
    return base


def _is_order_visible_to_driver(
    order: Union[TaxiOrder, DeliveryOrder],
    driver_id: int,
    driver_tariff: Optional[Tariff] = None,
    driver_has_accepted_order: bool = False,
) -> bool:
    """
    Determine whether the current driver is allowed to see the order.
    - Public orders are always visible.
    - Non-public orders are visible to the assigned driver.
    - Drivers with an accepted order can see non-public, unassigned orders for batching.
    - Orders assigned to another driver are never visible.
    """
    if isinstance(order, TaxiOrder) and not _can_driver_take_taxi_order(driver_tariff, order.tariff):
        return False

    assigned_driver_id = getattr(order, "driver_id", None)
    if assigned_driver_id and assigned_driver_id != driver_id:
        return False
    if getattr(order, "public_order", False):
        return True
    if assigned_driver_id == driver_id:
        return True
    if driver_has_accepted_order:
        return True
    return False


def _ensure_order_visibility(
    order: Union[TaxiOrder, DeliveryOrder],
    driver: Driver,
    db: Session,
    driver_has_accepted_order: Optional[bool] = None,
):
    """Enforce visibility rules for a driver on an order."""
    effective_active = (
        driver_has_accepted_order
        if driver_has_accepted_order is not None
        else _driver_has_accepted_order(db, driver.id)
    )
    if not _is_order_visible_to_driver(
        order,
        driver.id,
        driver.tariff,
        effective_active,
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Order is not visible to this driver",
        )


def _serialize_taxi_order_for_passenger(order: TaxiOrder) -> dict:
    payload = {
        "id": order.id,
        "order_type": "taxi",
        "user_id": order.user_id,
        "driver_id": order.driver_id,
        "username": order.username,
        "telephone": order.telephone,
        "from_region_id": order.from_region_id,
        "from_district_id": order.from_district_id,
        "to_region_id": order.to_region_id,
        "to_district_id": order.to_district_id,
        "pickup_latitude": order.pickup_latitude,
        "pickup_longitude": order.pickup_longitude,
        "pickup_address": order.pickup_address,
        "dropoff_latitude": order.dropoff_latitude,
        "dropoff_longitude": order.dropoff_longitude,
        "dropoff_address": order.dropoff_address,
        "passengers": order.passengers,
        "seat_type": _enum_value(order.seat_type),
        "tariff": _enum_value(order.tariff),
        "is_mail_delivery": order.is_mail_delivery,
        "date": order.date,
        "time_start": order.time_start,
        "time_end": order.time_end,
        "scheduled_datetime": _datetime_to_iso(order.scheduled_datetime),
        "price": _decimal_to_float(order.price),
        "service_fee": _decimal_to_float(order.service_fee),
        "driver_earnings": _decimal_to_float(order.driver_earnings),
        "note": order.note,
        "status": _enum_value(order.status),
        "cancellation_reason": order.cancellation_reason,
        "created_at": _datetime_to_iso(order.created_at),
        "accepted_at": _datetime_to_iso(order.accepted_at),
        "completed_at": _datetime_to_iso(order.completed_at),
    }
    if order.driver:
        payload["driver"] = _build_driver_payload(order.driver)
    return payload


def _serialize_delivery_order_for_passenger(order: DeliveryOrder) -> dict:
    payload = {
        "id": order.id,
        "order_type": "delivery",
        "user_id": order.user_id,
        "driver_id": order.driver_id,
        "username": order.username,
        "sender_telephone": order.sender_telephone,
        "receiver_telephone": order.receiver_telephone,
        "from_region_id": order.from_region_id,
        "from_district_id": order.from_district_id,
        "to_region_id": order.to_region_id,
        "to_district_id": order.to_district_id,
        "pickup_latitude": order.pickup_latitude,
        "pickup_longitude": order.pickup_longitude,
        "pickup_address": order.pickup_address,
        "dropoff_latitude": order.dropoff_latitude,
        "dropoff_longitude": order.dropoff_longitude,
        "dropoff_address": order.dropoff_address,
        "item_type": _enum_value(order.item_type),
        "date": order.date,
        "time_start": order.time_start,
        "time_end": order.time_end,
        "scheduled_datetime": _datetime_to_iso(order.scheduled_datetime),
        "price": _decimal_to_float(order.price),
        "service_fee": _decimal_to_float(order.service_fee),
        "driver_earnings": _decimal_to_float(order.driver_earnings),
        "note": order.note,
        "status": _enum_value(order.status),
        "cancellation_reason": order.cancellation_reason,
        "created_at": _datetime_to_iso(order.created_at),
        "accepted_at": _datetime_to_iso(order.accepted_at),
        "completed_at": _datetime_to_iso(order.completed_at),
    }
    if order.driver:
        payload["driver"] = _build_driver_payload(order.driver)
    return payload


def _collect_passenger_active_orders(user_id: int, db: Session) -> List[dict]:
    taxi_orders = db.query(TaxiOrder).filter(
        TaxiOrder.user_id == user_id,
        TaxiOrder.status.in_(ACTIVE_ORDER_STATUSES)
    ).order_by(TaxiOrder.created_at.desc()).all()

    delivery_orders = db.query(DeliveryOrder).filter(
        DeliveryOrder.user_id == user_id,
        DeliveryOrder.status.in_(ACTIVE_ORDER_STATUSES)
    ).order_by(DeliveryOrder.created_at.desc()).all()

    orders: List[dict] = []
    orders.extend(_serialize_taxi_order_for_passenger(order) for order in taxi_orders)
    orders.extend(_serialize_delivery_order_for_passenger(order) for order in delivery_orders)
    orders.sort(key=lambda item: item.get("created_at") or "", reverse=True)
    return orders


async def _push_passenger_active_orders_snapshot(user_id: int, db: Session):
    if not user_id:
        return
    orders = _collect_passenger_active_orders(user_id, db)
    payload = {
        "type": "active_orders_snapshot",
        "user_id": user_id,
        "orders": jsonable_encoder(orders),
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }
    await asyncio.gather(
        manager.send_to_user(user_id, payload),
        manager.broadcast_to_all_users(payload),
    )


async def _collect_available_orders_for_driver(
    driver: Driver,
    db: Session,
    from_region_id: Optional[int] = None,
    from_region_ids: Optional[Set[int]] = None,
    to_region_id: Optional[int] = None,
    to_region_ids: Optional[Set[int]] = None,
    region_id: Optional[int] = None,
    from_district_id: Optional[int] = None,
    from_district_ids: Optional[Set[int]] = None,
    to_district_id: Optional[int] = None,
    to_district_ids: Optional[Set[int]] = None,
    district_id: Optional[int] = None,
    order_type: Optional[str] = None,
    tariff: Optional[str] = None,
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
) -> dict:
    """
    Build the available (pending) orders payload for a driver.

    - Excludes orders held/confirmed by other drivers.
    - Excludes orders the current driver cancelled/rejected.
    """
    if driver.is_blocked:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Blocked drivers cannot view new orders",
        )

    selected_order_types: Set[str] = set()
    if order_type:
        for token in order_type.split(","):
            candidate = token.strip().lower()
            if not candidate or candidate == "all":
                continue
            if candidate not in {"taxi", "delivery"}:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="order_type must contain only 'taxi' and/or 'delivery'",
                )
            selected_order_types.add(candidate)

    include_taxi = not selected_order_types or "taxi" in selected_order_types
    include_delivery = not selected_order_types or "delivery" in selected_order_types
    requested_taxi_tariffs = _parse_tariffs_csv(tariff)

    effective_from_region_ids: Set[int] = set(from_region_ids or set())
    if from_region_id:
        effective_from_region_ids.add(from_region_id)
    if region_id:
        effective_from_region_ids.add(region_id)

    effective_to_region_ids: Set[int] = set(to_region_ids or set())
    if to_region_id:
        effective_to_region_ids.add(to_region_id)

    effective_from_district_ids: Set[int] = set(from_district_ids or set())
    if from_district_id:
        effective_from_district_ids.add(from_district_id)
    if district_id:
        effective_from_district_ids.add(district_id)

    effective_to_district_ids: Set[int] = set(to_district_ids or set())
    if to_district_id:
        effective_to_district_ids.add(to_district_id)
    driver_has_accepted_order = _driver_has_accepted_order(db, driver.id)
    limit, offset = _normalize_pagination(limit, offset)
    fetch_size = limit + offset + 1
    taxi_orders: list[TaxiOrder] = []
    delivery_orders: list[DeliveryOrder] = []

    if include_taxi:
        blocked_taxi_ids = await _get_driver_cancelled_orders(driver.id, "taxi")
        allowed_taxi_tariffs = set(_allowed_taxi_tariffs_for_driver(driver.tariff))
        effective_taxi_tariffs = (
            allowed_taxi_tariffs & requested_taxi_tariffs
            if requested_taxi_tariffs
            else allowed_taxi_tariffs
        )
        if effective_taxi_tariffs:
            include_null_tariff_as_standard = Tariff.STANDARD in effective_taxi_tariffs
            tariff_filter = TaxiOrder.tariff.in_(list(effective_taxi_tariffs))
            if include_null_tariff_as_standard:
                tariff_filter = or_(tariff_filter, TaxiOrder.tariff.is_(None))

            taxi_query = db.query(TaxiOrder).filter(
                TaxiOrder.status == OrderStatus.PENDING,
                or_(TaxiOrder.driver_id.is_(None), TaxiOrder.driver_id == driver.id),
                or_(TaxiOrder.is_confirmed.is_(False), TaxiOrder.driver_id == driver.id),
                tariff_filter,
            )

            if effective_from_region_ids:
                taxi_query = taxi_query.filter(
                    TaxiOrder.from_region_id.in_(effective_from_region_ids),
                )

            if effective_to_region_ids:
                taxi_query = taxi_query.filter(
                    TaxiOrder.to_region_id.in_(effective_to_region_ids),
                )

            if effective_from_district_ids:
                taxi_query = taxi_query.filter(
                    TaxiOrder.from_district_id.in_(effective_from_district_ids),
                )

            if effective_to_district_ids:
                taxi_query = taxi_query.filter(
                    TaxiOrder.to_district_id.in_(effective_to_district_ids),
                )

            if not driver_has_accepted_order:
                taxi_query = taxi_query.filter(
                    or_(TaxiOrder.public_order.is_(True), TaxiOrder.driver_id == driver.id),
                )

            if blocked_taxi_ids:
                taxi_query = taxi_query.filter(~TaxiOrder.id.in_(blocked_taxi_ids))

            taxi_orders = (
                taxi_query.order_by(TaxiOrder.created_at.desc()).limit(fetch_size).all()
            )

    if include_delivery:
        blocked_delivery_ids = await _get_driver_cancelled_orders(driver.id, "delivery")
        delivery_query = db.query(DeliveryOrder).filter(
            DeliveryOrder.status == OrderStatus.PENDING,
            or_(DeliveryOrder.driver_id.is_(None), DeliveryOrder.driver_id == driver.id),
            or_(DeliveryOrder.is_confirmed.is_(False), DeliveryOrder.driver_id == driver.id),
        )

        if effective_from_region_ids:
            delivery_query = delivery_query.filter(
                DeliveryOrder.from_region_id.in_(effective_from_region_ids),
            )

        if effective_to_region_ids:
            delivery_query = delivery_query.filter(
                DeliveryOrder.to_region_id.in_(effective_to_region_ids),
            )

        if effective_from_district_ids:
            delivery_query = delivery_query.filter(
                DeliveryOrder.from_district_id.in_(effective_from_district_ids),
            )

        if effective_to_district_ids:
            delivery_query = delivery_query.filter(
                DeliveryOrder.to_district_id.in_(effective_to_district_ids),
            )

        if not driver_has_accepted_order:
            delivery_query = delivery_query.filter(
                or_(DeliveryOrder.public_order.is_(True), DeliveryOrder.driver_id == driver.id),
            )

        if blocked_delivery_ids:
            delivery_query = delivery_query.filter(
                ~DeliveryOrder.id.in_(blocked_delivery_ids),
            )

        delivery_orders = (
            delivery_query.order_by(DeliveryOrder.created_at.desc())
            .limit(fetch_size)
            .all()
        )

    combined: list[tuple[str, Union[TaxiOrder, DeliveryOrder], datetime]] = []
    combined.extend(
        ("taxi", order, order.created_at or datetime.min) for order in taxi_orders
    )
    combined.extend(
        ("delivery", order, order.created_at or datetime.min) for order in delivery_orders
    )
    combined.sort(key=lambda item: item[2], reverse=True)
    window = combined[offset : offset + limit]
    has_more = len(combined) > offset + limit

    taxi_payload: List[dict] = []
    delivery_payload: List[dict] = []

    for item in window:
        order_type, order, _ = item
        if order_type == "taxi" and isinstance(order, TaxiOrder):
            taxi_payload.append(
                {
                    "id": order.id,
                    "type": "taxi",
                    "user_id": order.user_id,
                    "driver_id": order.driver_id,
                    "from_region_id": order.from_region_id,
                    "from_district_id": order.from_district_id,
                    "to_region_id": order.to_region_id,
                    "to_district_id": order.to_district_id,
                    "passengers": order.passengers,
                    "client_gender": _enum_value(order.client_gender),
                    "seat_type": _enum_value(order.seat_type),
                    "tariff": _enum_value(order.tariff),
                    "is_new": order.is_new,
                    "price": str(order.price),
                    "date": order.date,
                    "time_start": order.time_start,
                    "time_end": order.time_end,
                    "scheduled_datetime": order.scheduled_datetime.isoformat()
                    if order.scheduled_datetime
                    else None,
                    "created_at": order.created_at.isoformat(),
                    "note": order.note,
                    "is_confirmed": order.is_confirmed,
                    "confirmed_at": order.confirmed_at.isoformat()
                    if order.confirmed_at
                    else None,
                    "status": order.status.value,
                },
            )
        elif order_type == "delivery" and isinstance(order, DeliveryOrder):
            delivery_payload.append(
                {
                    "id": order.id,
                    "type": "delivery",
                    "user_id": order.user_id,
                    "driver_id": order.driver_id,
                    "from_region_id": order.from_region_id,
                    "from_district_id": order.from_district_id,
                    "to_region_id": order.to_region_id,
                    "to_district_id": order.to_district_id,
                    "item_type": order.item_type.value,
                    "price": str(order.price),
                    "date": order.date,
                    "time_start": order.time_start,
                    "time_end": order.time_end,
                    "scheduled_datetime": order.scheduled_datetime.isoformat()
                    if order.scheduled_datetime
                    else None,
                    "created_at": order.created_at.isoformat(),
                    "note": order.note,
                    "is_confirmed": order.is_confirmed,
                    "confirmed_at": order.confirmed_at.isoformat()
                    if order.confirmed_at
                    else None,
                    "status": order.status.value,
                },
            )

    return {
        "taxi_orders": taxi_payload,
        "delivery_orders": delivery_payload,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "returned": len(window),
            "has_more": has_more,
        },
    }


async def _broadcast_order_to_eligible_drivers(
    payload: dict,
    order_id: int,
    order_type: str,
    exclude_driver_ids: Optional[Set[int]] = None,
):
    """
    Send an order payload only to drivers who haven't cancelled/rejected it.
    Falls back to a full broadcast if we can't resolve active driver ids.
    """
    try:
        normalized_order_id = int(order_id)
    except (TypeError, ValueError):
        normalized_order_id = None

    normalized_exclude: Set[int] = set()
    if exclude_driver_ids:
        for driver_id in exclude_driver_ids:
            try:
                normalized_exclude.add(int(driver_id))
            except (TypeError, ValueError):
                continue

    candidate_driver_ids: Set[int] = set(manager.driver_connections.keys())
    if manager.redis_pool:
        try:
            active_driver_ids = await manager.redis_pool.smembers("active_drivers")
            for raw_id in active_driver_ids:
                try:
                    candidate_driver_ids.add(int(raw_id))
                except (TypeError, ValueError):
                    continue
        except Exception:
            pass

    # If we failed to resolve active drivers or order id, keep old behaviour.
    if not candidate_driver_ids or normalized_order_id is None:
        await manager.broadcast_to_all_drivers(payload)
        return

    sanitized_payload = dict(payload)
    sanitized_payload.pop("_exclude_driver_ids", None)

    send_tasks = []
    for driver_id in candidate_driver_ids:
        if driver_id in normalized_exclude:
            continue
        cancelled_orders = await _get_driver_cancelled_orders(driver_id, order_type)
        if normalized_order_id in cancelled_orders:
            continue
        send_tasks.append(manager.send_to_driver(driver_id, sanitized_payload))

    if send_tasks:
        await asyncio.gather(*send_tasks, return_exceptions=True)


@router.post("/apply", response_model=DriverApplicationResponse, status_code=status.HTTP_201_CREATED)
async def apply_as_driver(
    application_data: DriverApplicationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Apply to become a driver"""
    # Check if user already has an active driver profile
    if current_user.driver_profile and current_user.role == UserRole.DRIVER:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You are already a driver"
        )
    
    # Check if user already has an application (any status)
    existing_application = db.query(DriverApplication).filter(
        DriverApplication.user_id == current_user.id
    ).first()
    
    if existing_application:
        if existing_application.status == ApplicationStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You already have a pending application"
            )
        # Update existing application and reset status to pending
        existing_application.full_name = application_data.full_name
        existing_application.car_model = application_data.car_model
        existing_application.car_number = application_data.car_number
        existing_application.license_photo = application_data.license_photo
        existing_application.car_photo = application_data.car_photo
        existing_application.tex_pas = application_data.tex_pas
        existing_application.telephone = current_user.telephone
        existing_application.status = ApplicationStatus.PENDING
        existing_application.rejection_reason = None
        existing_application.reviewed_by = None
        existing_application.reviewed_at = None
        db.commit()
        db.refresh(existing_application)
        return existing_application
    
    # Create application
    new_application = DriverApplication(
        user_id=current_user.id,
        full_name=application_data.full_name,
        telephone=current_user.telephone,
        car_model=application_data.car_model,
        car_number=application_data.car_number,
        license_photo=application_data.license_photo,
        car_photo=application_data.car_photo,
        tex_pas=application_data.tex_pas,
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
    
    if driver_update.car_photo is not None:
        driver.car_photo = driver_update.car_photo
    
    if driver_update.tex_pas is not None:
        driver.tex_pas = driver_update.tex_pas
    
    db.commit()
    db.refresh(driver)
    
    return driver


@router.patch("/profile/is-worked", response_model=DriverResponse)
def update_driver_work_status(
    payload: DriverWorkStatusUpdate,
    current_user: User = Depends(get_current_driver),
    db: Session = Depends(get_db),
):
    """Update current driver's work status."""
    driver = current_user.driver_profile
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver profile not found",
        )

    driver.is_worked = payload.is_worked
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
    
    today = datetime.now(timezone.utc).date()
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


@router.post("/bonus/convert", response_model=BonusToBalanceConvertResponse)
def convert_bonus_to_balance(
    convert_data: BonusToBalanceConvertRequest,
    current_user: User = Depends(get_current_driver),
    db: Session = Depends(get_db),
):
    """Convert driver's bonus_ball to driver balance."""
    driver = (
        db.query(Driver)
        .filter(Driver.user_id == current_user.id)
        .with_for_update()
        .first()
    )
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver profile not found",
        )

    user = (
        db.query(User)
        .filter(User.id == current_user.id)
        .with_for_update()
        .first()
    )
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    amount = convert_data.amount.quantize(Decimal("0.01"))
    bonus_ball = (user.bonus_ball or Decimal("0.00")).quantize(Decimal("0.01"))
    if amount > bonus_ball:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Requested amount exceeds available bonus ball",
        )

    user.bonus_ball = (bonus_ball - amount).quantize(Decimal("0.01"))
    driver.balance = ((driver.balance or Decimal("0.00")) + amount).quantize(Decimal("0.01"))

    transaction = BalanceTransaction(
        driver_id=driver.id,
        amount=amount,
        transaction_type="credit",
        description="Bonus ball converted to driver balance",
    )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    db.refresh(user)
    db.refresh(driver)

    notification = get_notification_message("balance_added", amount=amount)
    create_notification(
        db=db,
        title=notification["title"],
        message=notification["message"],
        notification_type="balance_added",
        driver_id=driver.id,
    )

    return {
        "success": True,
        "message": "Bonus successfully converted to balance",
        "transferred_amount": amount,
        "bonus_ball": user.bonus_ball,
        "balance": driver.balance,
        "transaction_id": transaction.id,
    }


@router.get("/balance/history", response_model=DriverBalanceHistoryResponse)
def get_driver_balance_history(
    transaction_type: Optional[str] = Query(default=None),
    source: Optional[str] = Query(default=None),
    period: Optional[str] = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_driver),
    db: Session = Depends(get_db),
):
    """Get current driver's balance transaction history with readable source labels."""
    allowed_sources = {"admin", "click", "bonus_convert", "order_fee", "order_fee_refund", "other"}
    if source and source not in allowed_sources:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid source. Must be one of: admin, click, bonus_convert, order_fee, order_fee_refund, other",
        )
    period_aliases = {
        "day": "day",
        "kun": "day",
        "month": "month",
        "oy": "month",
        "year": "year",
        "yil": "year",
        "yillik": "year",
    }
    normalized_period = None
    if period:
        normalized_period = period_aliases.get(period.strip().lower())
        if not normalized_period:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid period. Must be one of: day/kun, month/oy, year/yil/yillik",
            )

    driver = db.query(Driver).filter(Driver.user_id == current_user.id).first()
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver profile not found",
        )

    query = (
        db.query(BalanceTransaction)
        .filter(BalanceTransaction.driver_id == driver.id)
        .order_by(BalanceTransaction.created_at.desc())
    )

    if transaction_type:
        if transaction_type not in {"credit", "debit", "refund"}:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid transaction_type. Must be 'credit', 'debit', or 'refund'",
            )
        query = query.filter(BalanceTransaction.transaction_type == transaction_type)

    if normalized_period:
        now = datetime.now(timezone.utc)
        if normalized_period == "day":
            start_at = now.replace(hour=0, minute=0, second=0, microsecond=0)
            end_at = start_at + timedelta(days=1)
        elif normalized_period == "month":
            start_at = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            if start_at.month == 12:
                end_at = start_at.replace(year=start_at.year + 1, month=1)
            else:
                end_at = start_at.replace(month=start_at.month + 1)
        else:  # normalized_period == "year"
            start_at = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            end_at = start_at.replace(year=start_at.year + 1)
        query = query.filter(
            BalanceTransaction.created_at >= start_at,
            BalanceTransaction.created_at < end_at,
        )

    transactions = query.all()
    filtered = []
    for transaction in transactions:
        tx_source = _transaction_source(transaction)
        if source and source != tx_source:
            continue
        filtered.append((transaction, tx_source))

    page_items = filtered[offset : offset + limit]
    admin_ids = {transaction.admin_id for transaction, _ in page_items if transaction.admin_id}
    admins = {}
    if admin_ids:
        admins = {
            admin.id: admin.name
            for admin in db.query(User).filter(User.id.in_(admin_ids)).all()
        }

    return {
        "total": len(filtered),
        "current_balance": driver.balance,
        "transactions": [
            {
                "id": transaction.id,
                "amount": transaction.amount,
                "transaction_type": transaction.transaction_type,
                "description": transaction.description,
                "source": tx_source,
                "source_label": _transaction_source_label(tx_source),
                "admin_id": transaction.admin_id,
                "admin_name": admins.get(transaction.admin_id) if transaction.admin_id else None,
                "created_at": transaction.created_at,
            }
            for transaction, tx_source in page_items
        ],
    }


@router.get("/orders/my-orders")
def get_my_orders(
    status_filter: Optional[OrderStatus] = None,
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
    current_user: User = Depends(get_current_driver),
    db: Session = Depends(get_db)
):
    """Get driver's accepted and completed orders"""
    driver = current_user.driver_profile
    
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver profile not found"
        )
    
    # Build query for taxi orders assigned to this driver
    limit, offset = _normalize_pagination(limit, offset)
    fetch_size = limit + offset + 1

    taxi_query = db.query(TaxiOrder).filter(TaxiOrder.driver_id == driver.id)
    delivery_query = db.query(DeliveryOrder).filter(DeliveryOrder.driver_id == driver.id)
    
    # Apply status filter if provided
    if status_filter:
        taxi_query = taxi_query.filter(TaxiOrder.status == status_filter)
        delivery_query = delivery_query.filter(DeliveryOrder.status == status_filter)
    
    taxi_orders = (
        taxi_query.order_by(TaxiOrder.created_at.desc()).limit(fetch_size).all()
    )
    delivery_orders = (
        delivery_query.order_by(DeliveryOrder.created_at.desc()).limit(fetch_size).all()
    )

    combined: list[tuple[str, Union[TaxiOrder, DeliveryOrder], datetime]] = []
    combined.extend(
        ("taxi", order, order.created_at or datetime.min) for order in taxi_orders
    )
    combined.extend(
        ("delivery", order, order.created_at or datetime.min)
        for order in delivery_orders
    )
    combined.sort(key=lambda item: item[2], reverse=True)
    window = combined[offset : offset + limit]
    has_more = len(combined) > offset + limit

    taxi_payload: List[dict] = []
    delivery_payload: List[dict] = []

    for order_type, order, _ in window:
        if order_type == "taxi" and isinstance(order, TaxiOrder):
            taxi_payload.append(
                {
                    "id": order.id,
                    "type": "taxi",
                    "user_id": order.user_id,
                    "username": order.username,
                    "telephone": order.telephone,
                    "from_region_id": order.from_region_id,
                    "from_district_id": order.from_district_id,
                    "to_region_id": order.to_region_id,
                    "to_district_id": order.to_district_id,
                    "pickup_address": order.pickup_address,
                    "pickup_latitude": order.pickup_latitude,
                    "pickup_longitude": order.pickup_longitude,
                    "dropoff_address": order.dropoff_address,
                    "dropoff_latitude": order.dropoff_latitude,
                    "dropoff_longitude": order.dropoff_longitude,
                    "passengers": order.passengers,
                    "client_gender": _enum_value(order.client_gender),
                    "tariff": _enum_value(order.tariff),
                    "is_new": order.is_new,
                    "price": str(order.price),
                    "service_fee": str(order.service_fee),
                    "driver_earnings": str(order.driver_earnings),
                    "date": order.date,
                    "time_start": order.time_start,
                    "time_end": order.time_end,
                    "scheduled_datetime": order.scheduled_datetime.isoformat()
                    if order.scheduled_datetime
                    else None,
                    "status": order.status.value,
                    "note": order.note,
                    "created_at": order.created_at.isoformat()
                    if order.created_at
                    else None,
                    "accepted_at": order.accepted_at.isoformat()
                    if order.accepted_at
                    else None,
                    "completed_at": order.completed_at.isoformat()
                    if order.completed_at
                    else None,
                    "is_confirmed": order.is_confirmed,
                    "confirmed_at": order.confirmed_at.isoformat()
                    if order.confirmed_at
                    else None,
                },
            )
        elif order_type == "delivery" and isinstance(order, DeliveryOrder):
            delivery_payload.append(
                {
                    "id": order.id,
                    "type": "delivery",
                    "user_id": order.user_id,
                    "username": order.username,
                    "sender_telephone": order.sender_telephone,
                    "receiver_telephone": order.receiver_telephone,
                    "from_region_id": order.from_region_id,
                    "from_district_id": order.from_district_id,
                    "to_region_id": order.to_region_id,
                    "to_district_id": order.to_district_id,
                    "pickup_address": order.pickup_address,
                    "pickup_latitude": order.pickup_latitude,
                    "pickup_longitude": order.pickup_longitude,
                    "dropoff_address": order.dropoff_address,
                    "dropoff_latitude": order.dropoff_latitude,
                    "dropoff_longitude": order.dropoff_longitude,
                    "item_type": order.item_type.value,
                    "price": str(order.price),
                    "service_fee": str(order.service_fee),
                    "driver_earnings": str(order.driver_earnings),
                    "date": order.date,
                    "time_start": order.time_start,
                    "time_end": order.time_end,
                    "scheduled_datetime": order.scheduled_datetime.isoformat()
                    if order.scheduled_datetime
                    else None,
                    "status": order.status.value,
                    "note": order.note,
                    "created_at": order.created_at.isoformat()
                    if order.created_at
                    else None,
                    "accepted_at": order.accepted_at.isoformat()
                    if order.accepted_at
                    else None,
                    "completed_at": order.completed_at.isoformat()
                    if order.completed_at
                    else None,
                    "is_confirmed": order.is_confirmed,
                    "confirmed_at": order.confirmed_at.isoformat()
                    if order.confirmed_at
                    else None,
                },
            )

    return {
        "taxi_orders": taxi_payload,
        "delivery_orders": delivery_payload,
        "pagination": {
            "limit": limit,
            "offset": offset,
            "returned": len(window),
            "has_more": has_more,
        },
    }


@router.get("/orders/active")
async def get_active_orders(
    from_region_id: Optional[int] = None,
    from_region_ids: Optional[str] = Query(None),
    to_region_id: Optional[int] = None,
    to_region_ids: Optional[str] = Query(None),
    region_id: Optional[int] = None,
    from_district_id: Optional[int] = None,
    from_district_ids: Optional[str] = Query(None),
    to_district_id: Optional[int] = None,
    to_district_ids: Optional[str] = Query(None),
    district_id: Optional[int] = None,
    order_type: Optional[str] = None,
    tariff: Optional[str] = Query(None),
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
    current_user: User = Depends(get_current_driver),
    db: Session = Depends(get_db),
):
    """
    Get the current pool of active (pending/available) orders for drivers.

    This endpoint now mirrors `/orders/new` so newly created orders are
    discoverable, while hiding orders being viewed/held by other drivers.
    """
    driver = current_user.driver_profile

    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver profile not found",
        )

    return await _collect_available_orders_for_driver(
        driver,
        db,
        from_region_id=from_region_id,
        from_region_ids=_parse_ids_csv(from_region_ids),
        to_region_id=to_region_id,
        to_region_ids=_parse_ids_csv(to_region_ids),
        region_id=region_id,
        from_district_id=from_district_id,
        from_district_ids=_parse_ids_csv(from_district_ids),
        to_district_id=to_district_id,
        to_district_ids=_parse_ids_csv(to_district_ids),
        district_id=district_id,
        order_type=order_type,
        tariff=tariff,
        limit=limit,
        offset=offset,
    )


@router.get("/orders/history")
def get_order_history(
    current_user: User = Depends(get_current_driver),
    db: Session = Depends(get_db)
):
    """Get driver's completed orders history"""
    driver = current_user.driver_profile
    
    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver profile not found"
        )
    
    # Get only COMPLETED orders
    taxi_orders = db.query(TaxiOrder).filter(
        TaxiOrder.driver_id == driver.id,
        TaxiOrder.status == OrderStatus.COMPLETED
    ).order_by(TaxiOrder.completed_at.desc()).all()
    
    delivery_orders = db.query(DeliveryOrder).filter(
        DeliveryOrder.driver_id == driver.id,
        DeliveryOrder.status == OrderStatus.COMPLETED
    ).order_by(DeliveryOrder.completed_at.desc()).all()
    
    return {
        "taxi_orders": [
            {
                "id": order.id,
                "type": "taxi",
                "username": order.username,
                "from_region_id": order.from_region_id,
                "to_region_id": order.to_region_id,
                "passengers": order.passengers,
                "tariff": _enum_value(order.tariff),
                "price": str(order.price),
                "service_fee": str(order.service_fee),
                "driver_earnings": str(order.driver_earnings),
                "date": order.date,
                "status": order.status.value,
                "accepted_at": order.accepted_at.isoformat() if order.accepted_at else None,
                "completed_at": order.completed_at.isoformat() if order.completed_at else None
            }
            for order in taxi_orders
        ],
        "delivery_orders": [
            {
                "id": order.id,
                "type": "delivery",
                "username": order.username,
                "from_region_id": order.from_region_id,
                "to_region_id": order.to_region_id,
                "item_type": order.item_type.value,
                "price": str(order.price),
                "service_fee": str(order.service_fee),
                "driver_earnings": str(order.driver_earnings),
                "date": order.date,
                "status": order.status.value,
                "accepted_at": order.accepted_at.isoformat() if order.accepted_at else None,
                "completed_at": order.completed_at.isoformat() if order.completed_at else None
            }
            for order in delivery_orders
        ]
    }


@router.get("/orders/new")
async def get_new_orders(
    from_region_id: Optional[int] = None,
    from_region_ids: Optional[str] = Query(None),
    to_region_id: Optional[int] = None,
    to_region_ids: Optional[str] = Query(None),
    region_id: Optional[int] = None,
    from_district_id: Optional[int] = None,
    from_district_ids: Optional[str] = Query(None),
    to_district_id: Optional[int] = None,
    to_district_ids: Optional[str] = Query(None),
    district_id: Optional[int] = None,
    order_type: Optional[str] = None,
    tariff: Optional[str] = Query(None),
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
    current_user: User = Depends(get_current_driver),
    db: Session = Depends(get_db),
):
    """Get new pending orders for drivers."""
    driver = current_user.driver_profile

    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver profile not found",
        )

    return await _collect_available_orders_for_driver(
        driver,
        db,
        from_region_id=from_region_id,
        from_region_ids=_parse_ids_csv(from_region_ids),
        to_region_id=to_region_id,
        to_region_ids=_parse_ids_csv(to_region_ids),
        region_id=region_id,
        from_district_id=from_district_id,
        from_district_ids=_parse_ids_csv(from_district_ids),
        to_district_id=to_district_id,
        to_district_ids=_parse_ids_csv(to_district_ids),
        district_id=district_id,
        order_type=order_type,
        tariff=tariff,
        limit=limit,
        offset=offset,
    )


@router.post("/orders/preview/{order_type}/{order_id}")
async def preview_order(
    order_type: str,
    order_id: int,
    current_user: User = Depends(get_current_driver),
    db: Session = Depends(get_db),
):
    """
    Mark a pending order as being previewed by the current driver.

    This sets `is_confirmed = True` for pending orders so that
    they are treated as "held" and are not shown to other drivers.
    """
    driver = current_user.driver_profile

    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver profile not found",
        )

    # Get order based on type
    if order_type == "taxi":
        order = db.query(TaxiOrder).filter(TaxiOrder.id == order_id).first()
    elif order_type == "delivery":
        order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order type. Must be 'taxi' or 'delivery'",
        )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending orders can be previewed",
        )

    _ensure_order_visibility(order, driver, db)

    # If another driver is already holding this order, deny preview
    if order.driver_id and order.driver_id != driver.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is currently reserved by another driver",
        )

    # Mark order as held by this driver (but still pending)
    order.driver_id = driver.id
    order.is_confirmed = True
    order.accepted_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(order)

    # Broadcast reservation so other drivers hide this order
    await manager.broadcast_to_all_drivers(
        {
            "type": "order_reserved",
            "order_id": order.id,
            "order_type": order_type,
            "driver_id": driver.id,
            "reserved_until": order.accepted_at.isoformat()
            if order.accepted_at
            else datetime.now(timezone.utc).isoformat(),
        }
    )

    return {
        "success": True,
        "message": "Order preview started",
        "order": {
            "id": order.id,
            "type": order_type,
            "status": order.status.value,
            "is_confirmed": order.is_confirmed,
        },
    }


@router.post("/orders/preview/release/{order_type}/{order_id}")
async def release_preview_order(
    order_type: str,
    order_id: int,
    current_user: User = Depends(get_current_driver),
    db: Session = Depends(get_db),
    reason: Optional[str] = Body(default=None, embed=True),
):
    """
    Release preview/hold for a pending order so that it becomes visible
    to other drivers again.
    """
    driver = current_user.driver_profile

    if not driver:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Driver profile not found",
        )

    # Get order based on type
    if order_type == "taxi":
        order = db.query(TaxiOrder).filter(TaxiOrder.id == order_id).first()
    elif order_type == "delivery":
        order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order type. Must be 'taxi' or 'delivery'",
        )

    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found",
        )

    if order.status != OrderStatus.PENDING:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending orders can be released from preview",
        )

    if order.driver_id != driver.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You are not holding this order",
        )

    # Return order to general pool
    order.driver_id = None
    order.is_confirmed = False
    order.accepted_at = None

    db.commit()
    db.refresh(order)

    if _should_block_driver(reason):
        await _add_driver_cancelled_order(driver.id, order.id, order_type)

    # Notify all drivers that this order is available again
    await _broadcast_order_to_eligible_drivers(
        {
            "type": "order_returned",
            "order_id": order.id,
            "order_type": order_type,
            "driver_id": driver.id,
            "reason": "Preview released",
            "order": _serialize_pending_order_for_driver(order, order_type),
        },
        order.id,
        order_type,
        exclude_driver_ids={driver.id},
    )

    return {
        "success": True,
        "message": "Order preview released",
        "order": {
            "id": order.id,
            "type": order_type,
            "status": order.status.value,
        },
    }


@router.post("/orders/accept/{order_type}/{order_id}")
async def accept_order(
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

    _ensure_order_visibility(order, driver, db)

    # Accept order - no time limit check
    order.driver_id = driver.id
    order.status = OrderStatus.ACCEPTED
    order.accepted_at = datetime.now(timezone.utc)
    order.is_confirmed = False  # Not confirmed yet

    record_order_acceptance_history(
        db=db,
        driver_id=driver.id,
        order_type=order_type,
        order_id=order.id,
        action="accepted",
    )
    
    db.commit()
    db.refresh(order)
    
    # Release order lock
    await manager.release_order_lock(order_id)
    
    driver_payload = _build_driver_payload(driver)
    
    # Notify all drivers that this order is no longer available (WebSocket)
    await manager.broadcast_to_all_drivers({
        "type": "order_accepted",
        "order_id": order.id,
        "order_type": order_type,
        "driver_id": driver.id
    })
    
    # Notify user via WebSocket (direct + broadcast for filtering)
    await _notify_passenger_order_status(
        order=order,
        order_type=order_type,
        status=OrderStatus.ACCEPTED,
        driver_payload=driver_payload,
    )
    
    # Notify user via database notification
    notification = get_notification_message("order_accepted", order_id=order.id, order_type=order_type)
    create_notification(
        db=db,
        title=notification["title"],
        message=notification["message"],
        notification_type="order_accepted",
        user_id=order.user_id
    )

    await _push_passenger_active_orders_snapshot(order.user_id, db)

    telegram_message_id = await update_order_telegram_message(
        db=db,
        order=order,
        order_type=order_type,
        status_label="Qabul qilindi",
        driver=driver,
    )
    if telegram_message_id and telegram_message_id != order.telegram_message_id:
        order.telegram_message_id = telegram_message_id
        db.commit()
    
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
async def complete_order(
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
    
    # Check if order is confirmed
    if not order.is_confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must be confirmed before completion"
        )
    
    # Complete order
    order.status = OrderStatus.COMPLETED
    order.completed_at = datetime.now(timezone.utc)

    db.commit()
    db.refresh(order)
    db.refresh(driver)
    
    # Calculate and apply bonus if bonus_user_id is set
    from app.utils import calculate_and_apply_bonus
    bonus_amount = calculate_and_apply_bonus(db, order)
    
    # Notify user
    notification = get_notification_message("order_completed", order_id=order.id, order_type=order_type)
    create_notification(
        db=db,
        title=notification["title"],
        message=notification["message"],
        notification_type="order_completed",
        user_id=order.user_id
    )
    
    await _notify_passenger_order_status(
        order=order,
        order_type=order_type,
        status=OrderStatus.COMPLETED,
        driver_payload=_build_driver_payload(driver),
    )

    await _push_passenger_active_orders_snapshot(order.user_id, db)
    
    return {
        "success": True,
        "message": "Order completed successfully",
        "order": {
            "id": order.id,
            "type": order_type,
            "status": order.status
        }
    }


@router.post("/orders/confirm/{order_type}/{order_id}")
async def confirm_order(
    order_type: str,
    order_id: int,
    current_user: User = Depends(get_current_driver),
    db: Session = Depends(get_db)
):
    """Confirm an accepted order within 15 minutes"""
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
            detail="Invalid order type. Must be 'taxi' or 'delivery'"
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
            detail="Only accepted orders can be confirmed"
        )
    
    if order.is_confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is already confirmed"
        )
    
    # Check if confirmation time has expired (15 minutes)
    if order.accepted_at:
        time_diff = datetime.now(timezone.utc) - order.accepted_at
        if time_diff > timedelta(minutes=15):
            # Return order to pending state
            old_driver_id = order.driver_id
            order.driver_id = None
            order.status = OrderStatus.PENDING
            order.accepted_at = None
            order.is_confirmed = False
            
            db.commit()
            db.refresh(order)
            
            # Notify all drivers that order is available again
            await _broadcast_order_to_eligible_drivers(
                {
                    "type": "order_returned",
                    "order_id": order.id,
                    "order_type": order_type,
                    "reason": "Confirmation time expired",
                    "driver_id": old_driver_id,
                    "order": _serialize_pending_order_for_driver(order, order_type),
                },
                order.id,
                order_type,
            )
            
            # Notify the driver who lost the order
            notification = get_notification_message("order_expired", order_id=order.id, order_type=order_type)
            create_notification(
                db=db,
                title=notification["title"],
                message=notification["message"],
                notification_type="order_expired",
                driver_id=driver.id
            )
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Confirmation time has expired (15 minutes). Order returned to pending list."
            )
    
    # Confirm order
    order.is_confirmed = True
    order.confirmed_at = datetime.now(timezone.utc)
    charge_result = apply_service_fee_charge(db, order, order_type)

    db.commit()
    db.refresh(order)
    db.refresh(driver)

    if charge_result:
        fee_amount, charged_driver_id = charge_result
        notification = get_notification_message("service_fee_deducted", amount=fee_amount, order_id=order.id)
        create_notification(
            db=db,
            title=notification["title"],
            message=notification["message"],
            notification_type="service_fee_charged",
            driver_id=charged_driver_id,
        )
    
    # Notify user
    notification = get_notification_message("order_confirmed", order_id=order.id, order_type=order_type)
    create_notification(
        db=db,
        title=notification["title"],
        message=notification["message"],
        notification_type="order_confirmed",
        user_id=order.user_id
    )
    
    # Notify user via WebSocket
    driver_payload = _build_driver_payload(driver)
    await manager.send_to_user(order.user_id, {
        "type": "order_confirmed",
        "order_id": order.id,
        "order_type": order_type,
        "driver": driver_payload,
        "confirmed_at": order.confirmed_at.isoformat()
    })
    
    await _push_passenger_active_orders_snapshot(order.user_id, db)
    
    return {
        "success": True,
        "message": "Order confirmed successfully",
        "order": {
            "id": order.id,
            "type": order_type,
            "status": order.status,
            "is_confirmed": order.is_confirmed,
            "confirmed_at": order.confirmed_at.isoformat() if order.confirmed_at else None
        }
    }


@router.post("/orders/reject/{order_type}/{order_id}")
async def reject_order(
    order_type: str,
    order_id: int,
    current_user: User = Depends(get_current_driver),
    db: Session = Depends(get_db)
):
    """Reject an accepted order and return it to pending list"""
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
            detail="Invalid order type. Must be 'taxi' or 'delivery'"
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
            detail="Only accepted orders can be rejected"
        )
    
    if order.is_confirmed:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Confirmed orders cannot be rejected. Please complete the order."
        )
    
    previous_driver_id = order.driver_id

    # Return order to pending state
    order.driver_id = None
    order.status = OrderStatus.PENDING
    order.accepted_at = None
    order.is_confirmed = False

    record_order_acceptance_history(
        db=db,
        driver_id=previous_driver_id,
        order_type=order_type,
        order_id=order.id,
        action="returned_to_pending",
    )
    
    db.commit()
    db.refresh(order)

    await _add_driver_cancelled_order(driver.id, order.id, order_type)
    
    # Notify all drivers that order is available again
    await _broadcast_order_to_eligible_drivers(
        {
            "type": "order_returned",
            "order_id": order.id,
            "order_type": order_type,
            "driver_id": driver.id,
            "reason": "Driver rejected",
            "order": _serialize_pending_order_for_driver(order, order_type),
        },
        order.id,
        order_type,
        exclude_driver_ids={driver.id},
    )
    
    # Notify user
    notification = get_notification_message("order_returned", order_id=order.id, order_type=order_type)
    create_notification(
        db=db,
        title=notification["title"],
        message=notification["message"],
        notification_type="order_rejected",
        user_id=order.user_id
    )
    
    await _push_passenger_active_orders_snapshot(order.user_id, db)
    
    return {
        "success": True,
        "message": "Order rejected and returned to pending list",
        "order": {
            "id": order.id,
            "type": order_type,
            "status": order.status
        }
    }
