"""Pre-draw winner domain model."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Optional


@dataclass(slots=True)
class PreDrawWinner:
    """A winner selected before the live event Lucky Draw."""

    id: Optional[int]
    event_id: int
    guest_id: str
    name: str
    prize_name: str = ""
    prize_value: str = ""
    image_url: str = ""
    created_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PreDrawWinner":
        return cls(
            id=data.get("id"),
            event_id=int(data["event_id"]),
            guest_id=str(data.get("guest_id") or "").strip(),
            name=str(data.get("name") or "").strip(),
            prize_name=str(data.get("prize_name") or "").strip(),
            prize_value=str(data.get("prize_value") or "").strip(),
            image_url=str(data.get("image_url") or "").strip(),
            created_at=data.get("created_at"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_id": self.event_id,
            "guest_id": self.guest_id,
            "name": self.name,
            "prize_name": self.prize_name,
            "prize_value": self.prize_value,
            "image_url": self.image_url,
            "created_at": self.created_at,
        }