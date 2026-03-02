from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func, or_
from typing import List, Optional
from datetime import datetime, timezone
from app.database import get_db
from app.models import User, DeliveryOrder, OrderStatus, Driver, UserRole
from app.schemas import DeliveryOrderCreate, DeliveryOrderResponse, OrderCancellation, BulkDeleteRequest
from app.auth import get_current_user, get_optional_user
from app.services.phone import digits_only, normalize_phone
from app.utils import (
    apply_service_fee_refund,
    calculate_delivery_price,
    create_notification,
    calculate_service_fee,
    get_last_history_driver_id,
    get_or_create_guest_user,
    record_order_acceptance_history,
    send_order_telegram_message,
)
from app.localization import get_notification_message
from app.websocket import manager

DEFAULT_PAGE_SIZE = 10
MAX_PAGE_SIZE = 100


def _normalize_pagination(limit: Optional[int], offset: Optional[int]) -> tuple[int, int]:
    safe_limit = DEFAULT_PAGE_SIZE if limit is None or limit <= 0 else min(limit, MAX_PAGE_SIZE)
    safe_offset = 0 if offset is None or offset < 0 else offset
    return safe_limit, safe_offset


def _delivery_order_query(db: Session):
    return db.query(DeliveryOrder).options(
        joinedload(DeliveryOrder.driver).joinedload(Driver.user)
    )


def _phone_variants(phone: Optional[str]) -> set[str]:
    if not phone:
        return set()

    raw = str(phone).strip()
    variants = {raw} if raw else set()
    normalized = normalize_phone(raw)
    if normalized:
        variants.add(normalized)
    digits = digits_only(raw)
    if digits:
        variants.add(digits)
        if digits.startswith("998") and len(digits) == 12:
            variants.add(f"+{digits}")
            variants.add(f"0{digits[3:]}")
            variants.add(digits[3:])
    return {item for item in variants if item}


def _receiver_match_condition(user_phone: Optional[str]):
    phone_variants = _phone_variants(user_phone)
    if not phone_variants:
        return DeliveryOrder.id == -1

    digit_variants = {
        "".join(ch for ch in value if ch.isdigit())
        for value in phone_variants
        if any(ch.isdigit() for ch in value)
    }
    digit_variants = {value for value in digit_variants if value}

    receiver_digits = func.regexp_replace(DeliveryOrder.receiver_telephone, r"\D", "", "g")
    clauses = [DeliveryOrder.receiver_telephone.in_(phone_variants)]
    if digit_variants:
        clauses.append(receiver_digits.in_(digit_variants))
    return or_(*clauses)


def _is_order_receiver(order: DeliveryOrder, user_phone: Optional[str]) -> bool:
    if not user_phone:
        return False
    variants = _phone_variants(user_phone)
    if not variants:
        return False

    receiver_phone = str(order.receiver_telephone or "").strip()
    if receiver_phone in variants:
        return True

    receiver_digits = "".join(ch for ch in receiver_phone if ch.isdigit())
    return bool(receiver_digits and receiver_digits in {
        "".join(ch for ch in value if ch.isdigit()) for value in variants
    })


router = APIRouter(prefix="/api/delivery-orders", tags=["Delivery Orders"])


@router.post("/", response_model=DeliveryOrderResponse, status_code=status.HTTP_201_CREATED)
async def create_delivery_order(
    order_data: DeliveryOrderCreate,
    current_user: Optional[User] = Depends(get_optional_user),
    db: Session = Depends(get_db)
):
    """Create a new delivery order (works with or without authentication)"""
    # If user is not authenticated, create or get guest user
    if current_user is None:
        current_user = get_or_create_guest_user(
            db=db,
            telephone=order_data.sender_telephone,
            username=order_data.username
        )
    # Calculate price (district pricing > region pricing > default)
    price = calculate_delivery_price(
        db=db,
        from_region_id=order_data.from_region_id,
        to_region_id=order_data.to_region_id,
        from_district_id=order_data.from_district_id,
        to_district_id=order_data.to_district_id
    )
    
    # Calculate service fee and driver earnings
    service_fee, driver_earnings = calculate_service_fee(price, db)
    
    # Get default pending time from system settings (15 seconds by default)
    from app.models import SystemSettings
    pending_time_setting = db.query(SystemSettings).filter(
        SystemSettings.setting_key == "public_order_pending_time"
    ).first()
    default_pending_time = int(pending_time_setting.setting_value) if pending_time_setting else 15
    
    # Create order
    new_order = DeliveryOrder(
        user_id=current_user.id,
        bonus_user_id=order_data.bonus_user_id,
        username=order_data.username,
        sender_telephone=order_data.sender_telephone,
        receiver_telephone=order_data.receiver_telephone,
        from_region_id=order_data.from_region_id,
        from_district_id=order_data.from_district_id,
        to_region_id=order_data.to_region_id,
        to_district_id=order_data.to_district_id,
        pickup_latitude=order_data.pickup_latitude,
        pickup_longitude=order_data.pickup_longitude,
        pickup_address=order_data.pickup_address,
        dropoff_latitude=order_data.dropoff_latitude,
        dropoff_longitude=order_data.dropoff_longitude,
        dropoff_address=order_data.dropoff_address,
        who_pay=order_data.who_pay,
        item_type=order_data.item_type,
        date=order_data.date,
        time_start=order_data.time_start,
        time_end=order_data.time_end,
        scheduled_datetime=order_data.scheduled_datetime,
        price=price,
        service_fee=service_fee,
        driver_earnings=driver_earnings,
        note=order_data.note,
        status=OrderStatus.PENDING,
        public_order=False,
        is_new=True,
        pending_time=default_pending_time
    )
    
    db.add(new_order)
    db.commit()
    db.refresh(new_order)

    telegram_message_id = await send_order_telegram_message(
        db=db,
        order=new_order,
        order_type="delivery",
        status_label="Kutilmoqda",
    )
    if telegram_message_id:
        new_order.telegram_message_id = telegram_message_id
        db.commit()
        db.refresh(new_order)
    
    # Notify order owner only
    notification = get_notification_message("delivery_order_created", order_id=new_order.id)
    create_notification(
        db=db,
        title=notification["title"],
        message=notification["message"],
        notification_type="order_created",
        user_id=current_user.id,
    )
    
    # Broadcast to all drivers via WebSocket
    import asyncio
    order_data_dict = {
        "id": new_order.id,
        "type": "delivery",
        "from_region_id": new_order.from_region_id,
        "to_region_id": new_order.to_region_id,
        "item_type": new_order.item_type.value,
        "who_pay": new_order.who_pay,
        "price": float(new_order.price),
        "service_fee": float(new_order.service_fee),
        "driver_earnings": float(new_order.driver_earnings),
        "date": new_order.date,
        "time_start": new_order.time_start,
        "time_end": new_order.time_end,
        "scheduled_datetime": new_order.scheduled_datetime.isoformat() if new_order.scheduled_datetime else None,
        "created_at": new_order.created_at.isoformat(),
        "public_order": new_order.public_order,
        "is_new": new_order.is_new,
    }
    if new_order.public_order:
        asyncio.create_task(manager.broadcast_to_all_drivers({
            "type": "new_order",
            "order": order_data_dict
        }))
    elif new_order.driver_id:
        asyncio.create_task(manager.send_to_driver(new_order.driver_id, {
            "type": "new_order",
            "order": order_data_dict
        }))
    
    return new_order


@router.get("/", response_model=List[DeliveryOrderResponse])
def get_all_delivery_orders(
    status_filter: Optional[OrderStatus] = None,
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all delivery orders"""
    limit, offset = _normalize_pagination(limit, offset)
    query = _delivery_order_query(db)
    
    if status_filter:
        query = query.filter(DeliveryOrder.status == status_filter)
    
    orders = query.order_by(DeliveryOrder.created_at.desc()).offset(offset).limit(limit).all()
    return orders


@router.get("/active", response_model=List[DeliveryOrderResponse])
def get_active_delivery_orders(
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get active delivery orders (pending or accepted)"""
    limit, offset = _normalize_pagination(limit, offset)
    receiver_condition = _receiver_match_condition(current_user.telephone)
    orders = _delivery_order_query(db).filter(
        or_(
            DeliveryOrder.user_id == current_user.id,
            receiver_condition,
        ),
        DeliveryOrder.status.in_([OrderStatus.PENDING, OrderStatus.ACCEPTED])
    ).order_by(DeliveryOrder.created_at.desc()).offset(offset).limit(limit).all()
    
    return orders


@router.get("/history", response_model=List[DeliveryOrderResponse])
def get_delivery_order_history(
    limit: int = DEFAULT_PAGE_SIZE,
    offset: int = 0,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get completed and cancelled delivery orders"""
    limit, offset = _normalize_pagination(limit, offset)
    receiver_condition = _receiver_match_condition(current_user.telephone)
    history_ordering = func.coalesce(
        DeliveryOrder.completed_at,
        DeliveryOrder.cancelled_at,
        DeliveryOrder.created_at,
    )
    orders = _delivery_order_query(db).filter(
        or_(
            DeliveryOrder.user_id == current_user.id,
            receiver_condition,
        ),
        DeliveryOrder.status.in_([OrderStatus.COMPLETED, OrderStatus.CANCELLED])
    ).order_by(history_ordering.desc()).offset(offset).limit(limit).all()
    
    return orders


@router.get("/{order_id}", response_model=DeliveryOrderResponse)
def get_delivery_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get delivery order details"""
    order = _delivery_order_query(db).filter(DeliveryOrder.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if user owns the order or is the assigned driver
    if order.user_id != current_user.id:
        is_driver = current_user.driver_profile and order.driver_id == current_user.driver_profile.id
        is_receiver = _is_order_receiver(order, current_user.telephone)
        if not is_driver and not is_receiver:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to view this order"
            )
    
    return order


@router.delete("/delete-all", status_code=status.HTTP_200_OK)
def delete_all_delivery_orders(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete all delivery orders (Admin/Superadmin only)"""
    
    # Only admin or superadmin can delete all orders
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can delete all orders"
        )
    
    # Get all delivery orders
    all_orders = db.query(DeliveryOrder).all()
    total_orders = len(all_orders)
    
    if total_orders == 0:
        return {
            "message": "No orders to delete",
            "total_deleted": 0
        }
    
    # Delete all orders
    db.query(DeliveryOrder).delete()
    db.commit()
    
    return {
        "message": "Barcha yetkazib berish buyurtmalari muvaffaqiyatli o'chirildi",
        "total_deleted": total_orders
    }


@router.delete("/{order_id}", status_code=status.HTTP_200_OK)
def delete_delivery_order(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete a delivery order (only for cancelled or completed orders)"""
    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Allow order owner, admin, or superadmin to delete
    is_owner = order.user_id == current_user.id
    is_admin_or_superadmin = current_user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]
    
    if not (is_owner or is_admin_or_superadmin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to delete this order"
        )
    
    # Only allow deleting cancelled or completed orders
    if order.status not in [OrderStatus.CANCELLED, OrderStatus.COMPLETED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only cancelled or completed orders can be deleted"
        )
    
    # Delete the order
    db.delete(order)
    db.commit()
    
    return {
        "message": "Buyurtma muvaffaqiyatli o'chirildi",
        "order_id": order_id
    }


@router.post("/bulk-delete", status_code=status.HTTP_200_OK)
def bulk_delete_delivery_orders(
    delete_request: BulkDeleteRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Delete multiple delivery orders at once (only for cancelled or completed orders)"""
    
    # Check if user is admin or superadmin
    is_admin_or_superadmin = current_user.role in [UserRole.ADMIN, UserRole.SUPERADMIN]
    
    deleted_orders = []
    failed_orders = []
    
    for order_id in delete_request.order_ids:
        order = db.query(DeliveryOrder).filter(DeliveryOrder.id == order_id).first()
        
        if not order:
            failed_orders.append({
                "order_id": order_id,
                "reason": "Order not found"
            })
            continue
        
        # Allow order owner, admin, or superadmin to delete
        is_owner = order.user_id == current_user.id
        
        if not (is_owner or is_admin_or_superadmin):
            failed_orders.append({
                "order_id": order_id,
                "reason": "Not authorized to delete this order"
            })
            continue
        
        # Only allow deleting cancelled or completed orders
        if order.status not in [OrderStatus.CANCELLED, OrderStatus.COMPLETED]:
            failed_orders.append({
                "order_id": order_id,
                "reason": "Only cancelled or completed orders can be deleted"
            })
            continue
        
        # Delete the order
        db.delete(order)
        deleted_orders.append(order_id)
    
    db.commit()
    
    return {
        "message": f"Successfully deleted {len(deleted_orders)} order(s)",
        "deleted_orders": deleted_orders,
        "failed_orders": failed_orders,
        "total_requested": len(delete_request.order_ids),
        "total_deleted": len(deleted_orders),
        "total_failed": len(failed_orders)
    }


@router.post("/cancel", response_model=DeliveryOrderResponse)
async def cancel_delivery_order(
    cancellation: OrderCancellation,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Cancel a delivery order"""
    order = db.query(DeliveryOrder).filter(DeliveryOrder.id == cancellation.order_id).first()
    
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    is_owner = order.user_id == current_user.id
    driver_profile = current_user.driver_profile
    is_assigned_driver = driver_profile and order.driver_id == driver_profile.id
    if not (is_owner or is_assigned_driver):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this order"
        )
    
    if order.status not in [OrderStatus.PENDING, OrderStatus.ACCEPTED]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only pending or accepted orders can be cancelled"
        )
    if is_assigned_driver and order.status != OrderStatus.ACCEPTED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Drivers can only cancel accepted orders"
        )

    previous_status = order.status
    previous_driver_id = order.driver_id
    history_driver_id = previous_driver_id or get_last_history_driver_id(db, "delivery", order.id)
    
    # Update order status
    order.status = OrderStatus.CANCELLED
    order.cancellation_reason = cancellation.cancellation_reason
    order.cancelled_by_user_id = current_user.id
    order.cancelled_by_role = current_user.role.value if current_user.role else None
    order.cancelled_at = datetime.now(timezone.utc)
    refund_result = apply_service_fee_refund(db, order, "delivery")

    if history_driver_id:
        if previous_status == OrderStatus.ACCEPTED:
            record_order_acceptance_history(
                db=db,
                driver_id=history_driver_id,
                order_type="delivery",
                order_id=order.id,
                action="cancel_after_accept",
            )
        elif previous_status == OrderStatus.PENDING:
            record_order_acceptance_history(
                db=db,
                driver_id=history_driver_id,
                order_type="delivery",
                order_id=order.id,
                action="cancel_from_pending",
            )
    
    db.commit()
    db.refresh(order)
    
    # Notify driver if order was accepted
    if order.driver_id:
        driver = db.query(Driver).filter(Driver.id == order.driver_id).first()
        if driver:
            db.refresh(driver)
            notification = get_notification_message("order_cancelled_by_driver", order_id=order.id, order_type="yetkazib berish", reason=cancellation.cancellation_reason)
            create_notification(
                db=db,
                title=notification["title"],
                message=notification["message"],
                notification_type="order_cancelled",
                driver_id=driver.id
            )
            if refund_result and refund_result[1] == driver.id:
                refund_amount = refund_result[0]
                notification = get_notification_message("service_fee_refunded", order_id=order.id)
                create_notification(
                    db=db,
                    title=notification["title"],
                    message=notification["message"],
                    notification_type="service_fee_refunded",
                    driver_id=driver.id,
                )
    
    # Notify user
    notification = get_notification_message("order_cancelled_user", order_id=order.id, order_type="yetkazib berish")
    create_notification(
        db=db,
        title=notification["title"],
        message=notification["message"],
        notification_type="order_cancelled",
        user_id=order.user_id
    )

    await manager.broadcast_to_all_drivers({
        "type": "order_cancelled",
        "order_id": order.id,
        "order_type": "delivery",
        "driver_id": order.driver_id,
        "cancellation_reason": order.cancellation_reason,
    })
    
    return order
