from __future__ import annotations

import uuid
from typing import Any, Dict

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.session import get_async_db
from app.models import PaymentLog, TopUpStatus
from app.services.click_sign import is_valid_complete_sign, is_valid_prepare_sign
from app.services.topup_service import (
    ClickErrorCodes,
    ERROR_NOTES,
    credit_driver_balance,
    generate_confirm_id,
    generate_prepare_id,
    lock_driver_by_id,
    lock_topup_by_merchant_id,
    parse_amount,
    parse_int,
    utc_now,
)

router = APIRouter(prefix="/click", tags=["click"])


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

    error = ClickErrorCodes.SUCCESS

    if _blocked_by_ip(request):
        error = ClickErrorCodes.REQUEST_ERROR
    elif action != 0:
        error = ClickErrorCodes.INVALID_ACTION
    elif service_id != settings.click_service_id:
        error = ClickErrorCodes.REQUEST_ERROR
    elif (not settings.click_disable_sign_check) and not is_valid_prepare_sign(
        payload, settings.click_secret_key
    ):
        error = ClickErrorCodes.SIGN_CHECK_FAILED

    async with session.begin():
        log = PaymentLog(
            kind="prepare",
            merchant_trans_id=merchant_trans_id,
            click_trans_id=click_trans_id or None,
            payload=payload,
            request_id=req_id,
        )
        session.add(log)

        topup = None
        if error == ClickErrorCodes.SUCCESS:
            topup = await lock_topup_by_merchant_id(session, merchant_trans_id)
            if topup is None:
                error = ClickErrorCodes.TRANSACTION_NOT_FOUND
            elif amount is None or amount != topup.amount:
                error = ClickErrorCodes.INCORRECT_AMOUNT
            elif topup.status == TopUpStatus.PAID:
                error = ClickErrorCodes.ALREADY_PAID
            elif topup.status not in {TopUpStatus.CREATED, TopUpStatus.PREPARED}:
                error = ClickErrorCodes.REQUEST_ERROR
            elif topup.click_trans_id and topup.click_trans_id != click_trans_id:
                error = ClickErrorCodes.REQUEST_ERROR

        if error == ClickErrorCodes.SUCCESS and topup:
            if topup.click_trans_id is None:
                topup.click_trans_id = click_trans_id
            if topup.merchant_prepare_id is None:
                topup.merchant_prepare_id = generate_prepare_id()
            topup.status = TopUpStatus.PREPARED
            topup.raw_prepare = payload
            topup.updated_at = utc_now()

        response_payload = {
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "merchant_prepare_id": topup.merchant_prepare_id if topup else 0,
            "error": error,
            "error_note": ERROR_NOTES.get(error, "Error"),
        }
        log.response = response_payload

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
            merchant_trans_id=merchant_trans_id,
            click_trans_id=click_trans_id or None,
            payload=payload,
            request_id=req_id,
        )
        session.add(log)

        topup = None
        if error == ClickErrorCodes.SUCCESS:
            topup = await lock_topup_by_merchant_id(session, merchant_trans_id)
            if topup is None:
                error = ClickErrorCodes.TRANSACTION_NOT_FOUND
            elif amount is None or amount != topup.amount:
                error = ClickErrorCodes.INCORRECT_AMOUNT
            elif topup.merchant_prepare_id != merchant_prepare_id:
                error = ClickErrorCodes.REQUEST_ERROR
            elif topup.click_trans_id and topup.click_trans_id != click_trans_id:
                error = ClickErrorCodes.REQUEST_ERROR

        if error == ClickErrorCodes.SUCCESS and topup:
            topup.raw_complete = payload
            topup.error_code = click_error
            topup.updated_at = utc_now()

            if click_error != 0:
                if topup.status != TopUpStatus.PAID:
                    topup.status = TopUpStatus.FAILED
                response_payload = {
                    "click_trans_id": click_trans_id,
                    "merchant_trans_id": merchant_trans_id,
                    "merchant_confirm_id": topup.merchant_confirm_id or 0,
                    "error": click_error,
                    "error_note": ERROR_NOTES.get(click_error, "Error"),
                }
                log.response = response_payload
                return _json_response(response_payload)

            if topup.status == TopUpStatus.PAID:
                response_payload = {
                    "click_trans_id": click_trans_id,
                    "merchant_trans_id": merchant_trans_id,
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
                    await credit_driver_balance(session, driver.id, topup.amount)
                    topup.status = TopUpStatus.PAID
                    topup.paid_at = utc_now()
                    if topup.merchant_confirm_id is None:
                        topup.merchant_confirm_id = generate_confirm_id()

        response_payload = {
            "click_trans_id": click_trans_id,
            "merchant_trans_id": merchant_trans_id,
            "merchant_confirm_id": topup.merchant_confirm_id if topup else 0,
            "error": error,
            "error_note": ERROR_NOTES.get(error, "Error"),
        }
        log.response = response_payload

    return _json_response(response_payload)
