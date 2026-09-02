"""Check-in repository.

All check-in persistence is isolated here.

The actual check-in operation is performed through the PostgreSQL/DB RPC
``check_in_guest`` so concurrent scanners share one source of truth.

This repository is intentionally responsible only for check-in records and
the atomic check-in operation. Guest lookup remains in GuestRepository.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from .base import BaseRepository
from guest_management.core.exceptions import (
    DatabaseError,
    GuestAlreadyCheckedInError,
)


CHECKIN_COLUMNS = (
    "id,"
    "event_id,"
    "guest_id,"
    "scanner_id,"
    "result,"
    "checked_in_at,"
    "created_at"
)


class CheckinRepository(BaseRepository):
    """Repository for guest check-in operations and history."""

    # ==================================================================
    # ATOMIC CHECK-IN
    # ==================================================================

    def check_in(
        self,
        event_id: int,
        guest_id: str,
        scanner_id: str = "",
    ) -> Dict[str, Any]:
        """Perform an atomic guest check-in through the database RPC.

        The RPC is the source of truth for concurrent scanners.

        Args:
            event_id: Event the guest belongs to.
            guest_id: Guest identifier.
            scanner_id: Optional scanner/device identifier.

        Returns:
            RPC result dictionary.

        Raises:
            GuestAlreadyCheckedInError:
                When the guest has already checked in.
            DatabaseError:
                When the RPC fails or returns an invalid result.
        """

        if not event_id:
            raise ValueError("event_id is required")

        guest_id = str(guest_id or "").strip()

        if not guest_id:
            raise ValueError("guest_id is required")

        scanner_id = str(scanner_id or "").strip()

        try:
            response = self.db.rpc(
                "check_in_guest",
                {
                    "p_event_id": int(event_id),
                    "p_guest_id": guest_id,
                    "p_scanner_id": scanner_id or None,
                },
            ).execute()

            rows = response.data or []

            if not rows:
                raise DatabaseError(
                    "Check-in RPC returned no result"
                )

            if isinstance(rows, list):
                result = rows[0]
            else:
                result = rows

            if not isinstance(result, dict):
                raise DatabaseError(
                    "Check-in RPC returned an invalid result"
                )

            result_type = result.get("result")

            if result_type == "already_checked_in":
                raise GuestAlreadyCheckedInError(
                    result.get(
                        "message",
                        "Guest already checked in",
                    )
                )

            if result_type not in {
                "checked_in",
                "not_found",
            }:
                raise DatabaseError(
                    result.get(
                        "message",
                        "Check-in failed",
                    )
                )

            return result

        except GuestAlreadyCheckedInError:
            raise

        except DatabaseError:
            raise

        except Exception as exc:
            self._raise_db(
                "atomic guest check-in",
                exc,
            )

    # ==================================================================
    # READ CHECK-IN HISTORY
    # ==================================================================

    def get_by_event(
        self,
        event_id: int,
        limit: int = 500,
    ) -> List[Dict[str, Any]]:
        """Return check-in history for an event, newest first."""

        if not event_id:
            raise ValueError("event_id is required")

        if limit < 1 or limit > 1000:
            raise ValueError(
                "limit must be between 1 and 1000"
            )

        try:
            response = (
                self.db
                .table("checkins")
                .select(CHECKIN_COLUMNS)
                .eq("event_id", int(event_id))
                .order("checked_in_at", desc=True)
                .limit(int(limit))
                .execute()
            )

            return response.data or []

        except Exception as exc:
            self._raise_db(
                "list check-in history",
                exc,
            )

    def get_recent(
        self,
        event_id: int,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Return the most recent check-ins for an event."""

        if not event_id:
            raise ValueError("event_id is required")

        if limit < 1 or limit > 100:
            raise ValueError(
                "limit must be between 1 and 100"
            )

        try:
            response = (
                self.db
                .table("checkins")
                .select(CHECKIN_COLUMNS)
                .eq("event_id", int(event_id))
                .eq("result", "checked_in")
                .order("checked_in_at", desc=True)
                .limit(int(limit))
                .execute()
            )

            return response.data or []

        except Exception as exc:
            self._raise_db(
                "recent check-ins",
                exc,
            )

    # ==================================================================
    # COUNT
    # ==================================================================

    def count_by_event(
        self,
        event_id: int,
    ) -> int:
        """Return the number of check-in records for an event."""

        if not event_id:
            raise ValueError("event_id is required")

        try:
            response = (
                self.db
                .table("checkins")
                .select(
                    "id",
                    count="exact",
                    head=True,
                )
                .eq("event_id", int(event_id))
                .execute()
            )

            return int(response.count or 0)

        except Exception as exc:
            self._raise_db(
                "count check-ins",
                exc,
            )

    def count_successful(
        self,
        event_id: int,
    ) -> int:
        """Return successful check-ins for an event."""

        if not event_id:
            raise ValueError("event_id is required")

        try:
            response = (
                self.db
                .table("checkins")
                .select(
                    "id",
                    count="exact",
                    head=True,
                )
                .eq("event_id", int(event_id))
                .eq("result", "checked_in")
                .execute()
            )

            return int(response.count or 0)

        except Exception as exc:
            self._raise_db(
                "count successful check-ins",
                exc,
            )

    # ==================================================================
    # GUEST CHECK-IN HISTORY
    # ==================================================================

    def get_by_guest_id(
        self,
        guest_id: str,
        event_id: int,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Return check-in history for one guest within an event."""

        guest_id = str(guest_id or "").strip()

        if not guest_id:
            raise ValueError("guest_id is required")

        if not event_id:
            raise ValueError("event_id is required")

        if limit < 1 or limit > 500:
            raise ValueError(
                "limit must be between 1 and 500"
            )

        try:
            response = (
                self.db
                .table("checkins")
                .select(CHECKIN_COLUMNS)
                .eq("event_id", int(event_id))
                .eq("guest_id", guest_id)
                .order("checked_in_at", desc=True)
                .limit(int(limit))
                .execute()
            )

            return response.data or []

        except Exception as exc:
            self._raise_db(
                "guest check-in history",
                exc,
            )

    def get_latest_for_guest(
        self,
        guest_id: str,
        event_id: int,
    ) -> Optional[Dict[str, Any]]:
        """Return the latest check-in record for a guest."""

        rows = self.get_by_guest_id(
            guest_id=guest_id,
            event_id=event_id,
            limit=1,
        )

        return rows[0] if rows else None