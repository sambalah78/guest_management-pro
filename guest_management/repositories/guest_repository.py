"""Guest repository.

All guest queries are event-scoped and return only the columns required by the
calling use-case. The check-in path is delegated to a PostgreSQL RPC so that
concurrent scanners share one source of truth.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

from .base import BaseRepository


logger = logging.getLogger(__name__)

GUEST_LIST_COLUMNS = (
    "id,event_id,guest_id,name,email,status,table_number,amount,team_name,"
    "email_sent,created_at,updated_at"
)
GUEST_RESULT_COLUMNS = "id,event_id,guest_id,name,email,status,table_number,amount,team_name,email_sent,updated_at"


class GuestRepository(BaseRepository):
    def get_by_event(self, event_id: int, limit: int = 50, offset: int = 0) -> Tuple[List[Dict[str, Any]], int]:
        if limit < 1 or limit > 200:
            raise ValueError("limit must be between 1 and 200")
        if offset < 0:
            raise ValueError("offset cannot be negative")
        try:
            query = (
                self.db.table("guests")
                .select(GUEST_LIST_COLUMNS, count="exact")
                .eq("event_id", int(event_id))
                .order("id")
                .range(offset, offset + limit - 1)
            )
            response = query.execute()
            return response.data or [], int(response.count or 0)
        except Exception as exc:
            self._raise_db("list guests", exc)

    def get_by_guest_id(self, guest_id: str, event_id: int) -> Optional[Dict[str, Any]]:
        try:
            response = (
                self.db.table("guests")
                .select(GUEST_RESULT_COLUMNS)
                .eq("guest_id", guest_id.strip())
                .eq("event_id", int(event_id))
                .limit(1)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as exc:
            self._raise_db("get guest", exc)

    def get_by_guest_id_case_insensitive(self, guest_id: str, event_id: int) -> Optional[Dict[str, Any]]:
        try:
            response = (
                self.db.table("guests")
                .select(GUEST_RESULT_COLUMNS)
                .eq("event_id", int(event_id))
                .ilike("guest_id", guest_id.strip())
                .limit(1)
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as exc:
            self._raise_db("case-insensitive guest lookup", exc)


    def search(self, event_id: int, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        query = query.strip()
        if not query:
            return []
        safe_query = "".join(ch for ch in query if ch.isalnum() or ch in "@._- ")[:64]
        if not safe_query:
            return []
        try:
            response = (
                self.db.table("guests")
                .select(GUEST_RESULT_COLUMNS)
                .eq("event_id", int(event_id))
                .or_(f"guest_id.ilike.*{safe_query}*,name.ilike.*{safe_query}*,email.ilike.*{safe_query}*")
                .order("name")
                .limit(min(max(limit, 1), 50))
                .execute()
            )
            return response.data or []
        except Exception as exc:
            self._raise_db("search guests", exc)

    def create_batch(self, guests: List[Dict[str, Any]], batch_size: int = 500) -> int:
        if not guests:
            return 0
        if batch_size < 1 or batch_size > 500:
            raise ValueError("batch_size must be between 1 and 500")
        created = 0
        try:
            for start in range(0, len(guests), batch_size):
                batch = guests[start:start + batch_size]
                response = self.db.table("guests").insert(batch).execute()
                created += len(response.data or [])
            return created
        except Exception as exc:
            self._raise_db("bulk guest insert", exc)

    def upsert_batch(self, guests: List[Dict[str, Any]], batch_size: int = 500) -> int:
        if not guests:
            return 0
        try:
            created = 0
            for start in range(0, len(guests), batch_size):
                response = (
                    self.db.table("guests")
                    .upsert(guests[start:start + batch_size], on_conflict="event_id,guest_id", ignore_duplicates=True)
                    .execute()
                )
                created += len(response.data or [])
            return created
        except Exception as exc:
            self._raise_db("bulk guest upsert", exc)

    def update(self, guest_id: str, event_id: int, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        try:
            response = (
                self.db.table("guests")
                .update({**updates, "updated_at": datetime.now(timezone.utc).isoformat()})
                .eq("guest_id", guest_id.strip())
                .eq("event_id", int(event_id))
                .execute()
            )
            return response.data[0] if response.data else None
        except Exception as exc:
            self._raise_db("update guest", exc)

    def update_email_sent(self, guest_id: str, event_id: int) -> bool:
        return bool(self.update(guest_id, event_id, {"email_sent": True}))

    def delete_by_event(self, event_id: int) -> int:
        try:
            response = self.db.table("guests").delete().eq("event_id", int(event_id)).execute()
            return len(response.data or [])
        except Exception as exc:
            self._raise_db("delete guests for event", exc)

    def count_by_event(self, event_id: int) -> int:
        try:
            response = (
                self.db.table("guests")
                .select("id", count="exact", head=True)
                .eq("event_id", int(event_id))
                .execute()
            )
            return int(response.count or 0)
        except Exception as exc:
            self._raise_db("count guests", exc)

    def count_present(self, event_id: int) -> int:
        try:
            response = (
                self.db.table("guests")
                .select("id", count="exact", head=True)
                .eq("event_id", int(event_id))
                .eq("status", "Present")
                .execute()
            )
            return int(response.count or 0)
        except Exception as exc:
            self._raise_db("count present guests", exc)

    def get_present_guests(self, event_id: int) -> List[Dict[str, Any]]:
        """Compatibility method; prefer count_present for dashboard statistics."""
        try:
            response = (
                self.db.table("guests")
                .select("id,guest_id,name,email,status,table_number,team_name,amount,event_id,updated_at")
                .eq("event_id", int(event_id))
                .eq("status", "Present")
                .order("updated_at", desc=True)
                .execute()
            )
            return response.data or []
        except Exception as exc:
            self._raise_db("list present guests", exc)

    def get_recent_checkins(self, event_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        try:
            response = (
                self.db.table("guests")
                .select("id,name,table_number,team_name,status,updated_at")
                .eq("event_id", int(event_id))
                .eq("status", "Present")
                .order("updated_at", desc=True)
                .limit(min(max(limit, 1), 50))
                .execute()
            )
            return response.data or []
        except Exception as exc:
            self._raise_db("recent check-ins", exc)

    def get_existing_ids(self, event_id: int) -> set[str]:
        try:
            response = self.db.table("guests").select("guest_id").eq("event_id", int(event_id)).execute()
            return {str(row["guest_id"]) for row in (response.data or []) if row.get("guest_id") is not None}
        except Exception as exc:
            self._raise_db("existing guest ids", exc)
