"""Backward-compatible wrapper around the OTP auth service."""

from app.services.auth.otp_service import (
    send_sms_otp,
    verify_sms_otp,
    normalize_uz_phone_or_raise,
    hash_otp_code,
)

send_otp_code = send_sms_otp


def verify_otp_code_and_get_user(db, phone: str, code: str):
    return verify_sms_otp(db, phone, code)["user"]

__all__ = [
    "send_otp_code",
    "verify_otp_code_and_get_user",
    "send_sms_otp",
    "verify_sms_otp",
    "normalize_uz_phone_or_raise",
    "hash_otp_code",
]
