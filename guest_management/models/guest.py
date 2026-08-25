# guest_management/models/guest.py
"""Guest model."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class GuestStatus(str, Enum):
    """Guest status enum."""
    ABSENT = "Absent"
    PRESENT = "Present"


@dataclass(slots=True)
class Guest:
    """Guest data model."""
    guest_id: str
    name: str
    email: str = ""
    status: GuestStatus = GuestStatus.ABSENT
    table_number: str = "TBD"
    amount: float = 0.0
    team_name: str = ""
    qr_code: str = ""
    qr_url: str = ""
    email_sent: bool = False
    event_id: int = 0
    full_data: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Guest":
        """Create Guest from dictionary."""
        return cls(
            guest_id=data.get("guest_id", ""),
            name=data.get("name") or data.get("Name", ""),
            email=data.get("email") or data.get("Email", ""),
            status=GuestStatus(data.get("status", "Absent")),
            table_number=data.get("table_number") or data.get("Table", "TBD"),
            amount=float(data.get("amount", 0)),
            team_name=data.get("team_name") or data.get("Team", ""),
            qr_code=data.get("qr_code", ""),
            qr_url=data.get("qr_url", "") or data.get("qr_code", ""),
            email_sent=data.get("email_sent", False),
            event_id=int(data.get("event_id", 0)),
            full_data=data.get("full_data", {}),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Convert Guest to dictionary."""
        return {
            "guest_id": self.guest_id,
            "name": self.name,
            "email": self.email,
            "status": self.status.value,
            "table_number": self.table_number,
            "amount": self.amount,
            "team_name": self.team_name,
            "qr_code": self.qr_code,
            "qr_url": self.qr_url,
            "email_sent": self.email_sent,
            "event_id": self.event_id,
            "full_data": self.full_data,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }

    def to_display_dict(self) -> Dict[str, Any]:
        """Convert Guest to display dictionary for UI."""
        return {
            "Name": self.name,
            "Email": self.email,
            "ID": self.guest_id,
            "Table": self.table_number,
            "Status": self.status.value,
            "Email Sent": "✅" if self.email_sent else "❌",
            "email_sent": self.email_sent,
            "guest_id": self.guest_id,
            "Amount": f"RM {self.amount:.2f}" if self.amount > 0 else "RM 0.00",
            "amount_value": self.amount,
            "Team": self.team_name,
        }

    @property
    def is_present(self) -> bool:
        """Check if guest is present."""
        return self.status == GuestStatus.PRESENT

    def mark_present(self) -> None:
        """Mark guest as present."""
        self.status = GuestStatus.PRESENT

    def mark_absent(self) -> None:
        """Mark guest as absent."""
        self.status = GuestStatus.ABSENT