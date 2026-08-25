"""SendGrid Event Webhook processing."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from guest_management.repositories.email_job_repository import (
    EmailJobRepository,
)

logger = logging.getLogger(__name__)


class SendGridWebhookService:

    def __init__(
        self,
        repository: EmailJobRepository | None = None,
    ):
        self.repo = repository or EmailJobRepository()

    def process_events(
        self,
        events: List[Dict[str, Any]],
    ) -> Dict[str, int]:

        summary = {
            "received": 0,
            "updated": 0,
            "ignored": 0,
        }

        for event in events:

            summary["received"] += 1

            event_name = str(
                event.get("event") or ""
            ).strip()

            message_id = str(
                event.get("sg_message_id") or ""
            ).strip()

            if not event_name or not message_id:
                summary["ignored"] += 1
                continue

            reason = (
                event.get("reason")
                or event.get("response")
                or event.get("status")
            )

            try:
                updated = (
                    self.repo.update_provider_event(
                        provider_message_id=message_id,
                        event=event_name,
                        timestamp=event.get("timestamp"),
                        reason=reason,
                    )
                )

                if updated:
                    summary["updated"] += 1
                else:
                    summary["ignored"] += 1

            except Exception:
                logger.exception(
                    "Failed processing SendGrid event "
                    "message_id=%s event=%s",
                    message_id,
                    event_name,
                )
                summary["ignored"] += 1

        return summary