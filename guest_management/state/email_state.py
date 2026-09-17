"""Email management UI state backed by a durable email queue.

The UI never talks directly to SendGrid.

All email actions operate on the durable ``email_jobs`` queue.
The background email worker is responsible for actual delivery.

Supported operations:

- Send invitation to one guest
- Queue invitations for all unsent guests
- View email delivery summary
- View individual email jobs
- Refresh delivery status
- Retry failed/cancelled jobs
- Retry all failed/cancelled jobs
- Explicitly resend an already-sent email
- Success/error feedback through Reflex toasts
"""

from __future__ import annotations

import logging
import re
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import Any, Dict, List, Optional

import reflex as rx

from guest_management.core.exceptions import EventLahError
from guest_management.repositories import (

    GuestRepository,
)
from guest_management.services.event_service import EventService
from guest_management.repositories.email_job_repository import (
    EmailJobRepository,
)
from guest_management.services.email_service import EmailService


logger = logging.getLogger(__name__)


class EmailState(rx.State):
    # ==========================================================================
    # EXISTING EMAIL SEND STATE
    # ==========================================================================

    email_sending: bool = False
    email_progress: int = 0
    email_total: int = 0

    sending_email_guest_id: str = ""

    email_dialog_open: bool = False
    selected_guest_for_email: Optional[dict] = None

    is_loading: bool = False

    current_event_id: str = ""

    # ==========================================================================
    # EMAIL MANAGEMENT STATE
    # ==========================================================================

    email_management_open: bool = False
    email_management_loading: bool = False

    email_summary: Dict[str, int] = {
        "queued": 0,
        "processing": 0,
        "sent": 0,
        "failed": 0,
        "cancelled": 0,
    }

    email_jobs: List[Dict[str, Any]] = []

    # Currently executing job action.
    email_action_job_id: int = 0
    email_action_type: str = ""

    # UI feedback state.
    email_error: str = ""
    email_message: str = ""

    # Delivery-details modal.
    delivery_details_open: bool = False
    selected_delivery_job: Dict[str, Any] = {}
    selected_job_id: int = 0

    # ==========================================================================
    # COMPUTED COUNTS
    # ==========================================================================

    @rx.var
    def email_sent_count(self) -> int:
        return int(self.email_summary.get("sent", 0))

    @rx.var
    def email_queued_count(self) -> int:
        return int(self.email_summary.get("queued", 0))

    @rx.var
    def email_processing_count(self) -> int:
        return int(self.email_summary.get("processing", 0))

    @rx.var
    def email_failed_count(self) -> int:
        return int(self.email_summary.get("failed", 0))

    @rx.var
    def email_cancelled_count(self) -> int:
        return int(self.email_summary.get("cancelled", 0))

    @rx.var
    def email_pending_count(self) -> int:
        return (
            self.email_queued_count
            + self.email_processing_count
        )

    # ==========================================================================
    # URL / EVENT
    # ==========================================================================

    def _event_id_from_url(self) -> int:
        """Extract event_id from /dashboard/<event_id>."""

        path = getattr(
            self.router.url,
            "path",
            "",
        ) or ""

        match = re.search(
            r"/dashboard/(\d+)",
            path,
        )

        if not match:
            raise ValueError(
                "No event selected."
            )

        return int(match.group(1))

    @staticmethod
    def _format_delivery_datetime(value: Any) -> str:
        """Format stored UTC delivery timestamps as Malaysia time."""
        if value is None or value == "":
            return ""
        try:
            if isinstance(value, datetime):
                dt = value
            else:
                text_value = str(value).strip()
                if not text_value:
                    return ""
                dt = datetime.fromisoformat(text_value.replace("Z", "+00:00"))
            if dt.tzinfo is None:
                dt = dt.replace(tzinfo=timezone.utc)
            dt = dt.astimezone(ZoneInfo("Asia/Kuala_Lumpur"))
            return dt.strftime("%d-%b-%Y %H:%M:%S")
        except (TypeError, ValueError, OverflowError):
            return str(value)

    @classmethod
    def _prepare_delivery_job(cls, job: Dict[str, Any], event_id: int) -> Dict[str, Any]:
        """Normalize delivery fields for Reflex-safe rendering."""
        fields = {
            "id": int(job.get("id") or 0),
            "event_id": int(job.get("event_id") or event_id),
            "guest_id": str(job.get("guest_id") or ""),
            "email_type": str(job.get("email_type") or ""),
            "recipient": str(job.get("recipient") or ""),
            "subject": str(job.get("subject") or ""),
            "status": str(job.get("status") or ""),
            "attempts": int(job.get("attempts") or 0),
            "last_error": str(job.get("last_error") or ""),
            "provider_message_id": str(job.get("provider_message_id") or ""),
            "provider_status": str(job.get("provider_status") or ""),
        }
        for key in (
            "available_at", "locked_at", "sent_at", "delivered_at",
            "bounced_at", "opened_at", "clicked_at", "created_at", "updated_at",
        ):
            fields[key] = cls._format_delivery_datetime(job.get(key))
        return fields

    def _get_current_event_id(self) -> int:
        """Return the active event ID."""

        if self.current_event_id:
            return int(self.current_event_id)

        return self._event_id_from_url()

    # ==========================================================================
    # EMAIL DIALOG
    # ==========================================================================

    def open_email_dialog(
        self,
        guest: dict,
    ):
        """Open the email dialog for one guest."""

        self.selected_guest_for_email = dict(
            guest
        )

        self.current_event_id = str(
            self._event_id_from_url()
        )

        self.email_error = ""
        self.email_message = ""

        self.email_dialog_open = True

    def close_email_dialog(self):
        """Close the email dialog."""

        self.email_dialog_open = False
        self.selected_guest_for_email = None
        self.sending_email_guest_id = ""

        self.email_error = ""
        self.email_message = ""

    # ==========================================================================
    # SEND EMAIL TO ONE GUEST
    # ==========================================================================

    async def send_guest_email(self):
        """Queue an invitation email for the selected guest.

        If the guest already has ``email_sent=True``, this becomes an
        explicit resend operation by using ``force=True``.
        """

        if not self.selected_guest_for_email:
            yield rx.toast.error(
                "No guest selected."
            )
            return

        self.is_loading = True
        self.email_error = ""
        self.email_message = ""

        guest = self.selected_guest_for_email

        guest_id = str(
            guest.get("ID")
            or guest.get("guest_id")
            or ""
        )

        email = str(
            guest.get("Email")
            or guest.get("email")
            or ""
        ).strip()

        self.sending_email_guest_id = guest_id

        yield

        try:
            event_id = self._get_current_event_id()

            self.current_event_id = str(
                event_id
            )

            from guest_management.state.auth_state import AuthState

            auth = await self.get_state(AuthState)

            if not auth.user_id:
                raise ValueError("Not authenticated.")

            event = EventService().get_event(
                event_id,
                auth.user_id,
                auth.user,
            )

            if not event:
                raise ValueError(
                    "Event not found or access denied."
                )

            if not guest_id:
                raise ValueError(
                    "Guest ID is missing."
                )

            if not email:
                raise ValueError(
                    "No email address for this guest."
                )

            force = bool(
                guest.get("email_sent")
            )

            EmailService().enqueue_guest_invitation(
                event,
                {
                    **guest,
                    "guest_id": guest_id,
                    "email": email,
                },
                force=force,
            )

            self.email_dialog_open = False

            self.email_message = (
                "Email queued successfully. "
                "Delivery will continue in the background."
            )

            yield rx.toast.success(
                self.email_message
            )

        except EventLahError as exc:
            message = getattr(
                exc,
                "message",
                str(exc),
            )

            self.email_error = str(
                message
            )

            yield rx.toast.error(
                self.email_error
            )

        except Exception as exc:
            logger.exception(
                "Unable to queue guest email"
            )

            self.email_error = (
                "Unable to queue email. "
                "Please try again."
            )

            logger.debug(
                "Guest email queue error: %s",
                exc,
            )

            yield rx.toast.error(
                self.email_error
            )

        finally:
            self.is_loading = False
            self.sending_email_guest_id = ""

            yield

    # ==========================================================================
    # BULK EMAIL QUEUE
    # ==========================================================================

    async def process_email_queue(self):
        """Queue invitations for all currently unsent guests."""

        self.email_sending = True
        self.is_loading = True

        self.email_progress = 0
        self.email_total = 0

        self.email_error = ""
        self.email_message = ""

        yield

        try:
            event_id = self._event_id_from_url()

            self.current_event_id = str(
                event_id
            )

            from guest_management.state.auth_state import AuthState

            auth = await self.get_state(AuthState)

            if not auth.user_id:
                raise ValueError("Not authenticated.")

            event = EventService().get_event(
                event_id,
                auth.user_id,
                auth.user,
            )

            if not event:
                raise ValueError(
                    "Event not found or access denied."
                )

            guest_repo = GuestRepository()
            email_service = EmailService()

            queued = 0
            total_candidates = 0
            page = 1

            while True:
                guests, total = guest_repo.get_by_event(
                    event_id,
                    limit=200,
                    offset=(page - 1) * 200,
                )

                total_candidates = total

                if not guests:
                    break

                unsent = [
                    guest
                    for guest in guests
                    if guest.get("email")
                    and not guest.get("email_sent")
                ]

                if unsent:
                    queued += (
                        email_service.enqueue_bulk_invitations(
                            event,
                            unsent,
                        )
                    )

                self.email_progress = queued
                self.email_total = total_candidates

                yield

                if len(guests) < 200:
                    break

                page += 1

            self.email_sending = False
            self.is_loading = False

            self.email_message = (
                f"Queued {queued} invitation "
                f"email(s). Delivery continues "
                f"in the background."
            )

            yield rx.toast.success(
                self.email_message
            )

        except Exception as exc:
            logger.exception(
                "Bulk email queueing failed"
            )

            self.email_sending = False
            self.is_loading = False

            self.email_error = (
                "Unable to queue bulk email. "
                "Please try again."
            )

            logger.debug(
                "Bulk email error: %s",
                exc,
            )

            yield rx.toast.error(
                self.email_error
            )

        finally:
            self.email_sending = False
            self.is_loading = False
            self.sending_email_guest_id = ""

            yield

    # ==========================================================================
    # EMAIL MANAGEMENT
    # ==========================================================================

    def open_email_management(self):
        """Open the dashboard email management panel."""

        self.current_event_id = str(
            self._event_id_from_url()
        )

        self.email_error = ""
        self.email_message = ""

        self.email_management_open = True

        self.load_email_management()

    def close_email_management(self):
        """Close the dashboard email management panel."""

        self.email_management_open = False

    def load_email_management(self):
        """Load email counts and recent jobs."""

        try:
            event_id = self._get_current_event_id()

            repo = EmailJobRepository()

            self.email_summary = (
                repo.get_event_summary(
                    event_id
                )
            )

            self.email_jobs = [
                self._prepare_delivery_job(job, event_id)
                for job in repo.get_event_jobs(event_id, limit=100)
            ]

            self.email_error = ""

        except Exception:
            logger.exception(
                "Unable to load email management"
            )

            self.email_summary = {
                "queued": 0,
                "processing": 0,
                "sent": 0,
                "failed": 0,
                "cancelled": 0,
            }

            self.email_jobs = []

            self.email_error = (
                "Unable to load email delivery status."
            )

    # ==========================================================================
    # REFRESH
    # ==========================================================================

    async def refresh_email_management(self):
        """Refresh email dashboard data."""

        self.email_management_loading = True
        self.email_error = ""
        self.email_message = ""

        yield

        try:
            self.load_email_management()

            if self.email_error:
                yield rx.toast.error(
                    self.email_error
                )
            else:
                self.email_message = (
                    "Email status refreshed."
                )

                yield rx.toast.success(
                    self.email_message
                )

        except Exception:
            logger.exception(
                "Email management refresh failed"
            )

            self.email_error = (
                "Unable to refresh email status."
            )

            yield rx.toast.error(
                self.email_error
            )

        finally:
            self.email_management_loading = False

            yield

    # ==========================================================================
    # SAFE RETRY
    # ==========================================================================

    async def retry_email_job(
        self,
        job_id: int,
    ):
        """Retry a failed or cancelled email job.

        This method deliberately refuses to retry jobs that are already
        queued, processing, or sent.
        """

        self.email_action_job_id = int(
            job_id
        )

        self.email_action_type = "retry"

        self.email_error = ""
        self.email_message = ""

        yield

        try:
            event_id = self._get_current_event_id()

            repo = EmailJobRepository()

            job = repo.get_job(
                int(job_id),
                event_id,
            )

            if not job:
                raise ValueError(
                    "Email job not found."
                )

            status = str(
                job.get("status")
                or ""
            ).lower()

            if status not in {
                "failed",
                "cancelled",
            }:
                raise ValueError(
                    f"This email is '{status}' "
                    "and cannot be retried. "
                    "Only failed or cancelled "
                    "emails can be retried."
                )

            repo.retry_failed_job(
                int(job_id),
                event_id,
            )

            self.load_email_management()

            self.email_message = (
                f"Email job #{job_id} "
                "queued for retry."
            )

            yield rx.toast.success(
                self.email_message
            )

        except Exception as exc:
            logger.exception(
                "Unable to retry email job %s",
                job_id,
            )

            self.email_error = str(
                exc
            )

            yield rx.toast.error(
                self.email_error
            )

        finally:
            self.email_action_job_id = 0
            self.email_action_type = ""

            yield

    # ==========================================================================
    # SAFE RESEND
    # ==========================================================================

    async def resend_email_job(
        self,
        job_id: int,
    ):
        """Explicitly resend an already-sent email.

        This is intentionally separate from retry:

        - retry = failed/cancelled only
        - resend = sent only

        The repository performs the force enqueue against the same
        event/guest/email_type uniqueness key.
        """

        self.email_action_job_id = int(
            job_id
        )

        self.email_action_type = "resend"

        self.email_error = ""
        self.email_message = ""

        yield

        try:
            event_id = self._get_current_event_id()

            repo = EmailJobRepository()

            job = repo.get_job(
                int(job_id),
                event_id,
            )

            if not job:
                raise ValueError(
                    "Email job not found."
                )

            status = str(
                job.get("status")
                or ""
            ).lower()

            if status != "sent":
                raise ValueError(
                    f"This email is '{status}'. "
                    "Only sent emails can be resent."
                )

            result = repo.resend_sent_job(
                int(job_id),
                event_id,
            )

            if result is False:
                raise ValueError(
                    "Unable to queue email for resend."
                )

            self.load_email_management()

            self.email_message = (
                f"Email job #{job_id} "
                "queued for resend."
            )

            yield rx.toast.success(
                self.email_message
            )

        except Exception as exc:
            logger.exception(
                "Unable to resend email job %s",
                job_id,
            )

            self.email_error = str(
                exc
            )

            yield rx.toast.error(
                self.email_error
            )

        finally:
            self.email_action_job_id = 0
            self.email_action_type = ""

            yield

    # ==========================================================================
    # DELIVERY DETAILS
    # ==========================================================================

    def open_delivery_details(self, job_id: int):
        """Load one complete event-scoped delivery record and open its modal."""
        try:
            event_id = self._get_current_event_id()
            repo = EmailJobRepository()
            job = repo.get_delivery_details(
                int(job_id),
                event_id,
            )

            if not job:
                self.email_error = "Email job not found."
                self.delivery_details_open = False
                self.selected_delivery_job = {}
                return rx.toast.error(self.email_error)

            self.selected_delivery_job = self._prepare_delivery_job(
                job,
                event_id,
            )
            self.selected_job_id = int(job.get("id") or 0)
            self.delivery_details_open = True
            self.email_error = ""
            return
        except Exception as exc:
            logger.exception(
                "Unable to load delivery details for email job %s",
                job_id,
            )
            self.selected_delivery_job = {}
            self.delivery_details_open = False
            self.email_error = str(exc)
            return rx.toast.error(self.email_error)

    def close_delivery_details(self):
        """Close and clear the delivery-details modal."""
        self.delivery_details_open = False
        self.selected_delivery_job = {}
        self.selected_job_id = 0

    # ==========================================================================
    # UI COMPATIBILITY WRAPPER
    # ==========================================================================
    @rx.event
    def set_selected_job(self, job_id: int):
        self.selected_job_id = int(job_id)

    async def resend_job(
        self,
        job_id: int,
        event_id: int | None = None,
    ):
        """Compatibility wrapper used by the dashboard UI.

        The dashboard previously called:

            EmailState.resend_job(job_id, event_id)

        Keep this method so the UI does not break.

        The event_id argument is accepted for compatibility, but the
        state verifies the event from the current dashboard URL.
        """

        try:
            resolved_event_id = self._get_current_event_id()

            if event_id is not None:
                supplied_event_id = int(
                    event_id
                )

                if supplied_event_id != resolved_event_id:
                    yield rx.toast.error(
                        "Invalid event selected."
                    )
                    return

            async for result in self.resend_email_job(
                int(job_id)
            ):
                yield result

        except Exception as exc:
            logger.exception(
                "Dashboard resend failed for job %s",
                job_id,
            )

            self.email_error = str(
                exc
            )

            yield rx.toast.error(
                self.email_error
            )

    # ==========================================================================
    # RETRY JOB COMPATIBILITY WRAPPER
    # ==========================================================================

    async def retry_job(
        self,
        job_id: int,
        event_id: int | None = None,
    ):
        """Compatibility wrapper for dashboard retry buttons."""

        try:
            resolved_event_id = self._get_current_event_id()

            if event_id is not None:
                supplied_event_id = int(
                    event_id
                )

                if supplied_event_id != resolved_event_id:
                    yield rx.toast.error(
                        "Invalid event selected."
                    )
                    return

            async for result in self.retry_email_job(
                int(job_id)
            ):
                yield result

        except Exception as exc:
            logger.exception(
                "Dashboard retry failed for job %s",
                job_id,
            )

            self.email_error = str(
                exc
            )

            yield rx.toast.error(
                self.email_error
            )

    # ==========================================================================
    # RETRY ALL FAILED / CANCELLED
    # ==========================================================================

    async def retry_all_failed(self):
        """Queue all failed/cancelled jobs for this event."""

        self.email_management_loading = True
        self.email_error = ""
        self.email_message = ""

        yield

        try:
            event_id = self._get_current_event_id()

            repo = EmailJobRepository()

            count = repo.retry_failed_jobs(
                event_id
            )

            self.load_email_management()

            self.email_message = (
                f"{count} email job(s) "
                "queued for retry."
            )

            yield rx.toast.success(
                self.email_message
            )

        except Exception as exc:
            logger.exception(
                "Unable to retry failed email jobs"
            )

            self.email_error = str(
                exc
            )

            yield rx.toast.error(
                self.email_error
            )

        finally:
            self.email_management_loading = False

            yield

    # ==========================================================================
    # OPTIONAL ALIASES
    # ==========================================================================

    async def refresh_email_status(
        self,
        event_id: int | str | None = None,
    ):
        """Compatibility alias for older UI code."""

        if event_id is not None:
            self.current_event_id = str(
                int(event_id)
            )

        async for result in self.refresh_email_management():
            yield result

    # ==========================================================================
    # AUTH
    # ==========================================================================

    async def _current_user_id(self) -> str:
        """Return the currently authenticated user ID."""

        from guest_management.state.auth_state import (
            AuthState,
        )

        auth = await self.get_state(
            AuthState
        )

        return str(
            auth.user_id or ""
        )