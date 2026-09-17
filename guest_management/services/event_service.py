"""Event application service."""

from __future__ import annotations

import base64
import mimetypes
import logging

from typing import Any, Dict, List, Optional
from guest_management.services.auth_service import AuthService
from guest_management.core.exceptions import (
    AuthorizationError,
    DatabaseError,
    EventNotFoundError,
)
from guest_management.services.storage_service import StorageService
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
            storage_service: Optional[StorageService] = None,
    ):
        self.repo = (
                repository
                or EventRepository()
        )

        self.guest_repo = (
                guest_repository
                or GuestRepository()
        )

        # Storage service is injected by callers when needed.
        # Keep infrastructure dependencies provider-independent.
        # OAuth requires the authenticated user's ID.
        self.storage_service = storage_service or StorageService()

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
            user: Optional[Dict[str, Any]] = None,
    ) -> List[Dict[str, Any]]:
        """Return events accessible to the authenticated user."""

        if not user_id:
            raise AuthorizationError(
                "Authenticated user required"
            )

        from guest_management.services.auth_service import AuthService

        if AuthService.can_manage_events(user):
            return self.repo.get_all()

        return self.repo.get_by_user(user_id)

    def get_event(
            self,
            event_id: int,
            user_id: str,
            user: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Return an event accessible to the authenticated user."""

        if not user_id:
            raise AuthorizationError(
                "Authenticated user required"
            )

        from guest_management.services.auth_service import AuthService

        if AuthService.can_manage_events(user):
            event = self.repo.get_by_id_any(
                int(event_id)
            )
        else:
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

    def create_event(
        self,
        event_data: Dict[str, Any],
        user_id: str,
        user: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        Create an event and provision its storage assets

        Flow:

            1. Validate authenticated user.
            2. Create the event in the database.
            3. Upload event assets to Supabase Storage.
            4. Save the Storage asset paths.
            5. Upload event logo when provided.
            6. Upload wedding invitation when provided.
            7. Save Supabase Storage asset metadata.

        If a Storage operation fails after the database event is created,
        the event remains valid and the failure is logged.
        """

        if not user_id:
            raise AuthorizationError(
                "Authenticated user required"
            )
        if not AuthService.can_manage_events(user):
            raise AuthorizationError(
                "User is not authorized to create events"
            )

        data = dict(event_data)

        data["user_id"] = user_id

        data.setdefault("guest_count", 0)
        data.setdefault("present_count", 0)

        # --------------------------------------------------------------
        # Supabase Storage asset metadata defaults
        # --------------------------------------------------------------

        data.setdefault("logo_storage_path", "")
        data.setdefault("logo_filename", "")
        data.setdefault("logo_mime_type", "")

        data.setdefault("invitation_storage_path", "")
        data.setdefault("invitation_filename", "")
        data.setdefault("invitation_mime_type", "")

        data.setdefault("guest_list_storage_path", "")
        data.setdefault("guest_list_filename", "")
        data.setdefault("guest_list_mime_type", "")

        # --------------------------------------------------------------
        # Extract uploaded images before database insert
        # --------------------------------------------------------------

        logo_data_url = data.pop("logo", None)
        invitation_data_url = data.pop(
            "wedding_invitation",
            None,
        )

        # Keep the database's legacy image fields empty.
        # These columns are NOT NULL; actual uploaded files are stored
        # in Supabase Storage and referenced by the *_storage_path fields.
        data["logo"] = ""
        data["wedding_invitation"] = ""

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
        # 4. Upload event logo
        # --------------------------------------------------------------

        # --------------------------------------------------------------
        # 2. Upload event logo to Supabase Storage
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

                logo_asset = self.storage_service.upload(
                    event_id=event_id,
                    asset_type="logo",
                    content=logo_bytes,
                    filename=logo_filename,
                    mime_type=logo_mime_type,
                    upsert=True,
                )

                event = self.repo.update(
                    event_id,
                    {
                        "logo_storage_path": logo_asset.path,
                        "logo_filename": logo_asset.filename,
                        "logo_mime_type": logo_asset.mime_type,
                    },
                )

            except Exception:
                logger.exception(
                    "Failed to upload logo for event %s",
                    event_id,
                )

        # --------------------------------------------------------------
        # 5. Upload wedding invitation
        # --------------------------------------------------------------

        # --------------------------------------------------------------
        # 3. Upload wedding invitation to Supabase Storage
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

                invitation_asset = self.storage_service.upload(
                    event_id=event_id,
                    asset_type="invitation",
                    content=invitation_bytes,
                    filename=invitation_filename,
                    mime_type=invitation_mime_type,
                    upsert=True,
                )

                event = self.repo.update(
                    event_id,
                    {
                        "invitation_storage_path": invitation_asset.path,
                        "invitation_filename": invitation_asset.filename,
                        "invitation_mime_type": invitation_asset.mime_type,
                    },
                )

            except Exception:
                logger.exception(
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
            user: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Update an event accessible to the authenticated user."""

        if not user_id:
            raise AuthorizationError("Authenticated user required")

        if AuthService.can_manage_events(user):
            existing = self.repo.get_by_id_any(
                int(event_id)
            )
        else:
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
            raise DatabaseError("Failed to update event")

        return result
    # ==================================================================
    # DELETE
    # ==================================================================

    def delete_event(
            self,
            event_id: int,
            user_id: str,
            user: Optional[Dict[str, Any]] = None,
    ) -> bool:
        """Delete an event and its Supabase Storage assets."""

        if not user_id:
            raise AuthorizationError(
                "Authenticated user required"
            )



        # --------------------------------------------------------------
        # 1. Verify ownership and capture Storage paths BEFORE delete
        # --------------------------------------------------------------

        from guest_management.services.auth_service import AuthService

        if AuthService.can_manage_events(user):
            event = self.repo.get_by_id_any(
                int(event_id)
            )
        else:
            event = self.repo.get_by_id(
                int(event_id),
                user_id,
            )

        if not event:
            raise AuthorizationError(
                "Event not found or access denied"
            )

        storage_paths = [
            event.get("logo_storage_path") or "",
            event.get("invitation_storage_path") or "",
            event.get("guest_list_storage_path") or "",
        ]

        # --------------------------------------------------------------
        # 2. Delete database event
        # --------------------------------------------------------------

        deleted = self.repo.delete(
            int(event_id)
        )

        if not deleted:
            return False

        # --------------------------------------------------------------
        # 3. Delete Supabase Storage assets
        # --------------------------------------------------------------

        for storage_path in storage_paths:
            if not storage_path:
                continue

            try:
                self.storage_service.delete(
                    storage_path
                )

                logging.getLogger(__name__).info(
                    "Deleted Supabase Storage asset for event %s: %s",
                    event_id,
                    storage_path,
                )

            except Exception:
                # Database deletion succeeded.
                # Do not report the whole operation as failed merely
                # because Storage cleanup failed.
                logging.getLogger(__name__).exception(
                    "Database event %s deleted, but Supabase "
                    "Storage asset cleanup failed: %s",
                    event_id,
                    storage_path,
                )

        return True

