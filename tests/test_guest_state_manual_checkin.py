import asyncio

import guest_management.state.guest_state as guest_state_module
from guest_management.state.guest_state import GuestState


class FakeAuthState:
    user_id = "admin-001"
    user = "admin@example.com"


class FakeEventService:
    def __init__(self):
        self.calls = []

    def get_event(self, event_id, user_id, user):
        self.calls.append(
            {
                "event_id": event_id,
                "user_id": user_id,
                "user": user,
            }
        )
        return {"id": event_id}


class FakeGuestRepository:
    def __init__(self, *, matches=None, created_guest=None):
        self.matches = matches or []
        self.created_guest = created_guest
        self.search_calls = []
        self.create_calls = []
    def get_by_event(self, event_id, limit=10, offset=0):
        return [], 0

    def search(self, event_id, name, limit=10):
        self.search_calls.append(
            {
                "event_id": event_id,
                "name": name,
                "limit": limit,
            }
        )
        return self.matches

    def create_batch(self, guests, batch_size=1):
        self.create_calls.append(
            {
                "guests": guests,
                "batch_size": batch_size,
            }
        )
        return 1

    def get_by_guest_id(self, guest_id, event_id):
        return self.created_guest


class FakeQRService:
    def __init__(self):
        self.calls = []

    def guest_url(self, guest_id, event_id):
        self.calls.append(
            {
                "guest_id": guest_id,
                "event_id": event_id,
            }
        )
        return f"https://example.test/checkin/{event_id}/{guest_id}"


class FakeCheckinService:
    def __init__(self):
        self.calls = []

    def check_in(
        self,
        event_id,
        raw_scan,
        scanner_id,
        *,
        scanner_access_token="",
        manual=False,
    ):
        self.calls.append(
            {
                "event_id": event_id,
                "raw_scan": raw_scan,
                "scanner_id": scanner_id,
                "scanner_access_token": scanner_access_token,
                "manual": manual,
            }
        )
        return {
            "result": "checked_in",
            "guest_id": raw_scan,
            "guest_name": "Test Guest",
            "table_number": "T01",
            "present_count": 1,
            "total_guests": 1,
        }


def consume(async_generator):
    async def run():
        async for _ in async_generator:
            pass

    asyncio.run(run())


def configure_state(monkeypatch, state):
    state.current_event_id = "18"
    state.is_loading = False
    state.no_id_name = "Test Guest"
    state.no_id_email = "test@example.com"
    state.no_id_phone = "0123456789"
    state.no_id_table_number = "T01"
    state.no_id_team_name = ""
    state.no_id_client_confirmed = True
    state.no_id_verification_open = True

    async def fake_get_state(self, _state_type):
        return FakeAuthState()

    async def fake_load_guests(self):
        if False:
            yield None

    monkeypatch.setattr(GuestState, "get_state", fake_get_state)
    monkeypatch.setattr(GuestState, "load_guests", fake_load_guests)
    monkeypatch.setattr(
        guest_state_module,
        "EventService",
        lambda: FakeEventService(),
    )


def test_confirm_no_id_existing_guest_uses_explicit_manual_checkin(monkeypatch):
    guest = {
        "event_id": 18,
        "guest_id": "GUEST-001",
        "name": "Test Guest",
        "email": "test@example.com",
        "phone": "0123456789",
        "status": "Absent",
        "table_number": "T01",
        "team_name": "",
    }

    repository = FakeGuestRepository(matches=[guest])
    checkin = FakeCheckinService()

    monkeypatch.setattr(
        guest_state_module,
        "GuestRepository",
        lambda: repository,
    )
    monkeypatch.setattr(
        guest_state_module,
        "CheckinService",
        lambda: checkin,
    )

    state = GuestState()
    configure_state(monkeypatch, state)

    consume(state.confirm_no_id_guest())

    assert checkin.calls == [
        {
            "event_id": 18,
            "raw_scan": "GUEST-001",
            "scanner_id": "MANUAL",
            "scanner_access_token": "",
            "manual": True,
        }
    ]


def test_confirm_no_id_new_guest_uses_explicit_manual_checkin(monkeypatch):
    created_guest = {
        "event_id": 18,
        "guest_id": "NO-ID-ABC123",
        "name": "New Guest",
        "email": "new@example.com",
        "phone": "0123456789",
        "status": "Absent",
        "table_number": "TBD",
        "team_name": None,
    }

    repository = FakeGuestRepository(
        matches=[],
        created_guest=created_guest,
    )
    checkin = FakeCheckinService()

    monkeypatch.setattr(
        guest_state_module,
        "GuestRepository",
        lambda: repository,
    )
    monkeypatch.setattr(
        guest_state_module,
        "CheckinService",
        lambda: checkin,
    )
    monkeypatch.setattr(
        guest_state_module,
        "QRService",
        lambda: FakeQRService(),
    )

    state = GuestState()
    configure_state(monkeypatch, state)
    state.no_id_name = "New Guest"

    consume(state.confirm_no_id_guest())

    assert len(checkin.calls) == 1
    assert checkin.calls[0]["event_id"] == 18
    assert checkin.calls[0]["raw_scan"].startswith("NO-ID-")
    assert len(checkin.calls[0]["raw_scan"]) == 16
    assert checkin.calls[0]["scanner_id"] == "MANUAL"
    assert checkin.calls[0]["scanner_access_token"] == ""
    assert checkin.calls[0]["manual"] is True
