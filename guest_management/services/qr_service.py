"""QR generation and validation service."""

from __future__ import annotations

import base64
import logging
from io import BytesIO
from typing import Optional
from urllib.parse import urlencode

import qrcode
from PIL import Image

from guest_management.core.config import settings
from guest_management.core.security import create_qr_token, verify_qr_token

logger = logging.getLogger(__name__)


class QRService:
    def __init__(self):
        self.app_url = settings.app_url

    @staticmethod
    def _normalize_url(url: str) -> str:
        return url.rstrip("/")

    def guest_url(self, guest_id: str, event_id: int) -> str:
        token = create_qr_token(int(event_id), guest_id)
        query = urlencode({"guest_id": guest_id, "token": token})
        return f"{self.app_url}/checkin/{int(event_id)}?{query}"

    def generate_guest_qr(self, guest_id: str, event_id: int) -> str:
        return self.generate_qr(self.guest_url(guest_id, event_id))

    def validate_guest_qr(self, guest_id: str, event_id: int, token: str) -> bool:
        return verify_qr_token(int(event_id), guest_id, token)

    def generate_event_qr(self, event_id: int) -> str:
        return self.generate_qr(f"{self.app_url}/checkin?event_id={int(event_id)}")

    def generate_stall_qr(self, stall_id: int, event_id: int) -> str:
        return self.generate_qr(
            f"{self.app_url}/stall?{urlencode({'stall_id': int(stall_id), 'event_id': int(event_id)})}"
        )

    def generate_qr(self, url: str) -> str:
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=8,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        image = qr.make_image(fill_color="black", back_color="white").convert("RGB")
        buffer = BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")

    def generate_qr_with_logo(self, url: str, logo_base64: Optional[str] = None) -> str:
        qr = qrcode.QRCode(
            version=None,
            error_correction=qrcode.constants.ERROR_CORRECT_H,
            box_size=8,
            border=4,
        )
        qr.add_data(url)
        qr.make(fit=True)
        image = qr.make_image(fill_color="black", back_color="white").convert("RGB")

        if logo_base64 and logo_base64.startswith("data:image"):
            try:
                logo_data = logo_base64.split(",", 1)[1]
                logo = Image.open(BytesIO(base64.b64decode(logo_data))).convert("RGBA")
                size = image.width // 5
                logo.thumbnail((size, size))
                position = ((image.width - logo.width) // 2, (image.height - logo.height) // 2)
                image.paste(logo, position, logo)
            except Exception:
                logger.exception("Failed to embed QR logo; generating QR without logo")

        buffer = BytesIO()
        image.save(buffer, format="PNG", optimize=True)
        return "data:image/png;base64," + base64.b64encode(buffer.getvalue()).decode("ascii")
