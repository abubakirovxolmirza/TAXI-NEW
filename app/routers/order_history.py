from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import or_
from sqlalchemy.orm import Session
from typing import Dict, List, Optional
from app.database import get_db
from app.models import (
    DeliveryOrder,
    OrderAcceptanceHistory,
    OrderStatus,
    TaxiOrder,
    User,
    UserRole,
)
from app.schemas import OrderAcceptanceHistoryResponse
from app.auth import get_current_user

router = APIRouter(prefix="/api/order-acceptance-history", tags=["Order Acceptance History"])


def _serialize_order_with_parties(order_type: str, order) -> Dict:
    """Return order details plus driver and customer info."""
    driver = order.driver
    user = order.user
    driver_user = driver.user if driver else None

    driver_info = None
    if driver:
        driver_info = {
            "id": driver.id,
            "full_name": driver.full_name,
            "telephone": driver_user.telephone if driver_user else None,
            "car_model": driver.car_model,
            "car_number": driver.car_number,
            "tariff": getattr(getattr(driver, "tariff", None), "value", None),
        }

    customer_info = None
    if user:
        customer_info = {
            "id": user.id,
            "name": getattr(user, "name", None),
            "telephone": getattr(user, "telephone", None),
        }

    base = {
        "order_type": order_type,
        "order_id": order.id,
        "status": order.status.value if hasattr(order.status, "value") else str(order.status),
        "price": str(order.price) if hasattr(order, "price") else None,
        "service_fee": str(getattr(order, "service_fee", None)) if hasattr(order, "service_fee") else None,
        "driver_earnings": str(getattr(order, "driver_earnings", None)) if hasattr(order, "driver_earnings") else None,
        "from_region_id": order.from_region_id,
        "to_region_id": order.to_region_id,
        "from_district_id": getattr(order, "from_district_id", None),
        "to_district_id": getattr(order, "to_district_id", None),
        "date": getattr(order, "date", None),
        "time_start": getattr(order, "time_start", None),
        "time_end": getattr(order, "time_end", None),
        "scheduled_datetime": order.scheduled_datetime.isoformat() if getattr(order, "scheduled_datetime", None) else None,
        "passengers": getattr(order, "passengers", None),
        "seat_type": getattr(getattr(order, "seat_type", None), "value", None),
        "tariff": getattr(getattr(order, "tariff", None), "value", None),
        "item_type": getattr(getattr(order, "item_type", None), "value", None),
        "created_at": order.created_at.isoformat() if getattr(order, "created_at", None) else None,
        "accepted_at": order.accepted_at.isoformat() if getattr(order, "accepted_at", None) else None,
        "completed_at": order.completed_at.isoformat() if getattr(order, "completed_at", None) else None,
        "cancelled_at": getattr(order, "cancelled_at", None).isoformat() if getattr(order, "cancelled_at", None) else None,
        "cancellation_reason": getattr(order, "cancellation_reason", None),
        "driver": driver_info,
        "customer": customer_info,
    }
    return base


def _require_admin(user: User):
    if user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view order acceptance history"
        )


@router.get("/", response_model=List[OrderAcceptanceHistoryResponse])
async def get_history(
    driver_id: Optional[int] = None,
    order_type: Optional[str] = None,  # "taxi" or "delivery"
    order_id: Optional[int] = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get order acceptance history across all orders (Admin only)"""
    _require_admin(current_user)

    query = db.query(OrderAcceptanceHistory)

    if driver_id:
        query = query.filter(OrderAcceptanceHistory.driver_id == driver_id)

    if order_type == "taxi":
        query = query.filter(OrderAcceptanceHistory.taxi_order_id.isnot(None))
        if order_id:
            query = query.filter(OrderAcceptanceHistory.taxi_order_id == order_id)
    elif order_type == "delivery":
        query = query.filter(OrderAcceptanceHistory.delivery_order_id.isnot(None))
        if order_id:
            query = query.filter(OrderAcceptanceHistory.delivery_order_id == order_id)
    elif order_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid order_type. Must be 'taxi' or 'delivery'"
        )
    elif order_id:
        # If order_id provided without type, match either taxi or delivery entries
        query = query.filter(
            or_(
                OrderAcceptanceHistory.taxi_order_id == order_id,
                OrderAcceptanceHistory.delivery_order_id == order_id,
            )
        )

    history = query.order_by(OrderAcceptanceHistory.created_at.desc()).all()
    return history


@router.get("/pending-returns")
async def get_pending_returns(
    order_type: Optional[str] = None,  # "taxi" or "delivery"
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Orders that were not kept by the driver and were returned to pending
    (e.g., driver preview/reject or cancelled while pending).
    """
    _require_admin(current_user)

    actions = ["returned_to_pending", "cancelled_from_pending"]
    query = db.query(OrderAcceptanceHistory).filter(OrderAcceptanceHistory.action.in_(actions))

    if order_type == "taxi":
        query = query.filter(OrderAcceptanceHistory.taxi_order_id.isnot(None))
    elif order_type == "delivery":
        query = query.filter(OrderAcceptanceHistory.delivery_order_id.isnot(None))
    elif order_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="order_type must be 'taxi' or 'delivery'",
        )

    results = []
    for entry in query.order_by(OrderAcceptanceHistory.created_at.desc()).all():
        order = None
        otype = "taxi" if entry.taxi_order_id else "delivery"
        if entry.taxi_order_id:
            order = db.query(TaxiOrder).filter(TaxiOrder.id == entry.taxi_order_id).first()
        elif entry.delivery_order_id:
            order = db.query(DeliveryOrder).filter(DeliveryOrder.id == entry.delivery_order_id).first()
        if not order:
            continue
        results.append({
            "action": entry.action,
            "recorded_at": entry.created_at.isoformat() if entry.created_at else None,
            "order": _serialize_order_with_parties(otype, order),
        })

    return results


@router.get("/cancelled-after-accept")
async def get_cancelled_after_accept(
    order_type: Optional[str] = None,  # "taxi" or "delivery"
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Orders accepted by a driver then cancelled before completion."""
    _require_admin(current_user)

    query = db.query(OrderAcceptanceHistory).filter(OrderAcceptanceHistory.action == "cancelled_after_accept")

    if order_type == "taxi":
        query = query.filter(OrderAcceptanceHistory.taxi_order_id.isnot(None))
    elif order_type == "delivery":
        query = query.filter(OrderAcceptanceHistory.delivery_order_id.isnot(None))
    elif order_type:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="order_type must be 'taxi' or 'delivery'",
        )

    results = []
    for entry in query.order_by(OrderAcceptanceHistory.created_at.desc()).all():
        order = None
        otype = "taxi" if entry.taxi_order_id else "delivery"
        if entry.taxi_order_id:
            order = db.query(TaxiOrder).filter(TaxiOrder.id == entry.taxi_order_id).first()
        elif entry.delivery_order_id:
            order = db.query(DeliveryOrder).filter(DeliveryOrder.id == entry.delivery_order_id).first()
        if not order:
            continue
        results.append({
            "action": entry.action,
            "recorded_at": entry.created_at.isoformat() if entry.created_at else None,
            "order": _serialize_order_with_parties(otype, order),
        })

    return results


@router.get("/completed")
async def get_completed_orders(
    order_type: Optional[str] = None,  # "taxi" or "delivery"
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Orders that were fulfilled/completed."""
    _require_admin(current_user)

    results = []

    include_taxi = order_type in (None, "taxi")
    include_delivery = order_type in (None, "delivery")

    if include_taxi:
        taxi_orders = db.query(TaxiOrder).filter(TaxiOrder.status == OrderStatus.COMPLETED).order_by(TaxiOrder.completed_at.desc()).all()
        for order in taxi_orders:
            results.append({
                "order": _serialize_order_with_parties("taxi", order),
                "action": "completed",
                "recorded_at": order.completed_at.isoformat() if order.completed_at else None,
            })

    if include_delivery:
        delivery_orders = db.query(DeliveryOrder).filter(DeliveryOrder.status == OrderStatus.COMPLETED).order_by(DeliveryOrder.completed_at.desc()).all()
        for order in delivery_orders:
            results.append({
                "order": _serialize_order_with_parties("delivery", order),
                "action": "completed",
                "recorded_at": order.completed_at.isoformat() if order.completed_at else None,
            })

    results.sort(key=lambda item: item.get("recorded_at") or "", reverse=True)
    return results


@router.get("/driver/{driver_id}", response_model=List[OrderAcceptanceHistoryResponse])
async def get_driver_history(
    driver_id: int,
    order_type: Optional[str] = None,  # "taxi" or "delivery"
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get order acceptance history for a specific driver (Admin only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view order acceptance history"
        )
    
    query = db.query(OrderAcceptanceHistory).filter(
        OrderAcceptanceHistory.driver_id == driver_id
    )
    
    if order_type == "taxi":
        query = query.filter(OrderAcceptanceHistory.taxi_order_id.isnot(None))
    elif order_type == "delivery":
        query = query.filter(OrderAcceptanceHistory.delivery_order_id.isnot(None))
    
    history = query.order_by(OrderAcceptanceHistory.created_at.desc()).all()
    
    return history


@router.get("/order/taxi/{order_id}", response_model=List[OrderAcceptanceHistoryResponse])
async def get_taxi_order_history(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all drivers who received a specific taxi order (Admin only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view order acceptance history"
        )
    
    history = db.query(OrderAcceptanceHistory).filter(
        OrderAcceptanceHistory.taxi_order_id == order_id
    ).order_by(OrderAcceptanceHistory.created_at.desc()).all()
    
    return history


@router.get("/order/delivery/{order_id}", response_model=List[OrderAcceptanceHistoryResponse])
async def get_delivery_order_history(
    order_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get all drivers who received a specific delivery order (Admin only)"""
    if current_user.role not in [UserRole.ADMIN, UserRole.SUPERADMIN]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can view order acceptance history"
        )
    
    history = db.query(OrderAcceptanceHistory).filter(
        OrderAcceptanceHistory.delivery_order_id == order_id
    ).order_by(OrderAcceptanceHistory.created_at.desc()).all()
    
    return history
