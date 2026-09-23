from unittest.mock import patch

import pytest

from guest_management.core.request_context import (
    RequestContextError,
    get_client_ip,
    get_cookie,
    get_event_context,
    get_headers,
    get_router_data,
    get_session_id,
)


class FakeContext:
    def __init__(self, router_data):
        self.router_data = router_data


def test_get_router_data_returns_event_context_router_data():
    context = FakeContext(
        {
            "headers": {
                "cookie": "eventlah_session=test-session",
            },
            "client_ip": "192.168.1.10",
        }
    )

    with patch(
        "guest_management.core.request_context.EventContext.get",
        return_value=context,
    ):
        assert get_router_data()["client_ip"] == "192.168.1.10"


def test_get_headers_normalizes_header_names():
    context = FakeContext(
        {
            "headers": {
                "Cookie": "eventlah_session=test-session",
                "X-Test": "value",
            }
        }
    )

    with patch(
        "guest_management.core.request_context.EventContext.get",
        return_value=context,
    ):
        assert get_headers() == {
            "cookie": "eventlah_session=test-session",
            "x-test": "value",
        }


def test_get_cookie_returns_requested_cookie():
    context = FakeContext(
        {
            "headers": {
                "cookie": (
                    "foo=bar; "
                    "eventlah_session=abc123; "
                    "another=value"
                )
            }
        }
    )

    with patch(
        "guest_management.core.request_context.EventContext.get",
        return_value=context,
    ):
        assert get_cookie("eventlah_session") == "abc123"


def test_get_session_id_returns_eventlah_session():
    context = FakeContext(
        {
            "headers": {
                "cookie": "eventlah_session=abc123",
            }
        }
    )

    with patch(
        "guest_management.core.request_context.EventContext.get",
        return_value=context,
    ):
        assert get_session_id() == "abc123"


def test_get_session_id_returns_none_when_cookie_missing():
    context = FakeContext(
        {
            "headers": {
                "cookie": "other=value",
            }
        }
    )

    with patch(
        "guest_management.core.request_context.EventContext.get",
        return_value=context,
    ):
        assert get_session_id() is None


def test_get_cookie_handles_missing_cookie_header():
    context = FakeContext(
        {
            "headers": {},
        }
    )

    with patch(
        "guest_management.core.request_context.EventContext.get",
        return_value=context,
    ):
        assert get_cookie("eventlah_session") is None


def test_get_cookie_handles_malformed_cookie_header():
    context = FakeContext(
        {
            "headers": {
                "cookie": "\x00\x01\x02",
            }
        }
    )

    with patch(
        "guest_management.core.request_context.EventContext.get",
        return_value=context,
    ):
        assert get_cookie("eventlah_session") is None


def test_get_client_ip_returns_router_client_ip():
    context = FakeContext(
        {
            "client_ip": "203.0.113.10",
        }
    )

    with patch(
        "guest_management.core.request_context.EventContext.get",
        return_value=context,
    ):
        assert get_client_ip() == "203.0.113.10"


def test_get_client_ip_returns_none_when_missing():
    context = FakeContext({})

    with patch(
        "guest_management.core.request_context.EventContext.get",
        return_value=context,
    ):
        assert get_client_ip() is None


def test_get_event_context_raises_when_no_context():
    with patch(
        "guest_management.core.request_context.EventContext.get",
        side_effect=RuntimeError("no context"),
    ):
        with pytest.raises(RequestContextError):
            get_event_context()
