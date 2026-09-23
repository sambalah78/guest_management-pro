"""Durable Gmail email worker.

Run:

    python -m guest_management.workers.email_worker

The worker:
1. Claims queued email jobs.
2. Generates the guest QR code.
3. Creates a Gmail SMTP email.
4. Adds the QR as an inline MIME image.
5. Adds event branding from storage.
6. Sends the email through Gmail SMTP.
7. Marks the job sent.
8. Marks the guest email_sent=True.
9. Retries eligible failures.
"""

from __future__ import annotations

import io
import logging
import os
import smtplib
import time

logger = logging.getLogger(__name__)
from email.message import EmailMessage
from email.utils import formataddr
from typing import Any, Dict, Optional

import qrcode

from guest_management.core.config import settings
from guest_management.repositories.email_job_repository import (
    EmailJobRepository,
)
from guest_management.repositories.event_repository import EventRepository
from guest_management.repositories.guest_repository import GuestRepository
from guest_management.services.storage_service import StorageService

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
        self.storage_service = StorageService()

        provider = getattr(
            settings,
            "email_provider",
            "gmail",
        ).strip().lower()

        if provider != "gmail":
            raise RuntimeError(
                f"Unsupported email provider: {provider}"
            )

        if not settings.smtp_username:
            raise RuntimeError(
                "SMTP_USERNAME is not configured"
            )

        if not settings.smtp_password:
            raise RuntimeError(
                "SMTP_PASSWORD is not configured"
            )

        if not settings.sender_email:
            raise RuntimeError(
                "SENDER_EMAIL is not configured"
            )

        self.sender = settings.sender_email

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
            "Using stored QR event=%s guest=%s",
            event_id,
            guest_id,
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

    def _add_storage_asset(
            self,
            message: EmailMessage,
            event: Dict[str, Any],
            *,
            storage_path_key: str,
            filename_key: str,
            mime_key: str,
            content_id: str,
            inline: bool,
    ) -> bool:
        """Download an event asset from Supabase Storage and add it to the email."""

        storage_path = str(
            event.get(storage_path_key) or ""
        ).strip()

        if not storage_path:
            return False

        try:
            data = self.storage_service.download(storage_path)

            if not data:
                logger.warning(
                    "Event asset is empty: event=%s path=%s",
                    event["id"],
                    storage_path,
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

            maintype, subtype = (
                mime_type.split("/", 1)
                if "/" in mime_type
                else ("application", "octet-stream")
            )

            if inline:
                # Add inline asset to the HTML/related part.
                payload = message.get_payload()

                if not isinstance(payload, list) or len(payload) < 2:
                    raise RuntimeError(
                        "Email message does not contain an HTML part"
                    )

                html_part = payload[-1]

                html_part.add_related(
                    data,
                    maintype=maintype,
                    subtype=subtype,
                    cid=f"<{content_id}>",
                    filename=filename,
                )

            else:
                # Regular attachment on the root email.
                message.add_attachment(
                    data,
                    maintype=maintype,
                    subtype=subtype,
                    filename=filename,
                )

            logger.info(
                "Event storage asset added: "
                "event=%s path=%s filename=%s inline=%s",
                event["id"],
                storage_path,
                filename,
                inline,
            )

            return True

        except Exception:
            logger.exception(
                "Failed to add event storage asset: "
                "event=%s path=%s",
                event.get("id"),
                storage_path,
            )
            return False

    def _add_event_branding(
        self,
        message: EmailMessage,
        event: Dict[str, Any],
    ) -> tuple[bool, bool]:
        """
        Add the event logo and invitation from Supabase Storage.

        Returns:
        (logo_added, invitation_added)
        """

        logo_added = self._add_storage_asset(
            message,
            event,
            storage_path_key="logo_storage_path",
            filename_key="logo_filename",
            mime_key="logo_mime_type",
            content_id="event-logo",
            inline=True,
        )

        invitation_storage_path = str(
            event.get("invitation_storage_path") or ""
        ).strip()

        invitation_mime = str(
            event.get("invitation_mime_type") or ""
        ).strip().lower()

        invitation_inline = bool(
            invitation_storage_path
            and invitation_mime.startswith("image/")
        )

        invitation_added = self._add_storage_asset(
            message,
            event,
            storage_path_key="invitation_storage_path",
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
    # BUILD GMAIL MESSAGE
    # ================================================================

    def build_message(
            self,
            job: Dict[str, Any],
    ) -> EmailMessage:
        event_id = int(job["event_id"])
        guest_id = str(job["guest_id"])

        recipient = str(job["recipient"]).strip()
        subject = str(
            job.get("subject") or "Event Invitation"
        )

        html_content = str(
            job.get("html_content") or ""
        )

        plain_text = str(
            job.get("plain_text") or ""
        )

        message = EmailMessage()

        message["From"] = formataddr(
            ("EventLah Solutions", self.sender)
        )
        message["To"] = recipient
        message["Subject"] = subject

        if plain_text:
            message.set_content(plain_text)

        message.add_alternative(
            html_content,
            subtype="html",
        )

        qr_png = self.build_qr_png(
            event_id=event_id,
            guest_id=guest_id,
        )

        message.get_payload()[1].add_related(
            qr_png,
            maintype="image",
            subtype="png",
            cid="<guest-qr>",
            filename="eventlah-guest-qr.png",
        )

        return message
    # ================================================================
    # SEND ONE
    # ================================================================

    def _connect_smtp(self) -> smtplib.SMTP:
        """Create and authenticate one Gmail SMTP connection."""

        smtp = smtplib.SMTP(
                settings.smtp_host,
                settings.smtp_port,
                timeout=30,
        )

        try:
            smtp.ehlo()
            smtp.starttls()
            smtp.ehlo()

            smtp.login(
                settings.smtp_username,
                settings.smtp_password,
            )

            return smtp

        except Exception:
            try:
                smtp.quit()
            except Exception:
                smtp.close()
            raise

    def send_one(
            self,
            job: Dict[str, Any],
            smtp: Optional[smtplib.SMTP] = None,
    ) -> str:
        job_id = int(job["id"])
        guest_id = str(job["guest_id"])
        recipient = str(job["recipient"]).strip()

        logger.info(
            "Sending Gmail email job=%s guest=%s",
            job_id,
            guest_id,
        )

        message = self.build_message(job)

        owns_smtp = smtp is None

        if owns_smtp:
            smtp = self._connect_smtp()

        try:
            smtp.send_message(message)

        finally:
            if owns_smtp:
                try:
                    smtp.quit()
                except Exception:
                    smtp.close()

        logger.info(
            "Gmail accepted email job=%s",
            job_id,
        )

        return ""

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
        smtp: Optional[smtplib.SMTP] = None

        try:
            for job in jobs:

                job_id = int(
                    job["id"]
                )

                attempts = int(
                    job.get("attempts")
                    or 0
                )

                try:

                    if smtp is None:
                        smtp = self._connect_smtp()

                    message_id = self.send_one(
                        job,
                        smtp=smtp,
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

                    # ------------------------------------------------
                    # Retry policy
                    # ------------------------------------------------

                    retry = attempts < settings.email_max_attempts

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

                    # ------------------------------------------------
                    # Discard a connection after an SMTP/network
                    # failure so the next job can establish a fresh
                    # authenticated connection.
                    # ------------------------------------------------

                    if isinstance(
                        exc,
                        (
                            smtplib.SMTPException,
                            OSError,
                            TimeoutError,
                        ),
                    ):
                        if smtp is not None:
                            try:
                                smtp.quit()
                            except Exception:
                                smtp.close()

                        smtp = None

        finally:
            if smtp is not None:
                try:
                    smtp.quit()
                except Exception:
                    smtp.close()

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
        batch_size=settings.email_worker_batch_size,
        poll_seconds=int(
            settings.email_worker_interval_seconds
        ),
    )

    worker.run_forever()


if __name__ == "__main__":
    main()