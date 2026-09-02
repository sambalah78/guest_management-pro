from __future__ import annotations

import logging
from typing import Any

from guest_management.repositories.winner_repository import WinnerRepository

logger = logging.getLogger(__name__)


class WinnerService:
    """Business logic for Lucky Draw winner management."""

    def __init__(
        self,
        repository: WinnerRepository | None = None,
    ):
        self.repo = repository or WinnerRepository()

    # ------------------------------------------------------------------
    # HISTORY
    # ------------------------------------------------------------------

    def get_by_event(
        self,
        event_id: int,
    ) -> list[dict[str, Any]]:
        """Return winner history for an event."""

        winners = self.repo.get_by_event(
            int(event_id),
            limit=500,
        ) or []

        for winner in winners:
            created_at = winner.get("created_at")

            if created_at:
                winner["formatted_date"] = str(
                    created_at
                ).split("T")[0]

        return winners

    # ------------------------------------------------------------------
    # CREATE WINNER
    # ------------------------------------------------------------------

    def create(
        self,
        *,
        event_id: int,
        guest_id: str,
        name: str,
        prize_name: str,
        prize_value: str = "",
        prize_image: str = "",
    ) -> dict[str, Any]:
        """Create a winner safely.

        The application checks for an existing winner first.

        The database UNIQUE(event_id, guest_id) constraint remains
        the final authority and protects against concurrent draws.
        """

        event_id = int(event_id)
        guest_id = str(guest_id or "").strip()
        name = str(name or "").strip()
        prize_name = str(prize_name or "").strip()
        prize_value = str(prize_value or "").strip()
        prize_image = str(prize_image or "").strip()

        if not guest_id:
            raise ValueError(
                "Winner guest ID is required."
            )

        if not name:
            raise ValueError(
                "Winner name is required."
            )

        if not prize_name:
            raise ValueError(
                "Prize name is required."
            )

        # --------------------------------------------------------------
        # Application-level duplicate check
        # --------------------------------------------------------------

        if self.repo.has_won(
            event_id,
            guest_id,
        ):
            raise ValueError(
                f"Guest {guest_id} has already won this event."
            )

        # --------------------------------------------------------------
        # Database write
        # --------------------------------------------------------------

        try:
            result = self.repo.create(
                event_id=event_id,
                guest_id=guest_id,
                name=name,
                prize_name=prize_name,
                prize_value=prize_value,
                prize_image=prize_image,
            )

        except Exception as exc:
            # ----------------------------------------------------------
            # Race-condition protection
            #
            # Another Lucky Draw screen may have awarded the same guest
            # between our has_won() check and repo.create().
            #
            # Re-check the database before deciding this is a genuine
            # failure.
            # ----------------------------------------------------------

            if self.repo.has_won(
                event_id,
                guest_id,
            ):
                raise ValueError(
                    f"Guest {guest_id} has already won this event."
                ) from exc

            logger.exception(
                "Failed to create winner "
                "event=%s guest=%s",
                event_id,
                guest_id,
            )

            raise

        # Some repository implementations return None rather than
        # raising when an INSERT fails.
        if not result:
            if self.repo.has_won(
                event_id,
                guest_id,
            ):
                raise ValueError(
                    f"Guest {guest_id} has already won this event."
                )

            raise RuntimeError(
                "Unable to save winner."
            )


        return result

    # ------------------------------------------------------------------
    # LOOKUP
    # ------------------------------------------------------------------

    def has_won(
        self,
        event_id: int,
        guest_id: str,
    ) -> bool:
        """Check whether a guest has already won."""

        return self.repo.has_won(
            int(event_id),
            str(guest_id).strip(),
        )

    def get_by_guest(
        self,
        event_id: int,
        guest_id: str,
    ) -> dict[str, Any] | None:
        """Return a guest's winner record, if any."""

        return self.repo.get_by_guest(
            int(event_id),
            str(guest_id).strip(),
        )

    # ------------------------------------------------------------------
    # STATISTICS
    # ------------------------------------------------------------------

    def count_by_event(
        self,
        event_id: int,
    ) -> int:
        """Return winner count for an event."""

        return self.repo.count_by_event(
            int(event_id)
        )

    # ------------------------------------------------------------------
    # DELETE
    # ------------------------------------------------------------------

    def delete_by_event(
        self,
        event_id: int,
    ) -> int:
        """Delete all winners for an event."""

        return self.repo.delete_by_event(
            int(event_id)
        )
