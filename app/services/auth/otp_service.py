from __future__ import annotations

import hashlib
import hmac
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.auth import create_access_token
from app.config import settings
from app.models import PhoneOtp, User
from app.services.phone import normalize_phone
from app.services.sms.eskiz_client import EskizClientError, eskiz_client


OTP_LENGTH = 6


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

    try:
        eskiz_client.send_sms(
            to_eskiz_phone(normalized_phone),
            f"TashkentGO: Your login code is {code}. Valid 2 minutes.",
        )
    except EskizClientError as exc:
        db.rollback()
        raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail="sms_provider_error") from exc

    db.commit()
    return {
        "success": True,
        "cooldown_seconds": settings.OTP_COOLDOWN_SECONDS,
    }


def verify_sms_otp(db: Session, phone: str, code: str) -> dict:
    normalized_phone = normalize_uz_phone_or_raise(phone)
    now = datetime.now(timezone.utc)

    if not code or len(code) != OTP_LENGTH or not code.isdigit():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="invalid_code")

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

    user = db.query(User).filter(User.telephone == normalized_phone).first()
    if not user:
        user = User(
            telephone=normalized_phone,
            name=normalized_phone,
            hashed_password="",
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
