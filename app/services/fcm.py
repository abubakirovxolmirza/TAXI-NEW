from typing import Any, Dict, List, Optional

from sqlalchemy.orm import Session

from app.models import DeviceToken
from app.services.fcm_client import send_push_once_to_token, send_push_to_tokens

__all__ = [
    "send_push_to_tokens",
    "send_push_once_to_token",
]


def send_push_to_tokens_compat(
    db: Session,
    device_tokens: List[DeviceToken],
    title: str,
    body: str,
    data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return send_push_to_tokens(
        db=db,
        device_tokens=device_tokens,
        title=title,
        body=body,
        data=data,
    )
