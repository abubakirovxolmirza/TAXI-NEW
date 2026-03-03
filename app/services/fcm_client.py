import json
import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import httpx
from google.auth.transport.requests import Request
from google.oauth2 import service_account
from sqlalchemy.orm import Session

from app.config import settings
from app.models import DeviceToken

logger = logging.getLogger(__name__)

FCM_SCOPE = "https://www.googleapis.com/auth/firebase.messaging"
FCM_SEND_URL_TEMPLATE = "https://fcm.googleapis.com/v1/projects/{project_id}/messages:send"
RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}
TOKEN_REFRESH_LEEWAY_SECONDS = 60

_token_lock = threading.Lock()
_cached_credentials: Optional[service_account.Credentials] = None
_cached_project_id: Optional[str] = None
_cached_access_token: Optional[str] = None
_cached_access_token_expiry: Optional[datetime] = None


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _ensure_aware_utc(dt: Optional[datetime]) -> Optional[datetime]:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


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


def _load_service_account_payload() -> Tuple[Optional[Dict[str, Any]], Optional[str]]:
    candidates = [
        settings.SERVICE_ACCOUNT_JSON_PATH,
        settings.FCM_SERVICE_ACCOUNT_FILE,
        settings.GOOGLE_APPLICATION_CREDENTIALS,
    ]
    for path in candidates:
        if not path:
            continue
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle), path
        except Exception:
            logger.exception("Failed to read service account file: %s", path)

    if settings.FCM_SERVICE_ACCOUNT_JSON:
        raw = settings.FCM_SERVICE_ACCOUNT_JSON.strip()
        if raw.startswith("{"):
            try:
                return json.loads(raw), "FCM_SERVICE_ACCOUNT_JSON"
            except json.JSONDecodeError:
                logger.exception("Invalid FCM_SERVICE_ACCOUNT_JSON JSON payload")
        else:
            try:
                with open(raw, "r", encoding="utf-8") as handle:
                    return json.load(handle), raw
            except Exception:
                logger.exception("Failed to read service account json path from FCM_SERVICE_ACCOUNT_JSON: %s", raw)

    return None, None


def _get_credentials() -> Tuple[Optional[service_account.Credentials], Optional[str]]:
    global _cached_credentials, _cached_project_id

    if _cached_credentials is not None and _cached_project_id:
        return _cached_credentials, _cached_project_id

    service_account_payload, source = _load_service_account_payload()
    if not service_account_payload:
        logger.warning("FCM service account is not configured; skipping push send")
        return None, None

    try:
        creds = service_account.Credentials.from_service_account_info(
            service_account_payload,
            scopes=[FCM_SCOPE],
        )
    except Exception:
        logger.exception("Failed to initialize google service account credentials")
        return None, None

    project_id = settings.FCM_PROJECT_ID or service_account_payload.get("project_id")
    if not project_id:
        logger.error("FCM project id is missing. Source=%s", source)
        return None, None

    _cached_credentials = creds
    _cached_project_id = project_id
    return _cached_credentials, _cached_project_id


def _get_access_token() -> Tuple[Optional[str], Optional[str]]:
    global _cached_access_token, _cached_access_token_expiry

    creds, project_id = _get_credentials()
    if creds is None or not project_id:
        return None, None

    with _token_lock:
        now = _utc_now()
        expiry_aware = _ensure_aware_utc(_cached_access_token_expiry)
        if (
            _cached_access_token
            and expiry_aware
            and expiry_aware > now + timedelta(seconds=TOKEN_REFRESH_LEEWAY_SECONDS)
        ):
            return _cached_access_token, project_id

        try:
            creds.refresh(Request())
        except Exception:
            logger.exception("Failed to refresh FCM OAuth token")
            return None, None

        _cached_access_token = creds.token
        expiry = _ensure_aware_utc(creds.expiry) if creds.expiry else now + timedelta(minutes=50)
        _cached_access_token_expiry = expiry
        return _cached_access_token, project_id


def _build_payload(
    *,
    token: str,
    title: str,
    body: str,
    data: Optional[Dict[str, Any]],
    android_channel_id: str,
    android_sound: str,
    ios_sound: str,
) -> Dict[str, Any]:
    return {
        "message": {
            "token": token,
            "notification": {
                "title": title,
                "body": body,
            },
            "data": _stringify_data(data),
            "android": {
                "priority": "HIGH",
                "notification": {
                    "channel_id": android_channel_id,
                    "sound": android_sound,
                },
            },
            "apns": {
                "headers": {
                    "apns-priority": "10",
                },
                "payload": {
                    "aps": {
                        "sound": ios_sound,
                    }
                },
            },
        }
    }


def _parse_json_response(response: httpx.Response) -> Dict[str, Any]:
    try:
        return response.json()
    except Exception:
        return {"raw": response.text}


def _extract_fcm_error_code(error_body: Dict[str, Any]) -> Optional[str]:
    error_obj = error_body.get("error")
    if not isinstance(error_obj, dict):
        return None
    details = error_obj.get("details")
    if isinstance(details, list):
        for detail in details:
            if not isinstance(detail, dict):
                continue
            error_code = detail.get("errorCode")
            if isinstance(error_code, str) and error_code:
                return error_code
    status_text = error_obj.get("status")
    return status_text if isinstance(status_text, str) else None


def _is_invalid_token(status_code: int, error_body: Dict[str, Any]) -> bool:
    error_code = _extract_fcm_error_code(error_body)
    if status_code == 404:
        return True
    if error_code in {"UNREGISTERED", "INVALID_ARGUMENT"}:
        return True
    message = str(error_body.get("error", {}).get("message", "")).lower()
    return "unregistered" in message or "registration token is not a valid fcm registration token" in message


def _token_preview(token: str) -> str:
    if len(token) <= 12:
        return token
    return f"{token[:8]}...{token[-4:]}"


def send_push_once_to_token(
    token: str,
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
    android_channel_id: str = "high_importance_channel",
    android_priority: str = "high",
    android_sound: str = "order_sound",
    ios_sound: str = "default",
) -> Dict[str, Any]:
    if not settings.FCM_ENABLED:
        return {"success": False, "skipped": True, "reason": "fcm_disabled", "status_code": None, "error_body": None}

    access_token, project_id = _get_access_token()
    if not access_token or not project_id:
        return {"success": False, "skipped": True, "reason": "fcm_not_configured", "status_code": None, "error_body": None}

    payload = _build_payload(
        token=token,
        title=title,
        body=body,
        data=data,
        android_channel_id=android_channel_id,
        android_sound=android_sound,
        ios_sound=ios_sound,
    )
    url = FCM_SEND_URL_TEMPLATE.format(project_id=project_id)
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=utf-8",
    }

    last_error: Optional[Dict[str, Any]] = None
    last_status: Optional[int] = None

    for attempt in range(3):
        try:
            with httpx.Client(timeout=settings.HTTP_TIMEOUT_SECONDS) as client:
                response = client.post(url, headers=headers, json=payload)
        except httpx.RequestError as exc:
            logger.exception("FCM request failed (attempt %s)", attempt + 1)
            last_error = {"reason": str(exc)}
            if attempt < 2:
                time.sleep(0.5 * (2 ** attempt))
                continue
            return {
                "success": False,
                "skipped": False,
                "reason": "request_error",
                "status_code": None,
                "error_body": last_error,
            }

        last_status = response.status_code
        body_json = _parse_json_response(response)

        if response.is_success:
            return {
                "success": True,
                "skipped": False,
                "reason": None,
                "status_code": response.status_code,
                "message_id": body_json.get("name"),
                "error_body": None,
                "response_body": body_json,
            }

        last_error = body_json
        if response.status_code in RETRYABLE_STATUS_CODES and attempt < 2:
            time.sleep(0.5 * (2 ** attempt))
            continue
        break

    return {
        "success": False,
        "skipped": False,
        "reason": "fcm_http_error",
        "status_code": last_status,
        "error_body": last_error,
        "response_body": None,
    }


def send_push_to_tokens(
    db: Session,
    device_tokens: List[DeviceToken],
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
    android_channel_id: str = "high_importance_channel",
    android_priority: str = "high",
    android_sound: str = "order_sound",
    ios_sound: str = "default",
) -> Dict[str, Any]:
    active_tokens = [item for item in device_tokens if item and item.is_active and item.token]
    invalid_tokens: List[DeviceToken] = []

    result = {
        "total_tokens": len(active_tokens),
        "success_count": 0,
        "failure_count": 0,
        "invalidated_tokens": 0,
        "skipped": False,
        "failure_reasons": [],
    }

    if not active_tokens:
        return result

    for token_model in active_tokens:
        response = send_push_once_to_token(
            token=token_model.token,
            title=title,
            body=body,
            data=data,
            android_channel_id=android_channel_id,
            android_priority=android_priority,
            android_sound=android_sound,
            ios_sound=ios_sound,
        )

        if response.get("skipped"):
            result["skipped"] = True
            result["failure_count"] += 1
            result["failure_reasons"].append(
                {
                    "device_token_id": token_model.id,
                    "user_id": token_model.user_id,
                    "platform": str(token_model.platform.value) if getattr(token_model, "platform", None) else None,
                    "token_preview": _token_preview(token_model.token),
                    "status_code": response.get("status_code"),
                    "reason": response.get("reason"),
                    "error_code": None,
                    "message": str((response.get("error_body") or {}).get("reason", "Push sending skipped")),
                }
            )
            continue

        if response.get("success"):
            result["success_count"] += 1
            token_model.last_seen_at = _utc_now()
            continue

        result["failure_count"] += 1
        status_code = response.get("status_code")
        error_body = response.get("error_body") or {}
        error_code = _extract_fcm_error_code(error_body) if isinstance(error_body, dict) else None
        error_message = None
        if isinstance(error_body, dict):
            error_message = str(error_body.get("error", {}).get("message", "")) or str(error_body)
        result["failure_reasons"].append(
            {
                "device_token_id": token_model.id,
                "user_id": token_model.user_id,
                "platform": str(token_model.platform.value) if getattr(token_model, "platform", None) else None,
                "token_preview": _token_preview(token_model.token),
                "status_code": status_code,
                "reason": response.get("reason"),
                "error_code": error_code,
                "message": error_message,
            }
        )
        if isinstance(status_code, int) and isinstance(error_body, dict) and _is_invalid_token(status_code, error_body):
            invalid_tokens.append(token_model)

    if invalid_tokens:
        now = _utc_now()
        for token_model in invalid_tokens:
            token_model.is_active = False
            token_model.updated_at = now
        result["invalidated_tokens"] = len(invalid_tokens)

    db.commit()
    return result
