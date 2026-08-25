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
        self.drive_service = GoogleDriveAssetService()

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

    @staticmethod
    def build_qr_png(
        event_id: int,
        guest_id: str,
    ) -> bytes:
        """
        Generate the guest's QR code.

        The URL must be the same URL used by EventLah's
        guest/check-in flow.
        """

        qr_url = EmailService.build_guest_qr_url(
            event_id=int(event_id),
            guest_id=str(guest_id),
        )

        logger.debug(
            "QR URL event=%s guest=%s: %s",
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

    def _add_wedding_invitation(
            self,
            message: Mail,
            event_id: int,
    ) -> None:
        """Attach the wedding invitation stored in Google Drive."""

        event = self.event_repo.get_by_id_public(
            int(event_id)
        )

        if not event:
            logger.warning(
                "Event %s not found while attaching wedding invitation",
                event_id,
            )
            return

        event_type = str(
            event.get("event_type") or ""
        ).strip().lower()

        if event_type != "wedding_dinner":
            return

        invitation_file_id = str(
            event.get("invitation_drive_file_id") or ""
        ).strip()

        if not invitation_file_id:
            logger.info(
                "Wedding event %s has no invitation asset",
                event_id,
            )
            return

        try:
            invitation_bytes = (
                self.drive_service.download_bytes(
                    invitation_file_id
                )
            )

            if not invitation_bytes:
                logger.warning(
                    "Wedding invitation asset is empty: "
                    "event=%s file=%s",
                    event_id,
                    invitation_file_id,
                )
                return

            filename = str(
                event.get("invitation_filename")
                or f"event_{event_id}_invitation.png"
            ).strip()

            mime_type = str(
                event.get("invitation_mime_type")
                or "application/octet-stream"
            ).strip()

            invitation_base64 = (
                base64.b64encode(
                    invitation_bytes
                ).decode("ascii")
            )

            attachment = Attachment()

            attachment.file_content = FileContent(
                invitation_base64
            )

            attachment.file_type = FileType(
                mime_type
            )

            attachment.file_name = FileName(
                filename
            )

            attachment.disposition = Disposition(
                "attachment"
            )

            message.add_attachment(
                attachment
            )

            logger.info(
                "Wedding invitation attached: "
                "event=%s file=%s filename=%s",
                event_id,
                invitation_file_id,
                filename,
            )

        except Exception:
            logger.exception(
                "Failed to attach wedding invitation: "
                "event=%s file=%s",
                event_id,
                invitation_file_id,
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

        # ------------------------------------------------------------
        # Build normal SendGrid message
        # ------------------------------------------------------------

        message = Mail(
            from_email=self.sender,
            to_emails=recipient,
            subject=subject,
        )

        # ------------------------------------------------------------
        # Plain text
        # ------------------------------------------------------------

        if plain_text:
            message.add_content(
                Content(
                    "text/plain",
                    plain_text,
                )
            )

        # ------------------------------------------------------------
        # HTML
        # ------------------------------------------------------------

        if html_content:
            message.add_content(
                Content(
                    "text/html",
                    html_content,
                )
            )

        # ------------------------------------------------------------
        # Generate QR
        # ------------------------------------------------------------

        qr_png = self.build_qr_png(
            event_id=event_id,
            guest_id=guest_id,
        )

        qr_base64 = base64.b64encode(
            qr_png
        ).decode("ascii")

        # ------------------------------------------------------------
        # Inline attachment
        #
        # This is what makes:
        #
        #     <img src="cid:guest-qr">
        #
        # work inside the email.
        # ------------------------------------------------------------

        attachment = Attachment()

        attachment.file_content = FileContent(
            qr_base64
        )

        attachment.file_type = FileType(
            "image/png"
        )

        attachment.file_name = FileName(
            "eventlah-guest-qr.png"
        )

        attachment.disposition = Disposition(
            "inline"
        )

        attachment.content_id = "guest-qr"

        message.add_attachment(
            attachment
        )
        # ------------------------------------------------------------
        # Wedding invitation
        # ------------------------------------------------------------

        self._add_wedding_invitation(
            message,
            event_id,
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