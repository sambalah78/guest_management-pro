"""Scanner station authentication service."""

from __future__ import annotations

from typing import Any, Dict, Optional

from ..core.config import settings
from ..repositories.scanner_repository import ScannerRepository


class ScannerStationAuthService:
    """Authenticate scanner workstations using opaque access tokens."""

    def __init__(
        self,
        repo: Optional[ScannerRepository] = None,
    ):
        self.repo = repo or ScannerRepository()

    def authenticate(
        self,
        event_id: int,
        access_token: str,
    ) -> Optional[Dict[str, Any]]:
        """Authenticate a scanner station by access token.

        Returns a scanner record only when the credential is valid
        and the scanner station is currently active.
        """

        token = str(access_token or "").strip()
        if not token:
            return None

        token_hash = ScannerRepository.hash_access_token(
            token,
            settings.scanner_station_secret,
        )

        scanner = self.repo.get_by_access_token_hash(token_hash)

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
    ) -> tuple[Dict[str, Any], str]:
        """Create a scanner station and return its plaintext credential once."""

        token = ScannerRepository.generate_access_token()

        token_hash = ScannerRepository.hash_access_token(
            token,
            settings.scanner_station_secret,
        )

        scanner = self.repo.create(
            event_id=int(event_id),
            device_name=device_name,
            access_token_hash=token_hash,
            assigned_by=assigned_by,
        )

        return scanner, token