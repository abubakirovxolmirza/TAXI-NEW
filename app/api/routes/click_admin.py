from __future__ import annotations

import uuid
from datetime import date, datetime

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth import get_current_admin
from app.db.session import get_async_db
from app.models import PaymentLog, User

router = APIRouter(prefix="/api/admin/click", tags=["Admin - Click"])


class PaymentLogItem(BaseModel):
    id: uuid.UUID
    kind: str
    merchant_trans_id: str
    click_trans_id: str | None
    payload: dict
    response: dict | None
    request_id: str | None
    created_at: datetime | None

    class Config:
        from_attributes = True


@router.get("/history", response_model=list[PaymentLogItem])
async def click_history(
    kind: str | None = Query(default=None, pattern="^(prepare|complete)$"),
    merchant_trans_id: str | None = Query(default=None, min_length=1),
    click_trans_id: str | None = Query(default=None, min_length=1),
    request_id: str | None = Query(default=None, min_length=1),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_admin),
    session: AsyncSession = Depends(get_async_db),
) -> list[PaymentLogItem]:
    stmt = select(PaymentLog)

    if kind:
        stmt = stmt.where(PaymentLog.kind == kind)
    if merchant_trans_id:
        stmt = stmt.where(PaymentLog.merchant_trans_id == merchant_trans_id)
    if click_trans_id:
        stmt = stmt.where(PaymentLog.click_trans_id == click_trans_id)
    if request_id:
        stmt = stmt.where(PaymentLog.request_id == request_id)
    if date_from:
        stmt = stmt.where(PaymentLog.created_at >= datetime.combine(date_from, datetime.min.time()))
    if date_to:
        stmt = stmt.where(PaymentLog.created_at <= datetime.combine(date_to, datetime.max.time()))

    stmt = stmt.order_by(PaymentLog.created_at.desc()).limit(limit).offset(offset)
    result = await session.execute(stmt)
    return list(result.scalars().all())
