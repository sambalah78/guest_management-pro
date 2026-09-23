"""Scanner station business service."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..core.exceptions import AuthorizationError
from ..repositories.scanner_repository import ScannerRepository
from .auth_service import AuthService
from .event_service import EventService


class ScannerService:
    def __init__(
        self,
        repo: Optional[ScannerRepository] = None,
        event_service: Optional[EventService] = None,
    ) -> None:
        self.repo = repo or ScannerRepository()
        self.event_service = event_service or EventService()

    def _authorize_event_admin(
        self,
        event_id: int,
        user_id: str,
        user: Optional[Dict[str, Any]],
    ) -> None:
        """Authorize an active OWNER/ADMIN for the requested event."""
        if not user_id:
            raise AuthorizationError("Authenticated user required")

        if not AuthService.can_manage_events(user):
            raise AuthorizationError(
                "User is not authorized to manage scanner stations"
            )

        # EventService enforces event-level access.
        self.event_service.get_event(
            int(event_id),
            user_id,
            user,
        )

    def get_scanners(
        self,
        event_id: int,
        user_id: str,
        user: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        self._authorize_event_admin(
            event_id=event_id,
            user_id=user_id,
            user=user,
        )

        return self.repo.get_by_event(int(event_id))

    def get_scanner(
        self,
        event_id: int,
        device_id: str,
        user_id: str,
        user: Optional[Dict[str, Any]] = None,
    ) -> Optional[Dict[str, Any]]:
        self._authorize_event_admin(
            event_id=event_id,
            user_id=user_id,
            user=user,
        )

        return self.repo.get_by_device(
            int(event_id),
            str(device_id).strip(),
        )

    def activate_scanner(
        self,
        event_id: int,
        device_id: str,
        user_id: str,
        user: Optional[Dict[str, Any]] = None,
    ):
        self._authorize_event_admin(
            event_id=event_id,
            user_id=user_id,
            user=user,
        )

        return self.repo.set_active(
            event_id=int(event_id),
            device_id=device_id,
            is_active=True,
        )

    def deactivate_scanner(
        self,
        event_id: int,
        device_id: str,
        user_id: str,
        user: Optional[Dict[str, Any]] = None,
    ):
        self._authorize_event_admin(
            event_id=event_id,
            user_id=user_id,
            user=user,
        )

        return self.repo.set_active(
            event_id=int(event_id),
            device_id=device_id,
            is_active=False,
        )

    def delete_scanner(
        self,
        event_id: int,
        device_id: str,
        user_id: str,
        user: Optional[Dict[str, Any]] = None,
    ):
        self._authorize_event_admin(
            event_id=event_id,
            user_id=user_id,
            user=user,
        )

        return self.repo.delete(
            event_id=int(event_id),
            device_id=device_id,
        )

    def record_scan(
        self,
        event_id: int,
        device_id: str,
    ):
        """
        Record a scanner scan.

        This is intentionally machine-side rather than human-admin
        authorization. The scanner identity has already been authenticated
        by CheckinService before the scan reaches this method.
        """
        return self.repo.increment_scans(
            event_id=int(event_id),
            device_id=device_id,
        )
