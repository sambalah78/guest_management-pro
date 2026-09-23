"""Server-side authentication session service."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

from guest_management.core.config import settings
from guest_management.core.security import (
    create_session_id,
    decrypt_session_token,
    encrypt_session_token,
    hash_session_id,
)
from guest_management.repositories.auth_repository import AuthRepository
from guest_management.repositories.auth_session_repository import (
    AuthSessionRepository,
)


class AuthSessionService:
    """Application service for secure server-side authentication sessions."""

    def __init__(
        self,
        repository: Optional[AuthSessionRepository] = None,
        auth_repository: Optional[AuthRepository] = None,
    ) -> None:
        self.repository = repository or AuthSessionRepository()
        self.auth_repository = auth_repository or AuthRepository()

    @staticmethod
    def _now() -> datetime:
        """Return the current UTC datetime."""
        return datetime.now(timezone.utc)

    @staticmethod
    def _session_expiry() -> datetime:
        """Return the expiry timestamp for a newly created session."""
        return (
            datetime.now(timezone.utc)
            + timedelta(seconds=settings.session_ttl_seconds)
        )

    @staticmethod
    def _validate_session_id(session_id: str) -> str:
        """Validate and normalize a browser-provided session ID."""
        value = (session_id or "").strip()

        if not value:
            raise ValueError("session_id must not be empty")

        return value

    def create_session(
        self,
        *,
        user_id: str,
        access_token: str,
        refresh_token: str,
    ) -> str:
        """
        Create a new opaque server-side session.

        The raw session ID is returned to the caller so it can be
        placed in the browser cookie. Supabase tokens never leave
        the server-side session store.
        """
        user_id = str(user_id or "").strip()

        if not user_id:
            raise ValueError("user_id must not be empty")

        if not access_token:
            raise ValueError("access_token must not be empty")

        if not refresh_token:
            raise ValueError("refresh_token must not be empty")

        session_id = create_session_id()
        session_id_hash = hash_session_id(session_id)

        self.repository.create(
            session_id_hash=session_id_hash,
            user_id=user_id,
            access_token_ciphertext=encrypt_session_token(access_token),
            refresh_token_ciphertext=encrypt_session_token(refresh_token),
            expires_at=self._session_expiry(),
        )

        return session_id

    def get_session_metadata(
        self,
        session_id: str,
        *,
        touch: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """Retrieve active session metadata without decrypting tokens."""
        session_id = self._validate_session_id(session_id)
        session_id_hash = hash_session_id(session_id)

        session = self.repository.get_active_metadata(
            session_id_hash
        )

        if session is None:
            return None

        if touch:
            self.repository.touch(session_id_hash)

        return {
            "id": session["id"],
            "session_id_hash": session["session_id_hash"],
            "user_id": str(session["user_id"]),
            "created_at": session["created_at"],
            "expires_at": session["expires_at"],
            "last_used_at": session["last_used_at"],
            "revoked_at": session["revoked_at"],
        }

    def get_session(
        self,
        session_id: str,
        *,
        touch: bool = True,
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve an active session and decrypt its server-side tokens.

        Returns None when the session is missing, expired, revoked,
        or otherwise invalid.
        """
        session_id = self._validate_session_id(session_id)
        session_id_hash = hash_session_id(session_id)

        session = self.repository.get_active(session_id_hash)

        if session is None:
            return None

        try:
            access_token = decrypt_session_token(
                session["access_token_ciphertext"]
            )
            refresh_token = decrypt_session_token(
                session["refresh_token_ciphertext"]
            )
        except (KeyError, TypeError, ValueError):
            return None

        if touch:
            self.repository.touch(session_id_hash)

        return {
            "id": session["id"],
            "session_id_hash": session["session_id_hash"],
            "user_id": str(session["user_id"]),
            "access_token": access_token,
            "refresh_token": refresh_token,
            "created_at": session["created_at"],
            "expires_at": session["expires_at"],
            "last_used_at": session["last_used_at"],
            "revoked_at": session["revoked_at"],
        }

    def revoke_session(self, session_id: str) -> bool:
        """Revoke one browser authentication session."""
        session_id = self._validate_session_id(session_id)
        return self.repository.revoke(
            hash_session_id(session_id)
        )

    def revoke_all_for_user(self, user_id: str) -> int:
        """Revoke all active authentication sessions for a user."""
        user_id = str(user_id or "").strip()

        if not user_id:
            raise ValueError("user_id must not be empty")

        return self.repository.revoke_all_for_user(user_id)

    def refresh_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """
        Refresh the Supabase session associated with a browser session.

        New Supabase tokens replace the encrypted tokens currently
        stored for the session.
        """
        session_id = self._validate_session_id(session_id)
        session_id_hash = hash_session_id(session_id)

        session = self.repository.get_active(session_id_hash)

        if session is None:
            return None

        try:
            refresh_token = decrypt_session_token(
                session["refresh_token_ciphertext"]
            )
        except (KeyError, TypeError, ValueError):
            return None

        refreshed = self.auth_repository.refresh_session(refresh_token)

        if not refreshed:
            self.repository.revoke(session_id_hash)
            return None

        access_token = refreshed.get("access_token")
        new_refresh_token = refreshed.get("refresh_token")
        user = refreshed.get("user")

        if not access_token or not new_refresh_token or not user:
            self.repository.revoke(session_id_hash)
            return None

        expires_at = self._session_expiry()

        updated = self.repository.update_tokens(
            session_id_hash=session_id_hash,
            access_token_ciphertext=encrypt_session_token(access_token),
            refresh_token_ciphertext=encrypt_session_token(
                new_refresh_token
            ),
            expires_at=expires_at,
        )

        if not updated:
            return None

        return {
            "session_id": session_id,
            "user_id": str(user["id"]),
            "access_token": access_token,
            "refresh_token": new_refresh_token,
            "expires_at": expires_at,
            "user": user,
        }

    def cleanup_expired_sessions(self) -> int:
        """Delete expired/revoked sessions beyond the retention period."""
        return self.repository.delete_expired()
