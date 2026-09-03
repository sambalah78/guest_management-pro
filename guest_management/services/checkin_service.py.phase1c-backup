"""Production check-in service.

The service is intentionally small: validation and QR authentication happen
here; concurrency and counters happen atomically in PostgreSQL.
"""

from __future__ import annotations

import os
from typing import Any, Dict

from guest_management.core.exceptions import GuestAlreadyCheckedInError, GuestNotFoundError, ValidationError
from guest_management.core.security import create_qr_token, extract_scan_payload, verify_qr_token
from guest_management.repositories.guest_repository import GuestRepository


class CheckinService:
    def __init__(self, repository: GuestRepository | None = None):
        self.repository = repository or GuestRepository()

    def check_in(self, event_id: int, raw_scan: str, scanner_id: str = "") -> Dict[str, Any]:
        try:
            event_id = int(event_id)
        except (TypeError, ValueError) as exc:
            raise ValidationError("Invalid event ID") from exc

        guest_id, token, embedded_event_id = extract_scan_payload(raw_scan)
        if not guest_id:
            raise ValidationError("QR code does not contain a guest ID")
        if embedded_event_id and embedded_event_id != str(event_id):
            raise ValidationError("QR code belongs to a different event")

        # New QR codes are cryptographically signed. Legacy plain guest IDs
        # remain supported only when explicitly enabled for migration.
        allow_legacy = os.getenv("ALLOW_LEGACY_QR", "false").lower() in {"1", "true", "yes"}
        if token:
            if not verify_qr_token(event_id, guest_id, token):
                raise ValidationError("Invalid or tampered QR code")
        elif not allow_legacy:
            raise ValidationError("Legacy QR codes are disabled")

        result = self.repository.check_in(event_id, guest_id, scanner_id)
        if result.get("result") == "already_checked_in":
            raise GuestAlreadyCheckedInError(result.get("message", "Guest already checked in"))
        if result.get("result") == "not_found":
            raise GuestNotFoundError(result.get("message", "Guest not found"))
        result["receipt_token"] = create_qr_token(event_id, guest_id)
        return result
