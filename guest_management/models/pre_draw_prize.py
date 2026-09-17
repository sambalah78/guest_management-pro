"""Pre-draw prize domain model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


VALID_PRE_DRAW_PRIZE_STATUSES = frozenset(
    {
        "draft",
        "ready",
        "generated",
        "archived",
    }
)


@dataclass(slots=True)
class PreDrawPrize:
    """Configuration for a system-generated pre-draw prize."""

    id: Optional[int]
    event_id: int
    name: str
    value: str = ""
    image_url: str = ""
    winner_count: int = 1
    sort_order: int = 0
    status: str = "draft"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def __post_init__(self) -> None:
        self.name = str(self.name or "").strip()
        self.value = str(self.value or "").strip()
        self.image_url = str(self.image_url or "").strip()
        self.status = str(self.status or "draft").strip().lower()

        if self.event_id <= 0:
            raise ValueError("event_id must be greater than zero")

        if not self.name:
            raise ValueError("Pre-draw prize name is required")

        if self.winner_count <= 0:
            raise ValueError("winner_count must be greater than zero")

        if self.sort_order < 0:
            raise ValueError("sort_order cannot be negative")

        if self.status not in VALID_PRE_DRAW_PRIZE_STATUSES:
            raise ValueError(
                f"Invalid pre-draw prize status: {self.status}"
            )

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PreDrawPrize":
        """Create a prize model from a database/service dictionary."""

        return cls(
            id=data.get("id"),
            event_id=int(data["event_id"]),
            name=str(data.get("name") or ""),
            value=str(data.get("value") or ""),
            image_url=str(data.get("image_url") or ""),
            winner_count=int(data.get("winner_count") or 1),
            sort_order=int(data.get("sort_order") or 0),
            status=str(data.get("status") or "draft"),
            created_at=data.get("created_at"),
            updated_at=data.get("updated_at"),
        )

    def to_dict(self) -> Dict[str, Any]:
        """Return a persistence/service-friendly dictionary."""

        return {
            "id": self.id,
            "event_id": self.event_id,
            "name": self.name,
            "value": self.value,
            "image_url": self.image_url,
            "winner_count": self.winner_count,
            "sort_order": self.sort_order,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }