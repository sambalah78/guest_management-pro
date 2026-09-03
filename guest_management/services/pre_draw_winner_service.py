"""Service layer for managing preliminary Lucky Draw winners."""

from __future__ import annotations

import logging
from typing import Any, Dict, List

from guest_management.repositories import (
    GuestRepository,
    PreDrawWinnerRepository,
)
from guest_management.services.excel_service import ExcelService

logger = logging.getLogger(__name__)


class PreDrawWinnerService:
    """Business logic for preliminary Lucky Draw winners."""

    def __init__(
        self,
        winner_repository: PreDrawWinnerRepository | None = None,
        guest_repository: GuestRepository | None = None,
        excel_service: ExcelService | None = None,
    ):
        self.winner_repository = (
            winner_repository or PreDrawWinnerRepository()
        )
        self.guest_repository = guest_repository or GuestRepository()
        self.excel_service = excel_service or ExcelService()

    # ------------------------------------------------------------------
    # Excel parsing
    # ------------------------------------------------------------------

    def parse_file(
        self,
        content: bytes,
    ) -> List[Dict[str, Any]]:
        """
        Parse and normalize a preliminary-winner Excel file.

        The Excel parser itself remains centralized in ExcelService.
        """
        if not content:
            raise ValueError("The uploaded file is empty.")

        winners = self.excel_service.parse_pre_draw_winners_file(content)

        if not winners:
            raise ValueError(
                "The uploaded file does not contain any preliminary winners."
            )

        return winners

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def validate_winners(
        self,
        event_id: int,
        winners: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Validate preliminary winners against the event's attending guests.

        Every preliminary winner must correspond to an existing guest in
        the same event. Duplicate guest IDs are rejected because one guest
        cannot appear more than once in the preliminary-winner list.
        """

        event_id = int(event_id)

        if not winners:
            raise ValueError("No preliminary winners were provided.")

        # --------------------------------------------------------------
        # Validate duplicate IDs inside the uploaded file first.
        # --------------------------------------------------------------

        seen_ids: set[str] = set()
        duplicate_ids: set[str] = set()

        for winner in winners:
            guest_id = str(
                winner.get("guest_id") or ""
            ).strip()

            if not guest_id:
                raise ValueError(
                    "Every preliminary winner must have a Guest ID."
                )

            normalized_id = guest_id.lower()

            if normalized_id in seen_ids:
                duplicate_ids.add(guest_id)
            else:
                seen_ids.add(normalized_id)

        if duplicate_ids:
            duplicate_text = ", ".join(sorted(duplicate_ids))
            raise ValueError(
                f"Duplicate Guest ID(s) found in preliminary winners: "
                f"{duplicate_text}"
            )

        # --------------------------------------------------------------
        # Load attending guests from the existing guest repository.
        # --------------------------------------------------------------

        guest_map: Dict[str, Dict[str, Any]] = {}

        page = 0
        page_size = 200

        while True:
            rows, total = self.guest_repository.get_by_event(
                event_id,
                limit=page_size,
                offset=page * page_size,
            )

            if not rows:
                break

            for guest in rows:
                guest_id = str(
                    guest.get("guest_id") or ""
                ).strip()

                if guest_id:
                    guest_map[guest_id.lower()] = guest

            if len(rows) < page_size:
                break

            if len(guest_map) >= int(total or 0):
                break

            page += 1

        if not guest_map:
            raise ValueError(
                "No attending guests have been uploaded for this event."
            )

        # --------------------------------------------------------------
        # Validate every preliminary winner against attending guests.
        # --------------------------------------------------------------

        missing_ids: List[str] = []
        normalized_winners: List[Dict[str, Any]] = []

        for winner in winners:
            guest_id = str(
                winner.get("guest_id") or ""
            ).strip()

            guest = guest_map.get(guest_id.lower())

            if not guest:
                missing_ids.append(guest_id)
                continue

            # Use the attendee's canonical name when available.
            # This prevents name mismatches between the two Excel files.
            attendee_name = str(
                guest.get("name") or ""
            ).strip()

            normalized_winner = {
                "guest_id": guest_id,
                "name": attendee_name
                or str(winner.get("name") or "").strip(),
                "prize_name": str(
                    winner.get("prize_name") or ""
                ).strip(),
                "prize_value": str(
                    winner.get("prize_value") or ""
                ).strip(),
                "image_url": str(
                    winner.get("image_url") or ""
                ).strip(),
            }

            if not normalized_winner["name"]:
                raise ValueError(
                    f"Guest {guest_id} does not have a valid name."
                )

            normalized_winners.append(normalized_winner)

        if missing_ids:
            missing_text = ", ".join(missing_ids)

            raise ValueError(
                "The following preliminary winner Guest ID(s) are not "
                f"present in the attending guest list: {missing_text}"
            )

        return normalized_winners

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def replace_for_event(
        self,
        event_id: int,
        winners: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """
        Validate and replace the complete preliminary-winner list.

        Existing preliminary winners are replaced only after the uploaded
        data has passed validation.
        """

        event_id = int(event_id)

        validated = self.validate_winners(
            event_id,
            winners,
        )

        return self.winner_repository.replace_for_event(
            event_id,
            validated,
        )

    # ------------------------------------------------------------------
    # Combined upload workflow
    # ------------------------------------------------------------------

    def import_file(
        self,
        event_id: int,
        content: bytes,
    ) -> List[Dict[str, Any]]:
        """
        Parse, validate and persist a preliminary-winner Excel file.
        """

        event_id = int(event_id)

        winners = self.parse_file(content)

        return self.replace_for_event(
            event_id,
            winners,
        )

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_by_event(
        self,
        event_id: int,
    ) -> List[Dict[str, Any]]:
        """Return preliminary winners for an event."""

        return self.winner_repository.get_by_event(
            int(event_id)
        )

    def get_guest_ids_by_event(
        self,
        event_id: int,
    ) -> List[str]:
        """Return Guest IDs that already won preliminary prizes."""

        return self.winner_repository.get_guest_ids_by_event(
            int(event_id)
        )

    def get_by_guest(
        self,
        event_id: int,
        guest_id: str,
    ) -> Dict[str, Any] | None:
        """Return a preliminary winner for a specific guest."""

        return self.winner_repository.get_by_guest(
            int(event_id),
            str(guest_id).strip(),
        )

    def delete_for_event(
        self,
        event_id: int,
    ) -> bool:
        """Remove all preliminary winners for an event."""

        return self.winner_repository.delete_by_event(
            int(event_id)
        )