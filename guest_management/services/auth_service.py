"""Authentication service using Google OAuth and application sessions."""
from urllib.parse import urlencode
from guest_management.repositories.auth_repository import AuthRepository
from guest_management.core.config import settings
from guest_management.services.google_drive_service import encrypt_refresh_token

class AuthService:
    def __init__(self): self.repo = AuthRepository()
    def google_authorization_url(self, state: str) -> str:
        params = {"client_id": settings.google_client_id, "redirect_uri": settings.google_redirect_uri,
                  "response_type": "code", "scope": "openid email profile https://www.googleapis.com/auth/drive.file",
                  "state": state, "access_type": "offline", "prompt": "consent"}
        return "https://accounts.google.com/o/oauth2/v2/auth?" + urlencode(params)

    def exchange_code(self, code: str) -> dict:
        import httpx

        response = httpx.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": settings.google_client_id,
                "client_secret": settings.google_client_secret,
                "redirect_uri": settings.google_redirect_uri,
                "grant_type": "authorization_code",
            },
            timeout=15,
        )

        response.raise_for_status()

        payload = response.json()

        user_info = self.repo.verify_google_id_token(
            payload["id_token"]
        )

        if not user_info:
            raise ValueError(
                "Google identity verification failed"
            )

        # ------------------------------------------------------
        # EventLah creator authorization
        # ------------------------------------------------------

        google_email = (
                user_info.get("email") or ""
        ).strip().lower()

        if not settings.is_event_creator(google_email):
            raise PermissionError(
                "This Google account is not authorized "
                "to create EventLah events."
            )

        # ------------------------------------------------------
        # Create/update local user
        # ------------------------------------------------------

        user = self.repo.upsert_google_user(
            user_info
        )

        refresh = payload.get("refresh_token")

        if refresh:
            self.repo.set_drive_refresh_token(
                user["id"],
                encrypt_refresh_token(refresh),
            )

        return {
            "user": self.repo.get_user(
                user["id"]
            ),
            "session": self.repo.create_session(
                user["id"]
            ),
        }

    def get_current_user(self, session_token: str | None): return self.repo.get_user_by_session(session_token or "")
    def logout(self, session_token: str | None): self.repo.revoke_session(session_token or "")
