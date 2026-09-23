"""
Opt-in PostgreSQL integration tests for random Pre-Draw finalization.

Run only against the disposable TEST_DATABASE_URL PostgreSQL database:

    $env:TEST_DATABASE_URL = "postgresql://..."
    python -m pytest -q tests\test_pre_draw_finalize_postgres.py

These tests never target production intentionally.
"""

from __future__ import annotations

import os
from types import SimpleNamespace

import pytest
from sqlalchemy import delete, insert, select

from guest_management.database import (
    engine,
    events,
    pre_draw_prizes,
    pre_draw_winners,
    users,
)
from guest_management.repositories.pre_draw_winner_repository import (
    PreDrawWinnerRepository,
)


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "").strip()

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL is not configured.",
)


@pytest.fixture
def postgres_repository():
    """
    Provide the real application PostgreSQL engine to the repository.

    The repository only requires a db object exposing .engine for
    finalize_random_generation().
    """
    db = SimpleNamespace(engine=engine)
    return PreDrawWinnerRepository(db=db)


@pytest.fixture
def pre_draw_fixture():
    """
    Create one disposable event with two READY prizes.

    Prize A: 2 winners
    Prize B: 1 winner

    The fixture cleans up the complete event afterward, relying on the
    database's ON DELETE CASCADE relationships.
    """
    with engine.begin() as conn:
        user_id = conn.execute(
            select(users.c.id)
            .where(users.c.email == "pre_draw_test@eventlah.test")
            .limit(1)
        ).scalar_one_or_none()

        if user_id is None:
            pytest.fail(
                "TEST_DATABASE_URL database is missing the seeded "
                "pre_draw_test@eventlah.test user."
            )

        event_id = conn.execute(
            insert(events)
            .values(
                name="PostgreSQL Pre-Draw Finalize Test",
                event_type="company_dinner",
                company_name="EventLah Test",
                date="2026-01-01",
                time="19:00",
                venue="PostgreSQL Test Venue",
                theme="Pre-Draw Test",
                guest_count=3,
                present_count=0,
                user_id=user_id,
            )
            .returning(events.c.id)
        ).scalar_one()

        prize_rows = conn.execute(
            insert(pre_draw_prizes)
            .values(
                [
                    {
                        "event_id": event_id,
                        "name": "Prize A",
                        "value": "RM 100",
                        "image_url": "",
                        "winner_count": 2,
                        "sort_order": 1,
                        "status": "ready",
                    },
                    {
                        "event_id": event_id,
                        "name": "Prize B",
                        "value": "RM 50",
                        "image_url": "",
                        "winner_count": 1,
                        "sort_order": 2,
                        "status": "ready",
                    },
                ]
            )
            .returning(
                pre_draw_prizes.c.id,
                pre_draw_prizes.c.name,
                pre_draw_prizes.c.winner_count,
            )
        ).mappings().all()

    prize_by_name = {
        row["name"]: row for row in prize_rows
    }

    try:
        yield {
            "event_id": event_id,
            "prize_a_id": int(prize_by_name["Prize A"]["id"]),
            "prize_b_id": int(prize_by_name["Prize B"]["id"]),
        }
    finally:
        with engine.begin() as conn:
            conn.execute(
                delete(events).where(events.c.id == event_id)
            )


def _winner(
    guest_id: str,
    name: str,
    prize_id: int,
    prize_name: str,
) -> dict:
    return {
        "guest_id": guest_id,
        "name": name,
        "prize_id": prize_id,
        "prize_name": prize_name,
        "prize_value": "",
        "image_url": "",
    }


def _read_state(event_id: int) -> tuple[list[dict], list[dict]]:
    with engine.connect() as conn:
        winners = [
            dict(row)
            for row in conn.execute(
                select(
                    pre_draw_winners.c.guest_id,
                    pre_draw_winners.c.name,
                    pre_draw_winners.c.prize_name,
                )
                .where(pre_draw_winners.c.event_id == event_id)
                .order_by(pre_draw_winners.c.id)
            ).mappings().all()
        ]

        prizes = [
            dict(row)
            for row in conn.execute(
                select(
                    pre_draw_prizes.c.id,
                    pre_draw_prizes.c.name,
                    pre_draw_prizes.c.winner_count,
                    pre_draw_prizes.c.status,
                )
                .where(pre_draw_prizes.c.event_id == event_id)
                .order_by(pre_draw_prizes.c.sort_order)
            ).mappings().all()
        ]

    return winners, prizes


def test_finalize_random_generation_persists_winners_and_marks_prizes_generated(
    postgres_repository,
    pre_draw_fixture,
):
    event_id = pre_draw_fixture["event_id"]
    prize_a_id = pre_draw_fixture["prize_a_id"]
    prize_b_id = pre_draw_fixture["prize_b_id"]

    winners = [
        _winner("G001", "Guest One", prize_a_id, "Prize A"),
        _winner("G002", "Guest Two", prize_a_id, "Prize A"),
        _winner("G003", "Guest Three", prize_b_id, "Prize B"),
    ]

    persisted = postgres_repository.finalize_random_generation(
        event_id=event_id,
        winners=winners,
        prize_ids=[prize_a_id, prize_b_id],
    )

    assert len(persisted) == 3
    assert {
        row["guest_id"]
        for row in persisted
    } == {"G001", "G002", "G003"}

    stored_winners, stored_prizes = _read_state(event_id)

    assert stored_winners == [
        {
            "guest_id": "G001",
            "name": "Guest One",
            "prize_name": "Prize A",
        },
        {
            "guest_id": "G002",
            "name": "Guest Two",
            "prize_name": "Prize A",
        },
        {
            "guest_id": "G003",
            "name": "Guest Three",
            "prize_name": "Prize B",
        },
    ]

    assert [
        (row["name"], row["winner_count"], row["status"])
        for row in stored_prizes
    ] == [
        ("Prize A", 2, "generated"),
        ("Prize B", 1, "generated"),
    ]


def test_finalize_random_generation_rejects_winner_count_mismatch_atomically(
    postgres_repository,
    pre_draw_fixture,
):
    event_id = pre_draw_fixture["event_id"]
    prize_a_id = pre_draw_fixture["prize_a_id"]
    prize_b_id = pre_draw_fixture["prize_b_id"]

    winners = [
        _winner("G001", "Guest One", prize_a_id, "Prize A"),
        _winner("G003", "Guest Three", prize_b_id, "Prize B"),
    ]

    with pytest.raises(
        ValueError,
        match="winner counts no longer match",
    ):
        postgres_repository.finalize_random_generation(
            event_id=event_id,
            winners=winners,
            prize_ids=[prize_a_id, prize_b_id],
        )

    stored_winners, stored_prizes = _read_state(event_id)

    assert stored_winners == []

    assert [
        (row["name"], row["status"])
        for row in stored_prizes
    ] == [
        ("Prize A", "ready"),
        ("Prize B", "ready"),
    ]


def test_finalize_random_generation_rejects_fabricated_prize_configuration(
    postgres_repository,
    pre_draw_fixture,
):
    event_id = pre_draw_fixture["event_id"]
    prize_a_id = pre_draw_fixture["prize_a_id"]
    prize_b_id = pre_draw_fixture["prize_b_id"]

    fabricated_prize_id = max(
        prize_a_id,
        prize_b_id,
    ) + 999999

    winners = [
        _winner(
            "G001",
            "Guest One",
            prize_a_id,
            "Prize A",
        ),
        _winner(
            "G002",
            "Guest Two",
            prize_a_id,
            "Prize A",
        ),
        _winner(
            "G003",
            "Guest Three",
            prize_b_id,
            "Prize B",
        ),
    ]

    with pytest.raises(
        ValueError,
        match="prize configuration changed",
    ):
        postgres_repository.finalize_random_generation(
            event_id=event_id,
            winners=winners,
            prize_ids=[
                prize_a_id,
                prize_b_id,
                fabricated_prize_id,
            ],
        )

    stored_winners, stored_prizes = _read_state(event_id)

    assert stored_winners == []

    assert [
        (row["name"], row["status"])
        for row in stored_prizes
    ] == [
        ("Prize A", "ready"),
        ("Prize B", "ready"),
    ]


def test_finalize_random_generation_cannot_overwrite_existing_generation(
    postgres_repository,
    pre_draw_fixture,
):
    event_id = pre_draw_fixture["event_id"]
    prize_a_id = pre_draw_fixture["prize_a_id"]
    prize_b_id = pre_draw_fixture["prize_b_id"]

    original_winners = [
        _winner("G001", "Guest One", prize_a_id, "Prize A"),
        _winner("G002", "Guest Two", prize_a_id, "Prize A"),
        _winner("G003", "Guest Three", prize_b_id, "Prize B"),
    ]

    postgres_repository.finalize_random_generation(
        event_id=event_id,
        winners=original_winners,
        prize_ids=[prize_a_id, prize_b_id],
    )

    replacement_winners = [
        _winner("G101", "Guest One Hundred One", prize_a_id, "Prize A"),
        _winner("G102", "Guest One Hundred Two", prize_a_id, "Prize A"),
        _winner("G103", "Guest One Hundred Three", prize_b_id, "Prize B"),
    ]

    with pytest.raises(
        ValueError,
        match="winners already exist",
    ):
        postgres_repository.finalize_random_generation(
            event_id=event_id,
            winners=replacement_winners,
            prize_ids=[prize_a_id, prize_b_id],
        )

    stored_winners, stored_prizes = _read_state(event_id)

    assert [
        row["guest_id"]
        for row in stored_winners
    ] == [
        "G001",
        "G002",
        "G003",
    ]

    assert [
        (row["name"], row["status"])
        for row in stored_prizes
    ] == [
        ("Prize A", "generated"),
        ("Prize B", "generated"),
    ]
