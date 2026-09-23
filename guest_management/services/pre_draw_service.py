"""Business service for event-level random Pre-Draw generation."""

from __future__ import annotations

from secrets import SystemRandom
from typing import Any, Dict, List

from guest_management.repositories.event_repository import EventRepository
from guest_management.services.event_service import EventService
from guest_management.repositories.guest_repository import GuestRepository
from guest_management.repositories.pre_draw_prize_repository import (
    PreDrawPrizeRepository,
)
from guest_management.repositories.pre_draw_winner_repository import (
    PreDrawWinnerRepository,
)
from guest_management.utils.constants import EVENT_TYPES


class PreDrawService:
    """
    Generate and persist preliminary winners before the live event.

    Pre-Draw eligibility is based on the uploaded event guest/participant list.
    Live check-in status is intentionally not used.
    """

    PAGE_SIZE = 200

    def __init__(
        self,
        *,
        event_repository: EventRepository | None = None,
        guest_repository: GuestRepository | None = None,
        prize_repository: PreDrawPrizeRepository | None = None,
        winner_repository: PreDrawWinnerRepository | None = None,
        rng: Any | None = None,
    ):
        self.event_repository = (
            event_repository or EventRepository()
        )
        self.guest_repository = (
            guest_repository or GuestRepository()
        )
        self.prize_repository = (
            prize_repository or PreDrawPrizeRepository()
        )
        self.winner_repository = (
            winner_repository or PreDrawWinnerRepository()
        )
        self.rng = rng or SystemRandom()

    def _load_event(
        self,
        event_id: int,
        user_id: str,
        user: Dict[str, Any] | None = None,
    ) -> Dict[str, Any]:
        event_id = int(event_id)
        user_id = str(user_id or "").strip()

        if event_id <= 0:
            raise ValueError(
                "event_id must be greater than zero."
            )

        if not user_id:
            raise ValueError(
                "user_id is required."
            )

        event = EventService(
            repository=self.event_repository,
        ).get_event(
            event_id,
            user_id,
            user,
        )

        if not event:
            raise ValueError(
                f"Event {event_id} was not found."
            )

        return event

    def _validate_event_type(
        self,
        event: Dict[str, Any],
    ) -> None:
        event_type = str(
            event.get("event_type")
            or "company_dinner"
        ).strip().lower()

        config = EVENT_TYPES.get(event_type)

        if not config:
            raise ValueError(
                f"Unsupported event type: {event_type}"
            )

        if not config["features"].get("pre_draw", False):
            raise ValueError(
                f"Pre-Draw is not enabled for {config['name']} events."
            )

    def _load_participants(
        self,
        event_id: int,
    ) -> List[Dict[str, Any]]:
        participants: Dict[str, Dict[str, Any]] = {}

        page = 0

        while True:
            rows, total = self.guest_repository.get_by_event(
                event_id,
                limit=self.PAGE_SIZE,
                offset=page * self.PAGE_SIZE,
            )

            if not rows:
                break

            for guest in rows:
                guest_id = str(
                    guest.get("guest_id") or ""
                ).strip()

                if not guest_id:
                    continue

                normalized_id = guest_id.lower()

                if normalized_id in participants:
                    raise ValueError(
                        "Duplicate Guest IDs detected in the event "
                        f"participant list: {guest_id}"
                    )

                name = str(
                    guest.get("name") or ""
                ).strip()

                if not name:
                    raise ValueError(
                        f"Guest {guest_id} does not have a valid name."
                    )

                participants[normalized_id] = {
                    "guest_id": guest_id,
                    "name": name,
                }

            if len(rows) < self.PAGE_SIZE:
                break

            if len(participants) >= int(total or 0):
                break

            page += 1

        if not participants:
            raise ValueError(
                "No guests/participants have been uploaded for this event."
            )

        return list(participants.values())

    def _load_prizes(
        self,
        event_id: int,
    ) -> List[Dict[str, Any]]:
        prizes = self.prize_repository.get_by_event(
            event_id,
            include_archived=False,
            limit=500,
        )

        if not prizes:
            raise ValueError(
                "No active pre-draw prizes are configured."
            )

        normalized: List[Dict[str, Any]] = []

        for prize in prizes:
            status = str(
                prize.get("status") or "draft"
            ).strip().lower()

            if status == "generated":
                raise ValueError(
                    "Pre-draw winners have already been generated "
                    "for this prize configuration."
                )

            if status not in {"draft", "ready"}:
                raise ValueError(
                    f"Invalid active pre-draw prize status: {status}"
                )

            try:
                winner_count = int(
                    prize.get("winner_count", 1)
                )
            except (TypeError, ValueError) as exc:
                raise ValueError(
                    "Pre-draw winner count must be a positive integer."
                ) from exc

            if winner_count <= 0:
                raise ValueError(
                    "Pre-draw winner count must be greater than zero."
                )

            name = str(
                prize.get("name") or ""
            ).strip()

            if not name:
                raise ValueError(
                    "Every pre-draw prize must have a name."
                )

            normalized.append(
                {
                    "id": int(prize["id"]),
                    "name": name,
                    "value": str(
                        prize.get("value") or ""
                    ).strip(),
                    "image_url": str(
                        prize.get("image_url") or ""
                    ).strip(),
                    "winner_count": winner_count,
                    "sort_order": int(
                        prize.get("sort_order", 0)
                    ),
                }
            )

        normalized.sort(
            key=lambda prize: (
                prize["sort_order"],
                prize["id"],
            )
        )

        return normalized

    def _build_random_winners(
        self,
        participants: List[Dict[str, Any]],
        prizes: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        total_requested = sum(
            int(prize["winner_count"])
            for prize in prizes
        )

        if total_requested > len(participants):
            raise ValueError(
                "The configured number of Pre-Draw winners "
                f"({total_requested}) exceeds the available "
                f"participant count ({len(participants)})."
            )

        remaining = list(participants)
        winners: List[Dict[str, Any]] = []

        for prize in prizes:
            count = int(prize["winner_count"])

            selected = self.rng.sample(
                remaining,
                count,
            )

            selected_ids = {
                str(guest["guest_id"]).strip().lower()
                for guest in selected
            }

            for guest in selected:
                winners.append(
                    {
                        "prize_id": int(prize["id"]),
                        "guest_id": str(
                            guest["guest_id"]
                        ).strip(),
                        "name": str(
                            guest["name"]
                        ).strip(),
                        "prize_name": prize["name"],
                        "prize_value": prize["value"],
                        "image_url": prize["image_url"],
                    }
                )

            remaining = [
                guest
                for guest in remaining
                if str(
                    guest["guest_id"]
                ).strip().lower()
                not in selected_ids
            ]

        if len(winners) != total_requested:
            raise RuntimeError(
                "Random Pre-Draw generation produced an unexpected "
                "number of winners."
            )

        return winners

    def generate_random_winners(
        self,
        event_id: int,
        user_id: str,
        user: Dict[str, Any] | None = None,
    ) -> List[Dict[str, Any]]:
        event = self._load_event(
            event_id,
            user_id,
            user,
        )
        self._validate_event_type(event)

        participants = self._load_participants(
            int(event_id)
        )

        prizes = self._load_prizes(
            int(event_id)
        )

        winners = self._build_random_winners(
            participants,
            prizes,
        )

        return self.winner_repository.finalize_random_generation(
            int(event_id),
            winners,
            [int(prize["id"]) for prize in prizes],
        )
