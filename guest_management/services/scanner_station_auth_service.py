"""Scanner station authentication service.

Scanner workstations use a short admin-assigned PIN for the first login.
The PIN is never stored in plaintext. The existing access_token_hash column
is retained as the verifier column to avoid a database migration.

After PIN authentication, a signed short-lived station session is issued.
The browser stores that session in sessionStorage, so the agent enters the PIN
once per browser tab/session and does not have to re-enter it after navigation.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import re
import secrets
import time
from typing import Any, Dict, Optional

from ..core.config import settings
from ..repositories.scanner_repository import ScannerRepository


class ScannerStationAuthService:
    """Authenticate scanner workstations using a PIN or signed session."""

    SESSION_PREFIX = "ELSS_"
    SESSION_TTL_SECONDS = 12 * 60 * 60
    PIN_PATTERN = re.compile(r"^\d{4}$")

    def __init__(self, repo: Optional[ScannerRepository] = None):
        self.repo = repo or ScannerRepository()

    @staticmethod
    def _secret() -> bytes:
        secret = str(settings.scanner_station_secret or "")
        if len(secret) < 32:
            raise ValueError(
                "Scanner station credential secret must contain at least 32 characters."
            )
        return secret.encode("utf-8")

    @classmethod
    def _hash_pin(cls, pin: str) -> str:
        pin = str(pin or "").strip()
        if not cls.PIN_PATTERN.fullmatch(pin):
            raise ValueError("Scanner PIN must be exactly 4 digits.")
        return hmac.new(
            cls._secret(),
            pin.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @classmethod
    def _sign_session_payload(cls, encoded_payload: str) -> str:
        return hmac.new(
            cls._secret(),
            encoded_payload.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    @staticmethod
    def decrypt_pin(ciphertext: str) -> str:
        return ScannerRepository.decrypt_pin(ciphertext)

    @classmethod
    def issue_session(
        cls,
        scanner: Dict[str, Any],
        ttl_seconds: Optional[int] = None,
    ) -> str:
        """Issue a signed station session after successful PIN auth."""
        ttl = int(ttl_seconds or cls.SESSION_TTL_SECONDS)
        payload = {
            "event_id": int(scanner.get("event_id") or 0),
            "device_id": str(scanner.get("device_id") or ""),
            "exp": int(time.time()) + ttl,
            "nonce": secrets.token_urlsafe(12),
        }
        raw = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode()
        encoded = base64.urlsafe_b64encode(raw).decode().rstrip("=")
        signature = cls._sign_session_payload(encoded)
        return f"{cls.SESSION_PREFIX}{encoded}.{signature}"

    def _verify_session(
        self,
        event_id: int,
        session_token: str,
    ) -> Optional[Dict[str, Any]]:
        cls = type(self)
        token = str(session_token or "").strip()
        if not token.startswith(cls.SESSION_PREFIX):
            return None

        value = token[len(cls.SESSION_PREFIX):]
        try:
            encoded, signature = value.rsplit(".", 1)
        except ValueError:
            return None

        expected = cls._sign_session_payload(encoded)
        if not hmac.compare_digest(signature, expected):
            return None

        try:
            padded = encoded + "=" * (-len(encoded) % 4)
            payload = json.loads(
                base64.urlsafe_b64decode(padded.encode()).decode()
            )
            token_event_id = int(payload.get("event_id") or 0)
            device_id = str(payload.get("device_id") or "")
            exp = int(payload.get("exp") or 0)
        except Exception:
            return None

        if token_event_id != int(event_id):
            return None
        if not device_id or exp <= int(time.time()):
            return None

        scanner = self.repo.get_by_device(
            int(event_id),
            device_id,
        )
        if not scanner or not scanner.get("is_active", False):
            return None

        return scanner

    def authenticate(
        self,
        event_id: int,
        access_token: str,
    ) -> Optional[Dict[str, Any]]:
        """Authenticate a scanner station by PIN or signed station session.

        ``access_token`` is retained as the argument name for compatibility
        with existing CheckinService callers. New UI passes either a 4-digit
        PIN or an ``ELSS_`` station session token.
        """
        credential = str(access_token or "").strip()
        if not credential:
            return None

        if credential.startswith(self.SESSION_PREFIX):
            return self._verify_session(int(event_id), credential)

        # Backward compatibility for stations provisioned before the PIN
        # migration. The UI no longer exposes these tokens.
        if credential.startswith("ELST_"):
            token_hash = ScannerRepository.hash_access_token(
                credential,
                settings.scanner_station_secret,
            )
            scanner = self.repo.get_by_access_token_hash(token_hash)
            if (
                scanner
                and scanner.get("is_active", False)
                and int(scanner.get("event_id", 0)) == int(event_id)
            ):
                return scanner
            return None

        if not self.PIN_PATTERN.fullmatch(credential):
            return None

        pin_hash = self._hash_pin(credential)
        scanner = self.repo.get_by_access_token_hash(pin_hash)

        if not scanner:
            return None
        if not scanner.get("is_active", False):
            return None
        if int(scanner.get("event_id", 0)) != int(event_id):
            return None

        return scanner

    def provision_station(
        self,
        event_id: int,
        device_name: str,
        assigned_by: Optional[str] = None,
        actor_user_id: Optional[str] = None,
        actor_user: Optional[dict] = None,
        pin: Optional[str] = None,
    ) -> tuple[Dict[str, Any], str]:
        """Create a station using an admin-assigned 4-digit PIN."""
        del actor_user_id, actor_user

        scanner_pin = str(pin or "").strip()
        if not self.PIN_PATTERN.fullmatch(scanner_pin):
            raise ValueError("Scanner PIN must be exactly 4 digits.")

        pin_hash = self._hash_pin(scanner_pin)

        # A PIN must identify exactly one station within an event.
        for existing in self.repo.get_by_event(int(event_id)):
            if str(existing.get("access_token_hash") or "").strip() == pin_hash:
                raise ValueError(
                    "That PIN is already assigned to another scanner in this event."
                )

        pin_ciphertext = self.repo.encrypt_pin(scanner_pin)

        scanner = self.repo.create(
            event_id=int(event_id),
            device_name=str(device_name).strip(),
            access_token_hash=pin_hash,
            assigned_by=assigned_by,
            pin_ciphertext=pin_ciphertext,
        )

        return scanner, scanner_pin