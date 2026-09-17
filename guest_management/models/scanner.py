# guest_management/models/scanner.py
"""Scanner station data model."""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass(slots=True)
class ScannerDevice:
    """Persistent scanner station assigned to an event."""

    id: int
    event_id: int
    device_name: str
    device_id: str
    is_active: bool = True
    total_scans: int = 0
    last_used: Optional[datetime] = None
    assigned_by: Optional[str] = None
    assigned_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScannerDevice":
        return cls(
            id=int(data.get("id", 0)),
            event_id=int(data.get("event_id", 0)),
            device_name=str(data.get("device_name") or ""),
            device_id=str(data.get("device_id") or ""),
            is_active=bool(data.get("is_active", True)),
            total_scans=int(data.get("total_scans", 0)),
            last_used=data.get("last_used"),
            assigned_by=(
                str(data["assigned_by"])
                if data.get("assigned_by")
                else None
            ),
            assigned_at=data.get("assigned_at"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_id": self.event_id,
            "device_name": self.device_name,
            "device_id": self.device_id,
            "is_active": self.is_active,
            "total_scans": self.total_scans,
            "last_used": self.last_used,
            "assigned_by": self.assigned_by,
            "assigned_at": self.assigned_at,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }