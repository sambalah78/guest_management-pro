"""
Google Drive connection service.

Manages multiple Google Drive identities for one EventLah user.

Responsibilities:
    - Register/update Drive connections.
    - Enforce one active PRIMARY connection.
    - Support multiple BACKUP connections.
    - Promote a backup connection.
    - Deactivate connections.
    - Verify Drive access.
    - Keep encrypted refresh tokens out of UI/state.

This service deliberately does NOT replace GoogleDriveAssetService.
Existing asset/event/guest Drive operations remain unchanged.
"""

from __future__ import annotations

import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from guest_management.repositories.google_drive_connection_repository import (
    GoogleDriveConnectionRepository,
)
from guest_management.services.google_drive_service import (
    decrypt_refresh_token,
    encrypt_refresh_token,
)
from guest_management.core.config import settings


logger = logging.getLogger(__name__)


class GoogleDriveConnectionService:
    """Business logic for EventLah Google Drive connections."""

    def __init__(
        self,
        repository: Optional[
            GoogleDriveConnectionRepository
        ] = None,
    ):
        self.repo = (
            repository
            or GoogleDriveConnectionRepository()
        )

    # ================================================================
    # NORMALIZATION
    # ================================================================

    @staticmethod
    def _normalize_email(email: str) -> str:
        return str(email or "").strip().lower()

    @staticmethod
    def _normalize_user_id(user_id: str) -> str:
        return str(user_id or "").strip()

    @staticmethod
    def _normalize_connection_id(connection_id: str) -> str:
        return str(connection_id or "").strip()

    @staticmethod
    def _new_connection_id() -> str:
        return uuid.uuid4().hex

    # ================================================================
    # READ
    # ================================================================

    def list_connections(
        self,
        user_id: str,
        *,
        active_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Return connections belonging to the user.

        OAuth secrets are removed before returning.
        """

        user_id = self._normalize_user_id(user_id)

        if not user_id:
            return []

        rows = self.repo.list_by_user(
            user_id,
            active_only=active_only,
        )

        return [
            self._safe_connection(row)
            for row in rows
        ]

    def get_connection(
        self,
        connection_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Return a sanitized connection."""

        connection_id = self._normalize_connection_id(
            connection_id
        )

        if not connection_id:
            return None

        row = self.repo.get_by_id(
            connection_id
        )

        if not row:
            return None

        return self._safe_connection(row)

    def get_primary(
        self,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Return the active PRIMARY connection."""

        user_id = self._normalize_user_id(user_id)

        if not user_id:
            return None

        row = self.repo.get_primary(
            user_id
        )

        if not row:
            return None

        return self._safe_connection(row)

    def get_backups(
        self,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """Return active BACKUP connections."""

        user_id = self._normalize_user_id(user_id)

        if not user_id:
            return []

        rows = self.repo.get_backup_connections(
            user_id
        )

        return [
            self._safe_connection(row)
            for row in rows
        ]

    # ================================================================
    # REGISTER
    # ================================================================

    def register_connection(
        self,
        *,
        user_id: str,
        google_email: str,
        refresh_token: Optional[str] = None,
        encrypted_refresh_token: Optional[str] = None,
        root_folder_id: str = "",
        connection_role: str = "BACKUP",
        make_primary: bool = False,
    ) -> Dict[str, Any]:
        """
        Register or reconnect a Google Drive account.

        A plain refresh token may be supplied by an OAuth callback.
        It is encrypted before persistence.

        An already encrypted token may also be supplied internally.

        PRIMARY behavior:
            - Only one active PRIMARY is allowed per user.
            - Registering a new PRIMARY demotes the existing PRIMARY.
            - Reconnecting an existing account as PRIMARY promotes it.
        """

        user_id = self._normalize_user_id(user_id)
        google_email = self._normalize_email(
            google_email
        )

        if not user_id:
            raise ValueError("user_id is required")

        if not google_email:
            raise ValueError(
                "google_email is required"
            )

        role = (
            str(connection_role or "BACKUP")
            .strip()
            .upper()
        )

        if make_primary:
            role = "PRIMARY"

        if role not in {"PRIMARY", "BACKUP"}:
            raise ValueError(
                "connection_role must be PRIMARY or BACKUP"
            )

        # ------------------------------------------------------------
        # Encrypt token exactly once.
        # ------------------------------------------------------------

        encrypted = (
            str(encrypted_refresh_token).strip()
            if encrypted_refresh_token
            else None
        )

        if refresh_token:
            encrypted = encrypt_refresh_token(
                refresh_token
            )

        # ------------------------------------------------------------
        # Existing connection?
        # ------------------------------------------------------------

        existing = self.repo.get_by_user_and_email(
            user_id,
            google_email,
        )

        if existing:
            connection_id = self._get_connection_id(
                existing
            )

            if not connection_id:
                raise RuntimeError(
                    "Existing Google Drive connection "
                    "has no connection ID"
                )

            updates: Dict[str, Any] = {
                "is_active": True,
                "root_folder_id": (
                    str(root_folder_id or "").strip()
                    or existing.get("root_folder_id")
                    or ""
                ),
            }

            if encrypted:
                updates[
                    "encrypted_refresh_token"
                ] = encrypted

            if role == "PRIMARY":
                updates["connection_role"] = "PRIMARY"
                updates["is_primary"] = True
            else:
                # Do not automatically demote an existing
                # PRIMARY merely because OAuth was refreshed.
                if not existing.get("is_primary"):
                    updates["connection_role"] = "BACKUP"
                    updates["is_primary"] = False

            updated = self.repo.update(
                connection_id,
                updates,
            )

            if not updated:
                raise RuntimeError(
                    "Failed to update Google Drive connection"
                )

            if role == "PRIMARY":
                self._ensure_primary(
                    user_id,
                    connection_id,
                )

            # IMPORTANT:
            # Return the repository update result directly.
            #
            # Do NOT immediately call get_by_id() here.
            # The production repository already returns the updated
            # database record, and this also keeps the service
            # compatible with repository test doubles.
            return self._safe_connection(updated)

        # ------------------------------------------------------------
        # New connection.
        # ------------------------------------------------------------

        if role == "PRIMARY":
            # There must never be two active PRIMARY connections.
            self._demote_existing_primaries(
                user_id
            )

        connection_id = self._new_connection_id()

        created = self.repo.create(
            connection_id=connection_id,
            user_id=user_id,
            google_email=google_email,
            encrypted_refresh_token=encrypted,
            root_folder_id=(
                str(root_folder_id or "").strip()
            ),
            connection_role=role,
            is_primary=(role == "PRIMARY"),
            is_active=True,
        )

        if not created:
            raise RuntimeError(
                "Failed to create Google Drive connection"
            )

        # The repository create() contract returns the persisted
        # record, including its database `id`.
        #
        # Do NOT call repo.get_by_id() here. This avoids an unnecessary
        # database round-trip and keeps repository test doubles
        # compatible.
        return self._safe_connection(created)

    # ================================================================
    # PRIMARY MANAGEMENT
    # ================================================================

    def make_primary(
        self,
        user_id: str,
        connection_id: str,
    ) -> Dict[str, Any]:
        """
        Promote a connection to PRIMARY.

        Any other active PRIMARY belonging to this user
        is demoted to BACKUP first.
        """

        user_id = self._normalize_user_id(
            user_id
        )

        connection_id = self._normalize_connection_id(
            connection_id
        )

        if not user_id:
            raise ValueError(
                "user_id is required"
            )

        if not connection_id:
            raise ValueError(
                "connection_id is required"
            )

        connection = self.repo.get_by_id(
            connection_id
        )

        if not connection:
            raise ValueError(
                "Google Drive connection not found"
            )

        connection_user_id = str(
            connection.get("user_id") or ""
        ).strip()

        if connection_user_id != user_id:
            raise PermissionError(
                "Google Drive connection does not "
                "belong to this user"
            )

        self._demote_existing_primaries(
            user_id,
            except_connection_id=connection_id,
        )

        updated = self.repo.set_primary(
            connection_id
        )

        if not updated:
            raise RuntimeError(
                "Failed to promote Drive connection"
            )

        return self._safe_connection(updated)

    def _ensure_primary(
        self,
        user_id: str,
        connection_id: str,
    ) -> None:
        """
        Ensure only this connection is PRIMARY.
        """

        self._demote_existing_primaries(
            user_id,
            except_connection_id=connection_id,
        )

        updated = self.repo.set_primary(
            connection_id
        )

        if not updated:
            raise RuntimeError(
                "Failed to enforce PRIMARY connection"
            )

    def _demote_existing_primaries(
        self,
        user_id: str,
        except_connection_id: Optional[str] = None,
    ) -> None:
        """
        Demote all other active PRIMARY connections.

        This method only operates on connections belonging
        to the supplied user.
        """

        user_id = self._normalize_user_id(
            user_id
        )

        except_connection_id = (
            self._normalize_connection_id(
                except_connection_id
            )
            if except_connection_id
            else None
        )

        rows = self.repo.list_by_user(
            user_id,
            active_only=True,
        )

        for row in rows:
            connection_id = self._get_connection_id(
                row
            )

            if not connection_id:
                continue

            if (
                except_connection_id
                and connection_id == except_connection_id
            ):
                continue

            role = str(
                row.get("connection_role") or ""
            ).strip().upper()

            is_primary = bool(
                row.get("is_primary")
            )

            if not is_primary and role != "PRIMARY":
                continue

            updated = self.repo.set_backup(
                connection_id
            )

            if not updated:
                raise RuntimeError(
                    "Failed to demote PRIMARY Drive "
                    f"connection {connection_id}"
                )

    # ================================================================
    # BACKUP MANAGEMENT
    # ================================================================

    def make_backup(
        self,
        user_id: str,
        connection_id: str,
    ) -> Dict[str, Any]:
        """
        Demote a connection to BACKUP.
        """

        user_id = self._normalize_user_id(
            user_id
        )

        connection_id = self._normalize_connection_id(
            connection_id
        )

        if not user_id:
            raise ValueError(
                "user_id is required"
            )

        if not connection_id:
            raise ValueError(
                "connection_id is required"
            )

        connection = self.repo.get_by_id(
            connection_id
        )

        if not connection:
            raise ValueError(
                "Google Drive connection not found"
            )

        if str(
            connection.get("user_id") or ""
        ).strip() != user_id:
            raise PermissionError(
                "Google Drive connection does not "
                "belong to this user"
            )

        updated = self.repo.set_backup(
            connection_id
        )

        if not updated:
            raise RuntimeError(
                "Failed to set Drive connection as BACKUP"
            )

        return self._safe_connection(updated)

    # ================================================================
    # CONNECTION LIFECYCLE
    # ================================================================

    def deactivate(
        self,
        user_id: str,
        connection_id: str,
    ) -> Dict[str, Any]:
        """Deactivate a connection."""

        user_id = self._normalize_user_id(
            user_id
        )

        connection_id = self._normalize_connection_id(
            connection_id
        )

        if not user_id:
            raise ValueError(
                "user_id is required"
            )

        if not connection_id:
            raise ValueError(
                "connection_id is required"
            )

        connection = self.repo.get_by_id(
            connection_id
        )

        if not connection:
            raise ValueError(
                "Google Drive connection not found"
            )

        if str(
            connection.get("user_id") or ""
        ).strip() != user_id:
            raise PermissionError(
                "Google Drive connection does not "
                "belong to this user"
            )

        updated = self.repo.deactivate(
            connection_id
        )

        if not updated:
            raise RuntimeError(
                "Failed to deactivate Drive connection"
            )

        return self._safe_connection(updated)

    def activate(
        self,
        user_id: str,
        connection_id: str,
    ) -> Dict[str, Any]:
        """
        Reactivate a connection.

        Activation does not change PRIMARY/BACKUP status.
        If the caller wants to promote the connection to PRIMARY,
        use make_primary().
        """

        user_id = self._normalize_user_id(
            user_id
        )

        connection_id = self._normalize_connection_id(
            connection_id
        )

        if not user_id:
            raise ValueError(
                "user_id is required"
            )

        if not connection_id:
            raise ValueError(
                "connection_id is required"
            )

        connection = self.repo.get_by_id(
            connection_id
        )

        if not connection:
            raise ValueError(
                "Google Drive connection not found"
            )

        if str(
            connection.get("user_id") or ""
        ).strip() != user_id:
            raise PermissionError(
                "Google Drive connection does not "
                "belong to this user"
            )

        updated = self.repo.activate(
            connection_id
        )

        if not updated:
            raise RuntimeError(
                "Failed to activate Drive connection"
            )

        return self._safe_connection(updated)

    # ================================================================
    # TOKEN MANAGEMENT
    # ================================================================

    def get_decrypted_refresh_token(
        self,
        user_id: str,
        connection_id: str,
    ) -> str:
        """
        Return a decrypted refresh token for internal server use.

        This method must never be called from Reflex UI state or
        returned to the browser.
        """

        user_id = self._normalize_user_id(
            user_id
        )

        connection_id = self._normalize_connection_id(
            connection_id
        )

        if not user_id:
            raise ValueError(
                "user_id is required"
            )

        if not connection_id:
            raise ValueError(
                "connection_id is required"
            )

        connection = self.repo.get_by_id(
            connection_id
        )

        if not connection:
            raise ValueError(
                "Google Drive connection not found"
            )

        if str(
            connection.get("user_id") or ""
        ).strip() != user_id:
            raise PermissionError(
                "Google Drive connection does not "
                "belong to this user"
            )

        encrypted = str(
            connection.get(
                "encrypted_refresh_token"
            )
            or ""
        ).strip()

        if not encrypted:
            raise RuntimeError(
                "This Drive connection has no OAuth "
                "refresh token."
            )

        return decrypt_refresh_token(
            encrypted
        )

    # ================================================================
    # VERIFICATION
    # ================================================================

    def verify_connection(
        self,
        user_id: str,
        connection_id: str,
    ) -> Dict[str, Any]:
        """
        Verify a connection against Google Drive.

        This performs an authenticated Drive API request.

        The result contains only safe metadata.
        """

        user_id = self._normalize_user_id(
            user_id
        )

        connection_id = self._normalize_connection_id(
            connection_id
        )

        if not user_id:
            raise ValueError(
                "user_id is required"
            )

        if not connection_id:
            raise ValueError(
                "connection_id is required"
            )

        connection = self.repo.get_by_id(
            connection_id
        )

        if not connection:
            raise ValueError(
                "Google Drive connection not found"
            )

        if str(
            connection.get("user_id") or ""
        ).strip() != user_id:
            raise PermissionError(
                "Google Drive connection does not "
                "belong to this user"
            )

        try:
            refresh_token = (
                self.get_decrypted_refresh_token(
                    user_id,
                    connection_id,
                )
            )

            account = self._verify_with_drive(
                refresh_token
            )

            self.repo.mark_verified(
                connection_id
            )

            # mark_verified() may return an updated record.
            # Use it when available, otherwise retain the
            # original connection.
            verified = self.repo.get_by_id(
                connection_id
            )

            result = self._safe_connection(
                verified or connection
            )

            result["verified"] = True

            result["google_account"] = {
                "email": account.get(
                    "emailAddress"
                ),
                "display_name": account.get(
                    "displayName"
                ),
            }

            return result

        except Exception as exc:
            logger.exception(
                "Google Drive verification failed "
                "for connection %s",
                connection_id,
            )

            self.repo.mark_error(
                connection_id,
                str(exc),
            )

            raise

    def _verify_with_drive(
        self,
        refresh_token: str,
    ) -> Dict[str, Any]:
        """Perform an authenticated Google Drive API request."""

        from google.oauth2.credentials import Credentials
        from google.auth.transport.requests import Request
        from googleapiclient.discovery import build

        credentials = Credentials(
            token=None,
            refresh_token=refresh_token,
            token_uri="https://oauth2.googleapis.com/token",
            client_id=settings.google_client_id,
            client_secret=settings.google_client_secret,
            scopes=[
                "https://www.googleapis.com/auth/drive"
            ],
        )

        if credentials.expired or not credentials.valid:
            credentials.refresh(Request())

        drive = build(
            "drive",
            "v3",
            credentials=credentials,
            cache_discovery=False,
        )

        response = (
            drive.about()
            .get(
                fields=(
                    "user("
                    "displayName,"
                    "emailAddress,"
                    "permissionId"
                    ")"
                )
            )
            .execute()
        )

        return response.get(
            "user",
            {},
        )

    # ================================================================
    # TOKEN SYNCHRONIZATION
    # ================================================================

    def sync_existing_primary(
        self,
        user_id: str,
        google_email: str,
        encrypted_refresh_token: str,
        root_folder_id: str = "",
    ) -> Dict[str, Any]:
        """
        Synchronize the existing
        users.google_refresh_token_enc primary token
        into the connection table.

        This is intended for the current EventLah OAuth account.
        """

        return self.register_connection(
            user_id=user_id,
            google_email=google_email,
            encrypted_refresh_token=(
                encrypted_refresh_token
            ),
            root_folder_id=root_folder_id,
            connection_role="PRIMARY",
            make_primary=True,
        )

    # ================================================================
    # SAFE OUTPUT
    # ================================================================

    @staticmethod
    def _get_connection_id(
        connection: Dict[str, Any],
    ) -> str:
        """
        Get the canonical connection ID.

        Production records use `id`.

        `connection_id` is accepted as a compatibility fallback
        for repository/test-double records.
        """

        return str(
            connection.get("id")
            or connection.get("connection_id")
            or ""
        ).strip()

    @classmethod
    def _safe_connection(
        cls,
        connection: Dict[str, Any],
    ) -> Dict[str, Any]:
        """
        Remove all OAuth secrets from service output.

        This is intentionally defensive.
        """

        safe = dict(connection)

        # Normalize the public identifier.
        #
        # Production repository records already use `id`.
        # If a test/internal repository supplies `connection_id`,
        # expose it consistently as `id`.
        connection_id = cls._get_connection_id(
            safe
        )

        if connection_id and not safe.get("id"):
            safe["id"] = connection_id

        # Do not expose an internal alternate identifier.
        safe.pop(
            "connection_id",
            None,
        )

        # Never expose encrypted OAuth tokens.
        safe.pop(
            "encrypted_refresh_token",
            None,
        )

        # Never expose a plaintext OAuth token.
        safe.pop(
            "refresh_token",
            None,
        )

        return safe