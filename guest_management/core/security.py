"""Security helpers used by QR and scanner flows."""

from __future__ import annotations

import base64
import hashlib
import hmac
import secrets

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from urllib.parse import parse_qs, urlparse

from .config import settings
from .exceptions import ValidationError


_SESSION_ID_BYTES = 32
_AES_GCM_NONCE_BYTES = 12
_AES_KEY_BYTES = 32


def create_session_id() -> str:
    """Create a cryptographically random opaque session identifier."""
    return secrets.token_urlsafe(_SESSION_ID_BYTES)


def hash_session_id(session_id: str) -> str:
    """Return the SHA-256 digest used to identify a server-side session."""
    value = (session_id or "").strip()
    if not value:
        raise ValueError("session_id must not be empty")

    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def _session_encryption_key() -> bytes:
    """Decode and validate the configured AES-256-GCM key."""
    raw = settings.session_encryption_key.strip()

    try:
        key = base64.urlsafe_b64decode(raw.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise ValueError(
            "SESSION_ENCRYPTION_KEY must be a valid URL-safe base64 key"
        ) from exc

    if len(key) != _AES_KEY_BYTES:
        raise ValueError(
            "SESSION_ENCRYPTION_KEY must decode to exactly 32 bytes"
        )

    return key


def encrypt_session_token(token: str) -> str:
    """Encrypt a Supabase session token using AES-256-GCM."""
    if not token:
        raise ValueError("token must not be empty")

    nonce = secrets.token_bytes(_AES_GCM_NONCE_BYTES)
    ciphertext = AESGCM(_session_encryption_key()).encrypt(
        nonce,
        token.encode("utf-8"),
        None,
    )

    payload = nonce + ciphertext
    return base64.urlsafe_b64encode(payload).decode("ascii")


def decrypt_session_token(ciphertext: str) -> str:
    """Decrypt a server-side Supabase session token."""
    if not ciphertext:
        raise ValueError("ciphertext must not be empty")

    try:
        payload = base64.urlsafe_b64decode(ciphertext.encode("ascii"))
    except (ValueError, UnicodeEncodeError) as exc:
        raise ValueError("Invalid encrypted session token") from exc

    minimum_length = _AES_GCM_NONCE_BYTES + 16
    if len(payload) < minimum_length:
        raise ValueError("Invalid encrypted session token")

    nonce = payload[:_AES_GCM_NONCE_BYTES]
    encrypted = payload[_AES_GCM_NONCE_BYTES:]

    try:
        plaintext = AESGCM(_session_encryption_key()).decrypt(
            nonce,
            encrypted,
            None,
        )
    except (InvalidTag, ValueError) as exc:
        raise ValueError("Invalid encrypted session token") from exc

    return plaintext.decode("utf-8")


def create_qr_token(event_id: int, guest_id: str) -> str:
    """Create a non-forgeable deterministic token for a guest/event pair."""
    payload = f"{int(event_id)}:{guest_id.strip()}".encode()
    return hmac.new(settings.qr_secret.encode(), payload, hashlib.sha256).hexdigest()


def verify_qr_token(event_id: int, guest_id: str, token: str) -> bool:
    expected = create_qr_token(event_id, guest_id)
    return bool(token) and hmac.compare_digest(expected, token.strip())




def create_voucher_access_code(event_id: int, guest_id: str) -> str:
    """Create a deterministic, non-forgeable voucher access code."""
    payload = f"voucher-access:{int(event_id)}:{guest_id.strip()}".encode("utf-8")
    digest = hmac.new(
        settings.qr_secret.encode("utf-8"),
        payload,
        hashlib.sha256,
    ).hexdigest().upper()
    return digest[:16]


def verify_voucher_access_code(
    event_id: int,
    guest_id: str,
    code: str,
) -> bool:
    """Verify a voucher access code for one guest/event pair."""
    expected = create_voucher_access_code(event_id, guest_id)
    provided = str(code or "").strip().upper()
    if len(provided) != len(expected):
        return False
    return hmac.compare_digest(expected, provided)


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
