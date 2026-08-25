# guest_management/utils/url.py
"""URL utilities."""

import os
from typing import Optional


def normalize_base_url(url: str) -> str:
    """Normalize base URL for consistent usage."""
    if not url:
        return "http://localhost:3000"

    # Fix double protocols
    if url.startswith("https://http://"):
        url = url.replace("https://http://", "https://")
    elif url.startswith("http://https://"):
        url = url.replace("http://https://", "https://")

    # Remove trailing slash
    return url.rstrip('/')


def get_app_url() -> str:
    """Get the application URL from environment."""
    url = os.getenv("APP_URL", "http://localhost:3000")
    return normalize_base_url(url)


def extract_guest_id_from_url(url: str) -> Optional[str]:
    """Extract guest_id from QR URL."""
    try:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        return params.get("guest_id", [None])[0] or params.get("guest", [None])[0]
    except Exception:
        return None


def extract_event_id_from_url(url: str) -> Optional[str]:
    """Extract event_id from QR URL."""
    try:
        from urllib.parse import urlparse, parse_qs
        parsed = urlparse(url)
        path_parts = parsed.path.strip("/").split("/")
        if len(path_parts) >= 2 and path_parts[-2] in ("checkin", "scanner"):
            return path_parts[-1]

        params = parse_qs(parsed.query)
        return params.get("event_id", [None])[0]
    except Exception:
        return None


def is_public_route(path: str) -> bool:
    """Check if a route is public (no auth required)."""
    public_routes = [
        "/", "/home", "/login", "/checkin", "/success",
        "/already-checked", "/stall", "/stall/menu",
        "/scanner", "/scanner-guest", "/scanner_guest"
    ]
    return any(path.startswith(route) for route in public_routes)