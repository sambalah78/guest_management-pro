"""SendGrid webhook endpoint."""

from __future__ import annotations

import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from guest_management.services.sendgrid_webhook_service import (
    SendGridWebhookService,
)

logger = logging.getLogger(__name__)

router = APIRouter()


@router.post(
    "/api/webhooks/sendgrid",
    include_in_schema=False,
)
async def sendgrid_webhook(
    request: Request,
):
    try:
        payload = await request.json()

        if not isinstance(payload, list):
            return JSONResponse(
                status_code=400,
                content={
                    "error": "Expected JSON array"
                },
            )

        result = SendGridWebhookService().process_events(
            payload
        )

        logger.info(
            "SendGrid webhook processed: %s",
            result,
        )

        return JSONResponse(
            status_code=200,
            content={
                "ok": True,
                **result,
            },
        )

    except Exception:
        logger.exception(
            "SendGrid webhook processing failed"
        )

        # Return 200 so SendGrid doesn't repeatedly retry
        # malformed/unprocessable payloads forever.
        return JSONResponse(
            status_code=200,
            content={
                "ok": False,
            },
        )