from __future__ import annotations

import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any, Mapping, Optional

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import BalanceTransaction, Driver, TopUpTransaction, TopUpStatus


class ClickErrorCodes:
    SUCCESS = 0
    SIGN_CHECK_FAILED = -1
    INCORRECT_AMOUNT = -2
    TRANSACTION_NOT_FOUND = -3
    ALREADY_PAID = -4
    INVALID_ACTION = -5
    REQUEST_ERROR = -6


MIN_CLICK_AMOUNT = Decimal("1000.00")


ERROR_NOTES = {
    ClickErrorCodes.SUCCESS: "Success",
    ClickErrorCodes.SIGN_CHECK_FAILED: "SIGN CHECK FAILED",
    ClickErrorCodes.INCORRECT_AMOUNT: "Incorrect amount",
    ClickErrorCodes.TRANSACTION_NOT_FOUND: "Transaction not found",
    ClickErrorCodes.ALREADY_PAID: "Already paid",
    ClickErrorCodes.INVALID_ACTION: "Invalid action",
    ClickErrorCodes.REQUEST_ERROR: "Request error",
}


def generate_merchant_trans_id(driver_id: int) -> str:
    return f"topup_{driver_id}_{uuid.uuid4()}"


def generate_prepare_id() -> str:
    return f"prep_{uuid.uuid4()}"


def generate_confirm_id() -> str:
    return f"conf_{uuid.uuid4()}"


def build_payment_url(amount: Decimal, merchant_trans_id: str) -> str:
    amount_str = str(amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
    return (
        "https://my.click.uz/services/pay"
        f"?service_id={settings.click_service_id}"
        f"&merchant_id={settings.click_merchant_id}"
        f"&amount={amount_str}"
        f"&transaction_param={merchant_trans_id}"
    )


def parse_amount(value: Any) -> Optional[Decimal]:
    if value is None:
        return None
    try:
        raw = str(value)
        cleaned = raw.replace(" ", "").replace(",", "")
        amount = Decimal(cleaned)
        if amount.is_nan():
            return None
        return amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    except (InvalidOperation, ValueError, TypeError):
        return None


def parse_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(str(value))
    except (ValueError, TypeError):
        return None


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


async def create_topup(
    session: AsyncSession,
    driver_id: int,
    amount: Decimal,
) -> TopUpTransaction:
    merchant_trans_id = generate_merchant_trans_id(driver_id)
    topup = TopUpTransaction(
        merchant_trans_id=merchant_trans_id,
        driver_id=driver_id,
        amount=amount,
        status=TopUpStatus.CREATED,
    )
    session.add(topup)
    await session.flush()
    return topup


async def get_driver(session: AsyncSession, driver_id: int) -> Optional[Driver]:
    return await session.get(Driver, driver_id)


async def lock_topup_by_merchant_id(
    session: AsyncSession, merchant_trans_id: str
) -> Optional[TopUpTransaction]:
    result = await session.execute(
        select(TopUpTransaction)
        .where(TopUpTransaction.merchant_trans_id == merchant_trans_id)
        .with_for_update()
    )
    return result.scalar_one_or_none()


async def lock_topup_by_click_trans_id(
    session: AsyncSession, click_trans_id: str
) -> Optional[TopUpTransaction]:
    result = await session.execute(
        select(TopUpTransaction)
        .where(TopUpTransaction.click_trans_id == click_trans_id)
        .with_for_update()
    )
    return result.scalar_one_or_none()


async def lock_driver_by_id(session: AsyncSession, driver_id: int) -> Optional[Driver]:
    result = await session.execute(
        select(Driver).where(Driver.id == driver_id).with_for_update()
    )
    return result.scalar_one_or_none()


async def credit_driver_balance(
    session: AsyncSession,
    driver_id: int,
    amount: Decimal,
    description: str = "Click topup",
) -> None:
    await session.execute(
        update(Driver)
        .where(Driver.id == driver_id)
        .values(balance=Driver.balance + amount)
    )
    session.add(
        BalanceTransaction(
            driver_id=driver_id,
            amount=amount,
            transaction_type="credit",
            description=description,
        )
    )
