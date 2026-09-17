from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, event, select
from sqlalchemy.pool import StaticPool

from guest_management.database import (
    Database,
    checkins,
    events,
    guests,
)


@pytest.fixture
def database():
    """
    Create an isolated in-memory SQLite database for each test.
    """
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    # Create only the tables required by the check-in transaction.
    events.create(engine)
    guests.create(engine)
    checkins.create(engine)

    return Database(db_engine=engine)


def seed_event_and_guest(
    database,
    *,
    event_id=1,
    guest_id="G001",
    status="Absent",
    guest_count=1,
    present_count=0,
):
    """
    Insert a minimal event + guest fixture.
    """
    now = datetime.now(timezone.utc)

    with database.engine.begin() as conn:
        conn.execute(
            events.insert().values(
                id=event_id,
                name="Test Event",
                event_type="company_dinner",
                company_name="Test Company",
                date="2026-09-14",
                time="19:00",
                venue="Test Venue",
                theme="Test Theme",
                guest_count=guest_count,
                present_count=present_count,
                user_id="test-user",
                logo="",
                wedding_invitation="",
                logo_storage_path="",
                logo_filename="",
                logo_mime_type="",
                invitation_storage_path="",
                invitation_filename="",
                invitation_mime_type="",
                guest_list_storage_path="",
                guest_list_filename="",
                guest_list_mime_type="",
                guest_list_uploaded_at=None,
                created_at=now,
                updated_at=now,

            )
        )

        conn.execute(
            guests.insert().values(
                event_id=event_id,
                guest_id=guest_id,
                name="Test Guest",
                email="test@example.com",
                phone="0123456789",
                status=status,
                table_number="T01",
                amount=0,
                team_name=None,
                qr_code=None,
                qr_url=None,
                email_sent=False,
                full_data={},
                created_at=now,
                updated_at=now,
            )
        )


def get_guest(database, event_id, guest_id):
    with database.engine.connect() as conn:
        return conn.execute(
            select(guests).where(
                guests.c.event_id == event_id,
                guests.c.guest_id == guest_id,
            )
        ).mappings().one()


def get_event(database, event_id):
    with database.engine.connect() as conn:
        return conn.execute(
            select(events).where(events.c.id == event_id)
        ).mappings().one()


def get_checkins(database):
    with database.engine.connect() as conn:
        return conn.execute(
            select(checkins).order_by(checkins.c.id)
        ).mappings().all()


def test_successful_checkin_updates_guest_and_event(database):
    seed_event_and_guest(database)

    result = database.check_in_guest(
        {
            "p_event_id": 1,
            "p_guest_id": "G001",
            "p_scanner_id": "scanner-01",
        }
    )

    result = get_rpc_result(result)
    assert result["result"] == "checked_in"

    guest = get_guest(database, 1, "G001")
    event = get_event(database, 1)

    assert guest["status"] == "Present"
    assert event["guest_count"] == 1
    assert event["present_count"] == 1


def test_successful_checkin_creates_checkin_record(database):
    seed_event_and_guest(database)

    database.check_in_guest(
        {
            "p_event_id": 1,
            "p_guest_id": "G001",
            "p_scanner_id": "scanner-01",
        }
    )

    records = get_checkins(database)

    assert len(records) == 1

    record = records[0]

    assert record["event_id"] == 1
    assert record["guest_id"] == "G001"
    assert record["scanner_id"] == "scanner-01"
    assert record["result"] == "checked_in"
    assert record["checked_in_at"] is not None
    assert record["created_at"] is not None


def test_second_checkin_does_not_change_present_count(database):
    seed_event_and_guest(database)

    first = database.check_in_guest(
        {
            "p_event_id": 1,
            "p_guest_id": "G001",
            "p_scanner_id": "scanner-01",
        }
    )

    second = database.check_in_guest(
        {
            "p_event_id": 1,
            "p_guest_id": "G001",
            "p_scanner_id": "scanner-02",
        }
    )

    first = get_rpc_result(first)
    second = get_rpc_result(second)

    assert first["result"] == "checked_in"
    assert second["result"] == "already_checked_in"

    event = get_event(database, 1)

    assert event["guest_count"] == 1
    assert event["present_count"] == 1


def test_second_checkin_creates_already_checked_in_record(database):
    seed_event_and_guest(database)

    database.check_in_guest(
        {
            "p_event_id": 1,
            "p_guest_id": "G001",
            "p_scanner_id": "scanner-01",
        }
    )

    database.check_in_guest(
        {
            "p_event_id": 1,
            "p_guest_id": "G001",
            "p_scanner_id": "scanner-02",
        }
    )

    records = get_checkins(database)

    assert len(records) == 2

    assert records[0]["result"] == "checked_in"
    assert records[0]["scanner_id"] == "scanner-01"

    assert records[1]["result"] == "already_checked_in"
    assert records[1]["scanner_id"] == "scanner-02"


def test_missing_guest_returns_not_found(database):
    seed_event_and_guest(database)

    result = database.check_in_guest(
        {
            "p_event_id": 1,
            "p_guest_id": "DOES_NOT_EXIST",
            "p_scanner_id": "scanner-01",
        }
    )

    result = get_rpc_result(result)
    assert result["result"] == "not_found"

    event = get_event(database, 1)

    assert event["guest_count"] == 1
    assert event["present_count"] == 0

    records = get_checkins(database)

    assert len(records) == 1
    assert records[0]["event_id"] == 1
    assert records[0]["guest_id"] == "DOES_NOT_EXIST"
    assert records[0]["scanner_id"] == "scanner-01"
    assert records[0]["result"] == "not_found"


def test_guest_is_isolated_by_event(database):
    seed_event_and_guest(
        database,
        event_id=1,
        guest_id="G001",
    )

    seed_event_and_guest(
        database,
        event_id=2,
        guest_id="G001",
    )

    result = database.check_in_guest(
        {
            "p_event_id": 2,
            "p_guest_id": "G001",
            "p_scanner_id": "scanner-02",
        }
    )

    result = get_rpc_result(result)
    assert result["result"] == "checked_in"

    guest_event_1 = get_guest(database, 1, "G001")
    guest_event_2 = get_guest(database, 2, "G001")

    assert guest_event_1["status"] == "Absent"
    assert guest_event_2["status"] == "Present"

    event_1 = get_event(database, 1)
    event_2 = get_event(database, 2)

    assert event_1["present_count"] == 0
    assert event_2["present_count"] == 1


def test_scanner_id_is_optional(database):
    seed_event_and_guest(database)

    result = database.check_in_guest(
        {
            "p_event_id": 1,
            "p_guest_id": "G001",
        }
    )

    result = get_rpc_result(result)
    assert result["result"] == "checked_in"

    records = get_checkins(database)

    assert len(records) == 1
    assert records[0]["scanner_id"] is None


def test_checkin_transaction_rolls_back_all_changes_when_late_write_fails(database):
    """
    Verify the check-in operation is atomic.

    The production implementation performs several writes inside one
    transaction: guest status, check-in history, and event counters.
    Simulate a failure after the event UPDATE has executed so the test
    proves all changes are rolled back together.
    """
    seed_event_and_guest(database)

    def fail_after_event_update(
        conn, cursor, statement, parameters, context, executemany
    ):
        if "UPDATE EVENTS" in statement.upper():
            raise RuntimeError("simulated event counter update failure")

    event.listen(
        database.engine,
        "after_cursor_execute",
        fail_after_event_update,
    )

    try:
        with pytest.raises(
            RuntimeError,
            match="simulated event counter update failure",
        ):
            database.check_in_guest(
                {
                    "p_event_id": 1,
                    "p_guest_id": "G001",
                    "p_scanner_id": "scanner-01",
                }
            )
    finally:
        event.remove(
            database.engine,
            "after_cursor_execute",
            fail_after_event_update,
        )

    guest = get_guest(database, 1, "G001")
    event_row = get_event(database, 1)
    records = get_checkins(database)

    # Guest status must be restored.
    assert guest["status"] == "Absent"

    # Event counters must remain unchanged.
    assert event_row["guest_count"] == 1
    assert event_row["present_count"] == 0

    # No partial check-in record may remain.
    assert records == []



def test_multiple_guests_keep_event_counts_consistent(database):
    """
    Verify event counters track distinct guests as they check in.
    """
    seed_event_and_guest(database, guest_id="G001", guest_count=3)

    # Add two more guests to the same event.
    now = datetime.now(timezone.utc)
    with database.engine.begin() as conn:
        conn.execute(
            guests.insert().values(
                event_id=1,
                guest_id="G002",
                name="Second Guest",
                email="second@example.com",
                phone="0123456789",
                status="Absent",
                table_number="T02",
                amount=0,
                team_name=None,
                qr_code=None,
                qr_url=None,
                email_sent=False,
                full_data={},
                created_at=now,
                updated_at=now,
            )
        )
        conn.execute(
            guests.insert().values(
                event_id=1,
                guest_id="G003",
                name="Third Guest",
                email="third@example.com",
                phone="0123456789",
                status="Absent",
                table_number="T03",
                amount=0,
                team_name=None,
                qr_code=None,
                qr_url=None,
                email_sent=False,
                full_data={},
                created_at=now,
                updated_at=now,
            )
        )

    # Guest A -> 1/3
    result = get_rpc_result(
        database.check_in_guest(
            {
                "p_event_id": 1,
                "p_guest_id": "G001",
                "p_scanner_id": "scanner-01",
            }
        )
    )
    assert result["result"] == "checked_in"
    assert result["present_count"] == 1
    assert result["total_guests"] == 3

    event_row = get_event(database, 1)
    assert event_row["guest_count"] == 3
    assert event_row["present_count"] == 1

    # Guest B -> 2/3
    result = get_rpc_result(
        database.check_in_guest(
            {
                "p_event_id": 1,
                "p_guest_id": "G002",
                "p_scanner_id": "scanner-02",
            }
        )
    )
    assert result["result"] == "checked_in"
    assert result["present_count"] == 2
    assert result["total_guests"] == 3

    event_row = get_event(database, 1)
    assert event_row["guest_count"] == 3
    assert event_row["present_count"] == 2

    # Guest A scans again -> still 2/3.
    result = get_rpc_result(
        database.check_in_guest(
            {
                "p_event_id": 1,
                "p_guest_id": "G001",
                "p_scanner_id": "scanner-03",
            }
        )
    )
    assert result["result"] == "already_checked_in"
    assert result["present_count"] == 2
    assert result["total_guests"] == 3

    event_row = get_event(database, 1)
    assert event_row["guest_count"] == 3
    assert event_row["present_count"] == 2

    # Guest C -> 3/3.
    result = get_rpc_result(
        database.check_in_guest(
            {
                "p_event_id": 1,
                "p_guest_id": "G003",
                "p_scanner_id": "scanner-04",
            }
        )
    )
    assert result["result"] == "checked_in"
    assert result["present_count"] == 3
    assert result["total_guests"] == 3

    event_row = get_event(database, 1)
    assert event_row["guest_count"] == 3
    assert event_row["present_count"] == 3


def test_multiple_guest_checkin_history_records_are_independent(database):
    """
    Verify successful and duplicate scans create the expected history
    without corrupting another guest's check-in state.
    """
    seed_event_and_guest(database, guest_id="G001", guest_count=2)

    now = datetime.now(timezone.utc)
    with database.engine.begin() as conn:
        conn.execute(
            guests.insert().values(
                event_id=1,
                guest_id="G002",
                name="Second Guest",
                email="second@example.com",
                phone="0123456789",
                status="Absent",
                table_number="T02",
                amount=0,
                team_name=None,
                qr_code=None,
                qr_url=None,
                email_sent=False,
                full_data={},
                created_at=now,
                updated_at=now,
            )
        )

    database.check_in_guest(
        {
            "p_event_id": 1,
            "p_guest_id": "G001",
            "p_scanner_id": "scanner-01",
        }
    )
    database.check_in_guest(
        {
            "p_event_id": 1,
            "p_guest_id": "G002",
            "p_scanner_id": "scanner-02",
        }
    )
    database.check_in_guest(
        {
            "p_event_id": 1,
            "p_guest_id": "G001",
            "p_scanner_id": "scanner-03",
        }
    )

    records = get_checkins(database)

    assert len(records) == 3

    assert records[0]["guest_id"] == "G001"
    assert records[0]["scanner_id"] == "scanner-01"
    assert records[0]["result"] == "checked_in"

    assert records[1]["guest_id"] == "G002"
    assert records[1]["scanner_id"] == "scanner-02"
    assert records[1]["result"] == "checked_in"

    assert records[2]["guest_id"] == "G001"
    assert records[2]["scanner_id"] == "scanner-03"
    assert records[2]["result"] == "already_checked_in"

    assert get_guest(database, 1, "G001")["status"] == "Present"
    assert get_guest(database, 1, "G002")["status"] == "Present"

    event_row = get_event(database, 1)
    assert event_row["guest_count"] == 2
    assert event_row["present_count"] == 2



def test_missing_event_id_is_rejected_at_database_boundary(database):
    seed_event_and_guest(database)

    with pytest.raises(KeyError, match="p_event_id"):
        database.check_in_guest(
            {
                "p_guest_id": "G001",
                "p_scanner_id": "scanner-01",
            }
        )


def test_missing_guest_id_is_rejected_at_database_boundary(database):
    seed_event_and_guest(database)

    with pytest.raises(KeyError, match="p_guest_id"):
        database.check_in_guest(
            {
                "p_event_id": 1,
                "p_scanner_id": "scanner-01",
            }
        )


def test_non_numeric_event_id_is_rejected_at_database_boundary(database):
    seed_event_and_guest(database)

    with pytest.raises(ValueError):
        database.check_in_guest(
            {
                "p_event_id": "not-a-number",
                "p_guest_id": "G001",
                "p_scanner_id": "scanner-01",
            }
        )


def test_guest_id_whitespace_is_normalized(database):
    seed_event_and_guest(database)

    result = get_rpc_result(
        database.check_in_guest(
            {
                "p_event_id": "1",
                "p_guest_id": "  G001  ",
                "p_scanner_id": "scanner-01",
            }
        )
    )

    assert result["result"] == "checked_in"
    assert result["event_id"] == 1
    assert result["guest_id"] == "G001"

    guest = get_guest(database, 1, "G001")
    assert guest["status"] == "Present"

    records = get_checkins(database)
    assert len(records) == 1
    assert records[0]["guest_id"] == "G001"


def test_blank_guest_id_is_treated_as_unknown_guest(database):
    seed_event_and_guest(database)

    result = get_rpc_result(
        database.check_in_guest(
            {
                "p_event_id": 1,
                "p_guest_id": "   ",
                "p_scanner_id": "scanner-01",
            }
        )
    )

    assert result["result"] == "not_found"
    assert result["guest_id"] == ""

    guest = get_guest(database, 1, "G001")
    assert guest["status"] == "Absent"

    records = get_checkins(database)
    assert len(records) == 1
    assert records[0]["guest_id"] == ""
    assert records[0]["result"] == "not_found"

def get_rpc_result(result):
    """
    Unwrap the application's database Result wrapper.

    Database.check_in_guest() returns guest_management.database.Result,
    whose payload is stored in ``result.data``.
    """
    assert result.data, "Database.check_in_guest() returned no data"
    row = result.data[0]
    assert isinstance(row, dict), "Database result row must be a dict"
    return row


def test_existing_present_guest_returns_already_checked_in(database):
    seed_event_and_guest(
        database,
        status="Present",
        present_count=1,
    )

    result = get_rpc_result(
        database.check_in_guest(
            {
                "p_event_id": 1,
                "p_guest_id": "G001",
                "p_scanner_id": "scanner-01",
            }
        )
    )

    assert result["result"] == "already_checked_in"


    guest = get_guest(database, 1, "G001")
    event = get_event(database, 1)

    assert guest["status"] == "Present"
    assert event["present_count"] == 1
