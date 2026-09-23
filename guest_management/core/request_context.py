from __future__ import annotations

from http.cookies import SimpleCookie
from typing import Any

from reflex_base.event.context import EventContext


SESSION_COOKIE_NAME = "eventlah_session"


class RequestContextError(RuntimeError):
    """Raised when the current Reflex event context cannot be accessed."""


def get_event_context() -> EventContext:
    """Return the current Reflex EventContext."""
    try:
        return EventContext.get()
    except Exception as exc:
        raise RequestContextError(
            "No active Reflex EventContext is available."
        ) from exc


def get_router_data() -> dict[str, Any]:
    """Return router data from the current Reflex event."""
    context = get_event_context()
    return context.router_data


def get_headers() -> dict[str, str]:
    """Return HTTP headers captured by Reflex for the current event."""
    router_data = get_router_data()
    headers = router_data.get("headers", {})

    if not isinstance(headers, dict):
        return {}

    return {
        str(key).lower(): str(value)
        for key, value in headers.items()
    }


def get_cookie(name: str) -> str | None:
    """Return one cookie from the current request."""
    cookie_header = get_headers().get("cookie")

    if not cookie_header:
        return None

    cookie = SimpleCookie()

    try:
        cookie.load(cookie_header)
    except Exception:
        return None

    morsel = cookie.get(name)

    if morsel is None:
        return None

    value = morsel.value.strip()

    return value or None


def get_session_id() -> str | None:
    """Return the EventLah opaque session ID from the request cookie."""
    try:
        headers = get_headers()
        cookie_header = headers.get("cookie")
        session_id = get_cookie(SESSION_COOKIE_NAME)

        print(
            "[AUTH DEBUG] get_session_id:",
            {
                "has_cookie_header": bool(cookie_header),
                "cookie_header": (
                    cookie_header[:120]
                    if cookie_header
                    else None
                ),
                "has_session_id": bool(session_id),
            },
            flush=True,
        )

        return session_id

    except Exception as exc:
        print(
            "[AUTH DEBUG] get_session_id ERROR:",
            repr(exc),
            flush=True,
        )
        raise


def get_client_ip() -> str | None:
    """Return the client IP recorded by Reflex."""
    router_data = get_router_data()

    client_ip = router_data.get("client_ip")

    if client_ip is None:
        return None

    value = str(client_ip).strip()

    return value or None
