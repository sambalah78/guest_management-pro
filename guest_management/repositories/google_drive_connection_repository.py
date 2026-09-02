"""
Google Drive connection repository.

This repository is responsible only for persistence of Google Drive
connection records.

Business rules such as:
    - which account is PRIMARY
    - which account is BACKUP
    - OAuth authorization
    - Drive API verification
    - failover

belong in GoogleDriveConnectionService, not here.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from guest_management.database_client import get_db


logger = logging.getLogger(__name__)


class GoogleDriveConnectionRepository:
    """Persistence layer for Google Drive account connections."""

    TABLE = "google_drive_connections"

    def __init__(self, db=None):
        self.db = db or get_db()

    # ================================================================
    # READ
    # ================================================================

    def get_by_id(
        self,
        connection_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Return one connection by its ID."""

        connection_id = str(connection_id or "").strip()

        if not connection_id:
            return None

        try:
            response = (
                self.db
                .table(self.TABLE)
                .select("*")
                .eq("id", connection_id)
                .limit(1)
                .execute()
            )

            rows = response.data or []

            return rows[0] if rows else None

        except Exception:
            logger.exception(
                "Failed to get Google Drive connection %s",
                connection_id,
            )
            raise

    def get_by_user_and_email(
        self,
        user_id: str,
        google_email: str,
    ) -> Optional[Dict[str, Any]]:
        """Return a user's Drive connection for a Google email."""

        user_id = str(user_id or "").strip()
        google_email = str(google_email or "").strip().lower()

        if not user_id or not google_email:
            return None

        try:
            response = (
                self.db
                .table(self.TABLE)
                .select("*")
                .eq("user_id", user_id)
                .eq("google_email", google_email)
                .limit(1)
                .execute()
            )

            rows = response.data or []

            return rows[0] if rows else None

        except Exception:
            logger.exception(
                "Failed to get Drive connection "
                "user=%s email=%s",
                user_id,
                google_email,
            )
            raise

    def list_by_user(
        self,
        user_id: str,
        *,
        active_only: bool = False,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Return Drive connections belonging to a user."""

        user_id = str(user_id or "").strip()

        if not user_id:
            return []

        limit = min(max(int(limit), 1), 500)

        try:
            query = (
                self.db
                .table(self.TABLE)
                .select("*")
                .eq("user_id", user_id)
            )

            if active_only:
                query = query.eq("is_active", True)

            response = (
                query
                .order("is_primary", desc=True)
                .order("created_at", desc=False)
                .limit(limit)
                .execute()
            )

            return response.data or []

        except Exception:
            logger.exception(
                "Failed to list Drive connections "
                "for user=%s",
                user_id,
            )
            raise

    def get_primary(
        self,
        user_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Return the active PRIMARY Drive connection."""

        user_id = str(user_id or "").strip()

        if not user_id:
            return None

        try:
            response = (
                self.db
                .table(self.TABLE)
                .select("*")
                .eq("user_id", user_id)
                .eq("is_primary", True)
                .eq("is_active", True)
                .limit(1)
                .execute()
            )

            rows = response.data or []

            return rows[0] if rows else None

        except Exception:
            logger.exception(
                "Failed to get PRIMARY Drive connection "
                "for user=%s",
                user_id,
            )
            raise

    def get_backup_connections(
        self,
        user_id: str,
    ) -> List[Dict[str, Any]]:
        """Return active non-primary Drive connections."""

        user_id = str(user_id or "").strip()

        if not user_id:
            return []

        try:
            response = (
                self.db
                .table(self.TABLE)
                .select("*")
                .eq("user_id", user_id)
                .eq("is_primary", False)
                .eq("is_active", True)
                .order("created_at", desc=False)
                .execute()
            )

            return response.data or []

        except Exception:
            logger.exception(
                "Failed to get BACKUP Drive connections "
                "for user=%s",
                user_id,
            )
            raise

    # ================================================================
    # CREATE
    # ================================================================

    def create(
        self,
        *,
        connection_id: str,
        user_id: str,
        google_email: str,
        encrypted_refresh_token: Optional[str] = None,
        root_folder_id: str = "",
        connection_role: str = "BACKUP",
        is_primary: bool = False,
        is_active: bool = True,
    ) -> Dict[str, Any]:
        """Create a Google Drive connection record."""

        connection_id = str(connection_id or "").strip()
        user_id = str(user_id or "").strip()
        google_email = str(google_email or "").strip().lower()
        root_folder_id = str(root_folder_id or "").strip()
        connection_role = (
            str(connection_role or "BACKUP").strip().upper()
        )

        if not connection_id:
            raise ValueError(
                "connection_id is required"
            )

        if not user_id:
            raise ValueError(
                "user_id is required"
            )

        if not google_email:
            raise ValueError(
                "google_email is required"
            )

        if connection_role not in {"PRIMARY", "BACKUP"}:
            raise ValueError(
                "connection_role must be PRIMARY or BACKUP"
            )

        now = datetime.now(timezone.utc)

        payload = {
            "id": connection_id,
            "user_id": user_id,
            "google_email": google_email,
            "encrypted_refresh_token": (
                encrypted_refresh_token
                if encrypted_refresh_token
                else None
            ),
            "root_folder_id": root_folder_id,
            "connection_role": connection_role,
            "is_primary": bool(is_primary),
            "is_active": bool(is_active),
            "created_at": now,
            "updated_at": now,
        }

        try:
            response = (
                self.db
                .table(self.TABLE)
                .insert(payload)
                .execute()
            )

            rows = response.data or []

            if not rows:
                raise RuntimeError(
                    "Google Drive connection creation "
                    "returned no record"
                )

            return rows[0]

        except Exception:
            logger.exception(
                "Failed to create Drive connection "
                "user=%s email=%s",
                user_id,
                google_email,
            )
            raise

    # ================================================================
    # UPDATE
    # ================================================================

    def update(
        self,
        connection_id: str,
        updates: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Update a Drive connection."""

        connection_id = str(connection_id or "").strip()

        if not connection_id:
            raise ValueError(
                "connection_id is required"
            )

        if not updates:
            return self.get_by_id(connection_id)

        payload = dict(updates)

        # Never allow callers to accidentally change the identity
        # of a connection through a generic update operation.
        payload.pop("id", None)
        payload.pop("user_id", None)

        if "google_email" in payload:
            payload["google_email"] = (
                str(payload["google_email"] or "")
                .strip()
                .lower()
            )

        if "connection_role" in payload:
            role = (
                str(payload["connection_role"] or "")
                .strip()
                .upper()
            )

            if role not in {"PRIMARY", "BACKUP"}:
                raise ValueError(
                    "connection_role must be PRIMARY or BACKUP"
                )

            payload["connection_role"] = role

        payload["updated_at"] = datetime.now(timezone.utc)

        try:
            response = (
                self.db
                .table(self.TABLE)
                .update(payload)
                .eq("id", connection_id)
                .execute()
            )

            rows = response.data or []

            return rows[0] if rows else None

        except Exception:
            logger.exception(
                "Failed to update Drive connection %s",
                connection_id,
            )
            raise

    def update_refresh_token(
        self,
        connection_id: str,
        encrypted_refresh_token: str,
    ) -> Optional[Dict[str, Any]]:
        """Replace the encrypted OAuth refresh token."""

        encrypted_refresh_token = str(
            encrypted_refresh_token or ""
        ).strip()

        if not encrypted_refresh_token:
            raise ValueError(
                "encrypted_refresh_token is required"
            )

        return self.update(
            connection_id,
            {
                "encrypted_refresh_token":
                    encrypted_refresh_token,
            },
        )

    def update_root_folder(
        self,
        connection_id: str,
        root_folder_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Update the Drive root folder."""

        root_folder_id = str(
            root_folder_id or ""
        ).strip()

        return self.update(
            connection_id,
            {
                "root_folder_id": root_folder_id,
            },
        )

    def mark_verified(
        self,
        connection_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Mark a Drive connection as successfully verified."""

        return self.update(
            connection_id,
            {
                "last_verified_at":
                    datetime.now(timezone.utc),
                "last_error": None,
            },
        )

    def mark_error(
        self,
        connection_id: str,
        error_message: str,
    ) -> Optional[Dict[str, Any]]:
        """Record the latest Drive verification error."""

        error_message = str(
            error_message or ""
        ).strip()

        return self.update(
            connection_id,
            {
                "last_error": error_message,
            },
        )

    # ================================================================
    # PRIMARY / BACKUP FLAGS
    # ================================================================

    def set_primary(
        self,
        connection_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Mark a connection as PRIMARY.

        This method intentionally does not demote other connections.
        That orchestration belongs to the service layer.
        """

        return self.update(
            connection_id,
            {
                "connection_role": "PRIMARY",
                "is_primary": True,
                "is_active": True,
            },
        )

    def set_backup(
        self,
        connection_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Mark a connection as BACKUP."""

        return self.update(
            connection_id,
            {
                "connection_role": "BACKUP",
                "is_primary": False,
            },
        )

    def deactivate(
        self,
        connection_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Deactivate a Drive connection."""

        return self.update(
            connection_id,
            {
                "is_active": False,
                "is_primary": False,
            },
        )

    def activate(
        self,
        connection_id: str,
    ) -> Optional[Dict[str, Any]]:
        """Activate a Drive connection."""

        return self.update(
            connection_id,
            {
                "is_active": True,
            },
        )

    # ================================================================
    # DELETE
    # ================================================================

    def delete(
        self,
        connection_id: str,
    ) -> bool:
        """Delete a Drive connection."""

        connection_id = str(connection_id or "").strip()

        if not connection_id:
            return False

        try:
            response = (
                self.db
                .table(self.TABLE)
                .delete()
                .eq("id", connection_id)
                .execute()
            )

            return bool(response.data)

        except Exception:
            logger.exception(
                "Failed to delete Drive connection %s",
                connection_id,
            )
            raise