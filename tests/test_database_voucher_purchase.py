"""Database boundary tests for voucher purchases."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, select

from guest_management.database import (
    Database,
    events,
    guests,
    menu_items,
    metadata,
    stalls,
    transactions,
    users,
)


@pytest.fixture()
def database():
    """Create an isolated in-memory SQLite database for each test."""

    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
    )

    metadata.create_all(
        engine,
        tables=[
            users,
            events,
            guests,
            stalls,
            menu_items,
            transactions,
        ],
    )

    database = Database(db_engine=engine)

    try:
        yield database
    finally:
        metadata.drop_all(
            engine,
            tables=[
                transactions,
                menu_items,
                stalls,
                guests,
                events,
                users,
            ],
        )
        engine.dispose()


def seed_voucher_data(database: Database) -> None:
    """Seed two isolated events with guests, stalls, and menu items."""

    with database.engine.begin() as conn:
        conn.execute(
            users.insert().values(
                id="00000000-0000-0000-0000-000000000001",
                email="voucher-test@example.com",
                name="Voucher Test User",
                picture_url="",
                role="ADMIN",
                is_active=True,
            )
        )

        conn.execute(
            events.insert(),
            [
                {
                    "id": 1,
                    "name": "Event One",
                    "event_type": "company_dinner",
                    "company_name": "Company One",
                    "date": "2026-09-19",
                    "time": "18:00",
                    "venue": "Venue One",
                    "theme": "",
                    "guest_count": 1,
                    "present_count": 1,
                    "user_id": "00000000-0000-0000-0000-000000000001",
                    "logo": "",
                    "wedding_invitation": "",
                    "logo_storage_path": "",
                    "logo_filename": "",
                    "logo_mime_type": "",
                    "invitation_storage_path": "",
                    "invitation_filename": "",
                    "invitation_mime_type": "",
                    "guest_list_storage_path": "",
                    "guest_list_filename": "",
                    "guest_list_mime_type": "",
                },
                {
                    "id": 2,
                    "name": "Event Two",
                    "event_type": "company_dinner",
                    "company_name": "Company Two",
                    "date": "2026-09-20",
                    "time": "18:00",
                    "venue": "Venue Two",
                    "theme": "",
                    "guest_count": 1,
                    "present_count": 1,
                    "user_id": "00000000-0000-0000-0000-000000000001",
                    "logo": "",
                    "wedding_invitation": "",
                    "logo_storage_path": "",
                    "logo_filename": "",
                    "logo_mime_type": "",
                    "invitation_storage_path": "",
                    "invitation_filename": "",
                    "invitation_mime_type": "",
                    "guest_list_storage_path": "",
                    "guest_list_filename": "",
                    "guest_list_mime_type": "",
                },
            ],
        )

        conn.execute(
            guests.insert(),
            [
                {
                    "id": 1,
                    "event_id": 1,
                    "guest_id": "G001",
                    "name": "Guest One",
                    "email": "guest1@example.com",
                    "phone": "",
                    "status": "Present",
                    "table_number": "1",
                    "amount": 100,
                    "email_sent": False,
                    "full_data": {},
                },
                {
                    "id": 2,
                    "event_id": 2,
                    "guest_id": "G001",
                    "name": "Guest One Event Two",
                    "email": "guest2@example.com",
                    "phone": "",
                    "status": "Present",
                    "table_number": "2",
                    "amount": 100,
                    "email_sent": False,
                    "full_data": {},
                },
            ],
        )

        conn.execute(
            stalls.insert(),
            [
                {
                    "id": 10,
                    "event_id": 1,
                    "stall_name": "Event One Stall",
                    "description": "",
                    "qr_code": "",
                },
                {
                    "id": 20,
                    "event_id": 2,
                    "stall_name": "Event Two Stall",
                    "description": "",
                    "qr_code": "",
                },
            ],
        )

        conn.execute(
            menu_items.insert(),
            [
                {
                    "id": 100,
                    "stall_id": 10,
                    "item_name": "Event One Item",
                    "description": "",
                    "price": 25,
                    "image_url": "",
                },
                {
                    "id": 200,
                    "stall_id": 20,
                    "item_name": "Event Two Item",
                    "description": "",
                    "price": 25,
                    "image_url": "",
                },
            ],
        )


def get_guest(database: Database, event_id: int, guest_id: str):
    with database.engine.connect() as conn:
        return conn.execute(
            select(guests).where(
                guests.c.event_id == event_id,
                guests.c.guest_id == guest_id,
            )
        ).mappings().first()


def get_transactions(database: Database):
    with database.engine.connect() as conn:
        return conn.execute(
            select(transactions).order_by(transactions.c.id)
        ).mappings().all()


def get_rpc_result(result):
    assert result.data, "Database RPC returned no data"
    row = result.data[0]
    assert isinstance(row, dict)
    return row


def test_purchase_rejects_cross_event_stall(database):
    """
    A guest from Event 1 must not be able to purchase from
    a stall belonging to Event 2.
    """

    seed_voucher_data(database)

    result = get_rpc_result(
        database.process_voucher_purchase(
            {
                "p_event_id": 1,
                "p_guest_id": "G001",
                "p_stall_id": 20,
                "p_items": [
                    {
                        "id": 200,
                        "quantity": 1,
                    }
                ],
            }
        )
    )

    assert result["result"] == "invalid"
    assert result["message"] == "Invalid stall"

    guest = get_guest(database, 1, "G001")
    assert guest is not None
    assert float(guest["amount"]) == 100.0

    assert get_transactions(database) == []


def test_successful_purchase_updates_balance_and_creates_transaction(database):
    """A valid guest/stall/menu-item combination still completes normally."""

    seed_voucher_data(database)

    result = get_rpc_result(
        database.process_voucher_purchase(
            {
                "p_event_id": 1,
                "p_guest_id": "G001",
                "p_stall_id": 10,
                "p_items": [
                    {
                        "id": 100,
                        "quantity": 2,
                    }
                ],
            }
        )
    )

    assert result["result"] == "success"
    assert result["message"] == "Purchase completed"
    assert result["total"] == 50.0
    assert result["balance_after"] == 50.0

    guest = get_guest(database, 1, "G001")
    assert guest is not None
    assert float(guest["amount"]) == 50.0

    records = get_transactions(database)
    assert len(records) == 1
    assert records[0]["event_id"] == 1
    assert records[0]["guest_id"] == "G001"
    assert records[0]["stall_id"] == 10
    assert records[0]["menu_item_id"] == 100
    assert records[0]["quantity"] == 2
    assert float(records[0]["amount"]) == 50.0
