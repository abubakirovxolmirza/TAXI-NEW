from __future__ import annotations

import threading
from datetime import datetime, timezone

import httpx

from app.config import settings


class EskizClientError(Exception):
    pass


class EskizClient:
    def __init__(self) -> None:
        self._token: str | None = None
        self._obtained_at: datetime | None = None
        self._lock = threading.Lock()

    def _build_url(self, path: str) -> str:
        base = (settings.ESKIZ_BASE_URL or "https://notify.eskiz.uz/api").rstrip("/")
        return f"{base}/{path.lstrip('/')}"

    def _ensure_credentials(self) -> None:
        if not settings.ESKIZ_EMAIL or not settings.ESKIZ_SECRET:
            raise EskizClientError("Eskiz credentials are not configured")

    def _extract_token(self, payload: dict) -> str | None:
        if not isinstance(payload, dict):
            return None
        data = payload.get("data")
        if isinstance(data, dict) and data.get("token"):
            return str(data["token"])
        token = payload.get("token")
        if token:
            return str(token)
        return None

    def _login(self) -> str:
        self._ensure_credentials()
        try:
            response = httpx.post(
                self._build_url("auth/login"),
                data={
                    "email": settings.ESKIZ_EMAIL,
                    "password": settings.ESKIZ_SECRET,
                },
                timeout=settings.HTTP_TIMEOUT_SECONDS,
            )
        except httpx.HTTPError as exc:
            raise EskizClientError(f"Eskiz auth request failed: {exc}") from exc

        if response.status_code >= 400:
            raise EskizClientError(f"Eskiz auth failed with status {response.status_code}")

        try:
            payload = response.json()
        except ValueError as exc:
            raise EskizClientError("Eskiz auth returned invalid JSON") from exc

        token = self._extract_token(payload)
        if not token:
            raise EskizClientError("Eskiz auth returned no token")

        self._token = token
        self._obtained_at = datetime.now(timezone.utc)
        return token

    def _get_token(self) -> str:
        with self._lock:
            if self._token:
                return self._token
            return self._login()

    def _send_sms_request(self, token: str, phone_digits: str, message: str) -> httpx.Response:
        return httpx.post(
            self._build_url("message/sms/send"),
            headers={"Authorization": f"Bearer {token}"},
            data={
                "mobile_phone": phone_digits,
                "message": message,
                "from": settings.ESKIZ_FROM,
            },
            timeout=settings.HTTP_TIMEOUT_SECONDS,
        )

    def send_sms(self, phone_digits: str, message: str) -> None:
        token = self._get_token()

        try:
            response = self._send_sms_request(token, phone_digits, message)
        except httpx.HTTPError as exc:
            raise EskizClientError(f"Eskiz send request failed: {exc}") from exc

        if response.status_code == 401:
            with self._lock:
                token = self._login()
            try:
                response = self._send_sms_request(token, phone_digits, message)
            except httpx.HTTPError as exc:
                raise EskizClientError(f"Eskiz retry send failed: {exc}") from exc

        if response.status_code >= 400:
            raise EskizClientError(f"Eskiz send failed with status {response.status_code}")


eskiz_client = EskizClient()
