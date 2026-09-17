"""Event repository."""

from __future__ import annotations


from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .base import BaseRepository

class EventRepository(BaseRepository):
    """Repository for event persistence."""

    # ==================================================================
    # READ
    # ==================================================================
    def update_guest_list_asset(
            self,
            event_id: int,
            storage_path: str,
            filename: str,
            mime_type: str,
    ) -> Optional[Dict[str, Any]]:
        """Store Supabase Storage guest-list metadata for an event."""

        if not event_id:
            raise ValueError("event_id is required")

        if not storage_path:
            raise ValueError("storage_path is required")

        try:
            response = (
                self.db
                .table("events")
                .update(
                    {
                        "guest_list_storage_path": storage_path,
                        "guest_list_filename": filename or "",
                        "guest_list_mime_type": mime_type or "",
                        "guest_list_uploaded_at": datetime.now(timezone.utc),
                    }
                )
                .eq("id", int(event_id))
                .select("*")
                .limit(1)
                .execute()
            )

            return response.data[0] if response.data else None

        except Exception as exc:
            self._raise_db(
                "update guest list storage metadata",
                exc,
            )

        return None

    def get_by_user(
        self,
        user_id: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Return events belonging to a user."""

        response = (
            self.db.table("events")
            .select(
                """
                id,
                name,
                event_type,
                company_name,
                date,
                time,
                venue,
                theme,
                guest_count,
                present_count,
                user_id,

                logo,
                wedding_invitation,

                logo_storage_path,
                logo_filename,
                logo_mime_type,
                
                invitation_storage_path,
                invitation_filename,
                invitation_mime_type,
                
                guest_list_storage_path,
                guest_list_filename,
                guest_list_mime_type,
                guest_list_uploaded_at,

                created_at,
                updated_at
                """
            )
            .eq("user_id", user_id)
            .order("created_at", desc=True)
            .limit(
                min(
                    max(int(limit), 1),
                    200,
                )
            )
            .execute()
        )

        return response.data or []

    def get_all(
            self,
            limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Return all events for authorized global administrators."""

        response = (
            self.db.table("events")
            .select("""
                id,
                user_id,
                name,
                venue,
                date,
                time,
                theme,
                company_name,
                logo,
                wedding_invitation,
                logo_storage_path,
                logo_filename,
                logo_mime_type,
                invitation_storage_path,
                invitation_filename,
                invitation_mime_type,
                guest_list_storage_path,
                guest_list_filename,
                guest_list_mime_type,
                guest_list_uploaded_at,
                guest_count,
                present_count,
                created_at,
                updated_at
            """)
            .order("created_at", desc=True)
            .limit(min(max(int(limit), 1), 200))
            .execute()
        )

        return response.data or []

    def get_by_id_any(
            self,
            event_id: int,
    ) -> Dict[str, Any]:
        """Return an event without owner filtering.

        Caller must perform authorization before using this method.
        """
        response = (
            self.db.table("events")
            .select("*")
            .eq("id", int(event_id))
            .limit(1)
            .execute()
        )

        return response.data[0] if response.data else {}

    def get_by_id(
        self,
        event_id: int,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Return one event scoped to the authenticated user."""

        response = (
            self.db.table("events")
            .select("*")
            .eq("id", int(event_id))
            .eq("user_id", user_id)
            .limit(1)
            .execute()
        )

        return (
            response.data[0]
            if response.data
            else None
        )

    def get_by_id_public(
        self,
        event_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Return public event information."""

        response = (
            self.db.table("events")
            .select(
                """
                id,
                name,
                event_type,
                company_name,
                date,
                time,
                venue,
                theme,

                logo_storage_path,
                logo_filename,
                logo_mime_type,
                
                invitation_storage_path,
                invitation_filename,
                invitation_mime_type
                """
            )
            .eq("id", int(event_id))
            .limit(1)
            .execute()
        )

        return (
            response.data[0]
            if response.data
            else None
        )

    def get_owner_user_id(
            self,
            event_id: int,
    ) -> Optional[str]:
        """
        Return the user_id of the owner of an event.

        Internal use only.

        This is intentionally separate from get_by_id_public()
        because user_id is ownership/authentication information
        and should not be included in public event payloads.
        """

        if not event_id:
            raise ValueError("event_id is required")

        response = (
            self.db
            .table("events")
            .select("user_id")
            .eq("id", int(event_id))
            .limit(1)
            .execute()
        )

        if not response.data:
            return None

        user_id = str(
            response.data[0].get("user_id") or ""
        ).strip()

        return user_id or None

    # ==================================================================
    # CREATE
    # ==================================================================

    def create(
        self,
        event_data: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Create an event."""

        data = dict(event_data)

        now = datetime.now(timezone.utc)

        # SQLAlchemy DateTime columns must receive actual
        # datetime objects rather than ISO strings.
        data.setdefault(
            "created_at",
            now,
        )

        data.setdefault(
            "updated_at",
            now,
        )

        # Supabase Storage metadata.
        #
        # These defaults make the repository safe for events
        # created without uploaded assets.

        data.setdefault(
            "logo_storage_path",
            "",
        )

        data.setdefault(
            "logo_filename",
            "",
        )

        data.setdefault(
            "logo_mime_type",
            "",
        )

        data.setdefault(
            "invitation_storage_path",
            "",
        )

        data.setdefault(
            "invitation_filename",
            "",
        )

        data.setdefault(
            "invitation_mime_type",
            "",
        )

        data.setdefault(
            "guest_list_storage_path",
            "",
        )

        data.setdefault(
            "guest_list_filename",
            "",
        )

        data.setdefault(
            "guest_list_mime_type",
            "",
        )

        data.setdefault(
            "guest_list_uploaded_at",
            None,
        )

        response = (
            self.db
            .table("events")
            .insert(data)
            .execute()
        )

        return (
            response.data[0]
            if response.data
            else None
        )

    # ==================================================================
    # UPDATE
    # ==================================================================

    def update(
        self,
        event_id: int,
        updates: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Update an event."""

        data = dict(updates)

        data["updated_at"] = (
            datetime.now(timezone.utc)
        )

        response = (
            self.db
            .table("events")
            .update(data)
            .eq("id", int(event_id))
            .execute()
        )

        return (
            response.data[0]
            if response.data
            else None
        )

    # ==================================================================
    # DELETE
    # ==================================================================

    def delete(
        self,
        event_id: int,
    ) -> bool:
        """Delete an event."""

        response = (
            self.db
            .table("events")
            .delete()
            .eq("id", int(event_id))
            .execute()
        )

        return bool(
            response.data is not None
        )

    # ==================================================================
    # COUNTS
    # ==================================================================

    def update_counts(
        self,
        event_id: int,
        guest_count: Optional[int] = None,
        present_count: Optional[int] = None,
    ) -> bool:
        """Update cached guest/present counts."""

        updates: Dict[str, Any] = {}

        if guest_count is not None:
            updates["guest_count"] = int(
                guest_count
            )

        if present_count is not None:
            updates["present_count"] = int(
                present_count
            )

        if not updates:
            return True

        updates["updated_at"] = (
            datetime.now(timezone.utc)
        )

        response = (
            self.db
            .table("events")
            .update(updates)
            .eq("id", int(event_id))
            .execute()
        )

        return bool(response.data)

