"""
Durable SendGrid email worker.

Run:

    python -m guest_management.workers.email_worker

The worker:
1. Claims queued email jobs.
2. Generates the guest QR code.
3. Creates a SendGrid email.
4. Adds the QR as an inline attachment.
5. Sends the email.
6. Marks the job sent.
7. Marks the guest email_sent=True.
8. Retries failures.
"""

from __future__ import annotations

import base64
import io
import logging
import os
import time
from typing import Any, Dict, Optional

import qrcode
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import (
    Attachment,
    Content,
    Disposition,
    FileContent,
    FileName,
    FileType,
    Mail,
)

from guest_management.core.config import settings
from guest_management.repositories.email_job_repository import (
    EmailJobRepository,
)
from guest_management.services.email_service import EmailService

logger = logging.getLogger("eventlah.email_worker")

from guest_management.repositories.event_repository import EventRepository
from guest_management.repositories.guest_repository import GuestRepository
from guest_management.services.google_drive_asset_service import (
    GoogleDriveAssetService,
)
class EmailWorker:

    def __init__(
            self,
            batch_size: int = 10,
            poll_seconds: int = 5,
    ):
        self.batch_size = max(
            1,
            int(batch_size),
        )

        self.poll_seconds = max(
            1,
            int(poll_seconds),
        )

        self.repo = EmailJobRepository()
        self.event_repo = EventRepository()
        self.guest_repo = GuestRepository()

        api_key = (
                getattr(
                    settings,
                    "sendgrid_api_key",
                    None,
                )
                or os.getenv("SENDGRID_API_KEY")
                or ""
        ).strip()

        sender = (
                getattr(
                    settings,
                    "sender_email",
                    None,
                )
                or os.getenv("SENDER_EMAIL")
                or ""
        ).strip()

        if not api_key:
            raise RuntimeError(
                "SENDGRID_API_KEY is not configured"
            )

        if not sender:
            raise RuntimeError(
                "SENDER_EMAIL is not configured"
            )

        self.sender = sender

        self.client = SendGridAPIClient(
            api_key
        )

        logger.info(
            "Email worker initialized "
            "(sender=%s batch_size=%s)",
            self.sender,
            self.batch_size,
        )

    # ================================================================
    # QR GENERATION
    # ================================================================

    def build_qr_png(
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

    def _get_drive_service_for_event(
            self,
            event_id: int,
    ) -> GoogleDriveAssetService:
        """
        Create a Google Drive service authenticated as the
        owner of the specified EventLah event.
        """

        event_id = int(event_id)

        user_id = self.event_repo.get_owner_user_id(
            event_id
        )

        if not user_id:
            raise RuntimeError(
                f"Event {event_id} does not have a valid owner."
            )

        logger.debug(
            "Creating Google Drive service for "
            "event=%s owner=%s",
            event_id,
            user_id,
        )

        return GoogleDriveAssetService(
            user_id=user_id
        )

    def _add_drive_asset(
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

    # ================================================================
    # BUILD SENDGRID MESSAGE
    # ================================================================

    def build_message(
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

    # ================================================================
    # SEND ONE
    # ================================================================

    def send_one(
        self,
        job: Dict[str, Any],
    ) -> str:

        job_id = int(
            job["id"]
        )

        guest_id = str(
            job["guest_id"]
        )

        recipient = str(
            job["recipient"]
        )

        logger.info(
            "Sending email job=%s guest=%s recipient=%s",
            job_id,
            guest_id,
            recipient,
        )

        message = self.build_message(
            job
        )

        response = self.client.send(
            message
        )

        status_code = int(
            response.status_code
        )

        # SendGrid accepted the message.
        if 200 <= status_code < 300:

            message_id = ""

            try:
                headers = (
                    response.headers
                    or {}
                )

                message_id = (
                    headers.get(
                        "X-Message-Id"
                    )
                    or headers.get(
                        "x-message-id"
                    )
                    or ""
                )
            except Exception:
                logger.debug(
                    "Unable to read "
                    "SendGrid message ID",
                    exc_info=True,
                )

            logger.info(
                "SendGrid accepted job=%s "
                "status=%s message_id=%s",
                job_id,
                status_code,
                message_id,
            )

            return message_id

        raise RuntimeError(
            "SendGrid returned HTTP "
            f"{status_code}"
        )

    # ================================================================
    # RUN ONCE
    # ================================================================

    def run_once(self) -> int:

        jobs = self.repo.claim_batch(
            self.batch_size
        )

        if not jobs:
            return 0

        processed = 0

        for job in jobs:

            job_id = int(
                job["id"]
            )

            attempts = int(
                job.get("attempts")
                or 0
            )

            try:

                message_id = self.send_one(
                    job
                )

                self.repo.mark_sent(
                    job_id=job_id,
                    event_id=int(
                        job["event_id"]
                    ),
                    guest_id=str(
                        job["guest_id"]
                    ),
                    provider_message_id=(
                        message_id
                    ),
                )

                processed += 1

                logger.info(
                    "Email job %s marked SENT",
                    job_id,
                )

            except Exception as exc:

                logger.exception(
                    "Email job %s failed "
                    "(attempt %s)",
                    job_id,
                    attempts,
                )

                # ----------------------------------------------------
                # Retry policy
                # ----------------------------------------------------

                retry = attempts < 5

                try:

                    self.repo.mark_failed(
                        job_id=job_id,
                        error=str(exc),
                        retry=retry,
                    )

                except Exception:

                    logger.exception(
                        "Unable to mark "
                        "email job %s failed",
                        job_id,
                    )

        return processed

    # ================================================================
    # FOREVER
    # ================================================================

    def run_forever(self):

        logger.info(
            "EventLah email worker started"
        )

        while True:

            try:

                processed = self.run_once()

                if processed == 0:
                    time.sleep(
                        self.poll_seconds
                    )

            except KeyboardInterrupt:

                logger.info(
                    "Email worker stopped"
                )

                break

            except Exception:

                logger.exception(
                    "Email worker iteration failed"
                )

                time.sleep(
                    self.poll_seconds
                )


# ====================================================================
# ENTRY POINT
# ====================================================================

def main():

    worker = EmailWorker(
        batch_size=int(
            os.getenv(
                "EMAIL_WORKER_BATCH_SIZE",
                "10",
            )
        ),
        poll_seconds=int(
            os.getenv(
                "EMAIL_WORKER_POLL_SECONDS",
                "5",
            )
        ),
    )

    worker.run_forever()


if __name__ == "__main__":
    main()