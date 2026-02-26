from __future__ import annotations

import logging
import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_async_db
from app.localization import get_notification_message
from app.models import DeviceToken, Driver, Notification, PaymentLog, TopUpStatus, TopUpTransaction, User
from app.services.fcm import send_push_once_to_token
from app.services.click_sign import is_valid_complete_sign, is_valid_prepare_sign
from app.services.phone import digits_only, normalize_phone
from app.services.topup_service import (
    ClickErrorCodes,
    ERROR_NOTES,
    MIN_CLICK_AMOUNT,
    credit_driver_balance,
    generate_confirm_id,
    generate_prepare_id,
    lock_driver_by_id,
    lock_topup_by_merchant_id,
    lock_topup_by_click_trans_id,
    parse_amount,
    parse_int,
    utc_now,
)

router = APIRouter(prefix="/click", tags=["click"])
logger = logging.getLogger("click")


def _json_response(payload: Dict[str, Any]) -> JSONResponse:
    return JSONResponse(content=payload, status_code=200)


def _request_id(request: Request) -> str:
    return request.headers.get("X-Request-ID") or str(uuid.uuid4())


async def _parse_payload(request: Request) -> Dict[str, Any]:
    content_type = request.headers.get("content-type", "").lower()
    if content_type.startswith("application/json"):
        data = await request.json()
    else:
        form = await request.form()
        data = dict(form)
    return {str(k): v for k, v in data.items()}


def _blocked_by_ip(request: Request) -> bool:
    if not settings.click_allowed_ips:
        return False
    client_ip = request.client.host if request.client else ""
    return client_ip not in settings.click_allowed_ips


def _extract_account(payload: Dict[str, Any]) -> str:
    account = str(payload.get("transaction_param") or "").strip()
    if not account:
        account = str(payload.get("merchant_trans_id") or "").strip()
    return account


@router.post("/prepare")
async def click_prepare(
    request: Request,
    session: AsyncSession = Depends(get_async_db),
) -> JSONResponse:
    payload = await _parse_payload(request)
    req_id = _request_id(request)

    click_trans_id = str(payload.get("click_trans_id", ""))
    merchant_trans_id = str(payload.get("merchant_trans_id", ""))
    service_id = parse_int(payload.get("service_id"))
    amount = parse_amount(payload.get("amount"))
    action = parse_int(payload.get("action"))
    account_raw = _extract_account(payload)
    account_phone = normalize_phone(account_raw)

    error = ClickErrorCodes.SUCCESS

    if _blocked_by_ip(request):
        error = ClickErrorCodes.REQUEST_ERROR
    elif action != 0:
        error = ClickErrorCodes.INVALID_ACTION
    elif service_id != settings.click_service_id:
        error = ClickErrorCodes.REQUEST_ERROR
    elif not account_phone and not merchant_trans_id:
        error = ClickErrorCodes.SIGN_CHECK_FAILED
    elif (not settings.click_disable_sign_check) and not is_valid_prepare_sign(
        payload, settings.click_secret_key
    ):
        error = ClickErrorCodes.SIGN_CHECK_FAILED

    async with session.begin():
        log = PaymentLog(
            kind="prepare",
            merchant_trans_id=account_phone or merchant_trans_id,
            click_trans_id=click_trans_id or None,
            payload=payload,
            request_id=req_id,
        )
        session.add(log)

        topup = None
        if error == ClickErrorCodes.SUCCESS:
            topup = await lock_topup_by_click_trans_id(session, click_trans_id)

            if topup is not None:
                if amount is None or amount != topup.amount or amount < MIN_CLICK_AMOUNT:
                    error = ClickErrorCodes.INCORRECT_AMOUNT
                elif topup.status in {TopUpStatus.PREPARED, TopUpStatus.PAID}:
                    error = ClickErrorCodes.SUCCESS
                else:
                    error = ClickErrorCodes.REQUEST_ERROR
            else:
                # Legacy flow fallback: try to resolve by merchant_trans_id (order id)
                if not account_phone and merchant_trans_id:
                    legacy = await lock_topup_by_merchant_id(session, merchant_trans_id)
                    if legacy is None:
                        error = ClickErrorCodes.SIGN_CHECK_FAILED
                    else:
                        topup = legacy
                        if topup.click_trans_id is None:
                            topup.click_trans_id = click_trans_id
                        if amount is None or amount != topup.amount:
                            error = ClickErrorCodes.INCORRECT_AMOUNT
                else:
                    digits = digits_only(account_phone) if account_phone else None
                    driver = None
                    if digits:
                        result = await session.execute(
                            select(Driver)
                            .join(User, Driver.user_id == User.id)
                            .where(
                                or_(
                                    func.regexp_replace(User.telephone, r"\\D", "", "g") == digits,
                                    User.telephone == account_phone,
                                    func.replace(User.telephone, "+", "") == digits,
                                )
                            )
                        )
                        driver = result.scalar_one_or_none()

                    if driver is None:
                        error = ClickErrorCodes.TRANSACTION_NOT_FOUND
                    elif amount is None or amount < MIN_CLICK_AMOUNT:
                        error = ClickErrorCodes.INCORRECT_AMOUNT
                    else:
                        topup = TopUpTransaction(
                            merchant_trans_id=account_phone,
                            account_phone=account_phone,
                            driver_id=driver.id,
                            amount=amount,
                            status=TopUpStatus.PREPARED,
                            click_trans_id=click_trans_id,
                            merchant_prepare_id=generate_prepare_id(),
                            raw_prepare_payload=payload,
                            updated_at=utc_now(),
                        )
                        session.add(topup)

        if error == ClickErrorCodes.SUCCESS and topup:
            if topup.merchant_prepare_id is None:
                topup.merchant_prepare_id = generate_prepare_id()
            if topup.status == TopUpStatus.CREATED:
                topup.status = TopUpStatus.PREPARED
            topup.raw_prepare_payload = payload
            topup.updated_at = utc_now()

        response_payload = {
            "click_trans_id": click_trans_id,
            "merchant_trans_id": account_phone or merchant_trans_id,
            "merchant_prepare_id": topup.merchant_prepare_id if topup else 0,
            "error": error,
            "error_note": "Invalid account/phone"
            if error == ClickErrorCodes.SIGN_CHECK_FAILED and not account_phone
            else ERROR_NOTES.get(error, "Error"),
        }
    log.response = response_payload

    logger.info(
        "click.prepare",
        extra={
            "click_trans_id": click_trans_id,
            "account_phone": account_phone,
            "amount": amount,
            "action": action,
            "error": error,
            "client_ip": request.client.host if request.client else None,
        },
    )

    return _json_response(response_payload)


@router.post("/complete")
async def click_complete(
    request: Request,
    session: AsyncSession = Depends(get_async_db),
) -> JSONResponse:
    payload = await _parse_payload(request)
    req_id = _request_id(request)

    click_trans_id = str(payload.get("click_trans_id", ""))
    merchant_trans_id = str(payload.get("merchant_trans_id", ""))
    merchant_prepare_id = str(payload.get("merchant_prepare_id", ""))
    service_id = parse_int(payload.get("service_id"))
    amount = parse_amount(payload.get("amount"))
    action = parse_int(payload.get("action"))
    click_error = parse_int(payload.get("error")) or 0
    account_raw = _extract_account(payload)
    account_phone = normalize_phone(account_raw) if account_raw else None

    error = ClickErrorCodes.SUCCESS

    if _blocked_by_ip(request):
        error = ClickErrorCodes.REQUEST_ERROR
    elif action != 1:
        error = ClickErrorCodes.INVALID_ACTION
    elif service_id != settings.click_service_id:
        error = ClickErrorCodes.REQUEST_ERROR
    elif (not settings.click_disable_sign_check) and not is_valid_complete_sign(
        payload, settings.click_secret_key
    ):
        error = ClickErrorCodes.SIGN_CHECK_FAILED

    async with session.begin():
        log = PaymentLog(
            kind="complete",
            merchant_trans_id=account_phone or merchant_trans_id,
            click_trans_id=click_trans_id or None,
            payload=payload,
            request_id=req_id,
        )
        session.add(log)

        topup = None
        if error == ClickErrorCodes.SUCCESS:
            topup = await lock_topup_by_click_trans_id(session, click_trans_id)
            if topup is None:
                error = ClickErrorCodes.TRANSACTION_NOT_FOUND
            elif amount is None or amount != topup.amount or amount < MIN_CLICK_AMOUNT:
                error = ClickErrorCodes.INCORRECT_AMOUNT
            elif merchant_prepare_id and topup.merchant_prepare_id != merchant_prepare_id:
                error = ClickErrorCodes.REQUEST_ERROR

        if error == ClickErrorCodes.SUCCESS and topup:
            topup.raw_complete_payload = payload
            topup.error_code = click_error
            topup.updated_at = utc_now()

            if click_error != 0:
                if topup.status != TopUpStatus.PAID:
                    topup.status = TopUpStatus.FAILED
                response_payload = {
                    "click_trans_id": click_trans_id,
                    "merchant_trans_id": topup.account_phone or account_phone or merchant_trans_id,
                    "merchant_confirm_id": topup.merchant_confirm_id or 0,
                    "error": click_error,
                    "error_note": ERROR_NOTES.get(click_error, "Error"),
                }
                log.response = response_payload
                return _json_response(response_payload)

            if topup.status == TopUpStatus.PAID:
                response_payload = {
                    "click_trans_id": click_trans_id,
                    "merchant_trans_id": topup.account_phone or account_phone or merchant_trans_id,
                    "merchant_confirm_id": topup.merchant_confirm_id or 0,
                    "error": ClickErrorCodes.SUCCESS,
                    "error_note": ERROR_NOTES[ClickErrorCodes.SUCCESS],
                }
                log.response = response_payload
                return _json_response(response_payload)

            if topup.status in {TopUpStatus.FAILED, TopUpStatus.CANCELED}:
                error = ClickErrorCodes.REQUEST_ERROR
            else:
                driver = await lock_driver_by_id(session, topup.driver_id)
                if driver is None:
                    error = ClickErrorCodes.REQUEST_ERROR
                else:
                    click_ref = topup.click_trans_id or click_trans_id or "unknown"
                    await credit_driver_balance(
                        session,
                        driver.id,
                        topup.amount,
                        description=f"Click topup via Click. click_trans_id={click_ref}",
                    )
                    notification = get_notification_message("balance_added", amount=topup.amount)
                    notification_body = notification["message"]
                    session.add(
                        Notification(
                            driver_id=driver.id,
                            title=notification["title"],
                            message=notification_body,
                            body=notification_body,
                            notification_type="balance_added",
                        )
                    )
                    token_rows = await session.execute(
                        select(DeviceToken.token).where(
                            DeviceToken.user_id == driver.user_id,
                            DeviceToken.is_active == True,
                        )
                    )
                    device_tokens = [row[0] for row in token_rows.all() if row[0]]
                    for token in device_tokens:
                        send_push_once_to_token(
                            token=token,
                            title=notification["title"],
                            body=notification_body,
                            data={
                                "type": "notification",
                                "notification_type": "balance_added",
                            },
                        )
                    topup.status = TopUpStatus.PAID
                    topup.paid_at = utc_now()
                    if topup.merchant_confirm_id is None:
                        topup.merchant_confirm_id = generate_confirm_id()

    response_payload = {
        "click_trans_id": click_trans_id,
        "merchant_trans_id": (topup.account_phone if topup else account_phone) or merchant_trans_id,
        "merchant_confirm_id": topup.merchant_confirm_id if topup else 0,
        "error": error,
        "error_note": ERROR_NOTES.get(error, "Error"),
    }
    log.response = response_payload

    logger.info(
        "click.complete",
        extra={
            "click_trans_id": click_trans_id,
            "account_phone": (topup.account_phone if topup else account_phone),
            "amount": amount,
            "action": action,
            "error": error,
            "client_ip": request.client.host if request.client else None,
        },
    )

    return _json_response(response_payload)
