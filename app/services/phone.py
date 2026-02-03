from __future__ import annotations

import re
from typing import Optional

UZ_COUNTRY_CODE = "998"
UZ_LOCAL_LENGTH = 9


def normalize_phone(phone: str) -> Optional[str]:
    if not phone:
        return None
    digits = re.sub(r"\D", "", str(phone))
    if not digits:
        return None

    if digits.startswith(UZ_COUNTRY_CODE):
        if len(digits) != len(UZ_COUNTRY_CODE) + UZ_LOCAL_LENGTH:
            return None
        return f"+{digits}"

    if digits.startswith("0") and len(digits) == UZ_LOCAL_LENGTH + 1:
        digits = digits[1:]

    if len(digits) != UZ_LOCAL_LENGTH:
        return None

    return f"+{UZ_COUNTRY_CODE}{digits}"


def digits_only(phone: str) -> Optional[str]:
    normalized = normalize_phone(phone)
    if not normalized:
        return None
    return normalized.lstrip("+")
