"""Repository for pre-draw winner persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from .base import BaseRepository


PRE_DRAW_WINNER_COLUMNS = (
    "id,"
    "event_id,"
    "guest_id,"
    "name,"
    "prize_name,"
    "prize_value,"
    "image_url,"
    "created_at"
)


class PreDrawWinnerRepository(BaseRepository):
    """Persistence operations for preliminary winners."""

    def get_by_event(
        self,
        event_id: int,
        limit: int = 5000,
    ) -> List[Dict[str, Any]]:
        """Return all pre-draw winners for an event."""

        return (
            self.db
            .table("pre_draw_winners")
            .select(PRE_DRAW_WINNER_COLUMNS)
            .eq("event_id", int(event_id))
            .order("created_at", desc=False)
            .limit(limit)
            .execute()
            .data
            or []
        )

    def get_guest_ids_by_event(
        self,
        event_id: int,
    ) -> List[str]:
        """Return guest IDs that already won a preliminary prize."""

        rows = (
            self.db
            .table("pre_draw_winners")
            .select("guest_id")
            .eq("event_id", int(event_id))
            .execute()
            .data
            or []
        )

        return [
            str(row.get("guest_id") or "").strip()
            for row in rows
            if str(row.get("guest_id") or "").strip()
        ]

    def get_by_guest(
        self,
        event_id: int,
        guest_id: str,
    ) -> Dict[str, Any] | None:
        """Return a preliminary winner by event and guest ID."""

        rows = (
            self.db
            .table("pre_draw_winners")
            .select(PRE_DRAW_WINNER_COLUMNS)
            .eq("event_id", int(event_id))
            .eq("guest_id", str(guest_id).strip())
            .limit(1)
            .execute()
            .data
            or []
        )

        return rows[0] if rows else None

    def create(
        self,
        event_id: int,
        guest_id: str,
        name: str,
        prize_name: str = "",
        prize_value: str = "",
        image_url: str = "",
    ) -> Dict[str, Any]:
        """Create one preliminary winner."""

        now = datetime.now(timezone.utc)

        result = (
            self.db
            .table("pre_draw_winners")
            .insert(
                {
                    "event_id": int(event_id),
                    "guest_id": str(guest_id).strip(),
                    "name": str(name).strip(),
                    "prize_name": str(prize_name or "").strip(),
                    "prize_value": str(prize_value or "").strip(),
                    "image_url": str(image_url or "").strip(),
                    "created_at": now,
                }
            )
            .execute()
        )

        data = result.data or []

        if not data:
            raise RuntimeError("Failed to create pre-draw winner.")

        return data[0]

    def delete_by_event(
        self,
        event_id: int,
    ) -> bool:
        """Delete all preliminary winners for an event."""

        self.db.table("pre_draw_winners").delete().eq(
            "event_id",
            int(event_id),
        ).execute()

        return True

    def replace_for_event(
        self,
        event_id: int,
        winners: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Replace the preliminary winner list for an event.

        The existing list is removed before inserting the new validated list.
        """

        event_id = int(event_id)

        self.delete_by_event(event_id)

        if not winners:
            return []

        rows = []

        for winner in winners:
            rows.append(
                {
                    "event_id": event_id,
                    "guest_id": str(
                        winner.get("guest_id") or ""
                    ).strip(),
                    "name": str(
                        winner.get("name") or ""
                    ).strip(),
                    "prize_name": str(
                        winner.get("prize_name") or ""
                    ).strip(),
                    "prize_value": str(
                        winner.get("prize_value") or ""
                    ).strip(),
                    "image_url": str(
                        winner.get("image_url") or ""
                    ).strip(),
                    "created_at": datetime.now(timezone.utc),
                }
            )

        result = (
            self.db
            .table("pre_draw_winners")
            .insert(rows)
            .execute()
        )

        return result.data or []