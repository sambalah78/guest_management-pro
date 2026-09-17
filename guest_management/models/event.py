# guest_management/models/event.py
"""Event domain model.

The legacy ``logo`` and ``wedding_invitation`` fields are intentionally
retained for backward compatibility.

New event assets are stored in Supabase Storage, with metadata tracked
through the corresponding ``*_storage_path``, ``*_filename``, and
``*_mime_type`` fields.

The migration from legacy asset data to Supabase Storage is handled in
the create-event / asset-service layer and is NOT performed here.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class EventType(str, Enum):
    """Supported EventLah event types."""

    COMPANY_DINNER = "company_dinner"
    WEDDING_DINNER = "wedding_dinner"
    SPORTS_DAY = "sports_day"
    LUCKY_DRAW = "lucky_draw"

@dataclass(slots=True)
class Event:
    """Event data model.

    Legacy image fields remain available so existing events continue
    working while the application migrates image storage to Supabase Storage.
    """

    id: int
    name: str

    event_type: EventType = EventType.COMPANY_DINNER

    company_name: str = ""

    date: str = ""
    time: str = ""
    venue: str = ""
    theme: str = ""

    guest_count: int = 0
    present_count: int = 0

    user_id: str = ""

    # ------------------------------------------------------------------
    # LEGACY ASSET FIELDS
    # ------------------------------------------------------------------
    #
    # Existing events may contain base64/data-URL image content here.
    # DO NOT remove these fields yet.
    #

    logo: str = ""
    wedding_invitation: str = ""

    # ------------------------------------------------------------------
    # ASSET STORAGE
    # ------------------------------------------------------------------








    created_at: Optional[datetime] = None

    # ------------------------------------------------------------------
    # SUPABASE STORAGE ASSETS
    # ------------------------------------------------------------------

    logo_storage_path: str = ""
    logo_filename: str = ""
    logo_mime_type: str = ""

    invitation_storage_path: str = ""
    invitation_filename: str = ""
    invitation_mime_type: str = ""

    guest_list_storage_path: str = ""
    guest_list_filename: str = ""
    guest_list_mime_type: str = ""
    guest_list_uploaded_at: Optional[datetime] = None
    # ==================================================================
    # FACTORY
    # ==================================================================

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Event":
        """Create an Event instance from a database/repository dictionary."""

        raw_event_type = (
            data.get("event_type")
            or EventType.COMPANY_DINNER.value
        )

        try:
            event_type = EventType(raw_event_type)
        except (ValueError, TypeError):
            event_type = EventType.COMPANY_DINNER

        # --------------------------------------------------------------
        # Created timestamp
        # --------------------------------------------------------------

        created_at = data.get("created_at")

        if isinstance(created_at, str):
            try:
                created_at = datetime.fromisoformat(
                    created_at.replace("Z", "+00:00")
                )
            except ValueError:
                created_at = None

        # --------------------------------------------------------------
        # Guest-list uploaded timestamp
        # --------------------------------------------------------------

        guest_list_uploaded_at = data.get(
            "guest_list_uploaded_at"
        )

        if isinstance(guest_list_uploaded_at, str):
            try:
                guest_list_uploaded_at = datetime.fromisoformat(
                    guest_list_uploaded_at.replace("Z", "+00:00")
                )
            except ValueError:
                guest_list_uploaded_at = None

        return cls(
            id=int(
                data.get("id", 0) or 0
            ),

            name=str(
                data.get("name")
                or ""
            ),

            event_type=event_type,

            company_name=str(
                data.get("company_name")
                or ""
            ),

            date=str(
                data.get("date")
                or ""
            ),

            time=str(
                data.get("time")
                or ""
            ),

            venue=str(
                data.get("venue")
                or ""
            ),

            theme=str(
                data.get("theme")
                or ""
            ),

            guest_count=int(
                data.get("guest_count", 0)
                or 0
            ),

            present_count=int(
                data.get("present_count", 0)
                or 0
            ),

            user_id=str(
                data.get("user_id")
                or ""
            ),

            # ----------------------------------------------------------
            # Legacy assets
            # ----------------------------------------------------------

            logo=str(
                data.get("logo")
                or ""
            ),

            wedding_invitation=str(
                data.get("wedding_invitation")
                or ""
            ),

            logo_storage_path=str(data.get("logo_storage_path") or ""),
            logo_filename=str(data.get("logo_filename") or ""),
            logo_mime_type=str(data.get("logo_mime_type") or ""),

            invitation_storage_path=str(
                data.get("invitation_storage_path") or ""
            ),
            invitation_filename=str(
                data.get("invitation_filename") or ""
            ),
            invitation_mime_type=str(
                data.get("invitation_mime_type") or ""
            ),

            guest_list_storage_path=str(
                data.get("guest_list_storage_path") or ""
            ),
            guest_list_filename=str(
                data.get("guest_list_filename") or ""
            ),
            guest_list_mime_type=str(
                data.get("guest_list_mime_type") or ""
            ),

            guest_list_uploaded_at=guest_list_uploaded_at,

            created_at=created_at,
        )

    # ==================================================================
    # SUPABASE STORAGE HELPERS
    # ==================================================================

    @property
    def has_storage_logo(self) -> bool:
        """Whether a Supabase Storage logo is configured."""
        return bool(self.logo_storage_path)

    @property
    def has_storage_invitation(self) -> bool:
        """Whether a Supabase Storage invitation is configured."""
        return bool(self.invitation_storage_path)

    @property
    def has_storage_guest_list(self) -> bool:
        """Whether a Supabase Storage guest list is configured."""
        return bool(self.guest_list_storage_path)

    # ==================================================================
    # SERIALIZATION
    # ==================================================================

    def to_dict(self) -> Dict[str, Any]:
        """Convert Event to a repository/database-friendly dictionary."""

        return {
            # Supabase Storage logo.
            "logo_storage_path": self.logo_storage_path,
            "logo_filename": self.logo_filename,
            "logo_mime_type": self.logo_mime_type,

            # Supabase Storage invitation.
            "invitation_storage_path": self.invitation_storage_path,
            "invitation_filename": self.invitation_filename,
            "invitation_mime_type": self.invitation_mime_type,

            # Supabase Storage guest list.
            "guest_list_storage_path": self.guest_list_storage_path,
            "guest_list_filename": self.guest_list_filename,
            "guest_list_mime_type": self.guest_list_mime_type,
            "guest_list_uploaded_at": self.guest_list_uploaded_at,
            "id": self.id,
            "name": self.name,
            "event_type": self.event_type.value,
            "company_name": self.company_name,
            "date": self.date,
            "time": self.time,
            "venue": self.venue,
            "theme": self.theme,
            "guest_count": self.guest_count,
            "present_count": self.present_count,
            "user_id": self.user_id,

            # Legacy asset fields.
            "logo": self.logo,
            "wedding_invitation": self.wedding_invitation,




            "created_at": self.created_at,
        }


    # ==================================================================
    # LEGACY ASSET HELPERS
    # ==================================================================

    @property
    def has_legacy_logo(self) -> bool:
        """Whether the legacy logo field contains an asset."""
        return bool(
            self.logo
        )

    @property
    def has_legacy_invitation(self) -> bool:
        """Whether the legacy invitation field contains an asset."""
        return bool(
            self.wedding_invitation
        )

    # ==================================================================
    # GENERAL ASSET HELPERS
    # ==================================================================

    @property
    def has_logo(self) -> bool:
        """Whether any logo asset is available."""
        return self.has_storage_logo or self.has_legacy_logo

    @property
    def has_invitation(self) -> bool:
        """Whether any invitation asset is available."""
        return (
                self.has_storage_invitation
                or self.has_legacy_invitation
        )
    # ==================================================================
    # FORMATTING
    # ==================================================================

    @property
    def formatted_date(self) -> str:
        """Return the event date using the application's formatter."""

        if not self.date:
            return ""

        try:
            from guest_management.utils.formatting import (
                format_date,
            )

            return format_date(self.date)

        except Exception:
            return self.date

    @property
    def formatted_time(self) -> str:
        """Return the event time.

        Event time is currently stored as the event's local clock time,
        so no timezone conversion is performed here.
        """

        return self.time or ""