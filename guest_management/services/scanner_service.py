"""Scanner station business service."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from ..repositories.scanner_repository import ScannerRepository


class ScannerService:
    """Business operations for scanner stations."""

    def __init__(self, repo: Optional[ScannerRepository] = None):
        self.repo = repo or ScannerRepository()

    def get_scanners(self, event_id: int) -> List[Dict[str, Any]]:
        return self.repo.get_by_event(int(event_id))

    def get_scanner(
        self,
        event_id: int,
        device_id: str,
    ) -> Optional[Dict[str, Any]]:
        return self.repo.get_by_device(
            int(event_id),
            str(device_id).strip(),
        )



    def activate_scanner(
        self,
        event_id: int,
        device_id: str,
    ) -> Optional[Dict[str, Any]]:
        return self.repo.set_active(
            event_id=int(event_id),
            device_id=device_id,
            is_active=True,
        )

    def deactivate_scanner(
        self,
        event_id: int,
        device_id: str,
    ) -> Optional[Dict[str, Any]]:
        return self.repo.set_active(
            event_id=int(event_id),
            device_id=device_id,
            is_active=False,
        )

    def delete_scanner(
        self,
        event_id: int,
        device_id: str,
    ) -> bool:
        return self.repo.delete(
            event_id=int(event_id),
            device_id=device_id,
        )

    def record_scan(
        self,
        event_id: int,
        device_id: str,
    ) -> None:
        self.repo.increment_scans(
            event_id=int(event_id),
            device_id=device_id,
        )