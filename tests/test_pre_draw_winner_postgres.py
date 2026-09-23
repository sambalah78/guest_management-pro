"""
Opt-in PostgreSQL transaction/concurrency tests for pre-draw winners.

These tests require a dedicated disposable PostgreSQL database.

Set TEST_DATABASE_URL before running them:

    $env:TEST_DATABASE_URL = "postgresql://..."
    python -m pytest -q tests/test_pre_draw_winner_postgres.py

NEVER point TEST_DATABASE_URL at a production database.
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier

import pytest
from sqlalchemy import create_engine, delete, select
from sqlalchemy.exc import IntegrityError

from guest_management.database import (
    Database,
    events,
    pre_draw_winners,
    users,
)
from guest_management.repositories.pre_draw_winner_repository import (
    PreDrawWinnerRepository,
)


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "").strip()

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL is not configured; PostgreSQL pre-draw tests are opt-in.",
)

EVENT_ID = 990003


@pytest.fixture(scope="module")
def test_engine():
    """Create a bounded SQLAlchemy engine for the dedicated test database."""
    if not TEST_DATABASE_URL:
        pytest.skip("TEST_DATABASE_URL is not configured")

    engine = create_engine(
        TEST_DATABASE_URL,
        future=True,
        pool_size=4,
        max_overflow=0,
        pool_pre_ping=True,
    )

    assert engine.url.get_backend_name() == "postgresql", (
        "TEST_DATABASE_URL must point to PostgreSQL."
    )

    try:
        with engine.connect() as conn:
            conn.execute(select(1))
        yield engine
    finally:
        engine.dispose()


@pytest.fixture
def postgres_database(test_engine):
    """Create and clean one deterministic test event."""
    db = Database(db_engine=test_engine)

    cleanup_event(test_engine)

    user_id = get_test_user_id(test_engine)

    now = datetime.now(timezone.utc)

    with test_engine.begin() as conn:
        conn.execute(
            events.insert().values(
                id=EVENT_ID,
                name="Pre-Draw Concurrency Test Event",
                event_type="company_dinner",
                company_name="EventLah Pre-Draw Test",
                date="2026-09-21",
                time="19:00",
                venue="Pre-Draw Test Venue",
                theme="Pre-Draw Concurrency",
                guest_count=0,
                present_count=0,
                user_id=user_id,
                logo="",
                wedding_invitation="",
                guest_list_uploaded_at=None,
                created_at=now,
                updated_at=now,
            )
        )

    try:
        yield db
    finally:
        cleanup_event(test_engine)


def get_test_user_id(engine) -> str:
    """
    Reuse an existing test-database user.

    We deliberately do not create, modify, or delete users as part of
    this test suite.
    """
    with engine.connect() as conn:
        user_id = conn.execute(
            select(users.c.id).limit(1)
        ).scalar_one_or_none()

    if user_id is None:
        pytest.fail(
            "Dedicated TEST_DATABASE_URL database contains no users "
            "row to satisfy the events.user_id foreign key."
        )

    return str(user_id)


def cleanup_event(engine) -> None:
    """Remove only the deterministic pre-draw test event and children."""
    with engine.begin() as conn:
        conn.execute(
            delete(pre_draw_winners).where(
                pre_draw_winners.c.event_id == EVENT_ID
            )
        )
        conn.execute(
            delete(events).where(
                events.c.id == EVENT_ID
            )
        )


def read_winner_guest_ids(db: Database) -> list[str]:
    """Return the current winner IDs in deterministic order."""
    with db.engine.connect() as conn:
        rows = conn.execute(
            select(pre_draw_winners.c.guest_id)
            .where(
                pre_draw_winners.c.event_id == EVENT_ID
            )
            .order_by(
                pre_draw_winners.c.guest_id
            )
        ).scalars().all()

    return list(rows)


def test_failed_replacement_rolls_back_existing_winners(
    postgres_database,
):
    """
    A failed insert must not leave the event with an empty/partial list.

    The duplicate guest IDs deliberately violate the database unique
    constraint during the replacement insert.
    """
    repository = PreDrawWinnerRepository(db=postgres_database)

    original_winners = [
        {
            "guest_id": "ROLLBACK-A",
            "name": "Rollback A",
            "prize_name": "Original Prize A",
            "prize_value": "100",
            "image_url": "",
        },
        {
            "guest_id": "ROLLBACK-B",
            "name": "Rollback B",
            "prize_name": "Original Prize B",
            "prize_value": "200",
            "image_url": "",
        },
    ]

    repository.replace_for_event(
        EVENT_ID,
        original_winners,
    )

    assert read_winner_guest_ids(postgres_database) == [
        "ROLLBACK-A",
        "ROLLBACK-B",
    ]

    invalid_replacement = [
        {
            "guest_id": "BROKEN-A",
            "name": "Broken A",
            "prize_name": "Broken Prize A",
            "prize_value": "300",
            "image_url": "",
        },
        {
            # Deliberate duplicate inside the same transaction.
            "guest_id": "BROKEN-A",
            "name": "Broken Duplicate",
            "prize_name": "Broken Prize B",
            "prize_value": "400",
            "image_url": "",
        },
    ]

    with pytest.raises(IntegrityError):
        repository.replace_for_event(
            EVENT_ID,
            invalid_replacement,
        )

    # The failed INSERT must roll back the preceding DELETE.
    assert read_winner_guest_ids(postgres_database) == [
        "ROLLBACK-A",
        "ROLLBACK-B",
    ]


def test_concurrent_replacements_are_serialized(
    postgres_database,
):
    """
    Two simultaneous replacements for the same event must serialize.

    The final state must be exactly one complete replacement set:
    either A or B, but never A+B.
    """
    repository_a = PreDrawWinnerRepository(db=postgres_database)
    repository_b = PreDrawWinnerRepository(db=postgres_database)

    initial_winners = [
        {
            "guest_id": "INITIAL-A",
            "name": "Initial A",
            "prize_name": "",
            "prize_value": "",
            "image_url": "",
        }
    ]

    repository_a.replace_for_event(
        EVENT_ID,
        initial_winners,
    )

    winners_a = [
        {
            "guest_id": "SET-A-1",
            "name": "Set A 1",
            "prize_name": "Prize A1",
            "prize_value": "100",
            "image_url": "",
        },
        {
            "guest_id": "SET-A-2",
            "name": "Set A 2",
            "prize_name": "Prize A2",
            "prize_value": "200",
            "image_url": "",
        },
    ]

    winners_b = [
        {
            "guest_id": "SET-B-1",
            "name": "Set B 1",
            "prize_name": "Prize B1",
            "prize_value": "300",
            "image_url": "",
        },
        {
            "guest_id": "SET-B-2",
            "name": "Set B 2",
            "prize_name": "Prize B2",
            "prize_value": "400",
            "image_url": "",
        },
    ]

    barrier = Barrier(2)

    def worker(repository, winners):
        barrier.wait()
        return repository.replace_for_event(
            EVENT_ID,
            winners,
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(
            worker,
            repository_a,
            winners_a,
        )
        future_b = executor.submit(
            worker,
            repository_b,
            winners_b,
        )

        future_a.result()
        future_b.result()

    final_ids = set(
        read_winner_guest_ids(postgres_database)
    )

    assert final_ids == {"SET-A-1", "SET-A-2"} or final_ids == {
        "SET-B-1",
        "SET-B-2",
    }

    assert len(final_ids) == 2
