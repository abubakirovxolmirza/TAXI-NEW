import json
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

import firebase_admin
from firebase_admin import credentials, messaging
from sqlalchemy.orm import Session

from app.config import settings
from app.models import DeviceToken

logger = logging.getLogger(__name__)

_FIREBASE_APP: Optional[firebase_admin.App] = None

_INVALID_TOKEN_MARKERS = {
    "registration-token-not-registered",
    "invalid-registration-token",
    "unregistered",
}


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _stringify_data(data: Optional[Dict[str, Any]]) -> Dict[str, str]:
    payload: Dict[str, str] = {}
    if not data:
        return payload
    for key, value in data.items():
        if value is None:
            continue
        if isinstance(value, str):
            payload[str(key)] = value
        else:
            payload[str(key)] = json.dumps(value, ensure_ascii=False)
    return payload


def _load_firebase_credentials() -> Optional[credentials.Base]:
    if settings.FCM_SERVICE_ACCOUNT_FILE:
        return credentials.Certificate(settings.FCM_SERVICE_ACCOUNT_FILE)

    if settings.FCM_SERVICE_ACCOUNT_JSON:
        try:
            parsed = json.loads(settings.FCM_SERVICE_ACCOUNT_JSON)
        except json.JSONDecodeError:
            logger.exception("Invalid FCM_SERVICE_ACCOUNT_JSON")
            return None
        return credentials.Certificate(parsed)

    return None


def get_firebase_app() -> Optional[firebase_admin.App]:
    global _FIREBASE_APP

    if not settings.FCM_ENABLED:
        return None

    if _FIREBASE_APP is not None:
        return _FIREBASE_APP

    try:
        creds = _load_firebase_credentials()
        if creds is None:
            logger.warning("FCM credentials are not configured. Push sending is skipped.")
            return None
        _FIREBASE_APP = firebase_admin.initialize_app(creds)
        return _FIREBASE_APP
    except Exception:
        logger.exception("Failed to initialize Firebase Admin SDK")
        return None


def _is_invalid_token_error(exc: Exception) -> bool:
    marker = str(exc).lower()
    return any(token in marker for token in _INVALID_TOKEN_MARKERS)


def _deactivate_tokens(db: Session, tokens: Iterable[DeviceToken]) -> int:
    changed = 0
    now = _utc_now()
    for token in tokens:
        if token.is_active:
            token.is_active = False
            token.updated_at = now
            changed += 1
    return changed


def send_push_to_tokens(
    db: Session,
    device_tokens: List[DeviceToken],
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    app = get_firebase_app()
    active_tokens = [token for token in device_tokens if token and token.is_active and token.token]

    result = {
        "total_tokens": len(active_tokens),
        "success_count": 0,
        "failure_count": 0,
        "invalidated_tokens": 0,
        "skipped": False,
    }

    if not active_tokens:
        return result

    if app is None:
        result["skipped"] = True
        return result

    payload = _stringify_data(data)
    raw_tokens = [token.token for token in active_tokens]
    invalid_records: List[DeviceToken] = []

    for idx in range(0, len(raw_tokens), 500):
        batch_tokens = raw_tokens[idx : idx + 500]
        batch_models = active_tokens[idx : idx + 500]

        message = messaging.MulticastMessage(
            tokens=batch_tokens,
            notification=messaging.Notification(title=title, body=body),
            data=payload,
            android=messaging.AndroidConfig(priority="high"),
            apns=messaging.APNSConfig(
                payload=messaging.APNSPayload(
                    aps=messaging.Aps(sound="default", content_available=True)
                )
            ),
        )

        try:
            response = messaging.send_each_for_multicast(message, app=app)
        except Exception:
            logger.exception("FCM multicast send failed for batch of size %s", len(batch_tokens))
            result["failure_count"] += len(batch_tokens)
            continue

        result["success_count"] += response.success_count
        result["failure_count"] += response.failure_count

        for i, item in enumerate(response.responses):
            if item.success:
                batch_models[i].last_seen_at = _utc_now()
                continue
            exc = item.exception
            if exc and _is_invalid_token_error(exc):
                invalid_records.append(batch_models[i])

    if invalid_records:
        result["invalidated_tokens"] = _deactivate_tokens(db, invalid_records)

    db.commit()
    return result
