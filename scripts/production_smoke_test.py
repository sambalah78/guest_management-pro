"""
EventLah production database smoke test.

Read-only checks against the configured DATABASE_URL.
This script must never modify production data.
"""

import os
import sys

from dotenv import load_dotenv
from sqlalchemy import create_engine, inspect, text


REQUIRED_TABLES = {
    "users",
    "events",
    "guests",
    "scanner_devices",
    "stalls",
    "menu_items",
    "transactions",
    "checkins",
    "checkin_history",
    "email_jobs",
    "winners",
    "pre_draw_winners",
    "pre_draw_prizes",
    "event_assets",
}


def main() -> int:
    load_dotenv()

    database_url = os.getenv("DATABASE_URL", "").strip()

    if not database_url:
        print("FAIL: DATABASE_URL is not configured.")
        return 1

    if not database_url.startswith(("postgresql://", "postgres://")):
        print("FAIL: Production database must be PostgreSQL.")
        print(f"Configured scheme: {database_url.split(':', 1)[0]}")
        return 1

    print("EventLah Production Database Smoke Test")
    print("=" * 50)
    print("Database: PostgreSQL")
    print("Target: configured Supabase database")
    print("Mode: READ ONLY")
    print()

    engine = create_engine(
        database_url,
        future=True,
        pool_pre_ping=True,
    )

    try:
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            value = result.scalar_one()

            if value != 1:
                print("FAIL: Database connection test returned unexpected value.")
                return 1

            print("PASS: PostgreSQL connection successful.")

            database_name = conn.execute(
                text("SELECT current_database()")
            ).scalar_one()

            print(f"PASS: Database: {database_name}")

            server_version = conn.execute(
                text("SELECT version()")
            ).scalar_one()

            print(f"PASS: PostgreSQL server reachable.")
            print()

            inspector = inspect(conn)
            tables = set(inspector.get_table_names(schema="public"))

            missing_tables = REQUIRED_TABLES - tables

            if missing_tables:
                print("FAIL: Required EventLah tables are missing:")
                for table in sorted(missing_tables):
                    print(f"  - {table}")
                return 1

            print(
                f"PASS: All {len(REQUIRED_TABLES)} required EventLah tables exist."
            )

            users_columns = {
                column["name"]
                for column in inspector.get_columns("users", schema="public")
            }

            events_columns = {
                column["name"]
                for column in inspector.get_columns("events", schema="public")
            }

            guests_columns = {
                column["name"]
                for column in inspector.get_columns("guests", schema="public")
            }

            required_users_columns = {
                "id",
                "email",
                "name",
                "role",
                "is_active",
            }

            required_events_columns = {
                "id",
                "name",
                "event_type",
                "user_id",
                "guest_count",
                "present_count",
            }

            required_guests_columns = {
                "id",
                "event_id",
                "guest_id",
                "name",
                "email",
                "status",
                "table_number",
            }

            checks = [
                ("users", required_users_columns, users_columns),
                ("events", required_events_columns, events_columns),
                ("guests", required_guests_columns, guests_columns),
            ]

            for table_name, required, actual in checks:
                missing = required - actual

                if missing:
                    print(
                        f"FAIL: {table_name} is missing columns: "
                        f"{', '.join(sorted(missing))}"
                    )
                    return 1

                print(
                    f"PASS: {table_name} required columns present."
                )

            print()

            print("Production database smoke test PASSED.")
            print("No data was inserted, updated, or deleted.")

            return 0

    except Exception as exc:
        print()
        print("FAIL: Unable to complete production database smoke test.")
        print(f"Error: {exc}")
        return 1

    finally:
        engine.dispose()


if __name__ == "__main__":
    sys.exit(main())