"""Repository for pre-draw prize persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import BaseRepository


PRE_DRAW_PRIZE_COLUMNS = (
    "id,"
    "event_id,"
    "name,"
    "value,"
    "image_url,"
    "winner_count,"
    "sort_order,"
    "status,"
    "created_at,"
    "updated_at"
)


class PreDrawPrizeRepository(BaseRepository):
    """Persistence operations for event pre-draw prizes."""

    MAX_LIMIT = 500

    @staticmethod
    def _normalize_event_id(event_id: int) -> int:
        """Normalize and validate an event identifier."""
        value = int(event_id)

        if value <= 0:
            raise ValueError("event_id must be greater than zero")

        return value

    @staticmethod
    def _normalize_prize_id(prize_id: int) -> int:
        """Normalize and validate a prize identifier."""
        value = int(prize_id)

        if value <= 0:
            raise ValueError("prize_id must be greater than zero")

        return value

    @staticmethod
    def _normalize_name(name: str) -> str:
        """Normalize a prize name."""
        value = str(name or "").strip()

        if not value:
            raise ValueError("Pre-draw prize name is required")

        return value

    @staticmethod
    def _normalize_winner_count(winner_count: int) -> int:
        """Normalize and validate the number of winners."""
        value = int(winner_count)

        if value <= 0:
            raise ValueError("winner_count must be greater than zero")

        return value

    @staticmethod
    def _normalize_sort_order(sort_order: int) -> int:
        """Normalize and validate prize ordering."""
        value = int(sort_order)

        if value < 0:
            raise ValueError("sort_order cannot be negative")

        return value

    @staticmethod
    def _normalize_status(status: str) -> str:
        """Normalize prize status."""
        value = str(status or "draft").strip().lower()

        allowed = {
            "draft",
            "ready",
            "generated",
            "archived",
        }

        if value not in allowed:
            raise ValueError(
                f"Invalid pre-draw prize status: {value}"
            )

        return value

    def get_by_event(
        self,
        event_id: int,
        *,
        include_archived: bool = False,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """
        Return pre-draw prizes for an event.

        Prizes are returned in configured display order.
        Archived prizes are excluded by default.
        """
        event_id = self._normalize_event_id(event_id)

        limit = max(
            1,
            min(int(limit), self.MAX_LIMIT),
        )

        query = (
            self.db
            .table("pre_draw_prizes")
            .select(PRE_DRAW_PRIZE_COLUMNS)
            .eq("event_id", event_id)
        )

        if not include_archived:
            query = query.neq("status", "archived")

        return (
            query
            .order("sort_order", desc=False)
            .order("id", desc=False)
            .limit(limit)
            .execute()
            .data
            or []
        )

    def get_by_id(
        self,
        event_id: int,
        prize_id: int,
    ) -> Optional[Dict[str, Any]]:
        """
        Return one prize scoped to an event.

        Event scoping is intentional: a prize belonging to another
        event must never be returned accidentally.
        """
        event_id = self._normalize_event_id(event_id)
        prize_id = self._normalize_prize_id(prize_id)

        rows = (
            self.db
            .table("pre_draw_prizes")
            .select(PRE_DRAW_PRIZE_COLUMNS)
            .eq("event_id", event_id)
            .eq("id", prize_id)
            .limit(1)
            .execute()
            .data
            or []
        )

        return rows[0] if rows else None

    def create(
        self,
        event_id: int,
        name: str,
        value: str = "",
        image_url: str = "",
        winner_count: int = 1,
        sort_order: int = 0,
        status: str = "draft",
    ) -> Dict[str, Any]:
        """Create a pre-draw prize."""
        event_id = self._normalize_event_id(event_id)
        name = self._normalize_name(name)
        winner_count = self._normalize_winner_count(winner_count)
        sort_order = self._normalize_sort_order(sort_order)
        status = self._normalize_status(status)

        now = datetime.now(timezone.utc)

        result = (
            self.db
            .table("pre_draw_prizes")
            .insert(
                {
                    "event_id": event_id,
                    "name": name,
                    "value": str(value or "").strip(),
                    "image_url": str(image_url or "").strip(),
                    "winner_count": winner_count,
                    "sort_order": sort_order,
                    "status": status,
                    "created_at": now,
                    "updated_at": now,
                }
            )
            .execute()
        )

        data = result.data or []

        if not data:
            raise RuntimeError(
                "Failed to create pre-draw prize."
            )

        return data[0]

    def update(
        self,
        event_id: int,
        prize_id: int,
        updates: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """
        Update an event-scoped pre-draw prize.

        Only known mutable fields are accepted.
        """
        event_id = self._normalize_event_id(event_id)
        prize_id = self._normalize_prize_id(prize_id)

        allowed_fields = {
            "name",
            "value",
            "image_url",
            "winner_count",
            "sort_order",
            "status",
        }

        payload = {
            key: value
            for key, value in dict(updates).items()
            if key in allowed_fields
        }

        if not payload:
            return self.get_by_id(
                event_id,
                prize_id,
            )

        if "name" in payload:
            payload["name"] = self._normalize_name(
                payload["name"]
            )

        if "winner_count" in payload:
            payload["winner_count"] = (
                self._normalize_winner_count(
                    payload["winner_count"]
                )
            )

        if "sort_order" in payload:
            payload["sort_order"] = (
                self._normalize_sort_order(
                    payload["sort_order"]
                )
            )

        if "status" in payload:
            payload["status"] = self._normalize_status(
                payload["status"]
            )

        if "value" in payload:
            payload["value"] = str(
                payload["value"] or ""
            ).strip()

        if "image_url" in payload:
            payload["image_url"] = str(
                payload["image_url"] or ""
            ).strip()

        payload["updated_at"] = datetime.now(timezone.utc)

        result = (
            self.db
            .table("pre_draw_prizes")
            .update(payload)
            .eq("event_id", event_id)
            .eq("id", prize_id)
            .execute()
        )

        data = result.data or []

        return data[0] if data else None

    def archive(
        self,
        event_id: int,
        prize_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Archive a prize without deleting its history."""
        return self.update(
            event_id,
            prize_id,
            {"status": "archived"},
        )

    def delete(
        self,
        event_id: int,
        prize_id: int,
    ) -> bool:
        """
        Delete an event-scoped prize.

        This is retained for draft cleanup. Generated prize history
        should normally be archived rather than deleted.
        """
        event_id = self._normalize_event_id(event_id)
        prize_id = self._normalize_prize_id(prize_id)

        existing = self.get_by_id(
            event_id,
            prize_id,
        )

        if existing is None:
            return False

        (
            self.db
            .table("pre_draw_prizes")
            .delete()
            .eq("event_id", event_id)
            .eq("id", prize_id)
            .execute()
        )

        return True