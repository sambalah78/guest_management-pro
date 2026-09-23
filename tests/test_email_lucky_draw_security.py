import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

import guest_management.state.email_state as email_state_module
import guest_management.state.lucky_draw_state as lucky_draw_module
from guest_management.core.exceptions import AuthorizationError
from guest_management.state.email_state import EmailState
from guest_management.state.lucky_draw_state import LuckyDrawState


def make_admin_auth(user_id="admin-user-id"):
    return SimpleNamespace(
        user_id=user_id,
        user={
            "id": user_id,
            "role": "ADMIN",
            "is_active": True,
        },
    )


def configure_auth_state(monkeypatch, state_cls, auth):
    monkeypatch.setattr(
        state_cls,
        "get_state",
        AsyncMock(return_value=auth),
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


def test_open_delivery_details_rejects_unauthorized_event_before_repository(
    monkeypatch,
):
    state = EmailState()
    state.current_event_id = "10"

    auth = make_admin_auth()
    configure_auth_state(monkeypatch, EmailState, auth)

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
        state.open_delivery_details(123)
    )

    event_service.get_event.assert_called_once_with(
        10,
        "admin-user-id",
        auth.user,
    )

    repo_constructor.assert_not_called()


def test_open_delivery_details_allows_authorized_event(
    monkeypatch,
):
    state = EmailState()
    state.current_event_id = "10"

    auth = make_admin_auth()
    configure_auth_state(monkeypatch, EmailState, auth)

    event_service = make_authorized_event_service()

    monkeypatch.setattr(
        email_state_module,
        "EventService",
        lambda: event_service,
    )

    repo = MagicMock()
    repo.get_delivery_details.return_value = {
        "id": 123,
        "event_id": 10,
        "guest_id": 456,
        "status": "sent",
        "recipient": "guest@example.com",
    }

    monkeypatch.setattr(
        email_state_module,
        "EmailJobRepository",
        lambda: repo,
    )

    monkeypatch.setattr(
        EmailState,
        "_prepare_delivery_job",
        MagicMock(
            return_value={
                "id": 123,
                "status": "sent",
            }
        ),
    )

    asyncio.run(
        state.open_delivery_details(123)
    )

    event_service.get_event.assert_called_once_with(
        10,
        "admin-user-id",
        auth.user,
    )

    repo.get_delivery_details.assert_called_once_with(
        123,
        10,
    )

    assert state.delivery_details_open is True
    assert state.selected_job_id == 123


def test_load_lucky_draw_eligible_guests_rejects_unauthorized_event_before_repository(
    monkeypatch,
):
    state = LuckyDrawState()
    state.current_event_id = "10"

    auth = make_admin_auth()
    configure_auth_state(monkeypatch, LuckyDrawState, auth)

    event_service = make_unauthorized_event_service()

    monkeypatch.setattr(
        lucky_draw_module.EventService,
        "get_event",
        event_service.get_event,
    )

    repo_constructor = MagicMock()

    monkeypatch.setattr(
        lucky_draw_module,
        "GuestRepository",
        repo_constructor,
    )

    monkeypatch.setattr(
        LuckyDrawState,
        "load_pre_draw_winners",
        AsyncMock(),
    )

    asyncio.run(
        state.load_lucky_draw_eligible_guests()
    )

    event_service.get_event.assert_called_once_with(
        10,
        "admin-user-id",
        auth.user,
    )

    repo_constructor.assert_not_called()


def test_load_lucky_draw_eligible_guests_allows_authorized_event(
    monkeypatch,
):
    state = LuckyDrawState()
    state.current_event_id = "10"
    state.current_event = {
        "id": 10,
        "name": "Test Event",
        "event_type": "company_dinner",
    }

    auth = make_admin_auth()
    configure_auth_state(monkeypatch, LuckyDrawState, auth)

    event_service = make_authorized_event_service()

    monkeypatch.setattr(
        lucky_draw_module.EventService,
        "get_event",
        event_service.get_event,
    )

    repo = MagicMock()

    repo.get_by_event.return_value = (
        [
            {
                "guest_id": "G001",
                "name": "Guest One",
                "status": "present",
                "table_number": "T1",
                "email": "guest@example.com",
            }
        ],
        1,
    )

    monkeypatch.setattr(
        lucky_draw_module,
        "GuestRepository",
        lambda: repo,
    )

    monkeypatch.setattr(
        LuckyDrawState,
        "load_pre_draw_winners",
        AsyncMock(),
    )

    asyncio.run(
        state.load_lucky_draw_eligible_guests()
    )

    event_service.get_event.assert_called_once_with(
        10,
        "admin-user-id",
        auth.user,
    )

    repo.get_by_event.assert_called_once_with(
        10,
        limit=200,
        offset=0,
    )
    assert len(state.lucky_draw_eligible_guests) == 1
    assert state.lucky_draw_eligible_guests[0]["guest_id"] == "G001"

def test_load_winners_rejects_unauthorized_event_before_service(
    monkeypatch,
):
    state = LuckyDrawState()
    state.current_event_id = "10"

    auth = make_admin_auth()
    configure_auth_state(monkeypatch, LuckyDrawState, auth)

    event_service = make_unauthorized_event_service()

    monkeypatch.setattr(
        lucky_draw_module.EventService,
        "get_event",
        event_service.get_event,
    )

    service_constructor = MagicMock()

    monkeypatch.setattr(
        lucky_draw_module,
        "WinnerService",
        service_constructor,
    )

    asyncio.run(
        state.load_winners()
    )

    event_service.get_event.assert_called_once_with(
        10,
        "admin-user-id",
        auth.user,
    )

    service_constructor.assert_not_called()


def test_load_winners_allows_authorized_event(
    monkeypatch,
):
    state = LuckyDrawState()
    state.current_event_id = "10"

    auth = make_admin_auth()
    configure_auth_state(monkeypatch, LuckyDrawState, auth)

    event_service = make_authorized_event_service()

    monkeypatch.setattr(
        lucky_draw_module.EventService,
        "get_event",
        event_service.get_event,
    )

    service = MagicMock()

    service.get_by_event.return_value = [
        {
            "event_id": 10,
            "guest_id": "G001",
            "name": "Guest One",
        }
    ]

    monkeypatch.setattr(
        lucky_draw_module,
        "WinnerService",
        lambda: service,
    )

    asyncio.run(
        state.load_winners()
    )

    event_service.get_event.assert_called_once_with(
        10,
        "admin-user-id",
        auth.user,
    )

    service.get_by_event.assert_called_once_with(10)

    assert len(state.winners_list) == 1
    assert state.winners_list[0]["guest_id"] == "G001"

