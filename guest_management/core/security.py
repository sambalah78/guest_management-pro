"""Security helpers used by QR and scanner flows."""

from __future__ import annotations

import hashlib
import hmac

from urllib.parse import parse_qs, urlparse

from .config import settings
from .exceptions import ValidationError


def create_qr_token(event_id: int, guest_id: str) -> str:
    """Create a non-forgeable deterministic token for a guest/event pair."""
    payload = f"{int(event_id)}:{guest_id.strip()}".encode()
    return hmac.new(settings.qr_secret.encode(), payload, hashlib.sha256).hexdigest()


def verify_qr_token(event_id: int, guest_id: str, token: str) -> bool:
    expected = create_qr_token(event_id, guest_id)
    return bool(token) and hmac.compare_digest(expected, token.strip())




def extract_scan_payload(raw: str) -> tuple[str | None, str | None, str | None]:
    """Extract guest_id/token/event_id from a QR value or plain guest ID.

    Supports the legacy guest-id format during migration. New QR codes should
    contain /checkin/<event_id>?guest_id=...&token=....
    """
    value = (raw or "").strip()
    if not value:
        raise ValidationError("Empty QR code")

    if value.startswith("http://") or value.startswith("https://"):
        parsed = urlparse(value)
        query = parse_qs(parsed.query)
        guest_id = query.get("guest_id", [None])[0]
        token = query.get("token", [None])[0]
        path_parts = [part for part in parsed.path.split("/") if part]
        event_id = path_parts[-1] if len(path_parts) >= 2 and path_parts[-2] in {
            "checkin", "scanner", "scanner-guest", "scanner_guest"
        } else None
        return guest_id, token, event_id

    return value, None, None
