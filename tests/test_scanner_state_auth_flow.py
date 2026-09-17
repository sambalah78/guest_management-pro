import asyncio

import guest_management.state.scanner_state as scanner_state_module
from guest_management.state.scanner_state import ScannerState


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
            "guest_id": "G1",
            "guest_name": "Guest 1",
            "table_number": "T01",
            "present_count": 1,
            "total_guests": 1,
        }


def make_state():
    state = ScannerState()
    state.is_loading = False
    state.current_event_id = "18"
    state.current_scanner_id = "SCANNER_001"
    state.station_access_token = "ELST_test-secret"
    state.station_authenticated = True
    state.scanner_status = ""
    state.scanner_status_icon = "idle"
    state.last_scanned_code = ""
    state.checkin_guest_name = ""
    state.checkin_table_number = ""
    state.checkin_team_name = ""
    state.present_count = 0
    state.total_guests = 1
    state.absent_count = 1
    state.last_checkin_name = ""
    state.last_checkin_table = ""
    state.last_checkin_time = 0.0
    state.scanner_ready = True
    return state


def test_process_checkin_forwards_authenticated_station_token(monkeypatch):
    fake = FakeCheckinService()
    monkeypatch.setattr(scanner_state_module, "CheckinService", lambda: fake)
    state = make_state()

    async def run():
        async for _ in state._process_checkin(
                "signed-qr",
                "18",
                "SCANNER_001",
        ):
            pass

    asyncio.run(run())

    assert fake.calls == [
        {
            "event_id": 18,
            "raw_scan": "signed-qr",
            "scanner_id": "SCANNER_001",
            "scanner_access_token": "ELST_test-secret",
            "manual": False,
        }
    ]
