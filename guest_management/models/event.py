# guest_management/models/event.py
"""Event domain model.

The legacy ``logo`` and ``wedding_invitation`` fields are intentionally
retained for backward compatibility.

New events should eventually use the Google Drive metadata fields:

    event_drive_folder_id

    logo_drive_file_id
    logo_filename
    logo_mime_type

    invitation_drive_file_id
    invitation_filename
    invitation_mime_type

    guest_list_drive_file_id
    guest_list_filename
    guest_list_mime_type
    guest_list_uploaded_at

The actual migration from base64 assets to Google Drive is handled in
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
    working while the application migrates image storage to Google Drive.
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
    # GOOGLE DRIVE EVENT FOLDER
    # ------------------------------------------------------------------
    #
    # Each event can have its own folder under:
    #
    # EventLah Attendance/
    #
    # This stores only the Google Drive folder ID.
    #

    event_drive_folder_id: str = ""

    # ------------------------------------------------------------------
    # GOOGLE DRIVE EVENT LOGO
    # ------------------------------------------------------------------

    logo_drive_file_id: str = ""
    logo_filename: str = ""
    logo_mime_type: str = ""

    # ------------------------------------------------------------------
    # GOOGLE DRIVE INVITATION CARD
    # ------------------------------------------------------------------

    invitation_drive_file_id: str = ""
    invitation_filename: str = ""
    invitation_mime_type: str = ""

    # ------------------------------------------------------------------
    # GOOGLE DRIVE GUEST LIST
    # ------------------------------------------------------------------

    guest_list_drive_file_id: str = ""
    guest_list_filename: str = ""
    guest_list_mime_type: str = ""
    guest_list_uploaded_at: Optional[datetime] = None

    created_at: Optional[datetime] = None

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

            # ----------------------------------------------------------
            # Google Drive event folder
            # ----------------------------------------------------------

            event_drive_folder_id=str(
                data.get("event_drive_folder_id")
                or ""
            ),

            # ----------------------------------------------------------
            # Google Drive logo
            # ----------------------------------------------------------

            logo_drive_file_id=str(
                data.get("logo_drive_file_id")
                or ""
            ),

            logo_filename=str(
                data.get("logo_filename")
                or ""
            ),

            logo_mime_type=str(
                data.get("logo_mime_type")
                or ""
            ),

            # ----------------------------------------------------------
            # Google Drive invitation
            # ----------------------------------------------------------

            invitation_drive_file_id=str(
                data.get("invitation_drive_file_id")
                or ""
            ),

            invitation_filename=str(
                data.get("invitation_filename")
                or ""
            ),

            invitation_mime_type=str(
                data.get("invitation_mime_type")
                or ""
            ),

            # ----------------------------------------------------------
            # Google Drive guest list
            # ----------------------------------------------------------

            guest_list_drive_file_id=str(
                data.get("guest_list_drive_file_id")
                or ""
            ),

            guest_list_filename=str(
                data.get("guest_list_filename")
                or ""
            ),

            guest_list_mime_type=str(
                data.get("guest_list_mime_type")
                or ""
            ),

            guest_list_uploaded_at=guest_list_uploaded_at,

            created_at=created_at,
        )

    # ==================================================================
    # SERIALIZATION
    # ==================================================================

    def to_dict(self) -> Dict[str, Any]:
        """Convert Event to a repository/database-friendly dictionary."""

        return {
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

            # Google Drive event folder.
            "event_drive_folder_id": self.event_drive_folder_id,

            # Google Drive logo.
            "logo_drive_file_id": self.logo_drive_file_id,
            "logo_filename": self.logo_filename,
            "logo_mime_type": self.logo_mime_type,

            # Google Drive invitation.
            "invitation_drive_file_id": (
                self.invitation_drive_file_id
            ),
            "invitation_filename": (
                self.invitation_filename
            ),
            "invitation_mime_type": (
                self.invitation_mime_type
            ),

            # Google Drive guest list.
            "guest_list_drive_file_id": (
                self.guest_list_drive_file_id
            ),
            "guest_list_filename": (
                self.guest_list_filename
            ),
            "guest_list_mime_type": (
                self.guest_list_mime_type
            ),
            "guest_list_uploaded_at": (
                self.guest_list_uploaded_at
            ),

            "created_at": self.created_at,
        }

    # ==================================================================
    # GOOGLE DRIVE HELPERS
    # ==================================================================

    @property
    def has_drive_folder(self) -> bool:
        """Whether a Google Drive event folder is configured."""
        return bool(
            self.event_drive_folder_id
        )

    @property
    def has_drive_logo(self) -> bool:
        """Whether a Google Drive logo is configured."""
        return bool(
            self.logo_drive_file_id
        )

    @property
    def has_drive_invitation(self) -> bool:
        """Whether a Google Drive invitation card is configured."""
        return bool(
            self.invitation_drive_file_id
        )

    @property
    def has_drive_guest_list(self) -> bool:
        """Whether a Google Drive guest list is configured."""
        return bool(
            self.guest_list_drive_file_id
        )

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
        return (
            self.has_drive_logo
            or self.has_legacy_logo
        )

    @property
    def has_invitation(self) -> bool:
        """Whether any invitation asset is available."""
        return (
            self.has_drive_invitation
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