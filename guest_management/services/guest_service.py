"""Guest application service."""

from __future__ import annotations

import json
import math
from typing import Any, Dict, List, Tuple

from guest_management.core.exceptions import (
    AuthorizationError,
    GuestAlreadyCheckedInError,
    GuestNotFoundError,
    ValidationError,
)
from guest_management.repositories import EventRepository, GuestRepository, CheckinRepository
from guest_management.services.event_service import EventService
from guest_management.services.qr_service import QRService


class GuestService:

    def __init__(
        self,
        repo: GuestRepository | None = None,
        event_repo: EventRepository | None = None,
        checkin_repo: CheckinRepository | None = None,
        event_service: EventService | None = None,
    ):
        self.repo = repo or GuestRepository()
        self.event_repo = event_repo or EventRepository()
        self.checkin_repo = checkin_repo or CheckinRepository()
        self.event_service = event_service or EventService()
        self.qr_service = QRService()

    def _authorize_event_access(
        self,
        event_id: int,
        user_id: str | None,
        user: Dict[str, Any] | None,
    ) -> None:
        """Authorize access to an event before touching guest data."""
        if not user_id:
            raise AuthorizationError("Authenticated user required")

        self.event_service.get_event(
            int(event_id),
            user_id,
            user,
        )


    def get_guests_by_event(
        self,
        event_id: int,
        page: int = 1,
        page_size: int = 50,
        *,
        user_id: str | None = None,
        user: Dict[str, Any] | None = None,
    ) -> Tuple[List[Dict[str, Any]], int]:
        self._authorize_event_access(
            event_id,
            user_id,
            user,
        )

        page = max(1, int(page))
        page_size = min(max(1, int(page_size)), 200)

        return self.repo.get_by_event(
            int(event_id),
            page_size,
            (page - 1) * page_size,
        )

    def get_guest(
        self,
        guest_id: str,
        event_id: int,
        *,
        user_id: str | None = None,
        user: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        self._authorize_event_access(
            event_id,
            user_id,
            user,
        )

        guest = self.repo.get_by_guest_id(guest_id, event_id)
        if not guest:
            raise GuestNotFoundError(f"Guest {guest_id} not found")
        return guest

    def check_in_guest(self, guest_id: str, event_id: int, scanner_id: str = "") -> Dict[str, Any]:
        try:
            return self.checkin_repo.check_in(
                int(event_id),
                guest_id,
                scanner_id,
            )
        except GuestAlreadyCheckedInError:
            raise

    def get_guest_stats(
        self,
        event_id: int,
        *,
        user_id: str | None = None,
        user: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        self._authorize_event_access(
            event_id,
            user_id,
            user,
        )

        response = self.repo.db.rpc(
            "get_event_stats",
            {"p_event_id": int(event_id)},
        ).execute()
        row = (response.data or [{}])[0]
        total = int(row.get("total_guests", 0))
        present = int(row.get("present_count", 0))
        absent = int(row.get("absent_count", total - present))
        return {
            "total": total,
            "present": present,
            "absent": absent,
            "present_percentage": round(present / total * 100) if total else 0,
            "absent_percentage": round(absent / total * 100) if total else 0,
        }

    def process_guests_from_data(
        self,
        guests_data: List[Dict[str, Any]],
        event_id: int,
        event_type: str,
        *,
        user_id: str | None = None,
        user: Dict[str, Any] | None = None,
    ) -> Tuple[int, int]:
        self._authorize_event_access(
            event_id,
            user_id,
            user,
        )

        if not guests_data:
            return 0, 0

        prepared: list[dict[str, Any]] = []
        seen: set[str] = set()
        skipped = 0

        for index, row in enumerate(guests_data):
            # Resolve the participant ID from common spreadsheet column
            # variations while preserving the original row in full_data.
            normalized_row = {
                str(key).strip().lower().replace(" ", "_"): value
                for key, value in row.items()
            }

            raw_guest_id = (
                normalized_row.get("guest_id")
                or normalized_row.get("id")
                or f"ID_{event_id}_{index}"
            )

            if isinstance(raw_guest_id, float) and raw_guest_id.is_integer():
                guest_id = str(int(raw_guest_id))
            else:
                guest_id = str(raw_guest_id).strip()

            if not guest_id or guest_id in seen:
                skipped += 1
                continue

            seen.add(guest_id)

            prepared.append(
                self._prepare_guest_data(
                    row,
                    guest_id,
                    int(event_id),
                    event_type,
                )
            )

        created = self.repo.upsert_batch(
            prepared,
            batch_size=500,
        )

        skipped += max(
            0,
            len(prepared) - created,
        )

        self.event_repo.update_counts(
            int(event_id),
            guest_count=self.repo.count_by_event(
                int(event_id)
            ),
        )

        return created, skipped

    def _prepare_guest_data(self, row: Dict[str, Any], guest_id: str, event_id: int, event_type: str) -> Dict[str, Any]:
        def first(*keys: str, default: str = "") -> str:
            for key in keys:
                value = row.get(key)
                if value not in (None, ""):
                    return str(value).strip()
            return default

        name = first("name", "Name", "full name", default=f"Guest {guest_id}")
        email = first("email", "Email")
        table = first("table_number", "Table", "table", default="TBD")
        team = first("team_name", "Team", "team", "Group", "Squad") if event_type == "sports_day" else ""
        amount_raw = row.get("amount", row.get("Amount", 0))
        try:
            amount = float(amount_raw or 0)
            if not math.isfinite(amount):
                amount = 0.0
        except (TypeError, ValueError):
            amount = 0.0

        full_data = dict(row)
        full_data["event_type"] = event_type
        guest_url = self.qr_service.guest_url(guest_id, event_id)
        return {
            "name": name,
            "guest_id": guest_id,
            "email": email,
            "status": "Absent",
            "table_number": table,
            "amount": amount if event_type == "sports_day" else 0,
            "team_name": team,
            "qr_code": guest_url,
            "qr_url": guest_url,
            "email_sent": False,
            "event_id": event_id,
            "full_data": json.dumps(full_data, ensure_ascii=False, default=str),
        }
