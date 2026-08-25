"""Secure check-in success state."""

from __future__ import annotations

import logging
import re
from urllib.parse import parse_qs, urlparse

import reflex as rx

from guest_management.core.security import verify_qr_token
from guest_management.repositories import GuestRepository

logger = logging.getLogger(__name__)


class SuccessState(rx.State):
    guest_name: str = "Attendee"
    table_number: str = "N/A"
    team_name: str = "Individual"
    is_fetching: bool = False

    async def fetch_checked_in_guest_details(self):
        self.is_fetching = True
        try:
            url = getattr(self.router, "url", "") or ""
            parsed = urlparse(url)
            match = re.search(r"/(?:success|already-checked|already_checked)/(\d+)", parsed.path)
            if not match:
                return
            event_id = int(match.group(1))
            query = parse_qs(parsed.query)
            guest_id = query.get("guest_id", [""])[0].strip()
            token = query.get("token", [""])[0].strip()
            if not guest_id or not token or not verify_qr_token(event_id, guest_id, token):
                logger.warning("Rejected unsigned success-page request")
                return

            guest = GuestRepository().get_by_guest_id(guest_id, event_id)
            if not guest or guest.get("status") != "Present":
                return
            self.guest_name = str(guest.get("name") or "Attendee")
            self.table_number = str(guest.get("table_number") or "TBD")
            self.team_name = str(guest.get("team_name") or "Individual") or "Individual"
        except Exception:
            logger.exception("Unable to load secure check-in receipt")
        finally:
            self.is_fetching = False
