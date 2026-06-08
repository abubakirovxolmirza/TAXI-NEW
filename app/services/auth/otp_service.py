from __future__ import annotations

import hashlib
import hmac
import secrets
import logging
import time
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth import create_access_token, get_password_hash
from app.config import settings
from app.models import PhoneOtp, User
from app.services.phone import normalize_phone
from app.services.sms.eskiz_client import EskizClientError, EskizStatusNotReady, eskiz_client

logger = logging.getLogger(__name__)


OTP_LENGTH = 6
TEST_OTP_PHONE = "+998935204050"
TEST_OTP_CODE = "123321"
PENDING_DELIVERY_STATUSES = {"WAITING", "SENT", "QUEUED", "ACCEPTED"}
FAILED_DELIVERY_STATUSES = {
    "UNDELIVERED",
    "FAILED",
    "REJECTED",
    "EXPIRED",
    "ERROR",
    "UNDELIV",
    "REJECTD",
    "DROPPED",
}


def _as_utc(dt: datetime) -> datetime:
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def normalize_uz_phone_or_raise(phone: str) -> str:
    normalized = normalize_phone(phone)
    if not normalized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Uzbekistan phone format. Use +998XXXXXXXXX.",
        )
    return normalized


def to_eskiz_phone(phone: str) -> str:
    return phone.lstrip("+")


def generate_otp_code() -> str:
    return f"{secrets.randbelow(10 ** OTP_LENGTH):0{OTP_LENGTH}d}"


def hash_otp_code(normalized_phone: str, code: str) -> str:
    payload = f"{normalized_phone}:{code}:{settings.OTP_SALT}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _issue_sms_auth_token(db: Session, normalized_phone: str) -> dict:
    user = db.query(User).filter(User.telephone == normalized_phone).first()
    if not user:
        # Create a placeholder password so bcrypt verification doesn't fail before the user sets one.
        placeholder_password = get_password_hash(secrets.token_hex(8))
        user = User(
            telephone=normalized_phone,
            name=normalized_phone,
            hashed_password=placeholder_password,
            is_active=True,
        )
        db.add(user)

    db.commit()
    db.refresh(user)

    access_token = create_access_token(data={"sub": str(user.id)})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user": user,
    }


def _extract_delivery_status(payload: dict | None) -> str | None:
    if not isinstance(payload, dict):
        return None
    data = payload.get("data")
    if not isinstance(data, dict):
        return None
    status_value = data.get("status")
    if not status_value:
        return None
    return str(status_value).upper()


def _poll_delivery_status(provider_id: str) -> tuple[str | None, dict | None]:
    attempts = max(int(settings.ESKIZ_STATUS_POLL_ATTEMPTS), 0)
    interval = max(float(settings.ESKIZ_STATUS_POLL_INTERVAL_SECONDS), 0.0)
    latest_payload = None

    for attempt in range(attempts):
        if attempt > 0 and interval > 0:
            time.sleep(interval)
        try:
            latest_payload = eskiz_client.get_message_status(provider_id)
        except EskizStatusNotReady:
            # Provider may not index the message immediately after send.
            continue
        except EskizClientError as exc:
            logger.warning("Eskiz status check failed for %s: %s", provider_id, exc)
            break

        latest_status = _extract_delivery_status(latest_payload)
        if latest_status and latest_status not in PENDING_DELIVERY_STATUSES:
            return latest_status, latest_payload

    return _extract_delivery_status(latest_payload), latest_payload


def send_sms_otp(db: Session, phone: str) -> dict:
    normalized_phone = normalize_uz_phone_or_raise(phone)
    now = datetime.now(timezone.utc)

    latest = (
        db.query(PhoneOtp)
        .filter(PhoneOtp.phone == normalized_phone)
        .order_by(PhoneOtp.created_at.desc())
        .first()
    )

    if latest and latest.created_at:
        elapsed = int((now - _as_utc(latest.created_at)).total_seconds())
        if elapsed < settings.OTP_COOLDOWN_SECONDS:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="rate_limited",
            )

    code = generate_otp_code()
    otp = PhoneOtp(
        phone=normalized_phone,
        code_hash=hash_otp_code(normalized_phone, code),
        expires_at=now + timedelta(seconds=settings.OTP_EXPIRE_SECONDS),
        attempts=0,
        is_used=False,
    )

    db.add(otp)

    provider_payload = None
    delivery_payload = None
    delivery_status = None

    if settings.ESKIZ_DISABLE_SEND:
        logger.warning("ESKIZ_DISABLE_SEND=True — skipping SMS send for %s", normalized_phone)
    else:
        if settings.ESKIZ_TEST_MODE:
            # In Eskiz test mode provider only accepts a fixed text, so we can't include OTP in SMS.
            message = settings.ESKIZ_TEST_TEXT or "Bu Eskiz dan test"
        else:
            # Use approved template; {code} placeholder is replaced with actual OTP.
            template = settings.ESKIZ_MESSAGE_TEMPLATE or ""
            message = template.format(code=code) if "{code}" in template else f"{template} {code}".strip()

        try:
            provider_payload = eskiz_client.send_sms(
                to_eskiz_phone(normalized_phone),
                message,
            )
            logger.info("Eskiz send ok", extra={"payload": provider_payload, "phone": normalized_phone})
            provider_id = provider_payload.get("id")
            if provider_id:
                delivery_status, delivery_payload = _poll_delivery_status(str(provider_id))
                if delivery_status in FAILED_DELIVERY_STATUSES:
                    db.rollback()
                    detail = "sms_delivery_failed"
                    delivery_data = (delivery_payload or {}).get("data")
                    if isinstance(delivery_data, dict):
                        provider_msg = str(delivery_data.get("status"))
                    else:
                        provider_msg = "unknown_status"
                    raise HTTPException(
                        status_code=status.HTTP_502_BAD_GATEWAY,
                        detail=detail if not settings.DEBUG else f"{detail}: {provider_msg}",
                    )
        except EskizClientError as exc:
            db.rollback()
            logger.error("Eskiz SMS send failed: %s", exc)
            detail = "sms_provider_error"
            provider_msg = str(exc)
            if "Для теста можно использовать" in provider_msg:
                detail = "eskiz_test_text_required"
            elif "Temporarily inactive" in provider_msg:
                detail = "eskiz_inactive_account"
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=detail if not settings.DEBUG else f"{detail}: {provider_msg}",
            ) from exc

    db.commit()
    provider_meta = {}
    if provider_payload:
        provider_meta = {
            "provider_status": provider_payload.get("status"),
            "provider_id": provider_payload.get("id"),
            "delivery_status": delivery_status,
        }
        if settings.DEBUG:
            provider_meta["provider_message"] = provider_payload.get("message")

    return {
        "success": True,
        "cooldown_seconds": settings.OTP_COOLDOWN_SECONDS,
        "test_mode": settings.ESKIZ_TEST_MODE,
        **provider_meta,
        **({"debug_code": code} if settings.DEBUG and (settings.ESKIZ_TEST_MODE or settings.ESKIZ_DISABLE_SEND) else {}),
    }


def verify_sms_otp(db: Session, phone: str, code: str) -> dict:
    normalized_phone = normalize_uz_phone_or_raise(phone)
    now = datetime.now(timezone.utc)

    if not code or len(code) != OTP_LENGTH or not code.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_code")

    if normalized_phone == TEST_OTP_PHONE and code == TEST_OTP_CODE:
        return _issue_sms_auth_token(db, normalized_phone)

    otp = (
        db.query(PhoneOtp)
        .filter(
            PhoneOtp.phone == normalized_phone,
            PhoneOtp.is_used.is_(False),
        )
        .order_by(PhoneOtp.created_at.desc())
        .first()
    )

    if not otp:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_code")

    if otp.expires_at and now > _as_utc(otp.expires_at):
        raise HTTPException(status_code=status.HTTP_410_GONE, detail="expired")

    if otp.attempts >= settings.OTP_MAX_ATTEMPTS:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="too_many_attempts")

    provided_hash = hash_otp_code(normalized_phone, code)
    if not hmac.compare_digest(provided_hash, otp.code_hash):
        otp.attempts += 1
        db.commit()
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_code")

    otp.is_used = True
    otp.used_at = now

    return _issue_sms_auth_token(db, normalized_phone)
