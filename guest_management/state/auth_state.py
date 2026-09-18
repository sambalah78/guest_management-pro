"""EventLah authentication state using Supabase Auth."""

from __future__ import annotations



import reflex as rx

from guest_management.core.config import settings
from guest_management.services.auth_service import AuthService


class AuthState(rx.State):
    """Browser/application authentication state.

    Supabase Auth is responsible for authentication.

    The existing ``eventlah_session`` cookie is temporarily retained
    as the access-token cookie during the migration so that the rest of
    the application does not need to change authentication contracts
    all at once.
    """

    # ------------------------------------------------------------------
    # Authentication token
    # ------------------------------------------------------------------

    # IMPORTANT:
    # This cookie now contains the Supabase access token.
    #
    # We retain the existing cookie name temporarily so downstream
    # The existing cookie name is retained temporarily for compatibility.
    access_token: str = rx.Cookie(
        name="eventlah_session",
        max_age=settings.session_ttl_seconds,
        path="/",
        same_site="lax",
        secure=settings.is_production,
    )

    refresh_token: str = rx.Cookie(
        name="eventlah_refresh",
        max_age=settings.session_ttl_seconds,
        path="/",
        same_site="lax",
        secure=settings.is_production,
    )

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
        """Clear all local authentication state."""
        self.access_token = ""
        self.refresh_token = ""
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
    # Supabase login
    # ------------------------------------------------------------------

    async def login(self):
        """Sign in using Supabase Auth email/password."""
        self.is_loading = True
        self.auth_error = ""

        try:
            email = self.username.strip().lower()

            if not email:
                self.auth_error = "Please enter your email address."
                yield rx.toast.error(
                    title=self.auth_error
                )
                return

            if not self.password:
                self.auth_error = "Please enter your password."
                yield rx.toast.error(
                    title=self.auth_error
                )
                return

            result = AuthService().login(
                email=email,
                password=self.password,
            )

            user = result.get("user")

            if not user:
                self.auth_error = (
                    "Authentication succeeded, but "
                    "your EventLah profile could not be found."
                )
                yield rx.toast.error(
                    title=self.auth_error
                )
                return

            access_token = str(
                result.get("access_token") or ""
            )

            if not access_token:
                self.auth_error = (
                    "Authentication succeeded, but "
                    "no access token was returned."
                )
                yield rx.toast.error(
                    title=self.auth_error
                )
                return

            refresh_token = str(
                result.get("refresh_token") or ""
            )

            if not refresh_token:
                self.auth_error = (
                    "Authentication succeeded, but "
                    "no refresh token was returned."
                )
                yield rx.toast.error(
                    title=self.auth_error
                )
                return

            self.access_token = access_token
            self.refresh_token = refresh_token

            self._apply_user(user)
            self.auth_checked = True

            # Do not retain the password in application state after
            # successful authentication.
            self.password = ""

            yield rx.redirect("/events")

        except PermissionError as exc:
            self.auth_error = str(exc)
            self._clear_auth_state()

            yield rx.toast.error(
                title=self.auth_error
            )

        except ValueError as exc:
            self.auth_error = str(exc)

            yield rx.toast.error(
                title=self.auth_error
            )
        except Exception:
            self.auth_error = (
                "Unable to sign in. "
                "Please check your email and password."
            )

            self._clear_auth_state()

            yield rx.toast.error(
                title=self.auth_error
            )

        finally:
            self.is_loading = False



    # ------------------------------------------------------------------
    # Logout
    # ------------------------------------------------------------------

    def logout(self):
        """Sign out from Supabase and clear the local session."""

        try:
            AuthService().logout(
                access_token=self.access_token,
                refresh_token=self.refresh_token,
            )
        except Exception:
            # Even if the remote Supabase logout fails,
            # the local browser session must still be destroyed.
            pass

        self._clear_auth_state()
        self.auth_checked = True

        return [
            rx.remove_cookie("eventlah_session"),
            rx.remove_cookie("eventlah_refresh"),
            rx.redirect("/"),
        ]

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
            "/lucky-draw-display",
        )

        return (
            path in exact
            or path.startswith(prefixes)
        )
    def _get_valid_user(self) -> dict | None:
        """Return the current user, refreshing the session if necessary."""

        user = AuthService().get_current_user(
            self.access_token
        )

        if user:
            return user

        if not self.refresh_token:
            return None

        refreshed = AuthService().refresh_session(
            self.refresh_token
        )

        if not refreshed:
            return None

        new_access_token = str(
            refreshed.get("access_token") or ""
        )

        new_refresh_token = str(
            refreshed.get("refresh_token") or ""
        )

        refreshed_user = refreshed.get("user")

        if (
            not new_access_token
            or not new_refresh_token
            or not refreshed_user
        ):
            return None

        self.access_token = new_access_token
        self.refresh_token = new_refresh_token

        return refreshed_user

    # ------------------------------------------------------------------
    # Authentication checks
    # ------------------------------------------------------------------

    async def check_auth(self):
        """Validate the current Supabase access token."""


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
        """Validate the authentication token when the app loads."""


        user = self._get_valid_user()

        if user:
            self._apply_user(user)

        else:
            self._clear_auth_state()

        self.auth_checked = True

    async def ensure_valid_session(
        self,
    ) -> bool:
        """Validate the current Supabase access token."""
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
        """Compatibility setter for existing callers."""
        self.access_token = token or ""
