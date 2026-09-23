import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import guest_management.state.guest_state as guest_state_module
from guest_management.core.exceptions import AuthorizationError
from guest_management.state.guest_state import GuestState


def make_admin_auth(user_id="admin-user-id"):
    return SimpleNamespace(
        user_id=user_id,
        user={
            "id": user_id,
            "role": "ADMIN",
            "is_active": True,
        },
    )


def make_authorized_event_service():
    event_service = MagicMock()
    event_service.get_event.return_value = {
        "id": 10,
        "name": "Test Event",
    }
    return event_service


def make_unauthorized_event_service():
    event_service = MagicMock()
    event_service.get_event.side_effect = AuthorizationError(
        "Event access denied."
    )
    return event_service


def configure_auth_state(monkeypatch, auth):
    monkeypatch.setattr(
        GuestState,
        "get_state",
        AsyncMock(return_value=auth),
    )


def test_update_dashboard_stats_rejects_unauthorized_event_before_repository(
    monkeypatch,
):
    state = GuestState()
    state.current_event_id = "10"

    auth = make_admin_auth()
    configure_auth_state(monkeypatch, auth)

    event_service = make_unauthorized_event_service()

    monkeypatch.setattr(
        guest_state_module,
        "EventService",
        lambda: event_service,
    )

    repo_constructor = MagicMock()

    monkeypatch.setattr(
        guest_state_module,
        "GuestRepository",
        repo_constructor,
        raising=False,
    )

    asyncio.run(
        state.update_dashboard_stats().__anext__()
    )

    event_service.get_event.assert_called_once_with(
        10,
        "admin-user-id",
        auth.user,
    )

    repo_constructor.assert_not_called()


def test_update_dashboard_stats_allows_authorized_event(
    monkeypatch,
):
    state = GuestState()
    state.current_event_id = "10"

    auth = make_admin_auth()
    configure_auth_state(monkeypatch, auth)

    event_service = make_authorized_event_service()

    monkeypatch.setattr(
        guest_state_module,
        "EventService",
        lambda: event_service,
    )

    repo = MagicMock()

    rpc_response = MagicMock()
    rpc_response.data = [{
        "total_guests": 100,
        "present_count": 40,
        "absent_count": 60,
    }]

    repo.db.rpc.return_value.execute.return_value = rpc_response

    import guest_management.repositories as repositories_module

    monkeypatch.setattr(
        repositories_module,
        "GuestRepository",
        lambda: repo,
    )

    async def run():
        async for _ in state.update_dashboard_stats():
            pass

    asyncio.run(run())

    event_service.get_event.assert_called_once_with(
        10,
        "admin-user-id",
        auth.user,
    )

    repo.db.rpc.assert_called_once_with(
        "get_event_stats",
        {"p_event_id": 10},
    )

    assert state.total_guests == 100
    assert state.present_count == 40
    assert state.absent_count == 60
    assert state.present_percentage == 40
    assert state.absent_percentage == 60
