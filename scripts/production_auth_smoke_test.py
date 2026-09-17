"""
EventLah production authentication/authorization smoke test.

Read-only verification of the EventLah authorization profiles.
Does not perform login and does not modify Supabase.
"""

import os
import sys
import uuid

from dotenv import load_dotenv
from supabase import create_client


EXPECTED_ADMINS = {
    "eventlahsolutions@gmail.com": "OWNER",
    "sambalah.kenny@gmail.com": "ADMIN",
}


def main() -> int:
    load_dotenv()

    supabase_url = os.getenv("SUPABASE_URL", "").strip()
    service_role_key = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "").strip()

    if not supabase_url:
        print("FAIL: SUPABASE_URL is not configured.")
        return 1

    if not service_role_key:
        print("FAIL: SUPABASE_SERVICE_ROLE_KEY is not configured.")
        return 1

    try:
        client = create_client(
            supabase_url,
            service_role_key,
        )

        response = (
            client.table("users")
            .select("id,email,name,role,is_active")
            .in_("email", list(EXPECTED_ADMINS.keys()))
            .execute()
        )

        rows = response.data or []

        print("EventLah Production Authentication Smoke Test")
        print("=" * 55)
        print("Target: Supabase public.users")
        print("Mode: READ ONLY")
        print()

        found = {
            str(row.get("email", "")).strip().lower(): row
            for row in rows
        }

        for email, expected_role in EXPECTED_ADMINS.items():
            row = found.get(email)

            if not row:
                print(f"FAIL: Admin profile not found: {email}")
                return 1

            user_id = str(row.get("id", "")).strip()

            try:
                uuid.UUID(user_id)
            except ValueError:
                print(f"FAIL: Invalid UUID for {email}")
                return 1

            actual_role = str(row.get("role", "")).strip().upper()
            is_active = bool(row.get("is_active"))

            if actual_role != expected_role:
                print(
                    f"FAIL: {email} has role {actual_role!r}; "
                    f"expected {expected_role!r}."
                )
                return 1

            if not is_active:
                print(f"FAIL: {email} is inactive.")
                return 1

            print(
                f"PASS: {email} → {actual_role} → ACTIVE"
            )

        print()
        print("PASS: Both production administrator profiles are valid.")
        print("PASS: Authorization is role-based.")
        print("No data was inserted, updated, or deleted.")

        return 0

    except Exception as exc:
        print()
        print("FAIL: Authentication smoke test failed.")
        print(f"Error: {exc}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
