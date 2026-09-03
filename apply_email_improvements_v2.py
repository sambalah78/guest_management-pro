from pathlib import Path

ROOT = Path("guest_management")

# ================================================================
# EMAIL SERVICE
# ================================================================

path = ROOT / "services" / "email_service.py"
text = path.read_text(encoding="utf-8")

start = text.index("    @staticmethod\n    def _logo_html")
end = text.index("    def build_guest_invitation_job", start)

new_helpers = '''    @staticmethod
    def _logo_html(event: Dict[str, Any]) -> str:
        """Build the inline company-logo block."""
        if not str(event.get("logo_drive_file_id") or "").strip():
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
        file_id = str(
            event.get("invitation_drive_file_id") or ""
        ).strip()

        mime_type = str(
            event.get("invitation_mime_type") or ""
        ).strip().lower()

        if not file_id or not mime_type.startswith("image/"):
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

'''

text = text[:start] + new_helpers + text[end:]

start = text.index(
    "        logo_html = self._logo_html(event)"
)
end = text.index(
    "        plain_text = (",
    start,
)

new_html = '''        logo_html = self._logo_html(event)
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
    background:#f4f4f2;
    font-family:Arial,Helvetica,sans-serif;
    color:#252525;
">

<div style="padding:28px 10px;">

<div style="
    max-width:620px;
    margin:0 auto;
    background:#ffffff;
    border-radius:18px;
    overflow:hidden;
    border:1px solid #e8e8e6;
">

    <!-- HEADER -->

    <div style="
        padding:34px 28px 16px;
        text-align:center;
    ">

        {logo_html}

        {company_line}

        <div style="
            font-size:29px;
            line-height:1.2;
            font-weight:700;
            margin:4px 0 8px;
        ">
            {event_name}
        </div>

        <div style="
            font-size:14px;
            color:#888;
        ">
            You are warmly invited
        </div>

    </div>


    <!-- CONTENT -->

    <div style="padding:10px 28px 34px;">

        <p style="
            font-size:18px;
            margin:8px 0 18px;
        ">
            Hello <strong>{name}</strong>,
        </p>

        <p style="
            font-size:15px;
            line-height:1.7;
            color:#555;
            margin:0 0 24px;
        ">
            We are delighted to have you join us.
            Please find your personal event details below.
        </p>


        <!-- EVENT DETAILS -->

        <div style="
            background:#faf8f3;
            border:1px solid #eee6d8;
            border-radius:14px;
            padding:19px 20px;
            margin:0 0 24px;
        ">

            <div style="
                font-size:11px;
                text-transform:uppercase;
                letter-spacing:1.4px;
                color:#999;
                margin-bottom:11px;
            ">
                Event Details
            </div>

            <div style="
                font-size:15px;
                line-height:1.9;
            ">
                <strong>Date</strong>&nbsp;&nbsp;{date}<br>
                <strong>Time</strong>&nbsp;&nbsp;{time}<br>
                <strong>Venue</strong>&nbsp;&nbsp;{venue}<br>
                <strong>Table</strong>&nbsp;&nbsp;{table}
            </div>

        </div>


        <!-- EVENT INVITATION -->

        {invitation_html}


        <!-- PERSONAL QR -->

        <div style="
            text-align:center;
            padding:8px 0 2px;
        ">

            <div style="
                font-size:13px;
                color:#777;
                margin-bottom:12px;
            ">
                Your personal entry QR code
            </div>

            <div style="
                display:inline-block;
                background:#fff;
                padding:14px;
                border:1px solid #e8e8e8;
                border-radius:14px;
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
                font-size:12px;
                color:#999;
                margin-top:10px;
            ">
                Please present this QR code at the entrance.
            </div>

        </div>


        <p style="
            font-size:15px;
            line-height:1.7;
            color:#555;
            text-align:center;
            margin:28px 0 4px;
        ">
            We look forward to seeing you.
        </p>

    </div>


    <!-- FOOTER -->

    <div style="
        padding:17px 24px;
        background:#fafafa;
        border-top:1px solid #eee;
        text-align:center;
        font-size:11px;
        color:#999;
    ">
        This invitation was sent by EventLah.
        Please keep this email for event entry.
    </div>

</div>

</div>

</body>
</html>
""".strip()

'''

text = text[:start] + new_html + text[end:]

path.write_text(text, encoding="utf-8")

print("UPDATED:", path)


# ================================================================
# EMAIL WORKER
# ================================================================

path = ROOT / "workers" / "email_worker.py"
text = path.read_text(encoding="utf-8")

# Add GuestRepository import if not already present.
if "from guest_management.repositories.guest_repository import GuestRepository" not in text:
    marker = (
        "from guest_management.repositories.event_repository "
        "import EventRepository\n"
    )

    if marker not in text:
        raise SystemExit(
            "Could not locate EventRepository import."
        )

    text = text.replace(
        marker,
        marker
        + "from guest_management.repositories.guest_repository "
          "import GuestRepository\n",
        1,
    )


# Add repository instance.
if "self.guest_repo = GuestRepository()" not in text:

    marker = "        self.event_repo = EventRepository()\n"

    if marker not in text:
        raise SystemExit(
            "Could not locate self.event_repo initialization."
        )

    text = text.replace(
        marker,
        marker
        + "        self.guest_repo = GuestRepository()\n",
        1,
    )


# ---------------------------------------------------------------
# Replace QR generator.
# ---------------------------------------------------------------

start = text.index(
    "    @staticmethod\n    def build_qr_png("
)

end = text.index(
    "    def _get_drive_service_for_event",
    start,
)

new_qr = '''    def build_qr_png(
        self,
        event_id: int,
        guest_id: str,
    ) -> bytes:
        """
        Generate the email QR from the authoritative stored
        guest QR URL.

        The client's supplied guest ID is preserved.
        """

        response = (
            self.guest_repo.db
            .table("guests")
            .select("guest_id,qr_url,qr_code")
            .eq("event_id", int(event_id))
            .eq("guest_id", str(guest_id))
            .limit(1)
            .execute()
        )

        guest = (
            response.data[0]
            if response.data
            else None
        )

        if not guest:
            raise RuntimeError(
                f"Guest {guest_id} not found "
                f"for event {event_id}"
            )

        qr_url = str(
            guest.get("qr_url")
            or guest.get("qr_code")
            or ""
        ).strip()

        if not qr_url:
            raise RuntimeError(
                f"Guest {guest_id} has no stored QR URL"
            )

        logger.debug(
            "Using stored QR URL event=%s guest=%s: %s",
            event_id,
            guest_id,
            qr_url,
        )

        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=10,
            border=4,
        )

        qr.add_data(qr_url)
        qr.make(fit=True)

        image = qr.make_image(
            fill_color="black",
            back_color="white",
        ).convert("RGB")

        buffer = io.BytesIO()

        image.save(
            buffer,
            format="PNG",
            optimize=True,
        )

        return buffer.getvalue()

'''

text = text[:start] + new_qr + text[end:]


# ---------------------------------------------------------------
# Replace wedding-only Drive attachment implementation.
# ---------------------------------------------------------------

start = text.index(
    "    def _add_wedding_invitation("
)

end = text.index(
    "    # ================================================================\n"
    "    # BUILD SENDGRID MESSAGE",
    start,
)

new_branding = '''    def _add_drive_asset(
        self,
        message: Mail,
        event: Dict[str, Any],
        *,
        file_id_key: str,
        filename_key: str,
        mime_key: str,
        content_id: str,
        inline: bool,
    ) -> bool:
        """Download an event asset from Google Drive."""

        file_id = str(
            event.get(file_id_key) or ""
        ).strip()

        if not file_id:
            return False

        try:
            drive_service = (
                self._get_drive_service_for_event(
                    int(event["id"])
                )
            )

            data = drive_service.download_bytes(
                file_id
            )

            if not data:
                logger.warning(
                    "Event asset is empty: "
                    "event=%s file=%s",
                    event["id"],
                    file_id,
                )
                return False

            filename = str(
                event.get(filename_key)
                or f"event_{event['id']}_asset"
            ).strip()

            mime_type = str(
                event.get(mime_key)
                or "application/octet-stream"
            ).strip()

            attachment = Attachment()

            attachment.file_content = FileContent(
                base64.b64encode(data).decode("ascii")
            )

            attachment.file_type = FileType(
                mime_type
            )

            attachment.file_name = FileName(
                filename
            )

            if inline:
                attachment.disposition = (
                    Disposition("inline")
                )
                attachment.content_id = (
                    content_id
                )
            else:
                attachment.disposition = (
                    Disposition("attachment")
                )

            message.add_attachment(
                attachment
            )

            logger.info(
                "Event asset added: "
                "event=%s file=%s filename=%s inline=%s",
                event["id"],
                file_id,
                filename,
                inline,
            )

            return True

        except Exception:
            logger.exception(
                "Failed to add event asset: "
                "event=%s file=%s",
                event.get("id"),
                file_id,
            )
            return False


    def _add_event_branding(
        self,
        message: Mail,
        event: Dict[str, Any],
    ) -> tuple[bool, bool]:
        """
        Add the event logo and invitation from Google Drive.

        Returns:
            (logo_added, invitation_added)
        """

        logo_added = self._add_drive_asset(
            message,
            event,
            file_id_key="logo_drive_file_id",
            filename_key="logo_filename",
            mime_key="logo_mime_type",
            content_id="event-logo",
            inline=True,
        )

        invitation_file_id = str(
            event.get("invitation_drive_file_id")
            or ""
        ).strip()

        invitation_mime = str(
            event.get("invitation_mime_type")
            or ""
        ).strip().lower()

        invitation_inline = bool(
            invitation_file_id
            and invitation_mime.startswith("image/")
        )

        invitation_added = self._add_drive_asset(
            message,
            event,
            file_id_key="invitation_drive_file_id",
            filename_key="invitation_filename",
            mime_key="invitation_mime_type",
            content_id="event-invitation",
            inline=invitation_inline,
        )

        return (
            logo_added,
            invitation_added,
        )

'''

text = text[:start] + new_branding + text[end:]


# ---------------------------------------------------------------
# Replace build_message.
# ---------------------------------------------------------------

start = text.index(
    "    def build_message("
)

end = text.index(
    "    # ================================================================\n"
    "    # SEND ONE",
    start,
)

new_build = '''    def build_message(
        self,
        job: Dict[str, Any],
    ) -> Mail:

        event_id = int(
            job["event_id"]
        )

        guest_id = str(
            job["guest_id"]
        )

        recipient = str(
            job["recipient"]
        ).strip()

        subject = str(
            job.get("subject")
            or "Event Invitation"
        )

        html_content = str(
            job.get("html_content")
            or ""
        )

        plain_text = str(
            job.get("plain_text")
            or ""
        )

        event = (
            self.event_repo.get_by_id_public(
                event_id
            )
        )

        if not event:
            raise RuntimeError(
                f"Event {event_id} not found"
            )

        message = Mail(
            from_email=self.sender,
            to_emails=recipient,
            subject=subject,
        )

        logo_added, invitation_added = (
            self._add_event_branding(
                message,
                event,
            )
        )

        # If an asset was unavailable, remove its
        # corresponding HTML block rather than leaving
        # a broken CID image.

        if not logo_added:
            logo_html = EmailService._logo_html(
                event
            )

            if logo_html:
                html_content = html_content.replace(
                    logo_html,
                    "",
                )

        if not invitation_added:
            invitation_html = (
                EmailService._invitation_html(
                    event
                )
            )

            if invitation_html:
                html_content = html_content.replace(
                    invitation_html,
                    "",
                )

        if plain_text:
            message.add_content(
                Content(
                    "text/plain",
                    plain_text,
                )
            )

        if html_content:
            message.add_content(
                Content(
                    "text/html",
                    html_content,
                )
            )

        # ----------------------------------------------------------
        # Personal guest QR
        # ----------------------------------------------------------

        qr_png = self.build_qr_png(
            event_id=event_id,
            guest_id=guest_id,
        )

        qr_attachment = Attachment()

        qr_attachment.file_content = FileContent(
            base64.b64encode(
                qr_png
            ).decode("ascii")
        )

        qr_attachment.file_type = FileType(
            "image/png"
        )

        qr_attachment.file_name = FileName(
            "eventlah-guest-qr.png"
        )

        qr_attachment.disposition = (
            Disposition("inline")
        )

        qr_attachment.content_id = (
            "guest-qr"
        )

        message.add_attachment(
            qr_attachment
        )

        return message

'''

text = text[:start] + new_build + text[end:]

path.write_text(text, encoding="utf-8")

print("UPDATED:", path)

print()
print("=" * 70)
print("EMAIL IMPROVEMENTS APPLIED")
print("=" * 70)
