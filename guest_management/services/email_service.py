"""Application email service.

The web application never talks directly to SendGrid.

Flow:

    UI
      ↓
    EmailService
      ↓
    email_jobs table
      ↓
    email_worker
      ↓
    SendGrid
"""

from __future__ import annotations

import html
import logging
import os
import re
from datetime import datetime
from typing import Any, Dict, Optional

from guest_management.core.exceptions import EmailError, ValidationError
from guest_management.repositories.email_job_repository import EmailJobRepository

logger = logging.getLogger(__name__)

EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class EmailService:
    def __init__(self, repository: Optional[EmailJobRepository] = None):
        self.repo = repository or EmailJobRepository()

    @staticmethod
    def validate_email(address: str) -> str:
        address = (address or "").strip().lower()
        if not EMAIL_RE.match(address):
            raise ValidationError("Invalid email address")
        return address

    @staticmethod
    def build_guest_qr_url(event_id: int | str, guest_id: str | int) -> str:
        base_url = (
            os.getenv("APP_URL", "http://localhost:3000")
            or "http://localhost:3000"
        ).strip().rstrip("/")

        if base_url.startswith("https://http://"):
            base_url = base_url.replace("https://http://", "https://", 1)
        elif base_url.startswith("http://https://"):
            base_url = base_url.replace("http://https://", "https://", 1)

        return f"{base_url}/guest?event_id={int(event_id)}&guest_id={str(guest_id)}"

    @staticmethod
    def _format_event_date(value: Any) -> str:
        raw = str(value or "TBD").strip()
        if raw == "TBD":
            return raw
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(raw, fmt).strftime("%d-%b-%Y")
            except ValueError:
                continue
        return raw

    @staticmethod
    def _format_event_time(value: Any) -> str:
        raw = str(value or "TBD").strip()
        if raw == "TBD":
            return raw
        for fmt in ("%H:%M", "%H:%M:%S", "%I:%M %p", "%I:%M:%S %p"):
            try:
                return datetime.strptime(raw, fmt).strftime("%H:%M")
            except ValueError:
                continue
        return raw

    @staticmethod
    def _logo_html(event: Dict[str, Any]) -> str:
        """Build a safe company-logo block.

        A logo can be a public HTTPS URL or a data URI. A local/relative
        path is intentionally not emitted because recipients cannot access
        the developer's localhost filesystem.
        """
        logo = str(event.get("logo") or "").strip()
        if not logo:
            return ""

        if logo.startswith("data:image/"):
            src = logo
        elif logo.startswith("https://") or logo.startswith("http://"):
            src = logo
        else:
            return ""

        return (
            '<p style="margin:0 0 18px 0;">'
            f'<img src="{html.escape(src, quote=True)}" '
            'alt="Company logo" style="max-width:220px;max-height:90px;object-fit:contain;">'
            '</p>'
        )

    def build_guest_invitation_job(
        self,
        event: Dict[str, Any],
        guest: Dict[str, Any],
    ) -> Dict[str, Any]:
        raw_email = guest.get("email") or guest.get("Email") or ""
        recipient = self.validate_email(str(raw_email))

        event_id = int(event["id"])
        guest_id = str(guest.get("guest_id") or guest.get("ID") or "")
        if not guest_id:
            raise ValidationError("Guest ID is required")

        name = html.escape(str(guest.get("name") or guest.get("Name") or "Guest"))
        table = html.escape(str(guest.get("table_number") or guest.get("Table") or "TBD"))
        event_name = html.escape(str(event.get("name") or "Event"))
        company = html.escape(str(event.get("company_name") or ""))
        date = html.escape(self._format_event_date(event.get("date")))
        time = html.escape(self._format_event_time(event.get("time")))
        venue = html.escape(str(event.get("venue") or "TBD"))
        subject = f"Invitation: {event_name}"

        logo_html = self._logo_html(event)
        company_line = f"<p><strong>{company}</strong></p>" if company else ""

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <title>{subject}</title>
</head>
<body style="font-family:Arial,sans-serif;line-height:1.5;color:#222;">
    {logo_html}
    {company_line}

    <h1>Hello {name}!</h1>

    <p>You are invited to <strong>{event_name}</strong>.</p>

    <p>
        <strong>Date:</strong> {date}<br>
        <strong>Time:</strong> {time}<br>
        <strong>Venue:</strong> {venue}<br>
        <strong>Table:</strong> {table}
    </p>

    <p>Please present your event QR code at the entrance.</p>

    <p>
        <img src="cid:guest-qr" alt="Event QR Code" width="220">
    </p>

    <p>We look forward to seeing you.</p>
</body>
</html>
""".strip()

        plain_text = (
            f"Hello {name}!\n\n"
            f"You are invited to {event_name}.\n\n"
            f"Date: {date}\n"
            f"Time: {time}\n"
            f"Venue: {venue}\n"
            f"Table: {table}\n\n"
            "Please present your event QR code at the entrance.\n"
        )

        return {
            "event_id": event_id,
            "guest_id": guest_id,
            "email_type": "invitation",
            "recipient": recipient,
            "subject": subject,
            "html_content": html_content,
            "plain_text": plain_text,
        }

    def enqueue_guest_invitation(
        self,
        event: Dict[str, Any],
        guest: Dict[str, Any],
        force: bool = False,
    ) -> Dict[str, Any]:
        job = self.build_guest_invitation_job(event, guest)
        result = self.repo.enqueue(job, force=force)
        if not result:
            raise EmailError("Unable to queue email")
        return result

    def enqueue_bulk_invitations(
        self,
        event: Dict[str, Any],
        guests: list[Dict[str, Any]],
    ) -> int:
        jobs: list[Dict[str, Any]] = []
        for guest in guests:
            email = guest.get("email") or guest.get("Email")
            if not email:
                continue
            try:
                jobs.append(self.build_guest_invitation_job(event, guest))
            except ValidationError:
                logger.warning(
                    "Skipping guest with invalid email: %s",
                    guest.get("guest_id") or guest.get("ID"),
                )
        if not jobs:
            return 0
        return self.repo.enqueue_many(jobs)