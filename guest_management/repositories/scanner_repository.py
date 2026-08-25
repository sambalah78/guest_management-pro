"""Scanner repository."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from .base import BaseRepository


class ScannerRepository(BaseRepository):
    def get_by_event(self, event_id: int) -> List[Dict[str, Any]]:
        response = self.db.table("scanner_devices").select("*").eq("event_id", int(event_id)).order("scanner_number").execute()
        return response.data or []

    def create_default_scanners(self, event_id: int, count: int = 8) -> List[Dict[str, Any]]:
        count = min(max(int(count), 1), 32)
        rows = [
            {
                "event_id": int(event_id),
                "device_name": f"Scanner {i}",
                "device_id": f"SCANNER_{i:03d}",
                "scanner_number": i,
                "total_scans": 0,
            }
            for i in range(1, count + 1)
        ]
        response = (
            self.db.table("scanner_devices")
            .upsert(rows, on_conflict="event_id,device_id", ignore_duplicates=True)
            .execute()
        )
        return response.data or self.get_by_event(int(event_id))

    def increment_scans(self, device_id: str) -> None:
        response = (
            self.db.table("scanner_devices")
            .update({"last_used": datetime.now(timezone.utc).isoformat()})
            .eq("device_id", device_id)
            .execute()
        )
        # If the table has total_scans, use a DB RPC for atomic increment.
        self.db.rpc("increment_scanner_scans", {"p_device_id": device_id}).execute()
