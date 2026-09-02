"""Winner persistence repository.

All database access for Lucky Draw winners belongs here.

The repository intentionally contains no Lucky Draw business logic.
It is responsible only for reading, creating, counting, and deleting
winner records.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from guest_management.database_client import get_db

logger = logging.getLogger(__name__)


class WinnerRepository:
    """Repository for Lucky Draw winner records."""

    def __init__(self, db=None):
        self.db = db or get_db()

    # ================================================================
    # READ
    # ================================================================

    def get_by_event(
        self,
        event_id: int,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """Return winners for an event, newest first."""

        event_id = int(event_id)

        limit = min(max(int(limit), 1), 5000)

        try:
            response = (
                self.db
                .table("winners")
                .select("*")
                .eq("event_id", event_id)
                .order("created_at", desc=True)
                .limit(limit)
                .execute()
            )

            winners = response.data or []

            for winner in winners:
                created_at = winner.get("created_at")

                if created_at:
                    winner["formatted_date"] = str(
                        created_at
                    ).split("T")[0]

            return winners

        except Exception:
            logger.exception(
                "Failed to load winners for event %s",
                event_id,
            )
            raise

    def get_by_guest(
        self,
        event_id: int,
        guest_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Return the winner record for a guest in an event."""

        event_id = int(event_id)
        guest_id = str(guest_id or "").strip()

        if not guest_id:
            return None

        try:
            response = (
                self.db
                .table("winners")
                .select("*")
                .eq("event_id", event_id)
                .eq("guest_id", guest_id)
                .limit(1)
                .execute()
            )

            rows = response.data or []

            return rows[0] if rows else None

        except Exception:
            logger.exception(
                "Failed to find winner "
                "event=%s guest=%s",
                event_id,
                guest_id,
            )
            raise

    def has_won(
        self,
        event_id: int,
        guest_id: str,
    ) -> bool:
        """Return True when the guest has already won in this event."""

        return self.get_by_guest(
            event_id,
            guest_id,
        ) is not None

    def count_by_event(
        self,
        event_id: int,
    ) -> int:
        """Return the number of winners for an event."""

        event_id = int(event_id)

        try:
            response = (
                self.db
                .table("winners")
                .select("id", count="exact")
                .eq("event_id", event_id)
                .execute()
            )

            return int(response.count or 0)

        except Exception:
            logger.exception(
                "Failed to count winners for event %s",
                event_id,
            )
            raise

    # ================================================================
    # CREATE
    # ================================================================

    def create(
        self,
        *,
        event_id: int,
        guest_id: str,
        name: str,
        prize_name: str,
        prize_value: str = "",
        prize_image: str = "",
    ) -> Dict[str, Any]:
        """Create a winner record.

        The database unique constraint on (event_id, guest_id)
        provides the final protection against duplicate winners.
        """

        event_id = int(event_id)
        guest_id = str(guest_id or "").strip()
        name = str(name or "").strip()
        prize_name = str(prize_name or "").strip()
        prize_value = str(prize_value or "").strip()
        prize_image = str(prize_image or "").strip()

        if not guest_id:
            raise ValueError(
                "guest_id is required to create a winner"
            )

        if not name:
            raise ValueError(
                "name is required to create a winner"
            )

        if not prize_name:
            raise ValueError(
                "prize_name is required to create a winner"
            )

        payload = {
            "event_id": event_id,
            "guest_id": guest_id,
            "name": name,
            "prize_name": prize_name,
            "prize_value": prize_value,
            "prize_image": prize_image,
            "created_at": datetime.now(timezone.utc),
        }

        try:
            response = (
                self.db
                .table("winners")
                .insert(payload)
                .execute()
            )

            rows = response.data or []

            if not rows:
                raise RuntimeError(
                    "Winner creation returned no record"
                )

            return rows[0]

        except Exception:
            logger.exception(
                "Failed to create winner "
                "event=%s guest=%s prize=%s",
                event_id,
                guest_id,
                prize_name,
            )
            raise

    # ================================================================
    # DELETE
    # ================================================================

    def delete_by_event(
        self,
        event_id: int,
    ) -> int:
        """Delete all winner records belonging to an event."""

        event_id = int(event_id)

        try:
            response = (
                self.db
                .table("winners")
                .delete()
                .eq("event_id", event_id)
                .execute()
            )

            return len(response.data or [])

        except Exception:
            logger.exception(
                "Failed to delete winners "
                "for event %s",
                event_id,
            )
            raise