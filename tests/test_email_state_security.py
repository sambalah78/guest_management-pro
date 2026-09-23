import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import guest_management.state.email_state as email_state_module
from guest_management.core.exceptions import AuthorizationError
from guest_management.state.email_state import EmailState


def make_admin_auth(user_id="admin-user-id"):
    return SimpleNamespace(
        user_id=user_id,
        user={
            "id": user_id,
            "role": "ADMIN",
            "is_active": True,
        },
    )


def make_unauthorized_event_service():
    event_service = MagicMock()
    event_service.get_event.side_effect = AuthorizationError(
        "Event access denied."
    )
    return event_service


def make_authorized_event_service():
    event_service = MagicMock()
    event_service.get_event.return_value = {
        "id": 10,
        "name": "Test Event",
    }
    return event_service


def configure_auth_state(monkeypatch, auth):
    monkeypatch.setattr(
        EmailState,
        "get_state",
        AsyncMock(return_value=auth),
    )


def test_email_authorization_requires_authenticated_user(monkeypatch):
    state = EmailState()

    auth = SimpleNamespace(
        user_id="",
        user=None,
    )

    configure_auth_state(monkeypatch, auth)

    with pytest.raises(AuthorizationError, match="Authentication required"):
        asyncio.run(
            state._authorize_email_event(10)
        )


def test_email_authorization_delegates_to_event_service(monkeypatch):
    state = EmailState()
    auth = make_admin_auth()

    configure_auth_state(monkeypatch, auth)

    event_service = make_authorized_event_service()

    monkeypatch.setattr(
        email_state_module,
        "EventService",
        lambda: event_service,
    )

    result = asyncio.run(
        state._authorize_email_event(10)
    )

    assert result["id"] == 10

    event_service.get_event.assert_called_once_with(
        10,
        "admin-user-id",
        auth.user,
    )


def test_load_email_management_rejects_unauthorized_event_before_repository(
    monkeypatch,
):
    state = EmailState()
    state.current_event_id = "10"

    auth = make_admin_auth()
    configure_auth_state(monkeypatch, auth)

    event_service = make_unauthorized_event_service()

    monkeypatch.setattr(
        email_state_module,
        "EventService",
        lambda: event_service,
    )

    repo_constructor = MagicMock()

    monkeypatch.setattr(
        email_state_module,
        "EmailJobRepository",
        repo_constructor,
    )

    asyncio.run(
        state.load_email_management()
    )

    event_service.get_event.assert_called_once_with(
        10,
        "admin-user-id",
        auth.user,
    )

    repo_constructor.assert_not_called()

    assert state.email_jobs == []
    assert "Unable to load email delivery status." == state.email_error


def test_load_email_management_allows_authorized_event(
    monkeypatch,
):
    state = EmailState()
    state.current_event_id = "10"

    auth = make_admin_auth()
    configure_auth_state(monkeypatch, auth)

    event_service = make_authorized_event_service()

    repo = MagicMock()
    repo.get_event_summary.return_value = {
        "queued": 1,
        "processing": 0,
        "sent": 2,
        "failed": 0,
        "cancelled": 0,
    }
    repo.get_event_jobs.return_value = []

    monkeypatch.setattr(
        email_state_module,
        "EventService",
        lambda: event_service,
    )

    monkeypatch.setattr(
        email_state_module,
        "EmailJobRepository",
        lambda: repo,
    )

    asyncio.run(
        state.load_email_management()
    )

    event_service.get_event.assert_called_once_with(
        10,
        "admin-user-id",
        auth.user,
    )

    repo.get_event_summary.assert_called_once_with(10)
    repo.get_event_jobs.assert_called_once_with(
        10,
        limit=100,
    )

    assert state.email_summary["queued"] == 1
    assert state.email_summary["sent"] == 2
    assert state.email_error == ""


def test_retry_email_job_rejects_unauthorized_event_before_repository(
    monkeypatch,
):
    state = EmailState()
    state.current_event_id = "10"

    auth = make_admin_auth()
    configure_auth_state(monkeypatch, auth)

    event_service = make_unauthorized_event_service()

    monkeypatch.setattr(
        email_state_module,
        "EventService",
        lambda: event_service,
    )

    repo_constructor = MagicMock()

    monkeypatch.setattr(
        email_state_module,
        "EmailJobRepository",
        repo_constructor,
    )

    async def run():
        async for _ in state.retry_email_job(123):
            pass

    asyncio.run(run())

    event_service.get_event.assert_called_once_with(
        10,
        "admin-user-id",
        auth.user,
    )

    repo_constructor.assert_not_called()

    assert "Event access denied." in state.email_error


def test_resend_email_job_rejects_unauthorized_event_before_repository(
    monkeypatch,
):
    state = EmailState()
    state.current_event_id = "10"

    auth = make_admin_auth()
    configure_auth_state(monkeypatch, auth)

    event_service = make_unauthorized_event_service()

    monkeypatch.setattr(
        email_state_module,
        "EventService",
        lambda: event_service,
    )

    repo_constructor = MagicMock()

    monkeypatch.setattr(
        email_state_module,
        "EmailJobRepository",
        repo_constructor,
    )

    async def run():
        async for _ in state.resend_email_job(123):
            pass

    asyncio.run(run())

    event_service.get_event.assert_called_once_with(
        10,
        "admin-user-id",
        auth.user,
    )

    repo_constructor.assert_not_called()

    assert "Event access denied." in state.email_error


def test_retry_all_failed_rejects_unauthorized_event_before_repository(
    monkeypatch,
):
    state = EmailState()
    state.current_event_id = "10"

    auth = make_admin_auth()
    configure_auth_state(monkeypatch, auth)

    event_service = make_unauthorized_event_service()

    monkeypatch.setattr(
        email_state_module,
        "EventService",
        lambda: event_service,
    )

    repo_constructor = MagicMock()

    monkeypatch.setattr(
        email_state_module,
        "EmailJobRepository",
        repo_constructor,
    )

    async def run():
        async for _ in state.retry_all_failed():
            pass

    asyncio.run(run())

    event_service.get_event.assert_called_once_with(
        10,
        "admin-user-id",
        auth.user,
    )

    repo_constructor.assert_not_called()

    assert "Event access denied." in state.email_error
