"""Production check-in service.

QR validation/authentication is handled here.
Guest lookup and check-in persistence are handled by their respective
repositories.

Architecture:

    State
      ↓
    CheckinService
      ├── QR validation
      └── CheckinRepository
              ↓
          check_in_guest RPC
"""

from __future__ import annotations

import os
from typing import Any, Dict

from guest_management.core.exceptions import (
    GuestAlreadyCheckedInError,
    GuestNotFoundError,
    ValidationError,
)
from guest_management.core.security import (
    create_qr_token,
    extract_scan_payload,
    verify_qr_token,
)
from guest_management.repositories.checkin_repository import CheckinRepository


class CheckinService:
    """Application service for authenticated guest check-in."""

    def __init__(
        self,
        repository: CheckinRepository | None = None,
    ):
        self.repository = repository or CheckinRepository()

    def check_in(
        self,
        event_id: int,
        raw_scan: str,
        scanner_id: str = "",
    ) -> Dict[str, Any]:
        """Validate a QR code and perform an atomic check-in.

        Args:
            event_id: Event the scanner is operating against.
            raw_scan: Raw QR value returned by the scanner.
            scanner_id: Optional scanner/device identifier.

        Returns:
            Result returned by the check-in RPC, plus a receipt token.

        Raises:
            ValidationError:
                Invalid event, malformed QR, wrong event, invalid token,
                or disabled legacy QR.
            GuestAlreadyCheckedInError:
                Guest has already checked in.
            GuestNotFoundError:
                Guest does not exist in the selected event.
        """

        # --------------------------------------------------------------
        # 1. Validate event ID
        # --------------------------------------------------------------
        try:
            event_id = int(event_id)
        except (TypeError, ValueError) as exc:
            raise ValidationError("Invalid event ID") from exc

        if event_id <= 0:
            raise ValidationError("Invalid event ID")

        # --------------------------------------------------------------
        # 2. Extract QR payload
        # --------------------------------------------------------------
        guest_id, token, embedded_event_id = extract_scan_payload(
            raw_scan
        )

        if not guest_id:
            raise ValidationError(
                "QR code does not contain a guest ID"
            )

        # --------------------------------------------------------------
        # 3. Prevent cross-event QR usage
        # --------------------------------------------------------------
        if (
            embedded_event_id
            and embedded_event_id != str(event_id)
        ):
            raise ValidationError(
                "QR code belongs to a different event"
            )

        # --------------------------------------------------------------
        # 4. Validate signed QR / legacy QR
        # --------------------------------------------------------------
        allow_legacy = (
            os.getenv("ALLOW_LEGACY_QR", "false").lower()
            in {"1", "true", "yes"}
        )

        if token:
            if not verify_qr_token(
                event_id,
                guest_id,
                token,
            ):
                raise ValidationError(
                    "Invalid or tampered QR code"
                )

        elif not allow_legacy:
            raise ValidationError(
                "Legacy QR codes are disabled"
            )

        # --------------------------------------------------------------
        # 5. Atomic database check-in
        # --------------------------------------------------------------
        result = self.repository.check_in(
            event_id=event_id,
            guest_id=guest_id,
            scanner_id=scanner_id,
        )

        # --------------------------------------------------------------
        # 6. Normalize repository result
        # --------------------------------------------------------------
        if result.get("result") == "already_checked_in":
            raise GuestAlreadyCheckedInError(
                result.get(
                    "message",
                    "Guest already checked in",
                )
            )

        if result.get("result") == "not_found":
            raise GuestNotFoundError(
                result.get(
                    "message",
                    "Guest not found",
                )
            )

        if result.get("result") != "checked_in":
            raise ValidationError(
                result.get(
                    "message",
                    "Check-in failed",
                )
            )

        # --------------------------------------------------------------
        # 7. Generate receipt token
        # --------------------------------------------------------------
        result["receipt_token"] = create_qr_token(
            event_id,
            guest_id,
        )

        return result