"""Authentication service using Supabase Auth."""

from __future__ import annotations

import logging
from typing import Any, Optional

from guest_management.repositories.auth_repository import AuthRepository

logger = logging.getLogger(__name__)


class AuthService:
    """Application service for authentication.

    Supabase Auth is responsible for authentication and token issuance.
    EventLah's public.users profile is responsible for application-level
    authorization and account status.
    """

    def __init__(
        self,
        repo: AuthRepository | None = None,
    ):
        self.repo = repo or AuthRepository()

    # ------------------------------------------------------------------
    # Supabase authentication
    # ------------------------------------------------------------------

    def login(
        self,
        email: str,
        password: str,
    ) -> dict[str, Any]:
        """Authenticate an EventLah user using Supabase Auth.

        Returns:

            {
                "user": EventLah user profile,
                "access_token": Supabase access token,
                "refresh_token": Supabase refresh token,
            }

        Authentication is performed by Supabase Auth. The EventLah
        profile is then checked for application authorization.
        """
        email = email.strip().lower()

        if not email:
            raise ValueError("Email is required.")

        if not password:
            raise ValueError("Password is required.")

        logger.info(
            "EventLah authentication attempt for %s",
            email,
        )

        result = self.repo.sign_in_with_password(
            email=email,
            password=password,
        )

        user = result.get("user")

        if not user:
            raise RuntimeError(
                "Authentication succeeded but no EventLah user "
                "profile was returned."
            )

        logger.info(
            "EventLah authentication successful for user %s",
            user.get("id"),
        )

        return {
            "user": user,
            "access_token": result["access_token"],
            "refresh_token": result.get("refresh_token", ""),
        }

    def get_current_user(
        self,
        access_token: str | None,
    ) -> Optional[dict[str, Any]]:
        """Validate a Supabase access token and return the EventLah user."""
        if not access_token:
            return None

        return self.repo.get_user_by_access_token(
            access_token
        )

    def logout(
            self,
            access_token: str | None,
            refresh_token: str | None,
    ) -> None:
        """Sign out the current Supabase Auth session."""
        if not access_token or not refresh_token:
            logger.info(
                "EventLah logout requested without a complete session."
            )
            return

        self.repo.sign_out(
            access_token=access_token,
            refresh_token=refresh_token,
        )

        logger.info(
            "EventLah Supabase authentication logout completed."
        )

    def refresh_session(
            self,
            refresh_token: str | None,
    ) -> dict | None:
        """Refresh the current Supabase authentication session."""

        if not refresh_token:
            return None

        return self.repo.refresh_session(
            refresh_token=refresh_token,
        )

    # ------------------------------------------------------------------
    # Authorization helpers
    # ------------------------------------------------------------------

    @staticmethod
    def can_manage_events(
        user: dict[str, Any] | None,
    ) -> bool:
        """Return whether the user may manage EventLah events."""
        if not user:
            return False

        if not user.get("is_active", False):
            return False

        role = str(
            user.get("role") or ""
        ).strip().upper()

        return role in {
            "OWNER",
            "ADMIN",
        }

    @staticmethod
    def is_owner(
        user: dict[str, Any] | None,
    ) -> bool:
        """Return whether the user has OWNER privileges."""
        if not user:
            return False

        if not user.get("is_active", False):
            return False

        return (
            str(user.get("role") or "")
            .strip()
            .upper()
            == "OWNER"
        )

    @staticmethod
    def is_admin(
        user: dict[str, Any] | None,
    ) -> bool:
        """Return whether the user has ADMIN privileges."""
        if not user:
            return False

        if not user.get("is_active", False):
            return False

        return (
            str(user.get("role") or "")
            .strip()
            .upper()
            == "ADMIN"
        )