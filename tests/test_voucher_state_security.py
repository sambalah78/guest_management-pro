from unittest.mock import AsyncMock, MagicMock

import pytest

from guest_management.core.exceptions import AuthorizationError
from guest_management.state.voucher_state import VoucherState


def make_admin_auth(
    user_id="admin-user-id",
    role="ADMIN",
):
    auth = MagicMock()
    auth.user_id = user_id
    auth.user = {
        "id": user_id,
        "role": role,
        "is_active": True,
    }
    return auth


def make_event_service():
    service = MagicMock()
    service.get_event.return_value = {
        "id": 10,
        "name": "Test Event",
    }
    return service


@pytest.fixture
def admin_auth():
    return make_admin_auth()


@pytest.mark.asyncio
async def test_authorize_voucher_admin_uses_authenticated_state(
    monkeypatch,
    admin_auth,
):
    state = VoucherState()
    state.current_event_id = "10"

    get_state = AsyncMock(return_value=admin_auth)
    monkeypatch.setattr(
        VoucherState,
        "get_state",
        get_state,
    )

    event_service = make_event_service()
    monkeypatch.setattr(
        "guest_management.state.voucher_state.EventService",
        MagicMock(return_value=event_service),
    )

    auth, event_id = await state._authorize_voucher_admin()

    assert auth is admin_auth
    assert event_id == 10

    get_state.assert_awaited_once()

    event_service.get_event.assert_called_once_with(
        10,
        "admin-user-id",
        admin_auth.user,
    )


@pytest.mark.asyncio
async def test_authorize_voucher_admin_rejects_missing_event(
    monkeypatch,
    admin_auth,
):
    state = VoucherState()
    state.current_event_id = ""

    get_state = AsyncMock(return_value=admin_auth)
    monkeypatch.setattr(
        VoucherState,
        "get_state",
        get_state,
    )

    with pytest.raises(
        PermissionError,
        match="Event is not selected",
    ):
        await state._authorize_voucher_admin()

    get_state.assert_not_awaited()


@pytest.mark.asyncio
async def test_authorize_voucher_admin_rejects_invalid_event(
    monkeypatch,
    admin_auth,
):
    state = VoucherState()
    state.current_event_id = "not-an-event"

    get_state = AsyncMock(return_value=admin_auth)
    monkeypatch.setattr(
        VoucherState,
        "get_state",
        get_state,
    )

    with pytest.raises(
        PermissionError,
        match="Invalid event ID",
    ):
        await state._authorize_voucher_admin()

    get_state.assert_not_awaited()


@pytest.mark.asyncio
async def test_authorize_voucher_admin_rejects_unauthenticated(
    monkeypatch,
):
    state = VoucherState()
    state.current_event_id = "10"

    auth = MagicMock()
    auth.user_id = None
    auth.user = None

    get_state = AsyncMock(return_value=auth)
    monkeypatch.setattr(
        VoucherState,
        "get_state",
        get_state,
    )

    with pytest.raises(
        PermissionError,
        match="Voucher management requires event admin access",
    ):
        await state._authorize_voucher_admin()

    get_state.assert_awaited_once()


@pytest.mark.asyncio
async def test_authorize_voucher_admin_rejects_non_admin(
    monkeypatch,
):
    state = VoucherState()
    state.current_event_id = "10"

    auth = MagicMock()
    auth.user_id = "regular-user-id"
    auth.user = {
        "id": "regular-user-id",
        "role": "USER",
        "is_active": True,
    }

    get_state = AsyncMock(return_value=auth)
    monkeypatch.setattr(
        VoucherState,
        "get_state",
        get_state,
    )

    with pytest.raises(
        PermissionError,
        match="Voucher management requires event admin access",
    ):
        await state._authorize_voucher_admin()

    get_state.assert_awaited_once()


@pytest.mark.asyncio
async def test_authorize_voucher_admin_rejects_event_access_failure(
    monkeypatch,
    admin_auth,
):
    state = VoucherState()
    state.current_event_id = "99"

    monkeypatch.setattr(
        VoucherState,
        "get_state",
        AsyncMock(return_value=admin_auth),
    )

    event_service = make_event_service()
    event_service.get_event.side_effect = AuthorizationError(
        "Event access denied"
    )

    monkeypatch.setattr(
        "guest_management.state.voucher_state.EventService",
        MagicMock(return_value=event_service),
    )

    with pytest.raises(
        AuthorizationError,
        match="Event access denied",
    ):
        await state._authorize_voucher_admin()

    event_service.get_event.assert_called_once_with(
        99,
        "admin-user-id",
        admin_auth.user,
    )


@pytest.mark.asyncio
async def test_show_guest_history_uses_authenticated_state(
    monkeypatch,
):
    state = VoucherState()
    state.current_event_id = "10"

    guest = {
        "id": "guest-123",
        "event_id": 10,
        "name": "Test Guest",
    }

    auth = make_admin_auth()

    get_state = AsyncMock(return_value=auth)
    monkeypatch.setattr(
        VoucherState,
        "get_state",
        get_state,
    )

    event_service = make_event_service()
    monkeypatch.setattr(
        "guest_management.state.voucher_state.EventService",
        MagicMock(return_value=event_service),
    )

    db = MagicMock()

    transaction_response = MagicMock()
    transaction_response.data = []

    (
        db.table.return_value
        .select.return_value
        .eq.return_value
        .eq.return_value
        .execute.return_value
    ) = transaction_response

    monkeypatch.setattr(
        "guest_management.state.voucher_state.get_db",
        MagicMock(return_value=db),
    )

    events = []

    async for event in state.show_guest_history(guest):
        events.append(event)

    get_state.assert_awaited_once()

    event_service.get_event.assert_called_once_with(
        10,
        "admin-user-id",
        auth.user,
    )

    db.table.assert_called_with("transactions")
    db.table.return_value.select.assert_called_once_with("*")

    first_eq = db.table.return_value.select.return_value.eq

    first_eq.assert_called_once_with(
        "guest_id",
        "guest-123",
    )

    second_eq = first_eq.return_value.eq

    second_eq.assert_called_once_with(
        "event_id",
        10,
    )


@pytest.mark.asyncio
async def test_show_guest_history_rejects_unauthenticated(
    monkeypatch,
):
    state = VoucherState()
    state.current_event_id = "10"

    guest = {
        "id": "guest-123",
        "event_id": 10,
        "name": "Test Guest",
    }

    auth = MagicMock()
    auth.user_id = None
    auth.user = None

    get_state = AsyncMock(return_value=auth)
    monkeypatch.setattr(
        VoucherState,
        "get_state",
        get_state,
    )

    events = []

    async for event in state.show_guest_history(guest):
        events.append(event)

    assert events
    assert "Authentication required" in str(events[0])

    get_state.assert_awaited_once()


def test_no_direct_authstate_construction_remains():
    from pathlib import Path

    path = Path("guest_management/state/voucher_state.py")
    text = path.read_text(encoding="utf-8-sig")

    assert "AuthState()" not in text
    assert text.count("await self.get_state(AuthState)") == 2
    assert text.count("await self._authorize_voucher_admin()") == 8
