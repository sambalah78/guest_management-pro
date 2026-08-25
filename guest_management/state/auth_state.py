"""Google authentication state."""
from __future__ import annotations
import secrets
import reflex as rx
from itsdangerous import TimestampSigner, BadSignature
from guest_management.core.config import settings
from guest_management.services.auth_service import AuthService

signer = TimestampSigner(settings.session_secret)

class AuthState(rx.State):
    session_token: str = rx.Cookie(name="eventlah_session", max_age=settings.session_ttl_seconds, path="/", same_site="lax", secure=settings.is_production)
    oauth_state: str = rx.Cookie(name="eventlah_oauth_state", max_age=600, path="/", same_site="lax", secure=settings.is_production)
    username: str = ""
    password: str = ""
    auth_error: str = ""
    is_authenticated: bool = False
    user: dict = {}
    user_id: str = ""
    user_email: str = ""
    auth_checked: bool = False
    is_loading: bool = False

    @rx.var
    def is_logged_in(self) -> bool: return self.is_authenticated and bool(self.user_id)

    @rx.var
    def google_login_url(self) -> str:
        if not settings.google_client_id: return "/login"
        return AuthService().google_authorization_url(self.oauth_state or "") if self.oauth_state else "/login"

    def start_google_login(self):
        state = secrets.token_urlsafe(32)
        self.oauth_state = state
        return rx.redirect(AuthService().google_authorization_url(state))

    def logout(self):
        AuthService().logout(self.session_token)

        self.session_token = ""
        self.is_authenticated = False
        self.auth_checked = True
        self.user_id = ""
        self.user_email = ""
        self.user = {}

        return [
            rx.remove_cookie("eventlah_session"),
            rx.redirect("/"),
        ]

    def _is_public_route(self, path: str) -> bool:
        if not path: return True
        exact = {"/", "/home", "/login", "/about", "/products", "/contact", "/select-event-type", "/health", "/auth/google/callback"}
        prefixes = ("/stall", "/scanner", "/scanner-guest", "/scanner_guest", "/checkin", "/success", "/already-checked", "/already_checked", "/lucky-draw-display")
        return path in exact or path.startswith(prefixes)

    async def check_auth(self):
        path = getattr(self.router.url, "path", "") or "/"
        if self._is_public_route(path): self.auth_checked = True; return
        user = AuthService().get_current_user(self.session_token)
        if user:
            self.user = user
            self.user_id = user["id"]
            self.user_email = str(user.get("email", "")).strip().lower()
            self.is_authenticated = True
        else:
            self.session_token = ""
            self.is_authenticated = False
            self.user_id = ""
            self.user_email = ""
            self.user = {}

            yield rx.redirect("/login")
        self.auth_checked = True

    async def check_session_on_load(self):
        user = AuthService().get_current_user(self.session_token)

        if user:
            self.user = user
            self.user_id = user["id"]
            self.user_email = str(user.get("email", "")).strip().lower()
            self.is_authenticated = True
        else:
            self.session_token = ""
            self.is_authenticated = False
            self.user_id = ""
            self.user_email = ""
            self.user = {}

        self.auth_checked = True

    async def ensure_valid_session(self) -> bool:
        user = AuthService().get_current_user(self.session_token)

        self.is_authenticated = bool(user)

        if user:
            self.user = user
            self.user_id = user["id"]
            self.user_email = str(user.get("email", "")).strip().lower()
        else:
            self.user = {}
            self.user_id = ""
            self.user_email = ""

        return bool(user)

    def set_username(self, value: str): self.username = value.strip()
    def set_password(self, value: str): self.password = value
    def set_access_token(self, token: str): self.session_token = token or ""
