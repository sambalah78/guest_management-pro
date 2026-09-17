"""
PostgreSQL concurrency tests for the database check-in boundary.

These tests are intentionally opt-in.

Set TEST_DATABASE_URL to a dedicated disposable PostgreSQL database before
running them. NEVER point TEST_DATABASE_URL at a live production database.

Examples (PowerShell):
    $env:TEST_DATABASE_URL = "postgresql://..."
    python -m pytest tests/test_database_checkin_postgres.py -q

The existing SQLite check-in tests remain the primary fast test suite.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, delete, select, text

from guest_management.database import Database, checkins, events, guests


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
TEST_ENGINE = None

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="Set TEST_DATABASE_URL to run PostgreSQL concurrency tests",
)


@pytest.fixture
def postgres_database():
    global TEST_ENGINE

    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not configured")

    TEST_ENGINE = create_engine(
        TEST_DATABASE_URL,
        pool_size=10,
        max_overflow=0,
        pool_pre_ping=True,
    )

    try:
        with TEST_ENGINE.connect() as conn:
            conn.execute(text("SELECT 1"))

        db = Database(db_engine=TEST_ENGINE)

        # Only clean the dedicated test event and its dependent rows.
        # Never modify public.users or auth.users.
        with TEST_ENGINE.begin() as conn:
            conn.execute(delete(checkins).where(checkins.c.event_id == 990001))
            conn.execute(delete(guests).where(guests.c.event_id == 990001))
            conn.execute(delete(events).where(events.c.id == 990001))

        yield db

    finally:
        # Clean only the dedicated test event and its dependent rows.
        if TEST_ENGINE is not None:
            with TEST_ENGINE.begin() as conn:
                conn.execute(delete(checkins).where(checkins.c.event_id == 990001))
                conn.execute(delete(guests).where(guests.c.event_id == 990001))
                conn.execute(delete(events).where(events.c.id == 990001))

            TEST_ENGINE.dispose()
            TEST_ENGINE = None


def seed_event(db: Database, guest_ids: list[str]) -> None:
    now = datetime.now(timezone.utc)
    test_user_id = "554208ae-d98e-4803-8e9b-0bb9625a6861"

    with db.engine.begin() as conn:


        conn.execute(
            events.insert().values(
                id=990001,
                name="Concurrency Test Event",
                event_type="company_dinner",
                company_name="Test Company",
                date="2026-09-14",
                time="19:00",
                venue="Test Venue",
                theme="Concurrency",
                guest_count=len(guest_ids),
                present_count=0,
                user_id=test_user_id,
                logo="test-logo",
                wedding_invitation="test-invitation",
                guest_list_uploaded_at=None,
                created_at=now,
                updated_at=now,
            )
        )

        conn.execute(
            guests.insert(),
            [
                {
                    "event_id": 990001,
                    "guest_id": guest_id,
                    "name": f"Guest {guest_id}",
                    "email": f"{guest_id.lower()}@example.com",
                    "phone": "0123456789",
                    "status": "Absent",
                    "table_number": "T01",
                    "amount": 0,
                    "team_name": None,
                    "qr_code": None,
                    "qr_url": None,
                    "email_sent": False,
                    "full_data": {},
                    "created_at": now,
                    "updated_at": now,
                }
                for guest_id in guest_ids
            ],
        )


def rpc_result(result):
    assert result.data
    assert isinstance(result.data[0], dict)
    return result.data[0]


def check_in_worker(engine, guest_id):
    db = Database(db_engine=engine)

    result = db.check_in_guest(
        {
            "p_event_id": 990001,
            "p_guest_id": guest_id,
            "p_scanner_id": f"scanner-{guest_id}",
        }
    )

    return result.data[0]["result"]

def read_guest(db: Database, guest_id: str):
    with db.engine.connect() as conn:
        return conn.execute(
            select(guests).where(
                guests.c.event_id == 990001,
                guests.c.guest_id == guest_id,
            )
        ).mappings().one()


def read_event(db: Database):
    with db.engine.connect() as conn:
        return conn.execute(
            select(events).where(events.c.id == 990001)
        ).mappings().one()


def read_checkins(db: Database):
    with db.engine.connect() as conn:
        return conn.execute(
            select(checkins)
            .where(checkins.c.event_id == 990001)
            .order_by(checkins.c.id)
        ).mappings().all()


def test_same_guest_concurrent_scans_accept_only_once(postgres_database):
    """
    Two independent PostgreSQL connections race to check in the same guest.

    Expected invariant:
      exactly one call is "checked_in"
      exactly one call is "already_checked_in"
      guest status is Present
      history contains both outcomes
    """
    seed_event(postgres_database, ["G001"])

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [
            executor.submit(check_in_worker, postgres_database.engine, "G001"),
            executor.submit(check_in_worker, postgres_database.engine, "G001"),
        ]
        results = [future.result() for future in futures]

    assert sorted(results) == ["already_checked_in", "checked_in"]

    guest = read_guest(postgres_database, "G001")
    assert guest["status"] == "Present"

    history = read_checkins(postgres_database)
    assert len(history) == 2
    assert sorted(row["result"] for row in history) == [
        "already_checked_in",
        "checked_in",
    ]


def test_different_guests_can_check_in_concurrently(postgres_database):
    """
    Multiple scanners check in different guests concurrently.

    Expected invariant:
      every guest is accepted exactly once
      all guest rows become Present
      event.present_count equals the number of Present guests
      event.guest_count remains the total guest count
    """
    guest_ids = [f"G{i:03d}" for i in range(1, 101)]
    seed_event(postgres_database, guest_ids)

    with ThreadPoolExecutor(max_workers=len(guest_ids)) as executor:
        futures = [
            executor.submit(
                check_in_worker,
                postgres_database.engine,
                guest_id,
            )
            for guest_id in guest_ids
        ]
        results = [future.result() for future in futures]

    assert results == ["checked_in"] * len(guest_ids)

    for guest_id in guest_ids:
        guest = read_guest(postgres_database, guest_id)
        assert guest["status"] == "Present"

    event = read_event(postgres_database)
    assert event["guest_count"] == len(guest_ids)
    assert event["present_count"] == len(guest_ids)

    history = read_checkins(postgres_database)
    assert len(history) == len(guest_ids)
    assert all(row["result"] == "checked_in" for row in history)
    assert {row["guest_id"] for row in history} == set(guest_ids)
