from __future__ import annotations

import threading
from datetime import datetime, timezone

import httpx

from app.config import settings


class EskizClientError(Exception):
    pass


class EskizStatusNotReady(EskizClientError):
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
            raise EskizClientError(
                f"Eskiz auth failed with status {response.status_code}: {response.text}"
            )

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

    def _get_status_request(self, token: str, message_id: str) -> httpx.Response:
        return httpx.get(
            self._build_url(f"message/sms/status_by_id/{message_id}"),
            headers={"Authorization": f"Bearer {token}"},
            timeout=settings.HTTP_TIMEOUT_SECONDS,
        )

    def _validate_send_response(self, response: httpx.Response) -> dict:
        """Ensure provider responded with success status inside JSON body."""
        try:
            payload = response.json()
        except ValueError:
            payload = None

        if response.status_code >= 400:
            raise EskizClientError(
                f"Eskiz send failed with status {response.status_code}: {response.text}"
            )

        if payload is None:
            raise EskizClientError("Eskiz send returned non-JSON response")

        status_value = str(payload.get("status", "")).lower()
        # Eskiz may return "waiting" while the provider queues the SMS; treat it as non-fatal.
        if status_value and status_value not in {"success", "sent", "queued", "waiting"}:
            raise EskizClientError(
                f"Eskiz send returned status '{status_value}': {payload.get('message') or payload}"
            )

        return payload

    def send_sms(self, phone_digits: str, message: str) -> dict:
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

        return self._validate_send_response(response)

    def get_message_status(self, message_id: str) -> dict:
        if not message_id:
            raise EskizClientError("message_id is required")

        token = self._get_token()
        try:
            response = self._get_status_request(token, message_id)
        except httpx.HTTPError as exc:
            raise EskizClientError(f"Eskiz status request failed: {exc}") from exc

        if response.status_code == 401:
            with self._lock:
                token = self._login()
            try:
                response = self._get_status_request(token, message_id)
            except httpx.HTTPError as exc:
                raise EskizClientError(f"Eskiz retry status request failed: {exc}") from exc

        if response.status_code == 404:
            try:
                payload = response.json()
            except ValueError:
                payload = {}
            message = ""
            if isinstance(payload, dict):
                data = payload.get("data")
                if isinstance(data, dict):
                    message = str(data.get("message") or "")
                if not message:
                    message = str(payload.get("message") or "")
            if "not found" in message.lower():
                raise EskizStatusNotReady(
                    f"Eskiz status is not ready for message {message_id}: {message or 'Not found'}"
                )

        if response.status_code >= 400:
            raise EskizClientError(
                f"Eskiz status failed with status {response.status_code}: {response.text}"
            )

        try:
            payload = response.json()
        except ValueError as exc:
            raise EskizClientError("Eskiz status returned invalid JSON") from exc

        if not isinstance(payload, dict):
            raise EskizClientError("Eskiz status returned invalid payload type")

        return payload


eskiz_client = EskizClient()
