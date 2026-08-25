"""Google OAuth + application session repository."""
from __future__ import annotations
import hashlib, secrets
from datetime import datetime, timedelta, timezone
from typing import Any, Optional
from guest_management.database import get_db
from guest_management.core.config import settings

class AuthRepository:
    def verify_google_id_token(self, credential: str) -> Optional[dict[str, Any]]:
        try:
            from google.oauth2 import id_token
            from google.auth.transport import requests
            info = id_token.verify_oauth2_token(credential, requests.Request(), settings.google_client_id)
            if info.get("iss") not in {"accounts.google.com", "https://accounts.google.com"}: return None
            if not info.get("sub") or not info.get("email") or not info.get("email_verified"): return None
            return info
        except Exception:
            return None

    def upsert_google_user(self, info: dict[str, Any]) -> dict[str, Any]:
        db = get_db()
        subject, email = str(info["sub"]), str(info["email"]).lower()
        existing = db.table("users").select("*").eq("google_subject", subject).limit(1).execute().data
        now = datetime.now(timezone.utc)
        payload = {"id": existing[0]["id"] if existing else secrets.token_urlsafe(24), "google_subject": subject, "email": email,
                   "name": info.get("name", email), "picture": info.get("picture", ""), "role": existing[0].get("role", "OWNER") if existing else "OWNER",
                   "is_active": True, "updated_at": now}
        if existing:
            db.table("users").update(payload).eq("id", existing[0]["id"]).execute()
        else:
            db.table("users").insert(payload).execute()
        return db.table("users").select("*").eq("id", payload["id"]).limit(1).execute().data[0]

    def get_user(self, user_id: str) -> Optional[dict[str, Any]]:
        rows = get_db().table("users").select("*").eq("id", user_id).limit(1).execute().data
        return rows[0] if rows else None

    def set_drive_refresh_token(self, user_id: str, encrypted_token: str) -> None:
        get_db().table("users").update({"google_refresh_token_enc": encrypted_token}).eq("id", user_id).execute()

    def create_session(self, user_id: str) -> str:
        token = secrets.token_urlsafe(48)
        token_hash = hashlib.sha256(token.encode()).hexdigest()
        now = datetime.now(timezone.utc)
        db = get_db()
        db.table("sessions").insert({"id": secrets.token_urlsafe(24), "user_id": user_id, "token_hash": token_hash,
                                     "expires_at": now + timedelta(seconds=settings.session_ttl_seconds), "created_at": now}).execute()
        return token



    @staticmethod
    def _ensure_utc(dt: datetime) -> datetime:
        """Normalize naive/aware datetimes to timezone-aware UTC."""
        if dt.tzinfo is None:
            return dt.replace(tzinfo=timezone.utc)

        return dt.astimezone(timezone.utc)

    def get_user_by_session(self, token: str) -> Optional[dict[str, Any]]:
        if not token:
            return None

        token_hash = hashlib.sha256(token.encode()).hexdigest()
        db = get_db()

        rows = (
            db.table("sessions")
            .select("user_id,expires_at")
            .eq("token_hash", token_hash)
            .limit(1)
            .execute()
            .data
        )

        if not rows:
            return None

        expires = rows[0]["expires_at"]

        if isinstance(expires, str):
            expires = datetime.fromisoformat(
                expires.replace("Z", "+00:00")
            )

        expires = self._ensure_utc(expires)

        if expires <= datetime.now(timezone.utc):
            db.table("sessions").delete().eq(
                "token_hash", token_hash
            ).execute()
            return None

        users = (
            db.table("users")
            .select("id,email,name,picture,role,is_active")
            .eq("id", rows[0]["user_id"])
            .limit(1)
            .execute()
            .data
        )

        return users[0] if users and users[0].get("is_active") else None


    def revoke_session(self, token: str) -> None:
        if token:
            get_db().table("sessions").delete().eq("token_hash", hashlib.sha256(token.encode()).hexdigest()).execute()
