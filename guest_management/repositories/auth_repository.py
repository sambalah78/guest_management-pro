"""Authentication repository.

Authentication repository backed by Supabase Auth.

This repository handles:
- Supabase email/password authentication
- Supabase access/refresh sessions
- EventLah user profile lookup
- Supabase session sign-out
"""

from __future__ import annotations

import hashlib
import secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional

from supabase import Client, create_client

from guest_management.core.config import settings
from guest_management.database import get_db


class AuthRepository:
    """Repository for authentication and application user profiles."""

    # ------------------------------------------------------------------
    # Supabase client
    # ------------------------------------------------------------------

    @staticmethod
    def _get_supabase_client() -> Client:
        """Create a Supabase client using the public/anon key.

        This client is used for user authentication operations.

        It must never be replaced with the service-role client for
        browser/user authentication.
        """
        if not settings.supabase_url:
            raise RuntimeError(
                "SUPABASE_URL is not configured."
            )

        if not settings.supabase_anon_key:
            raise RuntimeError(
                "SUPABASE_ANON_KEY is not configured."
            )

        return create_client(
            settings.supabase_url,
            settings.supabase_anon_key,
        )

    @staticmethod
    def _get_supabase_server_client() -> Client:
        """Create a privileged Supabase client for backend operations.

        The service-role key is server-only and must never be exposed
        to the browser.
        """
        if not settings.supabase_url:
            raise RuntimeError(
                "SUPABASE_URL is not configured."
            )

        if not settings.supabase_secret_key:
            raise RuntimeError(
                "SUPABASE_SECRET_KEY is not configured."
            )

        return create_client(
            settings.supabase_url,
            settings.supabase_secret_key,
        )
    # ------------------------------------------------------------------
    # Supabase Auth
    # ------------------------------------------------------------------

    def sign_in_with_password(
        self,
        email: str,
        password: str,
    ) -> dict[str, Any]:
        """Authenticate an existing user through Supabase Auth.

        Returns a normalized dictionary containing:

            {
                "access_token": "...",
                "refresh_token": "...",
                "user": {...},
            }

        The access token is subsequently used to validate the
        authenticated user on the server.
        """
        email = email.strip().lower()

        if not email:
            raise ValueError("Email is required.")

        if not password:
            raise ValueError("Password is required.")

        client = self._get_supabase_client()

        response = client.auth.sign_in_with_password(
            {
                "email": email,
                "password": password,
            }
        )

        session = getattr(response, "session", None)
        user = getattr(response, "user", None)

        if session is None:
            raise RuntimeError(
                "Supabase authentication succeeded without a session."
            )

        if user is None:
            raise RuntimeError(
                "Supabase authentication succeeded without a user."
            )

        access_token = getattr(session, "access_token", None)
        refresh_token = getattr(session, "refresh_token", None)

        if not access_token:
            raise RuntimeError(
                "Supabase authentication did not return an access token."
            )

        user_data = self._user_to_dict(user)

        profile = self.get_user(str(user_data["id"]))

        if not profile:
            raise PermissionError(
                "Authenticated Supabase user does not have an "
                "active EventLah user profile."
            )

        if not profile.get("is_active", False):
            raise PermissionError(
                "This EventLah account is inactive."
            )

        return {
            "access_token": access_token,
            "refresh_token": refresh_token or "",
            "user": profile,
        }

    def sign_out(
            self,
            access_token: str | None,
            refresh_token: str | None,
    ) -> None:
        """Sign out the current Supabase Auth session."""
        if not access_token or not refresh_token:
            return

        client = self._get_supabase_client()

        client.auth.set_session(
            access_token,
            refresh_token,
        )

        client.auth.sign_out({"scope": "local"})

    def refresh_session(
            self,
            refresh_token: str | None,
    ) -> dict[str, Any] | None:
        """Refresh a Supabase Auth session."""

        if not refresh_token:
            return None

        try:
            client = self._get_supabase_client()

            response = client.auth.refresh_session(
                refresh_token
            )

            session = getattr(response, "session", None)
            user = getattr(response, "user", None)

            if session is None or user is None:
                return None

            access_token = getattr(
                session,
                "access_token",
                None,
            )
            new_refresh_token = getattr(
                session,
                "refresh_token",
                None,
            )

            if not access_token:
                return None

            user_data = self._user_to_dict(user)
            user_id = str(
                user_data.get("id") or ""
            ).strip()

            if not user_id:
                return None

            profile = self.get_user(user_id)

            if not profile:
                return None

            if not profile.get("is_active", False):
                return None

            return {
                "access_token": access_token,
                "refresh_token": new_refresh_token or refresh_token,
                "user": profile,
            }

        except Exception:
            return None

    # ------------------------------------------------------------------
    # EventLah user profile
    # ------------------------------------------------------------------

    def get_user(
            self,
            user_id: str,
    ) -> Optional[dict[str, Any]]:
        """Return an EventLah user profile by Supabase UUID.

        This is a backend operation and therefore uses the Supabase
        service-role client. The service-role key is never sent to
        the browser.
        """
        if not user_id:
            return None

        response = (
            self._get_supabase_server_client()
            .table("users")
            .select(
                "id,email,name,picture_url,role,is_active,"
                "created_at,updated_at"
            )
            .eq("id", user_id)
            .limit(1)
            .execute()
        )

        rows = response.data or []

        if not rows:
            return None

        user = rows[0]

        user["email"] = str(
            user.get("email") or ""
        ).strip().lower()

        user["name"] = str(
            user.get("name") or user["email"]
        )

        user["picture"] = str(
            user.get("picture_url") or ""
        )

        user["role"] = str(
            user.get("role") or "ADMIN"
        ).upper()

        user["is_active"] = bool(
            user.get("is_active")
        )

        return user

    def get_user_by_access_token(
            self,
            access_token: str,
    ) -> Optional[dict[str, Any]]:
        """Validate a Supabase access token and return the EventLah profile."""
        if not access_token:
            return None

        try:
            client = self._get_supabase_client()
            response = client.auth.get_user(access_token)
            auth_user = getattr(response, "user", None)

            if auth_user is None:
                return None

            user_data = self._user_to_dict(auth_user)
            user_id = str(user_data.get("id") or "").strip()

            if not user_id:
                return None

            # Profile lookup uses the backend service-role client.
            return self.get_user(user_id)

        except Exception:
            return None

    @staticmethod
    def _user_to_dict(user: Any) -> dict[str, Any]:
        """Convert a Supabase Auth user object to a plain dictionary."""
        if isinstance(user, dict):
            return dict(user)

        result: dict[str, Any] = {}

        for field in (
            "id",
            "email",
            "phone",
            "role",
            "created_at",
            "updated_at",
            "user_metadata",
            "app_metadata",
        ):
            if hasattr(user, field):
                result[field] = getattr(user, field)

        return result

    # ------------------------------------------------------------------
    # EventLah user profile
    # ------------------------------------------------------------------




