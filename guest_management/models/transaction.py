# guest_management/models/transaction.py
"""Transaction model."""

from dataclasses import dataclass
from datetime import datetime
from typing import Optional, Dict, Any


@dataclass(slots=True)
class Transaction:
    """Transaction data model."""
    id: int
    guest_id: str
    event_id: int
    stall_id: int
    item_name: str
    amount: float
    balance_after: float
    created_at: Optional[datetime] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Transaction":
        return cls(
            id=int(data.get("id", 0)),
            guest_id=data.get("guest_id", ""),
            event_id=int(data.get("event_id", 0)),
            stall_id=int(data.get("stall_id", 0)),
            item_name=data.get("item_name", ""),
            amount=float(data.get("amount", 0)),
            balance_after=float(data.get("balance_after", 0)),
            created_at=data.get("created_at"),
        )

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "guest_id": self.guest_id,
            "event_id": self.event_id,
            "stall_id": self.stall_id,
            "item_name": self.item_name,
            "amount": self.amount,
            "balance_after": self.balance_after,
            "created_at": self.created_at,
        }