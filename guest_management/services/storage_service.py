# guest_management/services/storage_service.py

from __future__ import annotations

import logging
from dataclasses import dataclass

from guest_management.core.config import settings

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class StorageAsset:
    """Metadata for an asset stored in Supabase Storage."""

    path: str
    filename: str
    mime_type: str
    size: int = 0

    @property
    def is_valid(self) -> bool:
        return bool(self.path)


class StorageService:
    """
    Application-facing file storage service.

    Supabase Storage is an infrastructure detail and should not
    be referenced directly by UI/state classes.
    """

    BUCKET = "event-assets"

    def __init__(self, client=None) -> None:
        self._client = client

    @property
    def client(self):
        if self._client is None:
            from supabase import create_client

            if not settings.supabase_url:
                raise RuntimeError("SUPABASE_URL is not configured.")

            if not settings.supabase_secret_key:
                raise RuntimeError(
                    "SUPABASE_SECRET_KEY is not configured."
                )

            self._client = create_client(
                settings.supabase_url,
                settings.supabase_secret_key,
            )

        return self._client

    @staticmethod
    def _validate_event_id(event_id: int) -> int:
        try:
            event_id = int(event_id)
        except (TypeError, ValueError) as exc:
            raise ValueError("Invalid event ID.") from exc

        if event_id <= 0:
            raise ValueError("Event ID must be positive.")

        return event_id

    @staticmethod
    def _validate_content(content: bytes) -> None:
        if not content:
            raise ValueError("Cannot upload an empty file.")

    @staticmethod
    def _validate_filename(filename: str) -> str:
        filename = str(filename or "").strip()

        if not filename:
            raise ValueError("Filename is required.")

        # Prevent callers from escaping the event storage directory.
        filename = filename.replace("\\", "/").split("/")[-1]

        if filename in {".", ".."}:
            raise ValueError("Invalid filename.")

        return filename

    @staticmethod
    def _validate_mime_type(mime_type: str) -> str:
        mime_type = str(mime_type or "").strip()

        if not mime_type:
            raise ValueError("MIME type is required.")

        return mime_type

    def _build_path(
        self,
        event_id: int,
        asset_type: str,
        filename: str,
    ) -> str:
        event_id = self._validate_event_id(event_id)
        filename = self._validate_filename(filename)

        asset_type = str(asset_type or "").strip().lower()

        allowed_types = {
            "logo",
            "invitation",
            "guest-list",
        }

        if asset_type not in allowed_types:
            raise ValueError(
                f"Unsupported asset type: {asset_type}"
            )

        return f"events/{event_id}/{asset_type}/{filename}"

    def upload(
        self,
        *,
        event_id: int,
        asset_type: str,
        content: bytes,
        filename: str,
        mime_type: str,
        upsert: bool = True,
    ) -> StorageAsset:
        """
        Upload an EventLah asset to Supabase Storage.
        """

        self._validate_content(content)
        filename = self._validate_filename(filename)
        mime_type = self._validate_mime_type(mime_type)

        path = self._build_path(
            event_id=event_id,
            asset_type=asset_type,
            filename=filename,
        )

        logger.info(
            "Uploading storage asset "
            "event_id=%s type=%s path=%s size=%s",
            event_id,
            asset_type,
            path,
            len(content),
        )

        result = (
            self.client
            .storage
            .from_(self.BUCKET)
            .upload(
                path,
                content,
                {
                    "content-type": mime_type,
                    "upsert": str(upsert).lower(),
                },
            )
        )

        # Supabase returns different metadata depending on
        # client/storage version. The path we generated is the
        # authoritative identifier.
        if result is None:
            raise RuntimeError(
                f"Storage upload failed for {path}."
            )

        return StorageAsset(
            path=path,
            filename=filename,
            mime_type=mime_type,
            size=len(content),
        )

    def download(self, path: str) -> bytes:
        """Download an asset from Supabase Storage."""

        path = str(path or "").strip()

        if not path:
            raise ValueError("Storage path is required.")

        logger.debug(
            "Downloading storage asset path=%s",
            path,
        )

        return (
            self.client
            .storage
            .from_(self.BUCKET)
            .download(path)
        )

    def delete(self, path: str) -> bool:
        """Delete an asset from Supabase Storage."""

        path = str(path or "").strip()

        if not path:
            return False

        try:
            self.client.storage.from_(self.BUCKET).remove([path])

            logger.info(
                "Deleted storage asset path=%s",
                path,
            )

            return True

        except Exception:
            logger.exception(
                "Unable to delete storage asset path=%s",
                path,
            )
            return False

    def exists(self, path: str) -> bool:
        """Return whether an asset exists."""

        path = str(path or "").strip()

        if not path:
            return False

        try:
            parent = "/".join(path.split("/")[:-1])
            filename = path.split("/")[-1]

            files = (
                self.client
                .storage
                .from_(self.BUCKET)
                .list(parent)
            )

            return any(
                item.get("name") == filename
                for item in (files or [])
            )

        except Exception:
            logger.exception(
                "Unable to check storage asset path=%s",
                path,
            )
            return False

    def health_check(self) -> bool:
        """Verify that the Supabase Storage bucket is accessible."""

        try:
            self.client.storage.from_(self.BUCKET).list("")
            return True

        except Exception:
            logger.exception(
                "Supabase Storage health check failed."
            )
            return False