# guest_management/models/scanner.py
"""Scanner device model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass(slots=True)
class ScannerDevice:
    """Scanner device data model."""
    id: int
    event_id: int
    device_name: str
    device_id: str
    scanner_number: int
    total_scans: int = 0
    last_used: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    # In-memory state (not persisted)
    is_active: bool = False
    scan_buffer: str = ""
    status: str = "idle"  # idle, ready, processing, error

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScannerDevice":
        """Create ScannerDevice from dictionary."""
        return cls(
            id=int(data.get("id", 0)),
            event_id=int(data.get("event_id", 0)),
            device_name=data.get("device_name", ""),
            device_id=data.get("device_id", ""),
            scanner_number=int(data.get("scanner_number", 0)),
            total_scans=int(data.get("total_scans", 0)),
            last_used=data.get("last_used"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert ScannerDevice to dictionary."""
        return {
            "id": self.id,
            "event_id": self.event_id,
            "device_name": self.device_name,
            "device_id": self.device_id,
            "scanner_number": self.scanner_number,
            "total_scans": self.total_scans,
            "last_used": self.last_used,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_display_dict(self) -> Dict[str, Any]:
        """Convert to display dictionary for UI."""
        return {
            "id": self.id,
            "device_name": self.device_name,
            "device_id": self.device_id,
            "scanner_number": self.scanner_number,
            "total_scans": self.total_scans,
            "is_active": self.is_active,
            "status": self.status,
        }

    def activate(self) -> None:
        """Activate the scanner."""
        self.is_active = True
        self.status = "ready"
        self.scan_buffer = ""

    def deactivate(self) -> None:
        """Deactivate the scanner."""
        self.is_active = False
        self.status = "idle"
        self.scan_buffer = ""

    def record_scan(self) -> None:
        """Record a scan event."""
        self.total_scans += 1
        self.last_used = datetime.now()

    def set_processing(self) -> None:
        """Set scanner to processing state."""
        self.status = "processing"

    def set_error(self) -> None:
        """Set scanner to error state."""
        self.status = "error"

    def reset(self) -> None:
        """Reset scanner to idle state."""
        self.status = "idle" if not self.is_active else "ready"
        self.scan_buffer = ""

    @property
    def is_processing(self) -> bool:
        """Check if scanner is processing."""
        return self.status == "processing"

    @property
    def is_ready(self) -> bool:
        """Check if scanner is ready."""
        return self.status == "ready"

    @property
    def is_idle(self) -> bool:
        """Check if scanner is idle."""
        return self.status == "idle"

    @property
    def is_error(self) -> bool:
        """Check if scanner is in error state."""
        return self.status == "error"