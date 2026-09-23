"""HTTP authentication API for EventLah."""

from __future__ import annotations

import logging
from typing import Any
from urllib.parse import urlsplit

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from guest_management.core.config import settings
from guest_management.repositories.auth_repository import AuthRepository
from guest_management.services.auth_session_service import (
    AuthSessionService,
)


logger = logging.getLogger(__name__)

api = FastAPI(title="EventLah Auth API")

# Browser authentication requests originate from the Reflex frontend.
# Allow only the configured application origin in production, while also
# allowing the local 127.0.0.1 equivalent during development.
if settings.is_production:
    _auth_cors_origins = [settings.app_url]
else:
    _auth_cors_origins = [
        settings.app_url,
        "http://localhost:3000",
        "http://127.0.0.1:3000",
    ]

_auth_cors_origins = list(dict.fromkeys(
    origin.rstrip("/")
    for origin in _auth_cors_origins
    if origin
))

api.add_middleware(
    CORSMiddleware,
    allow_origins=_auth_cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type", "Accept", "Origin"],
)


SESSION_COOKIE_NAME = "eventlah_session"

# Keep the browser session cookie deliberately opaque.
SESSION_COOKIE_PATH = "/"
SESSION_COOKIE_SAMESITE = "lax"

# Production must use HTTPS.
SESSION_COOKIE_SECURE = settings.is_production


def _validate_request_origin(request: Request) -> None:
    """Reject cross-origin state-changing authentication requests."""
    origin = request.headers.get("origin")

    # Some legitimate clients and server-side calls do not send Origin.
    if not origin:
        return

    try:
        configured = urlsplit(settings.app_url)
        received = urlsplit(origin)
    except ValueError:
        raise HTTPException(
            status_code=403,
            detail="Invalid request origin.",
        )

    if (
        not configured.scheme
        or not configured.netloc
        or not received.scheme
        or not received.netloc
        or configured.scheme.lower() != received.scheme.lower()
        or configured.netloc.lower() != received.netloc.lower()
    ):
        raise HTTPException(
            status_code=403,
            detail="Invalid request origin.",
        )


# Session lifetime is controlled server-side by AuthSessionService.
# max_age mirrors the server session TTL for browser cleanup.


class LoginRequest(BaseModel):
    email: str = Field(min_length=1, max_length=320)
    password: str = Field(min_length=1, max_length=1024)


def _session_service() -> AuthSessionService:
    """Build the server-side authentication session service."""
    auth_repository = AuthRepository()

    return AuthSessionService(
        auth_repository=auth_repository,
    )


def _set_session_cookie(
    response: Response,
    session_id: str,
) -> None:
    """Set the production browser authentication cookie."""
    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=session_id,
        max_age=settings.session_ttl_seconds,
        path=SESSION_COOKIE_PATH,
        secure=SESSION_COOKIE_SECURE,
        httponly=True,
        samesite=SESSION_COOKIE_SAMESITE,
    )


def _clear_session_cookie(response: Response) -> None:
    """Clear the browser authentication cookie."""
    response.delete_cookie(
        key=SESSION_COOKIE_NAME,
        path=SESSION_COOKIE_PATH,
        secure=SESSION_COOKIE_SECURE,
        httponly=True,
        samesite=SESSION_COOKIE_SAMESITE,
    )


@api.get("/api/auth/health")
def auth_health() -> dict[str, bool]:
    return {"ok": True}


@api.post("/api/auth/session")
def create_auth_session(
    payload: LoginRequest,
    request: Request,
    response: Response,
) -> dict[str, Any]:
    """Authenticate credentials and establish a server-side browser session."""

    _validate_request_origin(request)

    email = payload.email.strip().lower()

    if not email:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    auth_repository = AuthRepository()

    try:
        authentication = auth_repository.sign_in_with_password(
            email,
            payload.password,
        )

        access_token = authentication.get("access_token")
        refresh_token = authentication.get("refresh_token")
        user = authentication.get("user")

        if not access_token or not refresh_token or not user:
            logger.warning(
                "Authentication succeeded without complete session data."
            )
            raise HTTPException(
                status_code=401,
                detail="Invalid email or password.",
            )

        user_id = str(user.get("id") or "").strip()

        if not user_id:
            logger.error(
                "Authenticated user did not contain a valid user ID."
            )
            raise HTTPException(
                status_code=500,
                detail="Authentication service error.",
            )

        session_service = AuthSessionService(
            auth_repository=auth_repository,
        )

        session_id = session_service.create_session(
            user_id=user_id,
            access_token=access_token,
            refresh_token=refresh_token,
        )

        _set_session_cookie(
            response,
            session_id,
        )

        return {
            "ok": True,
            "user": user,
        }

    except HTTPException:
        raise

    except (ValueError, PermissionError):
        # Do not reveal whether the email or password was incorrect.
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    except Exception:
        logger.exception(
            "Authentication session creation failed."
        )
        raise HTTPException(
            status_code=500,
            detail="Authentication service error.",
        )


@api.post("/api/auth/session/logout")
def destroy_auth_session(
    request: Request,
    response: Response,
) -> dict[str, bool]:
    """Revoke the current server-side session and clear its cookie."""

    _validate_request_origin(request)

    session_id = request.cookies.get(SESSION_COOKIE_NAME)

    if session_id:
        try:
            session_service = _session_service()
            session_service.revoke_session(session_id)
        except Exception:
            logger.exception(
                "Failed to revoke authentication session during logout."
            )

    _clear_session_cookie(response)

    return {"ok": True}
