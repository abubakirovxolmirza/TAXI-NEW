from __future__ import annotations

import hashlib
import hmac
from typing import Any, Mapping


def _md5_hex(value: str) -> str:
    return hashlib.md5(value.encode("utf-8")).hexdigest()


def _get(payload: Mapping[str, Any], key: str) -> str:
    value = payload.get(key)
    if value is None:
        return ""
    return str(value)


def calc_prepare_sign(payload: Mapping[str, Any], secret_key: str) -> str:
    """
    Prepare sign formula (CLICK docs):
    md5(click_trans_id + service_id + secret_key + merchant_trans_id + amount + action + sign_time)
    """
    parts = (
        _get(payload, "click_trans_id"),
        _get(payload, "service_id"),
        secret_key,
        _get(payload, "merchant_trans_id"),
        _get(payload, "amount"),
        _get(payload, "action"),
        _get(payload, "sign_time"),
    )
    return _md5_hex("".join(parts))


def calc_complete_sign(payload: Mapping[str, Any], secret_key: str) -> str:
    """
    Complete sign formula (CLICK docs):
    md5(click_trans_id + service_id + secret_key + merchant_trans_id + merchant_prepare_id + amount + action + sign_time)
    """
    parts = (
        _get(payload, "click_trans_id"),
        _get(payload, "service_id"),
        secret_key,
        _get(payload, "merchant_trans_id"),
        _get(payload, "merchant_prepare_id"),
        _get(payload, "amount"),
        _get(payload, "action"),
        _get(payload, "sign_time"),
    )
    return _md5_hex("".join(parts))


def is_valid_prepare_sign(payload: Mapping[str, Any], secret_key: str) -> bool:
    provided = _get(payload, "sign_string").lower()
    if not provided:
        return False
    expected = calc_prepare_sign(payload, secret_key).lower()
    return hmac.compare_digest(expected, provided)


def is_valid_complete_sign(payload: Mapping[str, Any], secret_key: str) -> bool:
    provided = _get(payload, "sign_string").lower()
    if not provided:
        return False
    expected = calc_complete_sign(payload, secret_key).lower()
    return hmac.compare_digest(expected, provided)
