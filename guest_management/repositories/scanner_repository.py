"""Scanner station repository."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from .base import BaseRepository
import hashlib
import hmac
import secrets


class ScannerRepository(BaseRepository):
    """Persistence operations for event scanner stations."""

    @staticmethod
    def generate_access_token() -> str:
        """Generate a high-entropy credential for a scanner station."""
        return f"ELST_{secrets.token_urlsafe(64)}"

    @staticmethod
    def hash_access_token(
            access_token: str,
            pepper: str,
    ) -> str:
        """Create the stored verifier for a scanner station credential."""
        token = str(access_token or "").strip()
        secret = str(pepper or "")

        if not token:
            raise ValueError("Scanner station access token is required.")

        if len(secret) < 32:
            raise ValueError(
                "Scanner station credential pepper must contain "
                "at least 32 characters."
            )

        return hmac.new(
            secret.encode("utf-8"),
            token.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def get_by_access_token_hash(
            self,
            access_token_hash: str,
    ) -> Optional[Dict[str, Any]]:
        """Return the scanner station matching a credential hash."""
        token_hash = str(access_token_hash or "").strip()

        if not token_hash:
            return None

        response = (
            self.db.table("scanner_devices")
            .select(
                "id,event_id,device_id,device_name,is_active,"
                "total_scans,last_used,assigned_by,assigned_at,"
                "created_at,updated_at"
            )
            .eq("access_token_hash", token_hash)
            .limit(1)
            .execute()
        )

        rows = response.data or []
        return rows[0] if rows else None

    def get_by_event(self, event_id: int) -> List[Dict[str, Any]]:
        response = (
            self.db.table("scanner_devices")
            .select("*")
            .eq("event_id", int(event_id))
            .order("id")
            .execute()
        )
        return response.data or []

    def get_by_device(
            self,
            event_id: int,
            device_id: str,
    ) -> Optional[Dict[str, Any]]:
        response = (
            self.db.table("scanner_devices")
            .select("*")
            .eq("event_id", int(event_id))
            .eq("device_id", str(device_id).strip())
            .limit(1)
            .execute()
        )

        rows = response.data or []
        return rows[0] if rows else None

    def create(
            self,
            event_id: int,
            device_name: str,
            access_token_hash: str,
            assigned_by: Optional[str] = None,
    ) -> Dict[str, Any]:
        event_id = int(event_id)
        device_name = str(device_name).strip()

        access_token_hash = str(access_token_hash or "").strip()

        if not access_token_hash:
            raise ValueError("Scanner station access token hash is required.")

        if not device_name:
            raise ValueError("Scanner station name is required.")

        # Opaque persistent identity.
        # Do NOT use sequential IDs here because concurrent station
        # creation can race.
        device_id = f"EL-{uuid4().hex.upper()}"

        now = datetime.now(timezone.utc).isoformat()

        row = {
            "event_id": event_id,
            "device_id": device_id,
            "device_name": device_name,
            "access_token_hash": access_token_hash,
            "is_active": True,
            "total_scans": 0,
            "assigned_by": assigned_by,
            "assigned_at": now if assigned_by else None,
        }

        response = (
            self.db.table("scanner_devices")
            .insert(row)
            .execute()
        )

        rows = response.data or []

        if not rows:
            raise RuntimeError("Scanner station creation returned no data.")

        return rows[0]

    def set_active(
            self,
            event_id: int,
            device_id: str,
            is_active: bool,
    ) -> Optional[Dict[str, Any]]:
        response = (
            self.db.table("scanner_devices")
            .update({
                "is_active": bool(is_active),
                "updated_at": datetime.now(timezone.utc).isoformat(),
            })
            .eq("event_id", int(event_id))
            .eq("device_id", str(device_id).strip())
            .execute()
        )

        rows = response.data or []
        return rows[0] if rows else None

    def delete(
            self,
            event_id: int,
            device_id: str,
    ) -> bool:
        response = (
            self.db.table("scanner_devices")
            .delete()
            .eq("event_id", int(event_id))
            .eq("device_id", str(device_id).strip())
            .execute()
        )

        return bool(response.data)

    def increment_scans(
            self,
            event_id: int,
            device_id: str,
    ) -> None:
        self.db.rpc(
            "increment_scanner_scans",
            {
                "p_event_id": int(event_id),
                "p_device_id": str(device_id).strip(),
            },
        ).execute()
