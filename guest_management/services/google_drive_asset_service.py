# guest_management/services/google_drive_asset_service.py
"""
Google Drive asset storage service.

EventLah event assets are stored in Google Drive.

The database stores only metadata:

    Event logo
        logo_drive_file_id
        logo_filename
        logo_mime_type

    Invitation card
        invitation_drive_file_id
        invitation_filename
        invitation_mime_type

    Guest list
        guest_list_drive_file_id
        guest_list_filename
        guest_list_mime_type
        guest_list_uploaded_at

The actual file bytes remain in Google Drive.

Architecture:

    Create Event
        |
        v
    GoogleDriveAssetService
        |
        v
    Google Drive
        |
        +---- Event logo
        |
        +---- Invitation card
        |
        +---- Guest list
        |
        v
    Database stores Drive metadata
        |
        v
    EmailService / Email Worker
        |
        v
    SendGrid


AUTHENTICATION
--------------

This version uses Google OAuth rather than a service account.

OAuth token:

    guest_management/secrets/eventlah-drive-token.json

OAuth client:

    guest_management/secrets/eventlah-drive-oauth-client.json

The OAuth setup script creates the token:

    python .\\guest_management\\scripts\\google_drive_oauth_setup.py

Environment variables can override the default paths:

    GOOGLE_DRIVE_OAUTH_TOKEN_FILE
    GOOGLE_DRIVE_OAUTH_CLIENT_FILE

Drive root folder:

    GOOGLE_DRIVE_ROOT_FOLDER_ID

Legacy:

    GOOGLE_DRIVE_FOLDER_ID

The service prefers GOOGLE_DRIVE_ROOT_FOLDER_ID.
"""


from __future__ import annotations

import io
import json
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import (
    MediaIoBaseDownload,
    MediaIoBaseUpload,
)
from google.oauth2.credentials import Credentials

from guest_management.core.config import settings
from guest_management.database import get_db
from guest_management.services.google_drive_service import (
    decrypt_refresh_token,
)

logger = logging.getLogger(__name__)


# ======================================================================
# CONSTANTS
# ======================================================================

DRIVE_SCOPE = (
    "https://www.googleapis.com/auth/drive"
)

DRIVE_FOLDER_MIME_TYPE = (
    "application/vnd.google-apps.folder"
)

DEFAULT_FOLDER_NAME = "EventLah Event Assets"

DEFAULT_OAUTH_TOKEN_FILENAME = (
    "eventlah-drive-token.json"
)

DEFAULT_OAUTH_CLIENT_FILENAME = (
    "eventlah-drive-oauth-client.json"
)


# ======================================================================
# RESULT MODEL
# ======================================================================
@dataclass(slots=True)
class DriveAsset:
    """Metadata describing a file stored in Google Drive."""

    file_id: str
    filename: str
    mime_type: str
    size: int = 0

    @property
    def is_valid(self) -> bool:
        """Return True when the Drive asset has a valid file ID."""
        return bool(self.file_id)

    @property
    def web_view_link(self) -> str:
        """
        Return a Google Drive browser URL.

        Google Drive folders use /drive/folders/<id>.
        Normal files use /file/d/<id>/view.
        """

        if not self.file_id:
            return ""

        if self.mime_type == DRIVE_FOLDER_MIME_TYPE:
            return (
                "https://drive.google.com/drive/folders/"
                f"{self.file_id}"
            )

        return (
            "https://drive.google.com/file/d/"
            f"{self.file_id}/view"
        )
# ======================================================================
# SERVICE
# ======================================================================

class GoogleDriveAssetService:
    """
    Store and retrieve EventLah assets from Google Drive.

    Authentication is OAuth-based.

    The service intentionally does NOT use a service account for
    uploading files because Google service accounts do not have their
    own My Drive storage quota.

    Required:

        GOOGLE_DRIVE_ROOT_FOLDER_ID

    Recommended:

        GOOGLE_DRIVE_OAUTH_TOKEN_FILE
        GOOGLE_DRIVE_OAUTH_CLIENT_FILE

    Defaults:

        guest_management/secrets/eventlah-drive-token.json
        guest_management/secrets/eventlah-drive-oauth-client.json

    Existing callers using:

        upload_bytes()
        upload_guest_list()
        download_bytes()
        get_metadata()
        delete()
        health_check()

    remain compatible.
    """

    DRIVE_SCOPE = DRIVE_SCOPE

    # ------------------------------------------------------------------
    # Default locations
    # ------------------------------------------------------------------

    DEFAULT_OAUTH_TOKEN_FILE = (
        DEFAULT_OAUTH_TOKEN_FILENAME
    )

    DEFAULT_OAUTH_CLIENT_FILE = (
        DEFAULT_OAUTH_CLIENT_FILENAME
    )

    def __init__(
            self,
            user_id: Optional[str] = None,
            *,
            credentials_json: Optional[str] = None,
            folder_id: Optional[str] = None,
            token_file: Optional[str] = None,
            client_file: Optional[str] = None,
    ) -> None:

        self.user_id = str(
            user_id or ""
        ).strip()

        self.folder_id = (
                folder_id
                or os.getenv(
            "GOOGLE_DRIVE_ROOT_FOLDER_ID",
            "",
        )
        ).strip()

        self.credentials_json = credentials_json
        self.token_file = (
                token_file
                or os.getenv(
            "GOOGLE_DRIVE_OAUTH_TOKEN_FILE",
            "",
        )
        )
        self.client_file = (
                client_file
                or os.getenv(
            "GOOGLE_DRIVE_OAUTH_CLIENT_FILE",
            "",
        )
        )

        self._drive = None

        # --------------------------------------------------------------
        # Project paths
        # --------------------------------------------------------------

        self._package_root = (
            Path(__file__).resolve().parents[1]
        )

        self._project_root = (
            self._package_root.parent
        )

        self.credentials_json = (
            credentials_json
            or os.getenv(
                "GOOGLE_DRIVE_SERVICE_ACCOUNT_FILE",
                "",
            )
            or os.getenv(
                "GOOGLE_DRIVE_SERVICE_ACCOUNT_JSON",
                "",
            )
        ).strip()

        # --------------------------------------------------------------
        # OAuth token
        # --------------------------------------------------------------

        configured_token = (
            token_file
            or os.getenv(
                "GOOGLE_DRIVE_OAUTH_TOKEN_FILE",
                "",
            )
        ).strip()

        if configured_token:
            self.token_file = self._resolve_path(
                configured_token
            )
        else:
            self.token_file = (
                self._package_root
                / "secrets"
                / DEFAULT_OAUTH_TOKEN_FILENAME
            )

        # --------------------------------------------------------------
        # OAuth client
        # --------------------------------------------------------------

        configured_client = (
            client_file
            or os.getenv(
                "GOOGLE_DRIVE_OAUTH_CLIENT_FILE",
                "",
            )
        ).strip()

        if configured_client:
            self.client_file = self._resolve_path(
                configured_client
            )
        else:
            self.client_file = (
                self._package_root
                / "secrets"
                / DEFAULT_OAUTH_CLIENT_FILENAME
            )

        # --------------------------------------------------------------
        # Root Drive folder
        # --------------------------------------------------------------

        self.folder_id = (
            folder_id
            or os.getenv(
                "GOOGLE_DRIVE_ROOT_FOLDER_ID",
                "",
            )
            or os.getenv(
                "GOOGLE_DRIVE_FOLDER_ID",
                "",
            )
        ).strip()

        # --------------------------------------------------------------
        # Cached Drive client
        # --------------------------------------------------------------

        self._drive = None

    # ==================================================================
    # PATH HELPERS
    # ==================================================================

    def _resolve_path(
        self,
        value: str,
    ) -> Path:
        """
        Resolve a configured path.

        Absolute paths are returned unchanged.

        Relative paths are resolved against the project root first,
        then against the current working directory.
        """

        path = Path(value).expanduser()

        if path.is_absolute():
            return path

        project_path = (
            self._project_root / path
        )

        if project_path.exists():
            return project_path

        package_path = (
            self._package_root / path
        )

        if package_path.exists():
            return package_path

        return path

    # ==================================================================
    # AUTHENTICATION
    # ==================================================================

    def _load_oauth_credentials(self) -> Credentials:
        """
        Load Google Drive OAuth credentials.

        Preferred source:
            users.google_refresh_token_enc

        The encrypted refresh token is tied to the EventLah user's
        Google OAuth grant and is decrypted using SESSION_SECRET.

        A local token file is NOT used here.

        This keeps GoogleDriveAssetService consistent with the
        application's normal Google login flow.
        """

        if not self.user_id:
            raise RuntimeError(
                "Google Drive user_id is required for database OAuth."
            )

        rows = (
                get_db()
                .table("users")
                .select(
                    "id,email,google_refresh_token_enc"
                )
                .eq("id", self.user_id)
                .limit(1)
                .execute()
                .data
                or []
        )

        if not rows:
            raise RuntimeError(
                f"EventLah user not found: {self.user_id}"
            )

        encrypted_token = (
                rows[0].get(
                    "google_refresh_token_enc"
                )
                or ""
        ).strip()

        if not encrypted_token:
            raise RuntimeError(
                "Google Drive permission is not connected "
                f"for {rows[0].get('email', 'this account')}. "
                "Please sign in with Google again."
            )

        try:
            refresh_token = decrypt_refresh_token(
                encrypted_token
            )

        except Exception as exc:
            raise RuntimeError(
                "Unable to decrypt the Google Drive refresh token. "
                "Verify that SESSION_SECRET has not changed."
            ) from exc

        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            scopes=[self.DRIVE_SCOPE],
        )

        # --------------------------------------------------------------
        # Refresh access token
        # --------------------------------------------------------------

        if credentials.expired or not credentials.valid:
            if not credentials.refresh_token:
                raise RuntimeError(
                    "Google Drive OAuth credentials have no refresh token."
                )

            try:
                credentials.refresh(
                    Request()
                )

            except Exception as exc:
                raise RuntimeError(
                    "Unable to refresh Google Drive OAuth token. "
                    "The Google authorization may have been revoked. "
                    "Please sign in with Google again."
                ) from exc

        return credentials

    # ==================================================================
    # DRIVE CLIENT
    # ==================================================================

    def _get_drive(self):
        """
        Return the authenticated Google Drive client.
        """

        if self._drive is not None:
            return self._drive

        credentials = (
            self._load_oauth_credentials()
        )

        self._drive = build(
            "drive",
            "v3",
            credentials=credentials,
            cache_discovery=False,
        )

        return self._drive

    # ==================================================================
    # FOLDER
    # ==================================================================

    def _ensure_folder(self) -> str:
        """
        Return the configured root Drive folder.

        If GOOGLE_DRIVE_ROOT_FOLDER_ID is configured, it is used
        directly.

        Otherwise the service searches for:

            EventLah Event Assets

        and creates it if necessary.
        """

        if self.folder_id:
            return self.folder_id

        drive = self._get_drive()

        query = (
            "name = "
            f"'{DEFAULT_FOLDER_NAME}' "
            "and mimeType = "
            f"'{DRIVE_FOLDER_MIME_TYPE}' "
            "and trashed = false"
        )

        response = (
            drive.files()
            .list(
                q=query,
                spaces="drive",
                fields="files(id,name)",
                pageSize=10,
            )
            .execute()
        )

        files = (
            response.get("files")
            or []
        )

        if files:
            self.folder_id = (
                files[0]["id"]
            )

            return self.folder_id

        metadata = {
            "name": DEFAULT_FOLDER_NAME,
            "mimeType": DRIVE_FOLDER_MIME_TYPE,
        }

        created = (
            drive.files()
            .create(
                body=metadata,
                fields="id",
            )
            .execute()
        )

        self.folder_id = (
            created["id"]
        )

        logger.info(
            "Created Google Drive asset folder "
            "id=%s",
            self.folder_id,
        )

        return self.folder_id

    # ==================================================================
    # VALIDATE FOLDER
    # ==================================================================

    def validate_folder(
        self,
        folder_id: Optional[str] = None,
    ) -> Optional[dict]:
        """
        Validate that a Drive folder exists and is accessible.

        Returns folder metadata or None.
        """

        target_id = (
            folder_id
            or self.folder_id
        )

        if not target_id:
            return None

        drive = self._get_drive()

        try:
            return (
                drive.files()
                .get(
                    fileId=target_id,
                    fields=(
                        "id,"
                        "name,"
                        "mimeType,"
                        "driveId,"
                        "trashed"
                    ),
                )
                .execute()
            )

        except Exception:
            logger.exception(
                "Unable to validate Google Drive folder "
                "id=%s",
                target_id,
            )

            return None

    # ==================================================================
    # UPLOAD
    # ==================================================================

    def upload_bytes(
        self,
        content: bytes,
        filename: str,
        mime_type: str,
        *,
        folder_id: Optional[str] = None,
    ) -> DriveAsset:
        """
        Upload raw bytes to Google Drive.

        Returns DriveAsset metadata.

        This is the main low-level upload method used by:

            upload_event_logo()
            upload_invitation_card()
            upload_guest_list()
        """

        if not content:
            raise ValueError(
                "Cannot upload an empty file."
            )

        filename = (
            str(filename or "")
            .strip()
        )

        if not filename:
            raise ValueError(
                "Filename is required."
            )

        mime_type = (
            str(mime_type or "")
            .strip()
        )

        if not mime_type:
            raise ValueError(
                "MIME type is required."
            )

        drive = self._get_drive()

        parent_id = (
            folder_id
            or self._ensure_folder()
        )

        metadata = {
            "name": filename,
            "parents": [parent_id],
        }

        media = MediaIoBaseUpload(
            io.BytesIO(content),
            mimetype=mime_type,
            resumable=False,
        )

        logger.info(
            "Uploading Drive asset "
            "filename=%s size=%s folder=%s",
            filename,
            len(content),
            parent_id,
        )

        created = (
            drive.files()
            .create(
                body=metadata,
                media_body=media,
                fields=(
                    "id,"
                    "name,"
                    "mimeType,"
                    "size"
                ),
            )
            .execute()
        )

        file_id = (
            created.get("id")
            or ""
        )

        if not file_id:
            raise RuntimeError(
                "Google Drive did not return "
                "a file ID."
            )

        size_value = (
            created.get("size")
        )

        size = None

        if size_value is not None:
            try:
                size = int(size_value)
            except (
                TypeError,
                ValueError,
            ):
                size = None

        logger.info(
            "Uploaded Drive asset "
            "file_id=%s filename=%s",
            file_id,
            filename,
        )

        return DriveAsset(
            file_id=file_id,
            filename=(
                created.get("name")
                or filename
            ),
            mime_type=(
                created.get("mimeType")
                or mime_type
            ),
            size=size,
        )

    # ==================================================================
    # EVENT LOGO
    # ==================================================================

    def upload_event_logo(
        self,
        content: bytes,
        filename: str,
        mime_type: str,
        *,
        folder_id: Optional[str] = None,
    ) -> DriveAsset:
        """
        Upload an event/company logo.

        The returned values map directly to:

            logo_drive_file_id
            logo_filename
            logo_mime_type
        """

        if not content:
            raise ValueError(
                "Cannot upload an empty event logo."
            )

        logger.info(
            "Uploading event logo "
            "filename=%s size=%s",
            filename,
            len(content),
        )

        return self.upload_bytes(
            content=content,
            filename=filename,
            mime_type=mime_type,
            folder_id=folder_id,
        )

    # ==================================================================
    # INVITATION CARD
    # ==================================================================

    def upload_invitation_card(
        self,
        content: bytes,
        filename: str,
        mime_type: str,
        *,
        folder_id: Optional[str] = None,
    ) -> DriveAsset:
        """
        Upload an event invitation card.

        The returned values map directly to:

            invitation_drive_file_id
            invitation_filename
            invitation_mime_type
        """

        if not content:
            raise ValueError(
                "Cannot upload an empty invitation card."
            )

        logger.info(
            "Uploading invitation card "
            "filename=%s size=%s",
            filename,
            len(content),
        )

        return self.upload_bytes(
            content=content,
            filename=filename,
            mime_type=mime_type,
            folder_id=folder_id,
        )

    # ==================================================================
    # GUEST LIST
    # ==================================================================

    def upload_guest_list(
        self,
        content: bytes,
        filename: str,
        mime_type: str,
        *,
        folder_id: Optional[str] = None,
    ) -> DriveAsset:
        """
        Upload the original guest-list file to Google Drive.

        The guest list is still imported into the database.

        Google Drive acts as the original-file archive.

        Supported formats normally include:

            .xlsx
            .xls
            .csv
        """

        if not content:
            raise ValueError(
                "Cannot upload an empty guest-list file."
            )

        filename = (
            str(filename or "")
            .strip()
        )

        if not filename:
            raise ValueError(
                "Guest-list filename is required."
            )

        mime_type = (
            str(mime_type or "")
            .strip()
        )

        if not mime_type:
            raise ValueError(
                "Guest-list MIME type is required."
            )

        logger.info(
            "Uploading guest list to Google Drive "
            "filename=%s size=%s",
            filename,
            len(content),
        )

        return self.upload_bytes(
            content=content,
            filename=filename,
            mime_type=mime_type,
            folder_id=folder_id,
        )

    # ==================================================================
    # DOWNLOAD
    # ==================================================================

    def download_bytes(
            self,
            file_id: str,
    ) -> bytes:
        """
        Download the actual binary content of a Google Drive file.

        Uses the authenticated user's OAuth access token and explicitly
        requests the Drive media endpoint.
        """

        file_id = str(file_id or "").strip()

        if not file_id:
            raise ValueError(
                "Google Drive file ID is required."
            )

        try:
            import requests

            credentials = self._load_oauth_credentials()

            # Make sure we have a valid access token.
            if not credentials.valid:
                if not credentials.refresh_token:
                    raise RuntimeError(
                        "Google Drive OAuth credentials are invalid "
                        "and cannot be refreshed."
                    )

                credentials.refresh(Request())

            access_token = credentials.token

            if not access_token:
                raise RuntimeError(
                    "Google Drive OAuth access token is unavailable."
                )

            url = (
                "https://www.googleapis.com/drive/v3/files/"
                f"{file_id}"
            )

            response = requests.get(
                url,
                params={
                    "alt": "media",
                },
                headers={
                    "Authorization": f"Bearer {access_token}",
                },
                timeout=60,
            )

            response.raise_for_status()

            content = response.content

            logger.debug(
                "Downloaded Drive asset "
                "file_id=%s size=%s",
                file_id,
                len(content),
            )

            return content

        except Exception:
            logger.exception(
                "Unable to download Drive asset "
                "file_id=%s",
                file_id,
            )
            raise

    # ==================================================================
    # METADATA
    # ==================================================================

    def get_metadata(
        self,
        file_id: str,
    ) -> Optional[dict]:
        """
        Return Google Drive file metadata.
        """

        file_id = (
            str(file_id or "")
            .strip()
        )

        if not file_id:
            return None

        drive = self._get_drive()

        try:
            return (
                drive.files()
                .get(
                    fileId=file_id,
                    fields=(
                        "id,"
                        "name,"
                        "mimeType,"
                        "size,"
                        "createdTime,"
                        "modifiedTime,"
                        "webViewLink"
                    ),
                )
                .execute()
            )

        except Exception:
            logger.exception(
                "Unable to retrieve Drive metadata "
                "for file_id=%s",
                file_id,
            )

            return None

    # ==================================================================
    # EXISTS
    # ==================================================================

    def exists(
        self,
        file_id: str,
    ) -> bool:
        """
        Return True if the Drive file exists and is accessible.
        """

        return (
            self.get_metadata(file_id)
            is not None
        )

    # ==================================================================
    # DELETE
    # ==================================================================

    def delete(
        self,
        file_id: str,
    ) -> bool:
        """
        Delete an asset from Google Drive.
        """

        file_id = (
            str(file_id or "")
            .strip()
        )

        if not file_id:
            return False

        drive = self._get_drive()

        try:
            (
                drive.files()
                .delete(
                    fileId=file_id,
                )
                .execute()
            )

            logger.info(
                "Deleted Drive asset "
                "file_id=%s",
                file_id,
            )

            return True

        except Exception:
            logger.exception(
                "Unable to delete Drive asset "
                "file_id=%s",
                file_id,
            )

            return False

    # ==================================================================
    # HEALTH CHECK
    # ==================================================================

    def health_check(self) -> bool:
        """
        Verify that Google Drive OAuth authentication works.

        Does not upload or modify anything.
        """

        try:
            drive = self._get_drive()

            drive.about().get(
                fields=(
                    "user("
                    "displayName,"
                    "emailAddress"
                    ")"
                ),
            ).execute()

            return True

        except Exception:
            logger.exception(
                "Google Drive health check failed."
            )

            return False

    # ==================================================================
    # ACCOUNT INFORMATION
    # ==================================================================

    def get_account_info(self) -> Optional[dict]:
        """
        Return the Google account currently used by OAuth.
        """

        try:
            drive = self._get_drive()

            response = (
                drive.about()
                .get(
                    fields=(
                        "user("
                        "displayName,"
                        "emailAddress,"
                        "permissionId"
                        ")"
                    ),
                )
                .execute()
            )

            return response.get("user")

        except Exception:
            logger.exception(
                "Unable to retrieve Google Drive "
                "account information."
            )

            return None

    # ==================================================================
    # ROOT FOLDER INFORMATION
    # ==================================================================

    def get_root_folder_metadata(
        self,
    ) -> Optional[dict]:
        """
        Return metadata for the configured EventLah root folder.
        """

        folder_id = (
            self._ensure_folder()
        )

        return self.get_metadata(
            folder_id
        )

    # ==================================================================
    # EVENT FOLDER COMPATIBILITY
    # ==================================================================

    def create_event_folder(
        self,
        event_name: str,
    ) -> DriveAsset:
        """
        Create a dedicated Google Drive folder for an event.

        This method is kept compatible with EventService.

        Folder structure:

            EventLah Attendance/
                Event Name/
                    logo
                    invitation
                    guest_list
        """

        event_name = str(event_name or "").strip()

        if not event_name:
            raise ValueError(
                "Event name is required."
            )

        drive = self._get_drive()

        root_folder_id = self._ensure_folder()

        metadata = {
            "name": event_name,
            "mimeType": DRIVE_FOLDER_MIME_TYPE,
            "parents": [root_folder_id],
        }

        created = (
            drive.files()
            .create(
                body=metadata,
                fields=(
                    "id,name,mimeType,size,"
                    "createdTime,modifiedTime,webViewLink"
                ),
            )
            .execute()
        )

        logger.info(
            "Created Google Drive event folder "
            "event=%s id=%s",
            event_name,
            created["id"],
        )

        return DriveAsset(
            file_id=created["id"],
            filename=created.get("name", event_name),
            mime_type=created.get(
                "mimeType",
                DRIVE_FOLDER_MIME_TYPE,
            ),
            size=int(
                created.get("size") or 0
            ),
        )

    # ==================================================================
    # EVENT INVITATION COMPATIBILITY
    # ==================================================================

    def upload_event_invitation(
        self,
        content: bytes,
        filename: str,
        mime_type: str,
        *,
        event_folder_id: Optional[str] = None,
    ) -> DriveAsset:
        """
        Compatibility wrapper used by EventService.

        Delegates to upload_invitation_card().
        """

        return self.upload_invitation_card(
            content=content,
            filename=filename,
            mime_type=mime_type,
            folder_id=event_folder_id,
        )

    # ==================================================================
    # DELETE COMPATIBILITY
    # ==================================================================

    def delete_file(
        self,
        file_id: str,
    ) -> bool:
        """
        Compatibility wrapper used by EventService.

        Delegates to delete().
        """

        return self.delete(file_id)