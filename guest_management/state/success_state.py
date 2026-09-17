"""Secure check-in success state."""

from __future__ import annotations

import logging
import re
from urllib.parse import parse_qs, urlparse

import reflex as rx

from guest_management.core.security import verify_qr_token
from guest_management.repositories import EventRepository, GuestRepository

logger = logging.getLogger(__name__)


class SuccessState(rx.State):
    """Load and expose verified check-in receipt details."""

    success_event_id: int = 0
    guest_id: str = ""
    guest_name: str = "Attendee"
    table_number: str = "TBD"
    team_name: str = "Individual"

    event_name: str = ""
    company_name: str = ""
    event_date: str = ""
    event_time: str = ""
    venue: str = ""

    is_fetching: bool = False

    async def fetch_checked_in_guest_details(self):
        """Validate the signed receipt and load guest/event details."""
        self.is_fetching = True
        try:
            url = getattr(self.router, "url", "") or ""
            parsed = urlparse(url)
            match = re.search(
                r"/(?:success|already-checked|already_checked)/(\d+)",
                parsed.path,
            )
            if not match:
                logger.warning("Success page missing event ID")
                return

            event_id = int(match.group(1))
            query = parse_qs(parsed.query)
            guest_id = query.get("guest_id", [""])[0].strip()
            token = query.get("token", [""])[0].strip()

            if (
                not guest_id
                or not token
                or not verify_qr_token(event_id, guest_id, token)
            ):
                logger.warning("Rejected unsigned or invalid success-page request")
                return

            guest = GuestRepository().get_by_guest_id(guest_id, event_id)
            if not guest or guest.get("status") != "Present":
                logger.warning("Success receipt guest not found or not checked in")
                return

            event = EventRepository().get_by_id_public(event_id)
            if not event:
                logger.warning("Success receipt event not found: %s", event_id)
                return

            self.success_event_id = event_id
            self.guest_id = guest_id
            self.guest_name = str(guest.get("name") or "Attendee")
            self.table_number = str(guest.get("table_number") or "TBD")
            self.team_name = str(
                guest.get("team_name") or "Individual"
            ) or "Individual"

            self.event_name = str(event.get("name") or "Event")
            self.company_name = str(event.get("company_name") or "")
            self.event_date = str(event.get("date") or "")
            self.event_time = str(event.get("time") or "")
            self.venue = str(event.get("venue") or "")

        except Exception:
            logger.exception("Unable to load secure check-in receipt")
        finally:
            self.is_fetching = False

