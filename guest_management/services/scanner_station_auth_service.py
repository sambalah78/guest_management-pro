"""Scanner station authentication and provisioning service."""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from ..core.config import settings
from ..core.exceptions import AuthorizationError
from ..repositories.scanner_repository import ScannerRepository
from .auth_service import AuthService
from .event_service import EventService


class ScannerStationAuthService:
    def __init__(
        self,
        repo: Optional[ScannerRepository] = None,
        event_service: Optional[EventService] = None,
    ) -> None:
        self.repo = repo or ScannerRepository()
        self.event_service = event_service or EventService()

    def authenticate(
        self,
        event_id: int,
        access_token: str,
    ) -> Dict[str, Any]:
        token = (access_token or "").strip()

        if not token:
            raise AuthorizationError("Scanner access token required")

        token_hash = ScannerRepository.hash_access_token(
            token,
            settings.scanner_station_secret,
        )

        scanner = self.repo.get_by_access_token_hash(token_hash)

        if not scanner:
            raise AuthorizationError("Invalid scanner access token")

        if not scanner.get("is_active"):
            raise AuthorizationError("Scanner station is inactive")

        if int(scanner["event_id"]) != int(event_id):
            raise AuthorizationError(
                "Scanner station is not assigned to this event"
            )

        return scanner

    def provision_station(
        self,
        event_id: int,
        device_name: str,
        actor_user_id: Optional[str] = None,
        actor_user: Optional[Dict[str, Any]] = None,
    ) -> Tuple[Dict[str, Any], str]:
        """
        Provision a scanner station.

        Scanner provisioning is an administrative operation and therefore
        requires an authenticated active OWNER/ADMIN with access to the
        requested event.
        """
        if not actor_user_id:
            raise AuthorizationError("Authenticated user required")

        if not AuthService.can_manage_events(actor_user):
            raise AuthorizationError(
                "User is not authorized to manage scanner stations"
            )

        # EventService enforces event-level authorization.
        self.event_service.get_event(
            int(event_id),
            actor_user_id,
            actor_user,
        )

        token = ScannerRepository.generate_access_token()

        token_hash = ScannerRepository.hash_access_token(
            token,
            settings.scanner_station_secret,
        )

        scanner = self.repo.create(
            event_id=int(event_id),
            device_name=device_name,
            access_token_hash=token_hash,
            assigned_by=actor_user_id,
        )

        # Plaintext token is returned only to the caller that provisioned
        # the scanner. Only the hash is persisted.
        return scanner, token
