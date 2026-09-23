"""Repository for pre-draw winner persistence."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from sqlalchemy import delete, insert, select

from guest_management.database import events, pre_draw_winners

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
        Atomically replace the preliminary winner list for an event.

        The event row is locked for the duration of the transaction so
        concurrent replacements for the same event are serialized. The
        existing winners are deleted and the replacement rows are inserted
        in the same transaction, ensuring that a failed insert rolls back
        the deletion as well.
        """

        event_id = int(event_id)

        with self.db.engine.begin() as conn:
            # Serialize winner-list replacements for this event.
            event_row = conn.execute(
                select(events.c.id)
                .where(events.c.id == event_id)
                .with_for_update()
            ).first()

            if event_row is None:
                raise ValueError(
                    f"Event {event_id} does not exist."
                )

            # Delete the existing winner list inside the same transaction.
            conn.execute(
                delete(pre_draw_winners).where(
                    pre_draw_winners.c.event_id == event_id
                )
            )

            if not winners:
                return []

            now = datetime.now(timezone.utc)

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
                        "created_at": now,
                    }
                )

            result = conn.execute(
                insert(pre_draw_winners).returning(
                    *pre_draw_winners.c
                ),
                rows,
            )

            return [dict(row) for row in result.mappings().all()]


    def finalize_random_generation(
        self,
        event_id: int,
        winners: List[Dict[str, Any]],
        prize_ids: List[int],
    ) -> List[Dict[str, Any]]:
        """
        Atomically persist a complete random pre-draw result.

        Concurrent generation requests for the same event are serialized by
        locking the event row. Existing preliminary winners are never silently
        replaced.

        Winner insertion and prize-status transition occur in one transaction.
        """
        from collections import Counter
        from datetime import datetime, timezone

        from sqlalchemy import insert, select, update

        from guest_management.database import (
            events,
            pre_draw_prizes,
            pre_draw_winners,
        )

        event_id = int(event_id)

        if event_id <= 0:
            raise ValueError("event_id must be greater than zero.")

        normalized_prize_ids = sorted(
            {
                int(prize_id)
                for prize_id in (prize_ids or [])
            }
        )

        if not normalized_prize_ids:
            raise ValueError("At least one pre-draw prize is required.")

        if not winners:
            raise ValueError("No random pre-draw winners were generated.")

        seen_guest_ids: set[str] = set()
        winner_counts: Counter[int] = Counter()

        for winner in winners:
            guest_id = str(
                winner.get("guest_id") or ""
            ).strip()

            if not guest_id:
                raise ValueError(
                    "Every random pre-draw winner must have a Guest ID."
                )

            normalized_guest_id = guest_id.lower()

            if normalized_guest_id in seen_guest_ids:
                raise ValueError(
                    f"Duplicate random pre-draw winner Guest ID: {guest_id}"
                )

            seen_guest_ids.add(normalized_guest_id)

            try:
                prize_id = int(winner.get("prize_id"))
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "Every random pre-draw winner must reference a prize."
                ) from exc

            winner_counts[prize_id] += 1

        with self.db.engine.begin() as conn:
            event_row = conn.execute(
                select(events.c.id)
                .where(events.c.id == event_id)
                .with_for_update()
            ).first()

            if event_row is None:
                raise ValueError(
                    f"Event {event_id} does not exist."
                )

            existing_winner = conn.execute(
                select(pre_draw_winners.c.id)
                .where(pre_draw_winners.c.event_id == event_id)
                .limit(1)
            ).first()

            if existing_winner is not None:
                raise ValueError(
                    "Pre-draw winners already exist for this event. "
                    "Clear the existing pre-draw winners before generating "
                    "a new random result."
                )

            prize_rows = conn.execute(
                select(
                    pre_draw_prizes.c.id,
                    pre_draw_prizes.c.name,
                    pre_draw_prizes.c.value,
                    pre_draw_prizes.c.image_url,
                    pre_draw_prizes.c.winner_count,
                    pre_draw_prizes.c.sort_order,
                    pre_draw_prizes.c.status,
                )
                .where(
                    pre_draw_prizes.c.event_id == event_id,
                    pre_draw_prizes.c.status != "archived",
                )
                .order_by(
                    pre_draw_prizes.c.sort_order.asc(),
                    pre_draw_prizes.c.id.asc(),
                )
                .with_for_update()
            ).mappings().all()

            if not prize_rows:
                raise ValueError(
                    "No active pre-draw prizes are configured."
                )

            authoritative_prize_ids = sorted(
                int(row["id"])
                for row in prize_rows
            )

            if authoritative_prize_ids != normalized_prize_ids:
                raise ValueError(
                    "The pre-draw prize configuration changed while the "
                    "random draw was being prepared. Please reload and try again."
                )

            if any(
                str(row["status"] or "").strip().lower()
                == "generated"
                for row in prize_rows
            ):
                raise ValueError(
                    "One or more pre-draw prizes have already been generated."
                )

            expected_counts = {
                int(row["id"]): int(row["winner_count"])
                for row in prize_rows
            }

            if dict(winner_counts) != expected_counts:
                raise ValueError(
                    "Generated winner counts no longer match the configured "
                    "pre-draw prize counts."
                )

            now = datetime.now(timezone.utc)

            insert_rows = [
                {
                    "event_id": event_id,
                    "guest_id": str(
                        winner["guest_id"]
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
                    "created_at": now,
                }
                for winner in winners
            ]

            if any(
                not row["name"] or not row["prize_name"]
                for row in insert_rows
            ):
                raise ValueError(
                    "Random pre-draw winners contain an invalid "
                    "name or prize."
                )

            result = conn.execute(
                insert(pre_draw_winners)
                .returning(*pre_draw_winners.c),
                insert_rows,
            )

            persisted = [
                dict(row)
                for row in result.mappings().all()
            ]

            if len(persisted) != len(insert_rows):
                raise RuntimeError(
                    "Random pre-draw winner persistence returned an "
                    "unexpected row count."
                )

            status_result = conn.execute(
                update(pre_draw_prizes)
                .where(
                    pre_draw_prizes.c.event_id == event_id,
                    pre_draw_prizes.c.id.in_(normalized_prize_ids),
                    pre_draw_prizes.c.status != "archived",
                )
                .values(
                    status="generated",
                    updated_at=now,
                )
            )

            if status_result.rowcount != len(prize_rows):
                raise RuntimeError(
                    "Pre-draw prize status update affected an unexpected "
                    "number of rows."
                )

            return persisted
