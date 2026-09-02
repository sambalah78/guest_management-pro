"""Event application service."""

from __future__ import annotations

import base64
import mimetypes
import logging

from typing import Any, Dict, List, Optional

from guest_management.core.exceptions import (
    AuthorizationError,
    DatabaseError,
    EventNotFoundError,
)
from guest_management.services.google_drive_asset_service import (
    GoogleDriveAssetService,
)
from guest_management.repositories import (
    EventRepository,
    GuestRepository,
)
logger = logging.getLogger(__name__)

class EventService:
    """Application service for event operations."""

    def __init__(
            self,
            repository: Optional[EventRepository] = None,
            guest_repository: Optional[GuestRepository] = None,
            drive_service: Optional[GoogleDriveAssetService] = None,
    ):
        self.repo = (
                repository
                or EventRepository()
        )

        self.guest_repo = (
                guest_repository
                or GuestRepository()
        )

        # Drive service is injected by callers that have a user context.
        # Do not create GoogleDriveAssetService() here because database
        # OAuth requires the authenticated user's ID.
        self.drive_service = drive_service

    @staticmethod
    def _decode_image_data_url(
        data_url: str,
        default_filename: str,
    ) -> tuple[bytes, str, str]:
        """
        Decode an image data URL into bytes, filename, and MIME type.

        Expected format:

            data:image/png;base64,<base64-data>

        Returns:

            (file_bytes, filename, mime_type)
        """

        if not data_url:
            raise ValueError("Image data is empty")

        if not data_url.startswith("data:"):
            raise ValueError("Invalid image data URL")

        try:
            header, encoded = data_url.split(",", 1)
        except ValueError as exc:
            raise ValueError("Invalid image data URL format") from exc

        if ";base64" not in header:
            raise ValueError("Image data must be base64 encoded")

        mime_type = header[5:].split(";", 1)[0].strip().lower()

        if not mime_type.startswith("image/"):
            raise ValueError(
                f"Unsupported image MIME type: {mime_type}"
            )

        try:
            file_bytes = base64.b64decode(
                encoded,
                validate=True,
            )
        except Exception as exc:
            raise ValueError(
                "Invalid base64 image data"
            ) from exc

        extension = mimetypes.guess_extension(mime_type) or ""

        filename = default_filename

        if extension and not filename.lower().endswith(extension):
            filename += extension

        return file_bytes, filename, mime_type

    # ==================================================================
    # READ
    # ==================================================================

    def get_user_events(
        self,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """Return events owned by the authenticated user."""

        if not user_id:
            raise AuthorizationError(
                "Authenticated user required"
            )

        return self.repo.get_by_user(
            user_id
        )

    def get_event(
        self,
        event_id: int,
        user_id: str,
    ) -> Dict[str, Any]:
        """Return one event belonging to the user."""

        if not user_id:
            raise AuthorizationError(
                "Authenticated user required"
            )

        event = self.repo.get_by_id(
            int(event_id),
            user_id,
        )

        if not event:
            raise EventNotFoundError(
                f"Event {event_id} not found"
            )

        return event

    def get_event_public(
        self,
        event_id: int,
    ) -> Dict[str, Any]:
        """Return public event information."""

        event = self.repo.get_by_id_public(
            int(event_id)
        )

        if not event:
            raise EventNotFoundError(
                f"Event {event_id} not found"
            )

        return event

    # ==================================================================
    # CREATE
    # ==================================================================
    def set_event_drive_folder(
        self,
        event_id: int,
        folder_id: str,
    ) -> Dict[str, Any]:
        """Store the Google Drive folder ID for an event."""

        if not folder_id:
            raise ValueError("Google Drive folder ID is required")

        updated = self.repo.update(
            int(event_id),
            {
                "event_drive_folder_id": folder_id,
            },
        )

        if not updated:
            raise DatabaseError(
                f"Unable to update event {event_id} with Google Drive folder"
            )

        return updated

    def create_event(
        self,
        event_data: Dict[str, Any],
        user_id: str,
    ) -> Dict[str, Any]:
        """
        Create an event and provision its Google Drive assets.

        Flow:

            1. Validate authenticated user.
            2. Create the event in the database.
            3. Create a dedicated Google Drive folder.
            4. Save the Drive folder ID.
            5. Upload event logo when provided.
            6. Upload wedding invitation when provided.
            7. Save Drive asset metadata.

        If a Drive operation fails after the database event is created,
        the event remains valid and the failure is logged.
        """

        if not user_id:
            raise AuthorizationError(
                "Authenticated user required"
            )

        data = dict(event_data)

        data["user_id"] = user_id

        data.setdefault("guest_count", 0)
        data.setdefault("present_count", 0)

        # --------------------------------------------------------------
        # Drive asset metadata defaults
        # --------------------------------------------------------------

        data.setdefault("logo_drive_file_id", "")
        data.setdefault("logo_filename", "")
        data.setdefault("logo_mime_type", "")

        data.setdefault("invitation_drive_file_id", "")
        data.setdefault("invitation_filename", "")
        data.setdefault("invitation_mime_type", "")

        data.setdefault("event_drive_folder_id", "")

        # --------------------------------------------------------------
        # Extract uploaded images before database insert
        # --------------------------------------------------------------

        logo_data_url = data.pop("logo", None)
        invitation_data_url = data.pop(
            "wedding_invitation",
            None,
        )

        # Keep the database's legacy image fields empty.
        data["logo"] = None
        data["wedding_invitation"] = None

        # --------------------------------------------------------------
        # 1. Create event in database
        # --------------------------------------------------------------

        event = self.repo.create(data)

        if not event:
            raise DatabaseError(
                "Failed to create event"
            )

        event_id = int(event["id"])

        # --------------------------------------------------------------
        # 2. Create dedicated Google Drive folder
        # --------------------------------------------------------------

        try:
            event_name = (
                str(event.get("name") or "Event")
                .strip()
            )

            drive_asset = (
                self.drive_service.create_event_folder(
                    event_name
                )
            )

            # ----------------------------------------------------------
            # 3. Save Drive folder ID
            # ----------------------------------------------------------

            event = self.set_event_drive_folder(
                event_id,
                drive_asset.file_id,
            )

        except Exception:
            import logging

            logger.exception(
                "Failed to create Google Drive folder for event %s",
                event_id,
            )

            return event

        event_folder_id = event.get(
            "event_drive_folder_id"
        )

        if not event_folder_id:
            logger.error(
                "Event %s has no Google Drive folder ID",
                event_id,
            )
            return event

        # --------------------------------------------------------------
        # 4. Upload event logo
        # --------------------------------------------------------------

        if logo_data_url:
            try:
                (
                    logo_bytes,
                    logo_filename,
                    logo_mime_type,
                ) = self._decode_image_data_url(
                    logo_data_url,
                    f"event_{event_id}_logo",
                )

                logo_asset = (
                    self.drive_service.upload_event_logo(
                        logo_bytes,
                        logo_filename,
                        logo_mime_type,
                        folder_id=event_folder_id,
                    )
                )

                event = self.repo.update(
                    event_id,
                    {
                        "logo_drive_file_id": (
                            logo_asset.file_id
                        ),
                        "logo_filename": (
                            logo_asset.filename
                        ),
                        "logo_mime_type": (
                            logo_asset.mime_type
                        ),
                    },
                )

            except Exception:
                import logging

                logging.getLogger(__name__).exception(
                    "Failed to upload logo for event %s",
                    event_id,
                )

        # --------------------------------------------------------------
        # 5. Upload wedding invitation
        # --------------------------------------------------------------

        if invitation_data_url:
            try:
                (
                    invitation_bytes,
                    invitation_filename,
                    invitation_mime_type,
                ) = self._decode_image_data_url(
                    invitation_data_url,
                    f"event_{event_id}_invitation",
                )

                invitation_asset = (
                    self.drive_service.upload_event_invitation(
                        invitation_bytes,
                        invitation_filename,
                        invitation_mime_type,
                        event_folder_id=event_folder_id,
                    )
                )

                event = self.repo.update(
                    event_id,
                    {
                        "invitation_drive_file_id": (
                            invitation_asset.file_id
                        ),
                        "invitation_filename": (
                            invitation_asset.filename
                        ),
                        "invitation_mime_type": (
                            invitation_asset.mime_type
                        ),
                    },
                )

            except Exception:
                import logging

                logging.getLogger(__name__).exception(
                    "Failed to upload invitation for event %s",
                    event_id,
                )

        # --------------------------------------------------------------
        # 6. Return latest event
        # --------------------------------------------------------------

        return self.repo.get_by_id(
            event_id,
            user_id,
        ) or event

    # ==================================================================
    # UPDATE
    # ==================================================================

    def update_event(
        self,
        event_id: int,
        user_id: str,
        updates: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Update an event owned by the user."""

        if not user_id:
            raise AuthorizationError(
                "Authenticated user required"
            )

        existing = self.repo.get_by_id(
            int(event_id),
            user_id,
        )

        if not existing:
            raise EventNotFoundError(
                f"Event {event_id} not found"
            )

        result = self.repo.update(
            int(event_id),
            updates,
        )

        if not result:
            raise DatabaseError(
                "Failed to update event"
            )

        return result

    # ==================================================================
    # DELETE
    # ==================================================================

    def delete_event(
            self,
            event_id: int,
            user_id: str,
    ) -> bool:
        """Delete an event and its Google Drive folder."""

        if not user_id:
            raise AuthorizationError(
                "Authenticated user required"
            )

        # --------------------------------------------------------------
        # 1. Verify ownership and capture Drive folder ID BEFORE delete
        # --------------------------------------------------------------

        event = self.repo.get_by_id(
            int(event_id),
            user_id,
        )

        if not event:
            raise AuthorizationError(
                "Event not found or access denied"
            )

        drive_folder_id = (
                event.get("event_drive_folder_id")
                or ""
        )

        # --------------------------------------------------------------
        # 2. Delete database event
        # --------------------------------------------------------------

        deleted = self.repo.delete(
            int(event_id)
        )

        if not deleted:
            return False

        # --------------------------------------------------------------
        # 3. Delete/trash Google Drive event folder
        # --------------------------------------------------------------

        if drive_folder_id:
            try:
                self.drive_service.delete_file(
                    drive_folder_id
                )

                logging.getLogger(__name__).info(
                    "Deleted Google Drive folder for event %s: %s",
                    event_id,
                    drive_folder_id,
                )

            except Exception:
                # Database deletion succeeded.
                # Do not report the whole operation as failed merely
                # because Drive cleanup failed.
                logging.getLogger(__name__).exception(
                    "Database event %s deleted, but Google Drive "
                    "folder cleanup failed: %s",
                    event_id,
                    drive_folder_id,
                )

        return True

    # ==================================================================
    # COUNTS
    # ==================================================================

    def update_event_counts(
        self,
        event_id: int,
    ) -> None:
        """Refresh cached event guest counts."""

        total = (
            self.guest_repo.count_by_event(
                int(event_id)
            )
        )

        present = (
            self.guest_repo.count_present(
                int(event_id)
            )
        )

        self.repo.update_counts(
            int(event_id),
            total,
            present,
        )

    # ==================================================================
    # EVENT TYPE
    # ==================================================================

    def get_event_type(
        self,
        event_id: int,
    ) -> Optional[str]:
        """Return the event type."""

        return self.repo.get_event_type(
            int(event_id)
        )
