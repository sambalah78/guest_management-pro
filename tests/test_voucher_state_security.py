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


@pytest.mark.asyncio
async def test_continue_to_menu_never_puts_guest_id_in_url(monkeypatch):
    state = VoucherState()
    state.url_stall_id = "10"
    state.url_event_id = "1"
    state.current_stall = {"id": 10, "event_id": 1, "stall_name": "Stall"}
    state.guest_authenticated = True
    state.authenticated_guest = {
        "event_id": 1,
        "guest_id": "G001",
        "name": "Guest One",
        "amount": 100,
        "status": "Present",
    }

    redirect = MagicMock(return_value="REDIRECT")
    monkeypatch.setattr("guest_management.state.voucher_state.rx.redirect", redirect)

    events = []
    async for event in state.continue_to_menu():
        events.append(event)

    redirect.assert_called_once_with("/stall/menu?stall_id=10&event_id=1")
    assert events == ["REDIRECT"]


@pytest.mark.asyncio


@pytest.mark.asyncio
async def test_start_order_rejects_invalid_voucher_access_code(monkeypatch):
    state = VoucherState()
    state.url_stall_id = "10"
    state.url_event_id = "18"
    state.guest_id_input = "G001"
    state.voucher_access_code_input = "WRONG-CODE"
    state.current_stall = {"id": 10, "event_id": 18}

    guest = {
        "event_id": 18,
        "guest_id": "G001",
        "name": "Guest One",
        "amount": 100,
        "email": "guest@example.com",
        "status": "Present",
    }

    db = MagicMock()
    db.table.return_value.select.return_value.eq.return_value.eq.return_value.execute.return_value.data = [guest]
    monkeypatch.setattr(
        "guest_management.state.voucher_state.get_db",
        MagicMock(return_value=db),
    )

    async for _ in state.start_order_from_landing():
        pass

    assert state.guest_authenticated is False
    assert state.authenticated_guest is None
    assert state.current_guest is None


def test_load_guest_by_id_cannot_switch_authenticated_voucher_guest():
    state = VoucherState()
    state.guest_authenticated = True
    state.authenticated_guest = {
        "event_id": 18,
        "guest_id": "G001",
        "name": "Guest One",
        "amount": 100,
        "status": "Present",
    }
    state.current_guest = state.authenticated_guest

    state.load_guest_by_id("G002")

    assert state.current_guest is None


@pytest.mark.asyncio
async def test_confirm_purchase_uses_authenticated_guest_not_current_guest(monkeypatch):
    state = VoucherState()
    state.current_event_id = "1"
    state.current_stall = {"id": 10, "event_id": 1}
    state.order_items = [{"id": 100, "item_name": "Item", "price": 10}]
    state.order_total = 10
    state.guest_authenticated = True
    state.authenticated_guest = {
        "event_id": 1,
        "guest_id": "G001",
        "name": "Guest One",
        "amount": 100,
        "status": "Present",
    }
    state.current_guest = {
        "event_id": 1,
        "guest_id": "ATTACKER",
        "name": "Wrong Guest",
        "amount": 9999,
        "status": "Present",
    }

    db = MagicMock()
    db.rpc.return_value.execute.return_value.data = [{
        "result": "success",
        "balance_after": 90,
        "total": 10,
    }]
    monkeypatch.setattr(
        "guest_management.state.voucher_state.get_db",
        MagicMock(return_value=db),
    )

    async for _ in state.confirm_purchase():
        pass

    params = db.rpc.call_args.args[1]
    assert params["p_event_id"] == 1
    assert params["p_guest_id"] == "G001"
    assert params["p_stall_id"] == 10


@pytest.mark.asyncio
async def test_confirm_purchase_rejects_without_authenticated_voucher_session(monkeypatch):
    state = VoucherState()
    state.current_event_id = "1"
    state.current_stall = {"id": 10, "event_id": 1}
    state.order_items = [{"id": 100}]
    state.current_guest = {"guest_id": "G001", "status": "Present"}

    db_get = MagicMock()
    monkeypatch.setattr(
        "guest_management.state.voucher_state.get_db",
        db_get,
    )

    events = []
    async for event in state.confirm_purchase():
        events.append(event)

    assert events
    db_get.assert_not_called()
    assert "Guest, stall, or event session is invalid" in str(events[0])


def test_source_no_longer_uses_guest_id_in_menu_url():
    from pathlib import Path

    text = Path("guest_management/state/voucher_state.py").read_text(encoding="utf-8-sig")

    assert "stall/menu?stall_id={stall_id}&guest_id={guest_id}" not in text
    assert "/stall/menu?stall_id={stall_id_int}&event_id={event_id_int}" in text
