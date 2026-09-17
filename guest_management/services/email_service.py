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
        """Build the inline company-logo block."""
        if not str(event.get("logo_storage_path") or "").strip():
            return ""

        return (
            '<div style="text-align:center;margin:0 0 18px 0;">'
            '<img src="cid:event-logo" alt="Company logo" '
            'style="display:inline-block;max-width:220px;max-height:90px;'
            'width:auto;height:auto;object-fit:contain;">'
            '</div>'
        )

    @staticmethod
    def _invitation_html(event: Dict[str, Any]) -> str:
        """Build an inline invitation image block."""

        storage_path = str(
            event.get("invitation_storage_path") or ""
        ).strip()

        mime_type = str(
            event.get("invitation_mime_type") or ""
        ).strip().lower()

        if not storage_path or not mime_type.startswith("image/"):
            return ""

        return (
            '<div style="margin:26px 0;text-align:center;">'
            '<div style="font-size:11px;text-transform:uppercase;'
            'letter-spacing:1.6px;color:#999;margin-bottom:10px;">'
            'Event Invitation'
            '</div>'
            '<img src="cid:event-invitation" '
            'alt="Event invitation" '
            'style="display:inline-block;max-width:100%;height:auto;'
            'border-radius:14px;border:1px solid #e8e8e8;">'
            '</div>'
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
        invitation_html = self._invitation_html(event)

        company_line = (
            f'<div style="font-size:11px;letter-spacing:1.8px;'
            f'text-transform:uppercase;color:#888;margin-bottom:10px;">'
            f'{company}</div>'
            if company
            else ""
        )

        html_content = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport"
          content="width=device-width,initial-scale=1.0">
    <title>{subject}</title>
</head>

<body style="
    margin:0;
    padding:0;
    background:#0b0b0b;
    font-family:Arial,Helvetica,sans-serif;
    color:#f4f1e8;
">

<div style="
    width:100%;
    padding:34px 10px;
    background:#0b0b0b;
">

    <div style="
        max-width:620px;
        margin:0 auto;
        background:#111111;
        border:1px solid #2d2a24;
        border-radius:20px;
        overflow:hidden;
    ">

        <!-- GOLD TOP ACCENT -->
        <div style="
            height:4px;
            background:#c9a227;
            font-size:0;
            line-height:0;
        ">&nbsp;</div>

        <!-- HEADER -->
        <div style="
            padding:38px 28px 30px;
            text-align:center;
            background:#111111;
        ">

            {logo_html}

            {company_line}

            <div style="
                width:46px;
                height:1px;
                background:#c9a227;
                margin:18px auto 20px;
            ">&nbsp;</div>

            <div style="
                font-size:30px;
                line-height:1.2;
                font-weight:700;
                letter-spacing:.2px;
                color:#f5f0e5;
                margin:0 0 10px;
            ">
                {event_name}
            </div>

            <div style="
                font-size:12px;
                line-height:1.6;
                text-transform:uppercase;
                letter-spacing:2.4px;
                color:#c9a227;
            ">
                You are warmly invited
            </div>

        </div>

        <!-- CONTENT -->
        <div style="
            padding:30px 28px 38px;
            background:#111111;
        ">

            <p style="
                font-size:18px;
                line-height:1.5;
                color:#f5f0e5;
                margin:0 0 16px;
            ">
                Hello <strong style="color:#d8b84c;">{name}</strong>,
            </p>

            <p style="
                font-size:15px;
                line-height:1.75;
                color:#b7b3aa;
                margin:0 0 28px;
            ">
                We are delighted to have you join us.
                Please keep this invitation for your event entry.
            </p>

            <!-- EVENT DETAILS -->
            <div style="
                background:#171614;
                border:1px solid #332f27;
                border-radius:16px;
                padding:20px;
                margin:0 0 28px;
            ">

                <div style="
                    font-size:11px;
                    text-transform:uppercase;
                    letter-spacing:1.8px;
                    color:#c9a227;
                    margin-bottom:16px;
                ">
                    Event Details
                </div>

                <div style="
                    font-size:14px;
                    line-height:1.9;
                    color:#eee9dd;
                ">
                    <div style="padding:7px 0;border-bottom:1px solid #292722;">
                        <span style="color:#918d84;">Date</span>
                        <span style="float:right;font-weight:600;">{date}</span>
                    </div>
                    <div style="padding:7px 0;border-bottom:1px solid #292722;">
                        <span style="color:#918d84;">Time</span>
                        <span style="float:right;font-weight:600;">{time}</span>
                    </div>
                    <div style="padding:7px 0;border-bottom:1px solid #292722;">
                        <span style="color:#918d84;">Venue</span>
                        <span style="float:right;font-weight:600;">{venue}</span>
                    </div>
                    <div style="padding:7px 0;">
                        <span style="color:#918d84;">Table</span>
                        <span style="float:right;font-weight:700;color:#d8b84c;">{table}</span>
                    </div>
                    <div style="clear:both;"></div>
                </div>

            </div>

            <!-- EVENT INVITATION -->
            {invitation_html}

            <!-- PERSONAL QR -->
            <div style="
                margin:30px 0 0;
                text-align:center;
                padding:26px 18px 24px;
                background:#171614;
                border:1px solid #332f27;
                border-radius:16px;
            ">

                <div style="
                    font-size:11px;
                    text-transform:uppercase;
                    letter-spacing:1.8px;
                    color:#c9a227;
                    margin-bottom:8px;
                ">
                    Your Personal Entry Pass
                </div>

                <div style="
                    font-size:14px;
                    color:#b7b3aa;
                    margin-bottom:18px;
                    line-height:1.5;
                ">
                    Present this QR code at the entrance.
                </div>

                <div style="
                    display:inline-block;
                    background:#ffffff;
                    padding:14px;
                    border:3px solid #c9a227;
                    border-radius:16px;
                ">

                    <img
                        src="cid:guest-qr"
                        alt="Event QR Code"
                        width="220"
                        style="
                            display:block;
                            width:220px;
                            height:220px;
                        "
                    >

                </div>

                <div style="
                    font-size:11px;
                    color:#817d74;
                    margin-top:14px;
                    line-height:1.5;
                ">
                    This QR code is personal to you.
                </div>

            </div>

            <p style="
                font-size:15px;
                line-height:1.7;
                color:#b7b3aa;
                text-align:center;
                margin:30px 0 0;
            ">
                We look forward to welcoming you.
            </p>

        </div>

        <!-- FOOTER -->
        <div style="
            padding:20px 24px;
            background:#0d0d0d;
            border-top:1px solid #292722;
            text-align:center;
        ">

            <div style="
                font-size:12px;
                font-weight:700;
                letter-spacing:1.2px;
                color:#c9a227;
                margin-bottom:7px;
            ">
                EVENTLAH
            </div>

            <div style="
                font-size:10px;
                line-height:1.6;
                color:#716e67;
            ">
                This invitation was sent by EventLah.<br>
                Please keep this email for event entry.
            </div>

        </div>

    </div>

</div>

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