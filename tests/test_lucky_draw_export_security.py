import asyncio
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import guest_management.state.lucky_draw_state as lucky_draw_state_module
import guest_management.services.event_service as event_service_module
from guest_management.core.exceptions import AuthorizationError
from guest_management.state.lucky_draw_state import LuckyDrawState


def make_admin_auth():
    user_id = "user-123"
    return SimpleNamespace(
        user_id=user_id,
        user={
            "id": user_id,
            "role": "ADMIN",
            "is_active": True,
        },
    )


def consume_async_generator(result):
    async def run():
        return [item async for item in result]

    return asyncio.run(run())


def invoke_download_winner_list(state):
    return LuckyDrawState.event_handlers["download_winner_list"].fn(state)


def test_download_winner_list_rejects_unauthorized_event_before_download(monkeypatch):
    state = LuckyDrawState()
    state.current_event_id = "10"
    state.winners_list = [
        {
            "name": "Alice",
            "guest_id": "G001",
            "prize_name": "Grand Prize",
            "prize_value": "RM100",
            "created_at": "2026-09-24T10:00:00",
        }
    ]

    auth = make_admin_auth()
    monkeypatch.setattr(
        LuckyDrawState,
        "get_state",
        AsyncMock(return_value=auth),
    )

    event_service = MagicMock()
    event_service.get_event.side_effect = AuthorizationError(
        "Event access denied."
    )
    monkeypatch.setattr(
        event_service_module,
        "EventService",
        lambda: event_service,
    )

    download = MagicMock()
    monkeypatch.setattr(
        lucky_draw_state_module.rx,
        "download",
        download,
    )

    results = consume_async_generator(invoke_download_winner_list(state))

    assert results
    download.assert_not_called()
    event_service.get_event.assert_called_once_with(
        10,
        "user-123",
        auth.user,
    )


def test_download_winner_list_allows_authorized_event(monkeypatch):
    state = LuckyDrawState()
    state.current_event_id = "10"
    state.winners_list = [
        {
            "name": "Alice",
            "guest_id": "G001",
            "prize_name": "Grand Prize",
            "prize_value": "RM100",
            "created_at": "2026-09-24T10:00:00",
        }
    ]

    auth = make_admin_auth()
    monkeypatch.setattr(
        LuckyDrawState,
        "get_state",
        AsyncMock(return_value=auth),
    )

    event_service = MagicMock()
    event_service.get_event.return_value = {
        "id": 10,
        "name": "Authorized Event",
        "event_type": "lucky_draw",
    }
    monkeypatch.setattr(
        event_service_module,
        "EventService",
        lambda: event_service,
    )

    download = MagicMock(return_value="DOWNLOAD")
    monkeypatch.setattr(
        lucky_draw_state_module.rx,
        "download",
        download,
    )

    results = consume_async_generator(invoke_download_winner_list(state))

    assert results
    download.assert_called_once()
    kwargs = download.call_args.kwargs
    assert "Winner Name" in kwargs["data"]
    assert "Guest ID" in kwargs["data"]
    assert "Grand Prize" in kwargs["data"]
    assert kwargs["filename"].startswith("winners_event_10_")
    assert kwargs["filename"].endswith(".csv")
    event_service.get_event.assert_called_once_with(
        10,
        "user-123",
        auth.user,
    )


def test_download_winner_list_requires_selected_event(monkeypatch):
    state = LuckyDrawState()
    state.current_event_id = ""
    state.winners_list = [
        {
            "name": "Alice",
            "guest_id": "G001",
            "prize_name": "Grand Prize",
            "prize_value": "RM100",
            "created_at": "2026-09-24T10:00:00",
        }
    ]

    get_state = AsyncMock()
    monkeypatch.setattr(LuckyDrawState, "get_state", get_state)

    download = MagicMock()
    monkeypatch.setattr(
        lucky_draw_state_module.rx,
        "download",
        download,
    )

    results = consume_async_generator(invoke_download_winner_list(state))

    assert results
    get_state.assert_not_awaited()
    download.assert_not_called()


def invoke_load_pre_draw_winners(state):
    return LuckyDrawState.event_handlers["load_pre_draw_winners"].fn(state)


def test_load_pre_draw_winners_rejects_unauthorized_event_before_repository(monkeypatch):
    state = LuckyDrawState()
    state.current_event_id = "10"

    auth = make_admin_auth()
    monkeypatch.setattr(
        LuckyDrawState,
        "get_state",
        AsyncMock(return_value=auth),
    )

    event_service = MagicMock()
    event_service.get_event.side_effect = AuthorizationError(
        "Event access denied."
    )
    monkeypatch.setattr(
        event_service_module,
        "EventService",
        lambda: event_service,
    )

    pre_draw_service = MagicMock()
    pre_draw_service.get_by_event.return_value = [
        {"guest_id": "G001", "name": "Alice"}
    ]
    monkeypatch.setattr(
        lucky_draw_state_module,
        "PreDrawWinnerService",
        lambda: pre_draw_service,
    )

    asyncio.run(invoke_load_pre_draw_winners(state))

    event_service.get_event.assert_called_once_with(
        10,
        "user-123",
        auth.user,
    )
    pre_draw_service.get_by_event.assert_not_called()
    assert state.pre_draw_winners == []


def test_load_pre_draw_winners_loads_authorized_event(monkeypatch):
    state = LuckyDrawState()
    state.current_event_id = "10"

    auth = make_admin_auth()
    monkeypatch.setattr(
        LuckyDrawState,
        "get_state",
        AsyncMock(return_value=auth),
    )

    event_service = MagicMock()
    event_service.get_event.return_value = {
        "id": 10,
        "name": "Authorized Event",
        "event_type": "company_dinner",
    }
    monkeypatch.setattr(
        event_service_module,
        "EventService",
        lambda: event_service,
    )

    pre_draw_service = MagicMock()
    pre_draw_service.get_by_event.return_value = [
        {
            "guest_id": "G001",
            "name": "Alice",
            "prize_name": "Grand Prize",
        }
    ]
    monkeypatch.setattr(
        lucky_draw_state_module,
        "PreDrawWinnerService",
        lambda: pre_draw_service,
    )

    asyncio.run(invoke_load_pre_draw_winners(state))

    event_service.get_event.assert_called_once_with(
        10,
        "user-123",
        auth.user,
    )
    pre_draw_service.get_by_event.assert_called_once_with(10)
    assert state.pre_draw_winners == [
        {
            "guest_id": "G001",
            "name": "Alice",
            "prize_name": "Grand Prize",
        }
    ]


def test_load_pre_draw_winners_requires_selected_event(monkeypatch):
    state = LuckyDrawState()
    state.current_event_id = ""

    get_state = AsyncMock()
    monkeypatch.setattr(
        LuckyDrawState,
        "get_state",
        get_state,
    )

    pre_draw_service = MagicMock()
    monkeypatch.setattr(
        lucky_draw_state_module,
        "PreDrawWinnerService",
        lambda: pre_draw_service,
    )

    asyncio.run(invoke_load_pre_draw_winners(state))

    get_state.assert_not_awaited()
    pre_draw_service.get_by_event.assert_not_called()
    assert state.pre_draw_winners == []
