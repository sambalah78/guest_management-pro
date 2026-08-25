# guest_management/services/scanner_service.py
"""Scanner service."""

import logging
from typing import Optional, Dict, Any, List

from guest_management.repositories import ScannerRepository
from guest_management.core.exceptions import ScannerError

logger = logging.getLogger(__name__)


class ScannerService:
    """Service for scanner operations."""

    def __init__(self):
        self.repo = ScannerRepository()

    def get_scanners(self, event_id: int) -> List[Dict[str, Any]]:
        """Get all scanners for an event."""
        return self.repo.get_by_event(event_id)

    def initialize_scanners(self, event_id: int, count: int = 8) -> List[Dict[str, Any]]:
        """Initialize scanners for an event."""
        return self.repo.create_default_scanners(event_id, count)

    def record_scan(self, device_id: str) -> None:
        """Record a scan event."""
        self.repo.increment_scans(device_id)