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
from guest_management.core.config import settings
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
from guest_management.services.scanner_station_auth_service import (
    ScannerStationAuthService,
)

class CheckinService:
    """Application service for authenticated guest check-in."""

    def __init__(
            self,
            repository: CheckinRepository | None = None,
            scanner_auth_service: ScannerStationAuthService | None = None,
    ):
        self.repository = repository or CheckinRepository()
        self.scanner_auth_service = (
                scanner_auth_service or ScannerStationAuthService()
        )

    def check_in(
        self,
        event_id: int,
        raw_scan: str,
        scanner_id: str = "",
        *,
        scanner_access_token: str = "",
        manual: bool = False,
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
        # 2–4. Resolve and validate check-in input
        # --------------------------------------------------------------
        if manual:
            # Manual check-in receives an already-resolved guest ID.
            # GuestState is responsible for authenticating the staff/admin
            # and resolving the guest within the selected event.
            guest_id = str(raw_scan or "").strip()

            if not guest_id:
                raise ValidationError(
                    "Guest ID is required for manual check-in"
                )

        else:
            # Normal scanner/QR check-in path.
            guest_id, token, embedded_event_id = extract_scan_payload(
                raw_scan
            )

            if not guest_id:
                raise ValidationError(
                    "QR code does not contain a guest ID"
                )

            # --------------------------------------------------------------
            # Prevent cross-event QR usage
            # --------------------------------------------------------------
            if (
                    embedded_event_id
                    and embedded_event_id != str(event_id)
            ):
                raise ValidationError(
                    "QR code belongs to a different event"
                )

            # --------------------------------------------------------------
            # Validate signed QR / legacy QR
            # --------------------------------------------------------------
            allow_legacy = settings.allow_legacy_qr

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
        # 5. Authorize scanner station at the service boundary
        # --------------------------------------------------------------
        #
        # ScannerState performs the same check for UI/state protection,
        # but the service must independently enforce the security boundary.
        #
        # Manual/admin check-ins intentionally do not require a scanner
        # station credential.
        #
        if not manual:
            authenticated_scanner_id = str(scanner_id or "").strip()
            scanner_token = str(scanner_access_token or "").strip()

            if not authenticated_scanner_id:
                raise ValidationError(
                    "Scanner station identity required"
                )

            if not scanner_token:
                raise ValidationError(
                    "Scanner station authentication required"
                )

            scanner = self.scanner_auth_service.authenticate(
                event_id=event_id,
                access_token=scanner_token,
            )

            if not scanner:
                raise ValidationError(
                    "Invalid, inactive, or incorrectly assigned scanner station"
                )

            authenticated_station_id = str(
                scanner.get("device_id") or ""
            ).strip()

            if authenticated_station_id != authenticated_scanner_id:
                raise ValidationError(
                    "Scanner station identity mismatch"
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