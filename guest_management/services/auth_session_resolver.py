from __future__ import annotations

import logging
from typing import Any

from guest_management.core.request_context import get_session_id
from guest_management.repositories.auth_repository import AuthRepository
from guest_management.services.auth_session_service import AuthSessionService


logger = logging.getLogger(__name__)


class AuthSessionResolutionError(RuntimeError):
    """Raised when authentication cannot be resolved because of an infrastructure error."""


class AuthSessionResolver:
    """Resolve the currently authenticated EventLah administrator.

    The resolver is request-scoped in behavior but stateless in storage.

    Returns None only when there is no valid authenticated session.
    Infrastructure or unexpected failures are raised as
    AuthSessionResolutionError so they are not silently treated as
    unauthenticated requests.
    """

    def __init__(
        self,
        session_service: AuthSessionService | None = None,
        auth_repository: AuthRepository | None = None,
    ) -> None:
        self.auth_repository = auth_repository or AuthRepository()
        self.session_service = (
            session_service
            or AuthSessionService(
                auth_repository=self.auth_repository,
            )
        )

    def get_current_user(self) -> dict[str, Any] | None:
        session_id = get_session_id()

        if not session_id:
            return None

        try:
            session = self.session_service.get_session_metadata(
                session_id
            )

            # No active, valid, non-expired session.
            if not session:
                return None

            user_id = session.get("user_id")

            if not user_id:
                logger.warning(
                    "Authenticated session is missing user_id."
                )
                return None

            user = self.auth_repository.get_user(str(user_id))

            if not user:
                return None

            if not bool(user.get("is_active", False)):
                return None

            return user

        except AuthSessionResolutionError:
            raise

        except Exception as exc:
            logger.exception(
                "Failed to resolve authenticated EventLah session."
            )
            raise AuthSessionResolutionError(
                "Unable to resolve authenticated session."
            ) from exc

    def require_current_user(self) -> dict[str, Any]:
        user = self.get_current_user()

        if user is None:
            raise PermissionError("Authentication required.")

        return user
