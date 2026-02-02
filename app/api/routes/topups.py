from __future__ import annotations

from datetime import datetime
import uuid

from pydantic import BaseModel, Field, field_validator
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth import get_current_user
from app.db.session import get_async_db
from app.services.topup_service import build_payment_url, create_topup, get_driver
from app.models import Driver, TopUpTransaction, User, UserRole

router = APIRouter(prefix="/api", tags=["topups"])


class TopUpCreateRequest(BaseModel):
    driver_id: int = Field(..., gt=0)
    amount: int = Field(..., gt=0)

    @field_validator("amount")
    @classmethod
    def validate_amount(cls, value: int) -> int:
        if value <= 0:
            raise ValueError("amount must be > 0")
        return value


class TopUpCreateResponse(BaseModel):
    merchant_trans_id: str
    payment_url: str


class TopUpHistoryItem(BaseModel):
    id: uuid.UUID
    merchant_trans_id: str
    amount: int
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


@router.post("/topups", response_model=TopUpCreateResponse, status_code=status.HTTP_201_CREATED)
async def create_topup_endpoint(
    payload: TopUpCreateRequest,
    session: AsyncSession = Depends(get_async_db),
) -> TopUpCreateResponse:
    driver = await get_driver(session, payload.driver_id)
    if driver is None:
        raise HTTPException(status_code=404, detail="Driver not found")

    topup = await create_topup(session, payload.driver_id, payload.amount)
    await session.commit()
    await session.refresh(topup)

    payment_url = build_payment_url(payload.amount, topup.merchant_trans_id)
    return TopUpCreateResponse(
        merchant_trans_id=topup.merchant_trans_id,
        payment_url=payment_url,
    )


@router.get("/topups/history", response_model=list[TopUpHistoryItem])
async def topup_history(
    driver_id: int | None = Query(default=None, gt=0),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    current_user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_async_db),
) -> list[TopUpHistoryItem]:
    if current_user.role in {UserRole.ADMIN, UserRole.SUPERADMIN}:
        if driver_id is None:
            raise HTTPException(status_code=400, detail="driver_id is required for admins")
        target_driver_id = driver_id
    else:
        if driver_id is not None:
            raise HTTPException(status_code=403, detail="Not authorized to access other drivers")
        result = await session.execute(select(Driver).where(Driver.user_id == current_user.id))
        driver = result.scalar_one_or_none()
        if driver is None:
            raise HTTPException(status_code=404, detail="Driver profile not found")
        target_driver_id = driver.id

    result = await session.execute(
        select(TopUpTransaction)
        .where(TopUpTransaction.driver_id == target_driver_id)
        .order_by(TopUpTransaction.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return list(result.scalars().all())
