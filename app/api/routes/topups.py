from __future__ import annotations

from datetime import date, datetime
import uuid
from decimal import Decimal

from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import func, select

from app.auth import get_current_user
from app.db.session import get_async_db
from app.models import Driver, TopUpStatus, TopUpTransaction, User, UserRole
from app.services.phone import normalize_phone

router = APIRouter(prefix="/api", tags=["topups"])


class TopUpHistoryItem(BaseModel):
    id: uuid.UUID
    merchant_trans_id: str
    amount: Decimal
    status: str
    click_trans_id: str | None
    merchant_prepare_id: str | None
    merchant_confirm_id: str | None
    error_code: int | None
    created_at: datetime | None
    updated_at: datetime | None
    paid_at: datetime | None

    class Config:
        from_attributes = True


class TopUpStatsBucket(BaseModel):
    period_start: date
    total_amount: Decimal


class TopUpStatsDriver(BaseModel):
    driver_id: int
    telephone: str | None
    total_amount: Decimal


class TopUpStatsResponse(BaseModel):
    period: str
    total_amount: Decimal
    buckets: list[TopUpStatsBucket]
    per_driver: list[TopUpStatsDriver]


@router.get("/topups/history", response_model=list[TopUpHistoryItem])
async def topup_history(
    driver_id: int | None = Query(default=None, gt=0),
    phone: str | None = Query(default=None, min_length=3),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_db),
) -> list[TopUpHistoryItem]:
    if current_user.role in {UserRole.ADMIN, UserRole.SUPERADMIN}:
        if driver_id is None and not phone:
            raise HTTPException(status_code=400, detail="driver_id or phone is required for admins")
        target_driver_id = driver_id
        account_phone = normalize_phone(phone) if phone else None
        if phone and not account_phone:
            raise HTTPException(status_code=400, detail="Invalid phone format")
    else:
        if driver_id is not None or phone is not None:
            raise HTTPException(status_code=403, detail="Not authorized to access other drivers")
        result = await session.execute(select(Driver).where(Driver.user_id == current_user.id))
        driver = result.scalar_one_or_none()
        if driver is None:
            raise HTTPException(status_code=404, detail="Driver profile not found")
        target_driver_id = driver.id
        account_phone = None

    stmt = select(TopUpTransaction)
    if target_driver_id is not None:
        stmt = stmt.where(TopUpTransaction.driver_id == target_driver_id)
    if account_phone:
        stmt = stmt.where(TopUpTransaction.account_phone == account_phone)
    stmt = stmt.order_by(TopUpTransaction.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/topups/history/paid", response_model=list[TopUpHistoryItem])
async def topup_history_paid(
    driver_id: int | None = Query(default=None, gt=0),
    phone: str | None = Query(default=None, min_length=3),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_db),
) -> list[TopUpHistoryItem]:
    if current_user.role in {UserRole.ADMIN, UserRole.SUPERADMIN}:
        if driver_id is None and not phone:
            raise HTTPException(status_code=400, detail="driver_id or phone is required for admins")
        target_driver_id = driver_id
        account_phone = normalize_phone(phone) if phone else None
        if phone and not account_phone:
            raise HTTPException(status_code=400, detail="Invalid phone format")
    else:
        if driver_id is not None or phone is not None:
            raise HTTPException(status_code=403, detail="Not authorized to access other drivers")
        result = await session.execute(select(Driver).where(Driver.user_id == current_user.id))
        driver = result.scalar_one_or_none()
        if driver is None:
            raise HTTPException(status_code=404, detail="Driver profile not found")
        target_driver_id = driver.id
        account_phone = None

    stmt = (
        select(TopUpTransaction)
        .where(TopUpTransaction.status == TopUpStatus.PAID)
    )
    if target_driver_id is not None:
        stmt = stmt.where(TopUpTransaction.driver_id == target_driver_id)
    if account_phone:
        stmt = stmt.where(TopUpTransaction.account_phone == account_phone)
    stmt = stmt.order_by(TopUpTransaction.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())


@router.get("/topups/stats", response_model=TopUpStatsResponse)
async def topup_stats(
    period: str = Query(default="month", pattern="^(day|week|month|year)$"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_db),
) -> TopUpStatsResponse:
    if current_user.role not in {UserRole.ADMIN, UserRole.SUPERADMIN}:
        raise HTTPException(status_code=403, detail="Not authorized")

    period_map = {
        "day": "day",
        "week": "week",
        "month": "month",
        "year": "year",
    }
    bucket = func.date_trunc(period_map[period], TopUpTransaction.paid_at).label("bucket")

    filters = [TopUpTransaction.status == TopUpStatus.PAID, TopUpTransaction.paid_at.is_not(None)]
    if date_from:
        filters.append(TopUpTransaction.paid_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        filters.append(TopUpTransaction.paid_at <= datetime.combine(date_to, datetime.max.time()))

    total_stmt = select(func.coalesce(func.sum(TopUpTransaction.amount), 0)).where(*filters)
    total_amount = (await session.execute(total_stmt)).scalar_one()

    bucket_stmt = (
        select(bucket, func.coalesce(func.sum(TopUpTransaction.amount), 0).label("total_amount"))
        .where(*filters)
        .group_by(bucket)
        .order_by(bucket)
    )
    bucket_rows = (await session.execute(bucket_stmt)).all()

    per_driver_stmt = (
        select(
            TopUpTransaction.driver_id,
            User.telephone,
            func.coalesce(func.sum(TopUpTransaction.amount), 0).label("total_amount"),
        )
        .join(Driver, Driver.id == TopUpTransaction.driver_id)
        .join(User, User.id == Driver.user_id)
        .where(*filters)
        .group_by(TopUpTransaction.driver_id, User.telephone)
        .order_by(func.coalesce(func.sum(TopUpTransaction.amount), 0).desc())
    )
    per_driver_rows = (await session.execute(per_driver_stmt)).all()

    return TopUpStatsResponse(
        period=period,
        total_amount=total_amount,
        buckets=[
            TopUpStatsBucket(period_start=row.bucket.date(), total_amount=row.total_amount)
            for row in bucket_rows
        ],
        per_driver=[
            TopUpStatsDriver(driver_id=row.driver_id, telephone=row.telephone, total_amount=row.total_amount)
            for row in per_driver_rows
        ],
    )
