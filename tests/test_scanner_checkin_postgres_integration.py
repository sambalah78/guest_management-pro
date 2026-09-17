"""Opt-in PostgreSQL integration tests for the production scanner check-in path.

These tests intentionally exercise the real application services/repositories
against a dedicated disposable PostgreSQL database.

Required environment:
    TEST_DATABASE_URL=<dedicated disposable PostgreSQL URL>

The test database must already contain the EventLah schema/migrations and the
admin UUID used below. NEVER point TEST_DATABASE_URL at production.

Coverage:
- production QR URL generation
- signed QR validation
- real scanner station provisioning/authentication
- scanner/event and scanner/device binding
- inactive/invalid scanner rejection
- concurrent same-guest check-in
- concurrent different-guest check-in
- event present_count correctness
- check-in history persistence
"""

from __future__ import annotations

import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone

import pytest
from sqlalchemy import create_engine, delete, select, update
from sqlalchemy.engine import Engine
from sqlalchemy.exc import SQLAlchemyError

from guest_management.core.exceptions import (
    GuestAlreadyCheckedInError,
    GuestNotFoundError,
    ValidationError,
)
from guest_management.core.security import create_qr_token
from guest_management.database import (
    Database,
    checkin_history,
    checkins,
    events,
    guests,
    scanner_devices,
)
from guest_management.repositories.checkin_repository import CheckinRepository
from guest_management.repositories.scanner_repository import ScannerRepository
from guest_management.services.checkin_service import CheckinService
from guest_management.services.qr_service import QRService
from guest_management.services.scanner_station_auth_service import (
    ScannerStationAuthService,
)


TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "").strip()

pytestmark = pytest.mark.skipif(
    not TEST_DATABASE_URL,
    reason="TEST_DATABASE_URL is not configured; PostgreSQL integration suite is opt-in.",
)

EVENT_ID = 990002
TEST_USER_ID = "554208ae-d98e-4803-8e9b-0bb9625a6861"

SAME_GUEST_ID = "integration-same-guest"
DIFFERENT_GUEST_PREFIX = "integration-guest-"

MAX_WORKERS = 10
DIFFERENT_GUEST_COUNT = 100


@pytest.fixture(scope="module")
def test_engine() -> Engine:
    """Create a bounded engine directly from the explicit disposable test URL."""
    # IMPORTANT: Database(db_engine=None) intentionally stores None in the
    # current provider-independent database layer. Build the test engine
    # explicitly so this suite can never silently fall back to the application
    # database.
    engine = create_engine(
        TEST_DATABASE_URL,
        future=True,
        pool_size=MAX_WORKERS,
        max_overflow=0,
        pool_pre_ping=True,
    )

    # Refuse to run if SQLAlchemy normalized the URL unexpectedly.
    assert engine.url.get_backend_name() == "postgresql", (
        "TEST_DATABASE_URL must point to PostgreSQL."
    )

    yield engine
    engine.dispose()


@pytest.fixture(scope="module")
def seeded_database(test_engine: Engine):
    """Seed one disposable event and its guests, then remove all test data."""
    db = Database(db_engine=test_engine)

    guest_ids = [
        SAME_GUEST_ID,
        *[
            f"{DIFFERENT_GUEST_PREFIX}{index:03d}"
            for index in range(DIFFERENT_GUEST_COUNT)
        ],
    ]

    cleanup_event(db)

    now = datetime.now(timezone.utc)

    with test_engine.begin() as conn:
        conn.execute(
            events.insert().values(
                id=EVENT_ID,
                name="Scanner Integration Test Event",
                event_type="company_dinner",
                company_name="EventLah Integration Test",
                date="2026-09-17",
                time="19:00",
                venue="Integration Test Venue",
                theme="Scanner Security",
                guest_count=len(guest_ids),
                present_count=0,
                user_id=TEST_USER_ID,
                logo="",
                wedding_invitation="",
                guest_list_uploaded_at=None,
                created_at=now,
                updated_at=now,
            )
        )

        conn.execute(
            guests.insert(),
            [
                {
                    "event_id": EVENT_ID,
                    "guest_id": guest_id,
                    "name": f"Integration Guest {guest_id}",
                    "email": f"{guest_id}@example.com",
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

    yield db

    cleanup_event(db)


def cleanup_event(db: Database) -> None:
    """Remove only the deterministic integration-test event and its children."""
    try:
        with db.engine.begin() as conn:
            # Explicit child cleanup keeps this safe even if FK cascade rules
            # change between environments.
            conn.execute(
                delete(scanner_devices).where(
                    scanner_devices.c.event_id == EVENT_ID
                )
            )
            conn.execute(
                delete(checkin_history).where(
                    checkin_history.c.event_id == EVENT_ID
                )
            )
            conn.execute(
                delete(checkins).where(
                    checkins.c.event_id == EVENT_ID
                )
            )
            conn.execute(
                delete(guests).where(
                    guests.c.event_id == EVENT_ID
                )
            )
            conn.execute(
                delete(events).where(
                    events.c.id == EVENT_ID
                )
            )
    except SQLAlchemyError as exc:
        # Cleanup before the fixture exists should be best-effort, but cleanup
        # after a test must still surface a real database problem.
        if os.getenv("PYTEST_CURRENT_TEST", "").endswith(" (setup)"):
            return
        raise RuntimeError("Integration-test cleanup failed") from exc


def production_qr(guest_id: str) -> str:
    """Generate the same signed check-in URL used by the application."""
    return QRService().guest_url(guest_id, EVENT_ID)


def build_checkin_service(test_engine: Engine) -> CheckinService:
    """Build the real check-in service against the disposable test database."""
    checkin_repo = CheckinRepository(db=Database(db_engine=test_engine))
    scanner_repo = ScannerRepository(db=Database(db_engine=test_engine))
    scanner_auth = ScannerStationAuthService(repo=scanner_repo)
    return CheckinService(
        repository=checkin_repo,
        scanner_auth_service=scanner_auth,
    )


def build_scanner_auth_service(test_engine: Engine) -> ScannerStationAuthService:
    """Build scanner authentication against the disposable test database."""
    scanner_repo = ScannerRepository(db=Database(db_engine=test_engine))
    return ScannerStationAuthService(repo=scanner_repo)


def direct_signed_qr(guest_id: str, event_id: int = EVENT_ID) -> str:
    """Fallback helper for security-negative cases where URL construction is explicit."""
    token = create_qr_token(event_id, guest_id)
    return (
        f"https://integration-test.invalid/checkin/{event_id}"
        f"?guest_id={guest_id}&token={token}"
    )


def provision_scanner(
    auth_service: ScannerStationAuthService,
    name: str,
) -> tuple[dict, str]:
    """Provision a real scanner station and keep its plaintext token in memory."""
    scanner, token = auth_service.provision_station(
        event_id=EVENT_ID,
        device_name=name,
        assigned_by=TEST_USER_ID,
    )

    assert scanner["event_id"] == EVENT_ID
    assert scanner["device_id"]
    assert scanner["is_active"] is True
    assert token.startswith("ELST_")

    # The persisted record returned by the repository must not contain the
    # plaintext access token.
    assert "access_token" not in scanner

    return scanner, token


def test_real_signed_qr_and_scanner_authenticate_and_check_in(seeded_database):
    auth_service = build_scanner_auth_service(seeded_database.engine)
    scanner, access_token = provision_scanner(
        auth_service,
        "Integration Scanner 01",
    )

    guest_id = SAME_GUEST_ID
    qr_value = production_qr(guest_id)

    result = build_checkin_service(seeded_database.engine).check_in(
        EVENT_ID,
        qr_value,
        scanner["device_id"],
        scanner_access_token=access_token,
    )

    assert result["result"] == "checked_in"
    assert result["event_id"] == EVENT_ID
    assert result["guest_id"] == guest_id
    assert result["receipt_token"]
    assert CheckinRepository(db=Database(db_engine=seeded_database.engine)).get_latest_for_guest(
        guest_id,
        EVENT_ID,
    )["result"] == "checked_in"


def test_invalid_scanner_credential_is_rejected_before_checkin(seeded_database):
    auth_service = build_scanner_auth_service(seeded_database.engine)
    scanner, _ = provision_scanner(
        auth_service,
        "Integration Scanner Invalid Credential",
    )

    with pytest.raises(
        ValidationError,
        match="Invalid, inactive, or incorrectly assigned scanner station",
    ):
        build_checkin_service(seeded_database.engine).check_in(
            EVENT_ID,
            production_qr(DIFFERENT_GUEST_PREFIX + "000"),
            scanner["device_id"],
            scanner_access_token="ELST_invalid_integration_credential",
        )


def test_scanner_identity_mismatch_is_rejected(seeded_database):
    auth_service = build_scanner_auth_service(seeded_database.engine)
    scanner, access_token = provision_scanner(
        auth_service,
        "Integration Scanner Identity",
    )

    with pytest.raises(
        ValidationError,
        match="Scanner station identity mismatch",
    ):
        build_checkin_service(seeded_database.engine).check_in(
            EVENT_ID,
            production_qr(DIFFERENT_GUEST_PREFIX + "001"),
            "EL-NOT-THE-AUTHENTICATED-SCANNER",
            scanner_access_token=access_token,
        )


def test_inactive_scanner_is_rejected(seeded_database):
    auth_service = build_scanner_auth_service(seeded_database.engine)
    scanner, access_token = provision_scanner(
        auth_service,
        "Integration Scanner Inactive",
    )

    ScannerRepository(db=Database(db_engine=seeded_database.engine)).set_active(
        EVENT_ID,
        scanner["device_id"],
        False,
    )

    with pytest.raises(
        ValidationError,
        match="Invalid, inactive, or incorrectly assigned scanner station",
    ):
        build_checkin_service(seeded_database.engine).check_in(
            EVENT_ID,
            production_qr(DIFFERENT_GUEST_PREFIX + "002"),
            scanner["device_id"],
            scanner_access_token=access_token,
        )


def test_cross_event_qr_is_rejected_before_scanner_authentication(seeded_database):
    auth_service = build_scanner_auth_service(seeded_database.engine)
    scanner, access_token = provision_scanner(
        auth_service,
        "Integration Scanner Cross Event",
    )

    foreign_qr = direct_signed_qr(
        DIFFERENT_GUEST_PREFIX + "003",
        event_id=EVENT_ID + 1,
    )

    with pytest.raises(
        ValidationError,
        match="QR code belongs to a different event",
    ):
        build_checkin_service(seeded_database.engine).check_in(
            EVENT_ID,
            foreign_qr,
            scanner["device_id"],
            scanner_access_token=access_token,
        )


def test_same_guest_concurrent_checkins_have_exactly_one_success(seeded_database):
    auth_service = build_scanner_auth_service(seeded_database.engine)
    scanners = [
        provision_scanner(auth_service, f"Concurrent Scanner {index}")
        for index in range(2)
    ]

    guest_id = SAME_GUEST_ID

    # Reset the deterministic guest because the first integration test may
    # have already checked it in.
    with seeded_database.engine.begin() as conn:
        conn.execute(
            update(guests)
            .where(
                guests.c.event_id == EVENT_ID,
                guests.c.guest_id == guest_id,
            )
            .values(status="Absent")
        )
        conn.execute(
            delete(checkin_history).where(
                checkin_history.c.event_id == EVENT_ID,
                checkin_history.c.guest_id == guest_id,
            )
        )
        conn.execute(
            delete(checkins).where(
                checkins.c.event_id == EVENT_ID,
                checkins.c.guest_id == guest_id,
            )
        )
        conn.execute(
            update(events)
            .where(events.c.id == EVENT_ID)
            .values(present_count=0)
        )

    qr_value = production_qr(guest_id)

    def worker(index: int) -> str:
        scanner, access_token = scanners[index % len(scanners)]
        try:
            build_checkin_service(seeded_database.engine).check_in(
                EVENT_ID,
                qr_value,
                scanner["device_id"],
                scanner_access_token=access_token,
            )
            return "checked_in"
        except GuestAlreadyCheckedInError:
            return "already_checked_in"

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        results = list(executor.map(worker, range(MAX_WORKERS)))

    assert results.count("checked_in") == 1
    assert results.count("already_checked_in") == MAX_WORKERS - 1

    with seeded_database.engine.connect() as conn:
        guest = conn.execute(
            select(guests.c.status).where(
                guests.c.event_id == EVENT_ID,
                guests.c.guest_id == guest_id,
            )
        ).scalar_one()

        present_count = conn.execute(
            select(events.c.present_count).where(
                events.c.id == EVENT_ID
            )
        ).scalar_one()

        history_count = conn.execute(
            select(checkins.c.id).where(
                checkins.c.event_id == EVENT_ID,
                checkins.c.guest_id == guest_id,
            )
        ).all()

    assert guest == "Present"
    assert present_count == 1
    assert len(history_count) == MAX_WORKERS


def test_100_different_guests_concurrently_all_update_event_counter(seeded_database):
    auth_service = build_scanner_auth_service(seeded_database.engine)
    scanners = [
        provision_scanner(auth_service, f"Load Scanner {index}")
        for index in range(3)
    ]

    guest_ids = [
        f"{DIFFERENT_GUEST_PREFIX}{index:03d}"
        for index in range(DIFFERENT_GUEST_COUNT)
    ]

    with seeded_database.engine.begin() as conn:
        conn.execute(
            update(events)
            .where(events.c.id == EVENT_ID)
            .values(present_count=0)
        )

        conn.execute(
            update(guests)
            .where(
                guests.c.event_id == EVENT_ID,
                guests.c.guest_id.in_(guest_ids),
            )
            .values(status="Absent")
        )

        conn.execute(
            delete(checkin_history).where(
                checkin_history.c.event_id == EVENT_ID,
                checkin_history.c.guest_id.in_(guest_ids),
            )
        )
        conn.execute(
            delete(checkins).where(
                checkins.c.event_id == EVENT_ID,
                checkins.c.guest_id.in_(guest_ids),
            )
        )

    def worker(index: int) -> str:
        guest_id = guest_ids[index]
        scanner, access_token = scanners[index % len(scanners)]

        try:
            result = build_checkin_service(seeded_database.engine).check_in(
                EVENT_ID,
                production_qr(guest_id),
                scanner["device_id"],
                scanner_access_token=access_token,
            )
            return result["result"]
        except GuestAlreadyCheckedInError:
            return "already_checked_in"
        except GuestNotFoundError:
            return "not_found"

    with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        futures = [
            executor.submit(worker, index)
            for index in range(DIFFERENT_GUEST_COUNT)
        ]
        results = [future.result() for future in as_completed(futures)]

    assert results.count("checked_in") == DIFFERENT_GUEST_COUNT
    assert results.count("already_checked_in") == 0
    assert results.count("not_found") == 0

    with seeded_database.engine.connect() as conn:
        present_count = conn.execute(
            select(events.c.present_count).where(
                events.c.id == EVENT_ID
            )
        ).scalar_one()

        guest_count = conn.execute(
            select(guests.c.id).where(
                guests.c.event_id == EVENT_ID,
                guests.c.guest_id.in_(guest_ids),
                guests.c.status == "Present",
            )
        ).all()

        successful_history = conn.execute(
            select(checkins.c.id).where(
                checkins.c.event_id == EVENT_ID,
                checkins.c.guest_id.in_(guest_ids),
                checkins.c.result == "checked_in",
            )
        ).all()

    assert present_count == DIFFERENT_GUEST_COUNT
    assert len(guest_count) == DIFFERENT_GUEST_COUNT
    assert len(successful_history) == DIFFERENT_GUEST_COUNT
