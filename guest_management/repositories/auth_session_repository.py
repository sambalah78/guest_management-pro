"""Server-side authentication session repository."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from guest_management.core.exceptions import DatabaseError
from guest_management.database import engine


class AuthSessionRepository:
    """Persistence operations for server-side authentication sessions."""

    @staticmethod
    def _now() -> datetime:
        """Return the current UTC datetime."""
        return datetime.now(timezone.utc)

    @staticmethod
    def _row_to_dict(row: Any) -> Dict[str, Any]:
        """Convert a SQLAlchemy row into a normal dictionary."""
        if row is None:
            return {}

        try:
            return dict(row._mapping)
        except AttributeError:
            return dict(row)

    @staticmethod
    def _raise_db(operation: str, exc: Exception) -> None:
        """Convert database exceptions into the application exception."""
        raise DatabaseError(
            f"Authentication session operation failed: {operation}"
        ) from exc

    def create(
        self,
        *,
        session_id_hash: str,
        user_id: str,
        access_token_ciphertext: str,
        refresh_token_ciphertext: str,
        expires_at: datetime,
    ) -> Dict[str, Any]:
        """Create a new server-side authentication session."""
        session_id_hash = str(session_id_hash or "").strip()
        user_id = str(user_id or "").strip()
        access_token_ciphertext = str(
            access_token_ciphertext or ""
        ).strip()
        refresh_token_ciphertext = str(
            refresh_token_ciphertext or ""
        ).strip()

        if not session_id_hash:
            raise ValueError("Session ID hash is required.")

        if not user_id:
            raise ValueError("User ID is required.")

        if not access_token_ciphertext:
            raise ValueError("Access token ciphertext is required.")

        if not refresh_token_ciphertext:
            raise ValueError("Refresh token ciphertext is required.")

        if not isinstance(expires_at, datetime):
            raise ValueError("expires_at must be a datetime.")

        now = self._now()

        try:
            with engine.begin() as conn:
                result = conn.execute(
                    text(
                        """
                        INSERT INTO auth_sessions (
                            session_id_hash,
                            user_id,
                            access_token_ciphertext,
                            refresh_token_ciphertext,
                            created_at,
                            expires_at,
                            last_used_at,
                            revoked_at
                        )
                        VALUES (
                            :session_id_hash,
                            :user_id,
                            :access_token_ciphertext,
                            :refresh_token_ciphertext,
                            :created_at,
                            :expires_at,
                            :last_used_at,
                            NULL
                        )
                        RETURNING *
                        """
                    ),
                    {
                        "session_id_hash": session_id_hash,
                        "user_id": user_id,
                        "access_token_ciphertext": access_token_ciphertext,
                        "refresh_token_ciphertext": refresh_token_ciphertext,
                        "created_at": now,
                        "expires_at": expires_at,
                        "last_used_at": now,
                    },
                )

                row = result.mappings().first()

                if not row:
                    raise RuntimeError(
                        "Authentication session creation returned no data."
                    )

                return self._row_to_dict(row)

        except SQLAlchemyError as exc:
            self._raise_db("create session", exc)

        raise RuntimeError("Authentication session creation failed.")

    def get_active(
        self,
        session_id_hash: str,
    ) -> Optional[Dict[str, Any]]:
        """Return a non-revoked, non-expired session."""
        session_id_hash = str(session_id_hash or "").strip()

        if not session_id_hash:
            return None

        now = self._now()

        try:
            with engine.connect() as conn:
                row = conn.execute(
                    text(
                        """
                        SELECT
                            id,
                            session_id_hash,
                            user_id,
                            access_token_ciphertext,
                            refresh_token_ciphertext,
                            created_at,
                            expires_at,
                            last_used_at,
                            revoked_at
                        FROM auth_sessions
                        WHERE session_id_hash = :session_id_hash
                          AND revoked_at IS NULL
                          AND expires_at > :now
                        LIMIT 1
                        """
                    ),
                    {
                        "session_id_hash": session_id_hash,
                        "now": now,
                    },
                ).mappings().first()

                return self._row_to_dict(row) if row else None

        except SQLAlchemyError as exc:
            self._raise_db("get active session", exc)

        return None

    def touch(
        self,
        session_id_hash: str,
    ) -> bool:
        """Update the last-used timestamp for an active session."""
        session_id_hash = str(session_id_hash or "").strip()

        if not session_id_hash:
            return False

        now = self._now()

        try:
            with engine.begin() as conn:
                result = conn.execute(
                    text(
                        """
                        UPDATE auth_sessions
                        SET last_used_at = :last_used_at
                        WHERE session_id_hash = :session_id_hash
                          AND revoked_at IS NULL
                          AND expires_at > :now
                        """
                    ),
                    {
                        "session_id_hash": session_id_hash,
                        "last_used_at": now,
                        "now": now,
                    },
                )

                return bool(result.rowcount)

        except SQLAlchemyError as exc:
            self._raise_db("touch session", exc)

        return False

    def update_tokens(
        self,
        *,
        session_id_hash: str,
        access_token_ciphertext: str,
        refresh_token_ciphertext: str,
        expires_at: datetime,
    ) -> bool:
        """Replace encrypted authentication tokens for an active session."""
        session_id_hash = (session_id_hash or "").strip()
        if not session_id_hash:
            raise ValueError("session_id_hash must not be empty")

        if not access_token_ciphertext:
            raise ValueError("access_token_ciphertext must not be empty")

        if not refresh_token_ciphertext:
            raise ValueError("refresh_token_ciphertext must not be empty")

        if not isinstance(expires_at, datetime):
            raise TypeError("expires_at must be a datetime")

        now = self._now()

        try:
            with engine.begin() as conn:
                result = conn.execute(
                    text(
                        """
                        UPDATE auth_sessions
                        SET
                            access_token_ciphertext = :access_token_ciphertext,
                            refresh_token_ciphertext = :refresh_token_ciphertext,
                            expires_at = :expires_at,
                            last_used_at = :last_used_at
                        WHERE session_id_hash = :session_id_hash
                          AND revoked_at IS NULL
                          AND expires_at > :now
                        """
                    ),
                    {
                        "session_id_hash": session_id_hash,
                        "access_token_ciphertext": access_token_ciphertext,
                        "refresh_token_ciphertext": refresh_token_ciphertext,
                        "expires_at": expires_at,
                        "last_used_at": now,
                        "now": now,
                    },
                )

            return result.rowcount == 1

        except SQLAlchemyError as exc:
            self._raise_db("update authentication session tokens", exc)

    def revoke(
        self,
        session_id_hash: str,
    ) -> bool:
        """Revoke one authentication session."""
        session_id_hash = str(session_id_hash or "").strip()

        if not session_id_hash:
            return False

        now = self._now()

        try:
            with engine.begin() as conn:
                result = conn.execute(
                    text(
                        """
                        UPDATE auth_sessions
                        SET revoked_at = :revoked_at
                        WHERE session_id_hash = :session_id_hash
                          AND revoked_at IS NULL
                        """
                    ),
                    {
                        "session_id_hash": session_id_hash,
                        "revoked_at": now,
                    },
                )

                return bool(result.rowcount)

        except SQLAlchemyError as exc:
            self._raise_db("revoke session", exc)

        return False

    def revoke_all_for_user(
        self,
        user_id: str,
    ) -> int:
        """Revoke all active authentication sessions for a user."""
        user_id = str(user_id or "").strip()

        if not user_id:
            return 0

        now = self._now()

        try:
            with engine.begin() as conn:
                result = conn.execute(
                    text(
                        """
                        UPDATE auth_sessions
                        SET revoked_at = :revoked_at
                        WHERE user_id = :user_id
                          AND revoked_at IS NULL
                        """
                    ),
                    {
                        "user_id": user_id,
                        "revoked_at": now,
                    },
                )

                return int(result.rowcount or 0)

        except SQLAlchemyError as exc:
            self._raise_db("revoke all user sessions", exc)

        return 0

    def delete_expired(
        self,
        *,
        older_than_days: int = 30,
    ) -> int:
        """Delete expired or revoked sessions older than the retention period."""
        older_than_days = max(1, int(older_than_days))
        cutoff = self._now() - timedelta(days=older_than_days)

        try:
            with engine.begin() as conn:
                result = conn.execute(
                    text(
                        """
                        DELETE FROM auth_sessions
                        WHERE (
                            expires_at < :cutoff
                            OR revoked_at < :cutoff
                        )
                        """
                    ),
                    {"cutoff": cutoff},
                )

                return int(result.rowcount or 0)

        except SQLAlchemyError as exc:
            self._raise_db("delete expired sessions", exc)

        return 0

    def count_active_for_user(
        self,
        user_id: str,
    ) -> int:
        """Return the number of active sessions for a user."""
        user_id = str(user_id or "").strip()

        if not user_id:
            return 0

        now = self._now()

        try:
            with engine.connect() as conn:
                result = conn.execute(
                    text(
                        """
                        SELECT COUNT(*)
                        FROM auth_sessions
                        WHERE user_id = :user_id
                          AND revoked_at IS NULL
                          AND expires_at > :now
                        """
                    ),
                    {
                        "user_id": user_id,
                        "now": now,
                    },
                )

                return int(result.scalar() or 0)

        except SQLAlchemyError as exc:
            self._raise_db("count active user sessions", exc)

        return 0
    def get_active_metadata(
        self,
        session_id_hash: str,
    ) -> Optional[Dict[str, Any]]:
        """Return active session metadata without decrypting credentials."""
        session_id_hash = str(session_id_hash or "").strip()

        if not session_id_hash:
            return None

        now = self._now()

        try:
            with engine.connect() as conn:
                row = conn.execute(
                    text(
                        """
                        SELECT
                            id,
                            session_id_hash,
                            user_id,
                            created_at,
                            expires_at,
                            last_used_at,
                            revoked_at
                        FROM auth_sessions
                        WHERE session_id_hash = :session_id_hash
                          AND revoked_at IS NULL
                          AND expires_at > :now
                        LIMIT 1
                        """
                    ),
                    {
                        "session_id_hash": session_id_hash,
                        "now": now,
                    },
                ).mappings().first()

                return self._row_to_dict(row) if row else None

        except SQLAlchemyError as exc:
            self._raise_db(
                "get active session metadata",
                exc,
            )

        return None
    def get_active_metadata(
        self,
        session_id_hash: str,
    ) -> Optional[Dict[str, Any]]:
        """Return active session metadata without decrypting credentials."""
        session_id_hash = str(session_id_hash or "").strip()

        if not session_id_hash:
            return None

        now = self._now()

        try:
            with engine.connect() as conn:
                row = conn.execute(
                    text(
                        """
                        SELECT
                            id,
                            session_id_hash,
                            user_id,
                            created_at,
                            expires_at,
                            last_used_at,
                            revoked_at
                        FROM auth_sessions
                        WHERE session_id_hash = :session_id_hash
                          AND revoked_at IS NULL
                          AND expires_at > :now
                        LIMIT 1
                        """
                    ),
                    {
                        "session_id_hash": session_id_hash,
                        "now": now,
                    },
                ).mappings().first()

                return self._row_to_dict(row) if row else None

        except SQLAlchemyError as exc:
            self._raise_db(
                "get active session metadata",
                exc,
            )

        return None
