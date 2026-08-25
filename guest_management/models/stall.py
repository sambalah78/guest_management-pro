# guest_management/models/stall.py
"""Stall and Menu Item models."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any


@dataclass(slots=True)
class MenuItem:
    """Menu item data model."""
    id: int
    stall_id: int
    item_name: str
    price: float

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "MenuItem":
        return cls(
            id=int(data.get("id", 0)),
            stall_id=int(data.get("stall_id", 0)),
            item_name=data.get("item_name", ""),
            price=float(data.get("price", 0)),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "stall_id": self.stall_id,
            "item_name": self.item_name,
            "price": self.price,
        }


@dataclass(slots=True)
class Stall:
    """Stall data model."""
    id: int
    event_id: int
    stall_name: str
    qr_code: str = ""
    menu_items: List[MenuItem] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Stall":
        stall = cls(
            id=int(data.get("id", 0)),
            event_id=int(data.get("event_id", 0)),
            stall_name=data.get("stall_name", ""),
            qr_code=data.get("qr_code", ""),
        )
        menu_items = data.get("menu_items", [])
        if menu_items:
            stall.menu_items = [MenuItem.from_dict(item) for item in menu_items]
        return stall

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "event_id": self.event_id,
            "stall_name": self.stall_name,
            "qr_code": self.qr_code,
            "menu_items": [item.to_dict() for item in self.menu_items],
        }