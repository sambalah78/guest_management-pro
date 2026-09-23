"""EventLah browser authentication state."""

from __future__ import annotations

import json
import os

import reflex as rx

from guest_management.services.auth_session_resolver import (
    AuthSessionResolutionError,
    AuthSessionResolver,
)


class AuthState(rx.State):
    """EventLah browser/application authentication state.

    Authentication credentials are kept server-side.

    The browser receives only the opaque ``eventlah_session`` HttpOnly
    session cookie from the authentication API. Supabase access and
    refresh tokens are never stored in Reflex state or browser-readable
    cookies.
    """

    # ------------------------------------------------------------------
    # Login form
    # ------------------------------------------------------------------

    username: str = ""
    password: str = ""

    auth_error: str = ""
    is_authenticated: bool = False

    user: dict = {}
    user_id: str = ""
    user_email: str = ""

    auth_checked: bool = False
    is_loading: bool = False

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _apply_user(
        self,
        user: dict,
    ) -> None:
        """Apply an EventLah user profile to state."""
        self.user = user
        self.user_id = str(
            user.get("id") or ""
        )
        self.user_email = str(
            user.get("email") or ""
        ).strip().lower()

        self.is_authenticated = bool(
            self.user_id
        )

        self.auth_error = ""

    def _clear_auth_state(self) -> None:
        """Clear all local authentication/profile state."""
        self.is_authenticated = False
        self.user_id = ""
        self.user_email = ""
        self.user = {}
        self.auth_error = ""

    # ------------------------------------------------------------------
    # Computed state
    # ------------------------------------------------------------------

    @rx.var
    def is_logged_in(self) -> bool:
        """Return whether an authenticated EventLah user is present."""
        return (
            self.is_authenticated
            and bool(self.user_id)
        )

    @rx.var
    def is_event_admin(self) -> bool:
        """Return whether the current user may manage events."""
        role = str(
            self.user.get("role") or ""
        ).strip().upper()

        return (
            self.is_logged_in
            and role in {"OWNER", "ADMIN"}
        )

    @rx.var
    def is_owner(self) -> bool:
        """Return whether the current user is an OWNER."""
        return (
            self.is_logged_in
            and str(
                self.user.get("role") or ""
            ).strip().upper()
            == "OWNER"
        )

    # ------------------------------------------------------------------
    # Login
    # ------------------------------------------------------------------

    def login(self):
        """Authenticate through the server-side authentication API.

        The browser calls ``/api/auth/session`` directly so that FastAPI
        can issue the HttpOnly session cookie. Supabase access/refresh
        tokens never enter Reflex state.
        """
        self.is_loading = True
        self.auth_error = ""

        email = self.username.strip().lower()

        if not email:
            self.auth_error = "Please enter your email address."
            self.is_loading = False
            return rx.toast.error(
                title=self.auth_error
            )

        if not self.password:
            self.auth_error = "Please enter your password."
            self.is_loading = False
            return rx.toast.error(
                title=self.auth_error
            )

        payload = json.dumps(
            {
                "email": email,
                "password": self.password,
            }
        )

        api_base_url = os.getenv(
            "API_URL",
            "http://localhost:8000",
        ).rstrip("/")

        script = f"""
(async () => {{
    try {{
        const apiBase = {json.dumps(api_base_url)};

        const response = await fetch(
            apiBase + "/api/auth/session",
            {{
                method: "POST",
                headers: {{
                    "Content-Type": "application/json"
                }},
                credentials: "include",
                body: {json.dumps(payload)}
            }}
        );

        let data = {{}};

        try {{
            data = await response.json();
        }} catch (_) {{
            data = {{}};
        }}

        return {{
            ok: response.ok,
            status: response.status,
            data: data
        }};
    }} catch (error) {{
        return {{
            ok: false,
            status: 0,
            data: {{
                detail: "Unable to connect to the authentication service."
            }}
        }};
    }}
}})()
"""

        return rx.call_script(
            script,
            callback=AuthState.handle_login_result,
        )

    def handle_login_result(self, result):
        """Handle the authentication API response."""
        # Never retain the submitted password after the authentication
        # request has completed, regardless of success or failure.
        self.password = ""
        self.is_loading = False

        if not isinstance(result, dict):
            self._clear_auth_state()
            self.auth_error = (
                "Unable to sign in. Please try again."
            )
            return rx.toast.error(
                title=self.auth_error
            )

        if not bool(result.get("ok")):
            data = result.get("data") or {}

            detail = str(
                data.get("detail")
                or "Unable to sign in. Please check your email and password."
            )

            self._clear_auth_state()
            self.auth_error = detail

            return rx.toast.error(
                title=self.auth_error
            )

        data = result.get("data") or {}
        user = data.get("user")

        if not isinstance(user, dict) or not user.get("id"):
            self._clear_auth_state()
            self.auth_error = (
                "Authentication succeeded, but "
                "your EventLah profile could not be found."
            )

            return rx.toast.error(
                title=self.auth_error
            )

        self._apply_user(user)
        self.auth_checked = True

        # Never retain the password after authentication.
        self.password = ""

        return rx.call_script(
            "window.location.assign('/events');"
        )

    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------

    def logout(self):
        """Revoke the server-side session and clear the browser cookie."""
        api_base_url = os.getenv(
            "API_URL",
            "http://localhost:8000",
        ).rstrip("/")

        script = f"""
(async () => {{
    try {{
        const apiBase = {json.dumps(api_base_url)};

        const response = await fetch(
            apiBase + "/api/auth/session/logout",
            {{
                method: "POST",
                credentials: "include"
            }}
        );

        return {{
            ok: response.ok,
            status: response.status
        }};
    }} catch (_) {{
        return {{
            ok: false,
            status: 0
        }};
    }}
}})()
"""

        return rx.call_script(
            script,
            callback=AuthState.handle_logout_result,
        )

    def handle_logout_result(self, result):
        """Clear local state after the logout API has been called."""
        self._clear_auth_state()
        self.password = ""
        self.auth_checked = True
        self.is_loading = False

        return rx.redirect("/")

    # ------------------------------------------------------------------
    # Route protection
    # ------------------------------------------------------------------

    def _is_public_route(
        self,
        path: str,
    ) -> bool:
        """Return whether a route does not require admin login."""
        if not path:
            return True

        exact = {
            "/",
            "/home",
            "/login",
            "/about",
            "/products",
            "/contact",
            "/select-event-type",
            "/health",
        }

        prefixes = (
            "/stall",
            "/scanner",
            "/scanner-guest",
            "/scanner_guest",
            "/checkin",
            "/success",
            "/already-checked",
            "/already_checked",
        )

        return (
            path in exact
            or path.startswith(prefixes)
        )

    def _get_valid_user(self) -> dict | None:
        """Resolve the current user from the server-side session."""
        try:
            return AuthSessionResolver().get_current_user()
        except AuthSessionResolutionError:
            return None
        except Exception:
            return None

    # ------------------------------------------------------------------
    # Authentication checks
    # ------------------------------------------------------------------

    async def check_auth(self):
        """Validate the current server-side authentication session."""

        path = (
            getattr(
                self.router.url,
                "path",
                "",
            )
            or "/"
        )

        if self._is_public_route(path):
            self.auth_checked = True
            return

        user = self._get_valid_user()

        if user:
            self._apply_user(user)
        else:
            self._clear_auth_state()

            yield rx.redirect(
                "/login"
            )

        self.auth_checked = True

    async def check_session_on_load(self):
        """Restore the authenticated user from the server-side session."""

        user = self._get_valid_user()

        if user:
            self._apply_user(user)
        else:
            self._clear_auth_state()

        self.auth_checked = True

    async def ensure_valid_session(
        self,
    ) -> bool:
        """Return whether the current server-side session is valid."""

        user = self._get_valid_user()

        if user:
            self._apply_user(user)
            return True

        self._clear_auth_state()

        return False

    # ------------------------------------------------------------------
    # Form setters
    # ------------------------------------------------------------------

    def set_username(
        self,
        value: str,
    ):
        self.username = value.strip()

    def set_password(
        self,
        value: str,
    ):
        self.password = value

    def set_access_token(
        self,
        token: str,
    ):
        """Deprecated compatibility setter.

        Admin authentication no longer stores Supabase access tokens.
        The method is retained temporarily so older callers do not fail.
        """
        return None
