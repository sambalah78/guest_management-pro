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



def test_download_guest_list_rejects_unauthorized_event_before_download(monkeypatch):
    state = GuestState()
    state.current_event_id = "10"
    state.guest_data = [
        {
            "Name": "Alice",
            "Email": "alice@example.com",
            "ID": "G001",
            "Table": "T01",
            "Status": "Present",
            "Email Sent": "✅",
        }
    ]

    auth = make_admin_auth()
    configure_auth_state(monkeypatch, auth)
    event_service = make_unauthorized_event_service()
    monkeypatch.setattr(
        guest_state_module,
        "EventService",
        lambda: event_service,
    )

    download = MagicMock(return_value="DOWNLOAD")
    monkeypatch.setattr(guest_state_module.rx, "download", download)

    async def run():
        return [item async for item in state.download_guest_list()]

    results = asyncio.run(run())

    assert download.call_count == 0
    assert results
    event_service.get_event.assert_called_once_with(
        10,
        "admin-user-id",
        auth.user,
    )


def test_export_guest_data_to_excel_rejects_unauthorized_event_before_download(monkeypatch):
    state = GuestState()
    state.current_event_id = "10"
    state.current_event = {"name": "Test Event"}
    state.guest_data = [
        {
            "Name": "Alice",
            "Email": "alice@example.com",
            "ID": "G001",
            "Table": "T01",
            "Status": "Present",
            "Email Sent": "✅",
        }
    ]

    auth = make_admin_auth()
    configure_auth_state(monkeypatch, auth)
    event_service = make_unauthorized_event_service()
    monkeypatch.setattr(
        guest_state_module,
        "EventService",
        lambda: event_service,
    )

    download = MagicMock(return_value="DOWNLOAD")
    monkeypatch.setattr(guest_state_module.rx, "download", download)

    async def run():
        return [item async for item in state.export_guest_data_to_excel()]

    results = asyncio.run(run())

    assert download.call_count == 0
    assert results
    event_service.get_event.assert_called_once_with(
        10,
        "admin-user-id",
        auth.user,
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

def test_set_current_event_from_url_rejects_without_authenticated_session(
    monkeypatch,
):
    state = SimpleNamespace(
        router=SimpleNamespace(
            url=SimpleNamespace(path="/dashboard/10")
        ),
        current_event_id="",
        current_event=None,
        event_type="",
    )

    import guest_management.services.auth_session_resolver as resolver_module

    resolver = MagicMock()
    resolver.get_current_user.return_value = None

    monkeypatch.setattr(
        resolver_module,
        "AuthSessionResolver",
        lambda: resolver,
    )

    event_service = MagicMock()

    monkeypatch.setattr(
        guest_state_module,
        "EventService",
        lambda: event_service,
    )

    GuestState.event_handlers["set_current_event_from_url"].fn(state)

    resolver.get_current_user.assert_called_once()
    event_service.get_event.assert_not_called()
    assert state.current_event_id == ""
    assert state.current_event is None


def test_set_current_event_from_url_rejects_unauthorized_event(
    monkeypatch,
):
    state = SimpleNamespace(
        router=SimpleNamespace(
            url=SimpleNamespace(path="/dashboard/10")
        ),
        current_event_id="",
        current_event=None,
        event_type="",
    )

    auth_user = {
        "id": "user-123",
        "role": "ADMIN",
        "is_active": True,
    }

    import guest_management.services.auth_session_resolver as resolver_module

    resolver = MagicMock()
    resolver.get_current_user.return_value = auth_user

    monkeypatch.setattr(
        resolver_module,
        "AuthSessionResolver",
        lambda: resolver,
    )

    event_service = MagicMock()
    event_service.get_event.side_effect = AuthorizationError(
        "Event access denied."
    )

    monkeypatch.setattr(
        guest_state_module,
        "EventService",
        lambda: event_service,
    )

    GuestState.event_handlers["set_current_event_from_url"].fn(state)

    event_service.get_event.assert_called_once_with(
        10,
        "user-123",
        auth_user,
    )
    assert state.current_event_id == ""
    assert state.current_event is None


def test_set_current_event_from_url_loads_authorized_event(
    monkeypatch,
):
    state = SimpleNamespace(
        router=SimpleNamespace(
            url=SimpleNamespace(path="/dashboard/10")
        ),
        current_event_id="",
        current_event=None,
        event_type="",
    )

    auth_user = {
        "id": "user-123",
        "role": "ADMIN",
        "is_active": True,
    }

    authorized_event = {
        "id": 10,
        "name": "Authorized Event",
        "event_type": "company_dinner",
    }

    import guest_management.services.auth_session_resolver as resolver_module

    resolver = MagicMock()
    resolver.get_current_user.return_value = auth_user

    monkeypatch.setattr(
        resolver_module,
        "AuthSessionResolver",
        lambda: resolver,
    )

    event_service = MagicMock()
    event_service.get_event.return_value = authorized_event

    monkeypatch.setattr(
        guest_state_module,
        "EventService",
        lambda: event_service,
    )

    GuestState.event_handlers["set_current_event_from_url"].fn(state)

    event_service.get_event.assert_called_once_with(
        10,
        "user-123",
        auth_user,
    )
    assert state.current_event_id == "10"
    assert state.current_event == authorized_event
    assert state.event_type == "company_dinner"
