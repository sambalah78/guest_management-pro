import asyncio
import base64
import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import guest_management.state.lucky_draw_state as lucky_draw_state_module
from guest_management.state.lucky_draw_state import LuckyDrawState


def consume_async_generator(result):
    async def run():
        return [item async for item in result]
    return asyncio.run(run())


def invoke_handler(name, state):
    return LuckyDrawState.event_handlers[name].fn(state)


def test_setup_complete_display_url_does_not_contain_winners(monkeypatch):
    state = SimpleNamespace(
        current_event_id="10",
        lucky_draw_event_name="Authorized Event",
        lucky_draw_event_type="company_dinner",
        prize_mode="multiple",
        current_prizes=[
            {"name": "Grand Prize", "value": "RM 1,000", "image_url": "https://example.test/prize.jpg"}
        ],
        lucky_draw_eligible_guests=[{"guest_id": "G001", "name": "Guest One"}],
        winners_list=[
            {"guest_id": "SECRET-001", "name": "Private Winner", "prize_name": "Grand Prize"}
        ],
        current_prize_index=0,
        redraw_count=7,
        excluded_guest_ids=["OLD"],
        draw_locked=True,
        draw_status="DONE",
        draw_finished=True,
        waiting_for_next_prize=True,
        prize_transitioning=True,
        lucky_draw_prize_name="Old Prize",
        lucky_draw_prize_value="RM 0",
        lucky_draw_prize_picture="old.jpg",
        single_prize_name="",
        single_prize_value="",
        single_prize_picture="",
        lucky_draw_only_present=True,
        _reset_candidate_state=MagicMock(),
        load_lucky_draw_eligible_guests=AsyncMock(),
        broadcast_lucky_draw_state=MagicMock(return_value="broadcast"),
    )

    captured = {}

    def fake_redirect(url):
        captured["url"] = url
        return {"redirect": url}

    monkeypatch.setattr(lucky_draw_state_module.rx, "redirect", fake_redirect)
    consume_async_generator(invoke_handler("setup_complete_and_go_to_display", state))

    url = captured["url"]
    assert "winners" not in url.lower()
    data_param = url.split("data=", 1)[1]
    decoded = base64.urlsafe_b64decode(
        data_param + "=" * (-len(data_param) % 4)
    ).decode("utf-8")
    payload = json.loads(decoded)
    assert "winners" not in payload


def test_live_display_does_not_trust_winners_from_url_payload(monkeypatch):
    malicious_payload = {
        "prize_mode": "multiple",
        "current_prizes": [{"name": "Injected Prize", "value": "RM 9999"}],
        "current_prize_index": 0,
        "current_event_id": "10",
        "current_event_name": "Injected Event",
        "event_type": "company_dinner",
        "lucky_draw_only_present": True,
        "winners": [{"guest_id": "ATTACKER", "name": "Injected Winner"}],
    }
    encoded = base64.urlsafe_b64encode(
        json.dumps(malicious_payload).encode("utf-8")
    ).decode("ascii")

    state = SimpleNamespace(
        router=SimpleNamespace(url=SimpleNamespace(query=f"?event_id=10&data={encoded}")),
        current_event_id="",
        current_prizes=[],
        current_prize_index=0,
        prize_mode="multiple",
        lucky_draw_event_name="",
        lucky_draw_event_type="",
        lucky_draw_only_present=False,
        winners_list=[{"guest_id": "SERVER-WINNER", "name": "Authoritative Winner"}],
        _set_current_prize=MagicMock(),
        _fetch_display_data_from_api=AsyncMock(),
        load_winners=AsyncMock(),
    )

    consume_async_generator(invoke_handler("load_lucky_draw_display_data", state))

    assert state.winners_list == [
        {"guest_id": "SERVER-WINNER", "name": "Authoritative Winner"}
    ]
    state._fetch_display_data_from_api.assert_awaited_once()