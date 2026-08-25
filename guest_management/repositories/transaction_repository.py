# guest_management/repositories/transaction_repository.py
"""Transaction repository."""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from .base import BaseRepository

logger = logging.getLogger(__name__)


class TransactionRepository(BaseRepository):
    """Repository for transaction operations."""

    def create(self, transaction_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Create a transaction."""
        try:
            if "created_at" not in transaction_data:
                transaction_data["created_at"] = datetime.now().isoformat()
            response = self.db.table("transactions").insert(transaction_data).execute()
            return response.data[0] if response.data else None
        except Exception as e:
            logger.error(f"Create transaction failed: {e}")
            return None

    def create_batch(self, transactions: List[Dict[str, Any]]) -> int:
        """Create multiple transactions."""
        created = 0
        try:
            for t in transactions:
                if "created_at" not in t:
                    t["created_at"] = datetime.now().isoformat()
            response = self.db.table("transactions").insert(transactions).execute()
            created = len(response.data or [])
        except Exception as e:
            logger.error(f"Batch create transactions failed: {e}")
        return created

    def get_by_guest(self, guest_id: str, event_id: int, limit: int = 50) -> List[Dict[str, Any]]:
        """Get transactions for a guest."""
        try:
            response = self.db.table("transactions").select("*").eq("guest_id", guest_id).eq("event_id",
                                                                                             event_id).order(
                "created_at", desc=True).limit(limit).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Get transactions for guest {guest_id} failed: {e}")
            return []

    def get_by_event(self, event_id: int) -> List[Dict[str, Any]]:
        """Get all transactions for an event."""
        try:
            response = self.db.table("transactions").select("*").eq("event_id", event_id).order("created_at",
                                                                                                desc=True).execute()
            return response.data or []
        except Exception as e:
            logger.error(f"Get transactions for event {event_id} failed: {e}")
            return []

    def get_total_spent(self, guest_id: str, event_id: int) -> float:
        """Get total spent by a guest."""
        try:
            response = self.db.table("transactions").select("amount").eq("guest_id", guest_id).eq("event_id",
                                                                                                  event_id).execute()
            return sum(t.get("amount", 0) for t in (response.data or []))
        except Exception as e:
            logger.error(f"Get total spent for guest {guest_id} failed: {e}")
            return 0.0