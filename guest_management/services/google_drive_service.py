"""Google Drive file service using the authenticated user's Drive grant."""
from __future__ import annotations
import io
from typing import Optional
from guest_management.core.config import settings
from guest_management.database import get_db
from cryptography.fernet import Fernet
import base64, hashlib

SCOPES = ["https://www.googleapis.com/auth/drive.file"]

def _fernet() -> Fernet:
    key = base64.urlsafe_b64encode(hashlib.sha256(settings.session_secret.encode()).digest())
    return Fernet(key)

def encrypt_refresh_token(token: str) -> str:
    return _fernet().encrypt(token.encode()).decode()

def decrypt_refresh_token(token: str) -> str:
    return _fernet().decrypt(token.encode()).decode()

class GoogleDriveService:
    def __init__(self, user_id: str): self.user_id = user_id
    def _credentials(self):
        from google.oauth2.credentials import Credentials
        rows = get_db().table("users").select("google_refresh_token_enc").eq("id", self.user_id).limit(1).execute().data
        if not rows or not rows[0].get("google_refresh_token_enc"):
            raise RuntimeError("Google Drive permission is not connected for this account")
        return Credentials(None, refresh_token=decrypt_refresh_token(rows[0]["google_refresh_token_enc"]), token_uri="https://oauth2.googleapis.com/token",
                           client_id=settings.google_client_id, client_secret=settings.google_client_secret, scopes=SCOPES)
    def _drive(self):
        from googleapiclient.discovery import build
        return build("drive", "v3", credentials=self._credentials(), cache_discovery=False)
    def ensure_root_folder(self) -> str:
        drive = self._drive()
        name = "EventLah"
        found = drive.files().list(q="name='EventLah' and mimeType='application/vnd.google-apps.folder' and trashed=false", spaces="drive", fields="files(id,name)", pageSize=1).execute().get("files", [])
        if found: return found[0]["id"]
        return drive.files().create(body={"name": name, "mimeType": "application/vnd.google-apps.folder"}, fields="id").execute()["id"]
    def upload_bytes(self, filename: str, content: bytes, mime_type: str, parent_id: Optional[str] = None) -> str:
        from googleapiclient.http import MediaIoBaseUpload
        drive = self._drive(); parent_id = parent_id or self.ensure_root_folder()
        media = MediaIoBaseUpload(io.BytesIO(content), mimetype=mime_type, resumable=False)
        file = drive.files().create(body={"name": filename, "parents": [parent_id]}, media_body=media, fields="id,webViewLink").execute()
        return file["id"]
