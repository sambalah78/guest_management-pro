"""
Tests for the Lucky Draw Pre-Draw public presentation state.

These tests intentionally avoid database I/O and Reflex rendering.
The persistence/repository layer is covered separately by the PostgreSQL
integration tests.
"""

from __future__ import annotations

import asyncio

import pytest

from guest_management.state.lucky_draw_state import LuckyDrawState


def run_async(coro):
    """Run one async state method in a normal pytest context."""
    return asyncio.run(coro)


def make_winner(
    guest_id: str,
    name: str,
    *,
    table_number: str = "",
    prize_name: str = "Prize",
    prize_value: str = "RM 100",
    image_url: str = "",
) -> dict:
    return {
        "guest_id": guest_id,
        "name": name,
        "table_number": table_number,
        "prize_name": prize_name,
        "prize_value": prize_value,
        "image_url": image_url,
    }


@pytest.fixture
def state() -> LuckyDrawState:
    state = LuckyDrawState()

    state.current_event_id = "1001"

    state.pre_draw_winners = [
        make_winner(
            "G001",
            "Alice",
            table_number="T01",
            prize_name="Prize A",
            prize_value="RM 100",
            image_url="https://example.com/prize-a.png",
        ),
        make_winner(
            "G002",
            "Bob",
            table_number="T02",
            prize_name="Prize B",
            prize_value="RM 200",
            image_url="https://example.com/prize-b.png",
        ),
        make_winner(
            "G003",
            "Charlie",
            table_number="T03",
            prize_name="Prize C",
            prize_value="RM 300",
            image_url="https://example.com/prize-c.png",
        ),
    ]

    state.lucky_draw_only_present = True
    state.lucky_draw_eligible_guests = []
    state.winners_list = [
        {
            "guest_id": "LIVE001",
            "name": "Live Winner",
        }
    ]

    state.predraw_page = 0
    state.predraw_page_size = 26

    return state


def test_rebuild_pre_draw_display_rows_uses_persisted_winners_only(state):
    state._rebuild_pre_draw_display_rows()

    assert len(state.pre_draw_display_participants) == 3

    assert [
        row["guest_id"]
        for row in state.pre_draw_display_participants
    ] == [
        "G001",
        "G002",
        "G003",
    ]

    assert [
        row["name"]
        for row in state.pre_draw_display_participants
    ] == [
        "Alice",
        "Bob",
        "Charlie",
    ]


def test_rebuild_pre_draw_display_rows_preserves_prize_information(state):
    state._rebuild_pre_draw_display_rows()

    first = state.pre_draw_display_participants[0]

    assert first["pre_draw_prize"] == "Prize A"
    assert first["pre_draw_value"] == "RM 100"
    assert first["pre_draw_image"] == "https://example.com/prize-a.png"


def test_rebuild_pre_draw_display_rows_sets_display_metadata(state):
    state._rebuild_pre_draw_display_rows()

    rows = state.pre_draw_display_participants

    assert rows[0]["display_number"] == 1
    assert rows[1]["display_number"] == 2
    assert rows[2]["display_number"] == 3

    assert rows[0]["table_number"] == "T01"
    assert rows[1]["table_number"] == "T02"
    assert rows[2]["table_number"] == "T03"

    assert all(row["is_pre_draw_winner"] is True for row in rows)


def test_pre_draw_display_does_not_depend_on_attendance_or_live_pool(state):
    state.lucky_draw_only_present = True
    state.lucky_draw_eligible_guests = []
    state.winners_list = []

    state._rebuild_pre_draw_display_rows()

    assert [
        row["guest_id"]
        for row in state.pre_draw_display_participants
    ] == [
        "G001",
        "G002",
        "G003",
    ]


def test_pre_draw_display_does_not_copy_into_live_winners(state):
    original_live_winners = [
        {
            "guest_id": "LIVE001",
            "name": "Live Winner",
        }
    ]

    state.winners_list = list(original_live_winners)

    state._rebuild_pre_draw_display_rows()

    assert state.winners_list == original_live_winners
    assert state.winners_list != state.pre_draw_winners


def test_pre_draw_empty_winner_list_produces_empty_display(state):
    state.pre_draw_winners = []

    state._rebuild_pre_draw_display_rows()

    assert state.pre_draw_display_participants == []
    assert state.predraw_page_count == 0
    assert state.predraw_visible_participants == []


def test_pre_draw_pagination_26_winners_is_one_page():
    state = LuckyDrawState()
    state.pre_draw_winners = [
        make_winner(f"G{i:03d}", f"Guest {i}")
        for i in range(1, 27)
    ]
    state.predraw_page_size = 26
    state.predraw_page = 0

    state._rebuild_pre_draw_display_rows()

    assert state.predraw_page_count == 1
    assert len(state.predraw_visible_participants) == 26
    assert state.predraw_visible_participants[0]["guest_id"] == "G001"
    assert state.predraw_visible_participants[-1]["guest_id"] == "G026"


def test_pre_draw_pagination_27_winners_creates_two_pages():
    state = LuckyDrawState()
    state.pre_draw_winners = [
        make_winner(f"G{i:03d}", f"Guest {i}")
        for i in range(1, 28)
    ]
    state.predraw_page_size = 26
    state.predraw_page = 0

    state._rebuild_pre_draw_display_rows()

    assert state.predraw_page_count == 2
    assert len(state.predraw_visible_participants) == 26

    state.predraw_next_page()

    assert state.predraw_page == 1
    assert len(state.predraw_visible_participants) == 1
    assert state.predraw_visible_participants[0]["guest_id"] == "G027"


def test_pre_draw_pagination_does_not_move_past_last_page():
    state = LuckyDrawState()
    state.pre_draw_winners = [
        make_winner(f"G{i:03d}", f"Guest {i}")
        for i in range(1, 28)
    ]
    state.predraw_page_size = 26
    state.predraw_page = 1

    state._rebuild_pre_draw_display_rows()

    state.predraw_next_page()

    assert state.predraw_page == 1
    assert state.predraw_is_last_page is True


def test_pre_draw_previous_page_does_not_move_before_first_page():
    state = LuckyDrawState()
    state.pre_draw_winners = [
        make_winner(f"G{i:03d}", f"Guest {i}")
        for i in range(1, 28)
    ]
    state.predraw_page_size = 26
    state.predraw_page = 0

    state._rebuild_pre_draw_display_rows()

    state.predraw_previous_page()

    assert state.predraw_page == 0


def test_pre_draw_left_right_split_even_page():
    state = LuckyDrawState()
    state.pre_draw_winners = [
        make_winner(f"G{i:03d}", f"Guest {i}")
        for i in range(1, 27)
    ]
    state.predraw_page_size = 26
    state.predraw_page = 0

    state._rebuild_pre_draw_display_rows()

    assert len(state.predraw_left_participants) == 13
    assert len(state.predraw_right_participants) == 13

    assert state.predraw_left_participants[0]["guest_id"] == "G001"
    assert state.predraw_left_participants[-1]["guest_id"] == "G013"
    assert state.predraw_right_participants[0]["guest_id"] == "G014"
    assert state.predraw_right_participants[-1]["guest_id"] == "G026"


def test_pre_draw_left_right_split_odd_page_puts_extra_row_left():
    state = LuckyDrawState()
    state.pre_draw_winners = [
        make_winner(f"G{i:03d}", f"Guest {i}")
        for i in range(1, 26)
    ]
    state.predraw_page_size = 25
    state.predraw_page = 0

    state._rebuild_pre_draw_display_rows()

    assert len(state.predraw_left_participants) == 13
    assert len(state.predraw_right_participants) == 12

    assert state.predraw_left_participants[-1]["guest_id"] == "G013"
    assert state.predraw_right_participants[0]["guest_id"] == "G014"
    assert state.predraw_right_participants[-1]["guest_id"] == "G025"


def test_pre_draw_page_indicator_and_range_label():
    state = LuckyDrawState()
    state.pre_draw_winners = [
        make_winner(f"G{i:03d}", f"Guest {i}")
        for i in range(1, 28)
    ]
    state.predraw_page_size = 26
    state.predraw_page = 0

    state._rebuild_pre_draw_display_rows()

    assert state.predraw_page_indicator == "PAGE 1 / 2"
    assert state.predraw_range_label == "Winners 1–26 of 27"

    state.predraw_next_page()

    assert state.predraw_page_indicator == "PAGE 2 / 2"
    assert state.predraw_range_label == "Winners 27–27 of 27"


def test_load_pre_draw_display_resets_to_first_page(monkeypatch, state):
    state.predraw_page = 1

    async def fake_load_pre_draw_winners(self):
        return None

    monkeypatch.setattr(
        LuckyDrawState,
        "load_pre_draw_winners",
        fake_load_pre_draw_winners,
    )

    run_async(state.load_pre_draw_display_participants())

    assert state.predraw_page == 0
