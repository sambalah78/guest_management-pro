# guest_management/state/lucky_draw_state.py
"""Lucky draw state."""

import reflex as rx
from typing import List, Dict, Any, Optional
from datetime import datetime
import random
import json
import base64
import asyncio

import logging
from ..services.winner_service import WinnerService
from ..services.pre_draw_winner_service import PreDrawWinnerService
from ..state.guest_state import GuestState
from ..utils.constants import EVENT_TYPES
from ..state.auth_state import AuthState
from ..repositories import EventRepository, GuestRepository
from ..services.excel_service import ExcelService
from guest_management.services.event_service import EventService
from guest_management.core.exceptions import (
    AuthorizationError,
    EventNotFoundError,
)



logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Draw lifecycle constants
# ---------------------------------------------------------------------------
DRAW_IDLE = "IDLE"
READY = "READY"
DRAWING = "DRAWING"
CANDIDATE = "CANDIDATE"
CONFIRMED = "CONFIRMED"
REDRAW = "REDRAW"
NEXT_PRIZE = "NEXT_PRIZE"
DONE = "DONE"


class LuckyDrawState(rx.State):
    """Lucky draw management state."""
    # Production draw lifecycle
    # IDLE -> DRAWING -> CANDIDATE -> CONFIRMED/REDRAW -> NEXT_PRIZE/DONE
    # ========================================================================
    # PRODUCTION DRAW LIFECYCLE
    # ========================================================================

    # SETUP
    #   ↓
    # READY
    #   ↓
    # DRAWING
    #   ↓
    # CANDIDATE
    #   ├── ABSENT → REDRAW SAME PRIZE
    #   └── PRESENT → CONFIRM WINNER
    #                         ↓
    #                    NEXT PRIZE
    #                         ↓
    #                       DONE

    draw_status: str = "IDLE"

    # Candidate currently displayed on the live draw screen.
    # This is NOT an official winner until confirmed.
    pending_candidate: Dict[str, Any] = {}

    # Number of redraws during the entire draw session.
    redraw_count: int = 0

    # Number of redraws for the current prize.
    current_prize_redraw_count: int = 0

    # Guests explicitly rejected because they were absent.
    # They must not be selected again during this draw session.
    excluded_guest_ids: List[str] = []

    # Prevents overlapping draw/confirm/redraw operations.
    draw_locked: bool = False

    # Optional session identifier for future audit/event logging.
    draw_session_id: str = ""
    candidate_rejected: bool = False
    draw_attempt: int = 0

    # Setup
    lucky_draw_ready: bool = False
    lucky_draw_event_name: str = ""
    current_event_id: str = ""
    current_event: Optional[Dict[str, Any]] = None
    lucky_draw_event_type: str = ""
    # Wheel animation
    wheel_rotation: int = 0
    wheel_names: List[str] = []
    # Guests
    lucky_draw_only_present: bool = True
    lucky_draw_excluded: str = ""
    lucky_draw_eligible_guests: List[Dict[str, Any]] = []
    # -----------------------------------------------------------------------
    # Pre-draw winners
    # -----------------------------------------------------------------------
    # These are winners selected before the live event.
    # They are intentionally separate from winners_list.
    pre_draw_winners: List[Dict[str, Any]] = []

    # By default, a preliminary winner cannot win again in the live draw.
    include_pre_draw_winners: bool = False

    # Temporary upload buffer. The file is persisted immediately after
    # validation and is not used as the source of truth.
    pre_draw_winner_selected_file_name: str = ""
    pre_draw_upload_dialog_open: bool = False
    pre_draw_winner_filename: str = ""
    _pre_draw_winner_file_content: bytes = b""
    _pre_draw_winner_filename: str = ""
    pre_draw_display_participants: List[Dict[str, Any]] = []
    # Draw state
    lucky_draw_spinning: bool = False
    lucky_draw_current_name: str = ""
    lucky_draw_current_id: str = ""
    lucky_draw_winner: Dict[str, Any] = {}

    # Winners
    winners_list: List[Dict[str, Any]] = []
    drawn_winners: List[Dict[str, Any]] = []

    # Prize system
    prize_mode: str = "multiple"
    current_prizes: List[Dict[str, Any]] = []
    current_prize_index: int = 0

    lucky_draw_prize_name: str = ""
    lucky_draw_prize_value: str = ""
    lucky_draw_prize_picture: str = ""

    # UI states
    draw_finished: bool = False
    prize_list: List[Dict[str, Any]] = []

    # Pre-draw presentation configuration.
    # "same" means one browser presentation can be duplicated by an AV splitter.
    # "different" means each physical display needs its own display client/feed;
    # a normal AV splitter cannot produce independent slides.
    predraw_display_mode: str = "same"
    predraw_screen_count: int = 1
    prize_excel_filename: str = ""
    lucky_draw_spinner_open: bool = False
    lucky_draw_show_new_draw_dialog: bool = False
    show_clear_confirm: bool = False

    predraw_page: int = 0
    predraw_page_size: int = 26
    predraw_rotation_interval_ms: int = 8000
    predraw_rotation_seconds: int = 8
    # Prize file
    prize_selected_file_name: str = ""
    _prize_file_content: bytes = b""
    _prize_filename: str = ""
    lucky_draw_window_opened: bool = False
    prize_transitioning: bool = False
    waiting_for_next_prize: bool = False
    lucky_draw_setup_complete: bool = False

    # Redraw state
    lucky_draw_redraw_count: int = 0
    lucky_draw_redraw_guest_id: str = ""
    lucky_draw_redraw_guest_name: str = ""

    def prepare_wheel_names(self):
        """Prepare up to 24 names for the display wheel."""
        names = [
            str(g.get("name") or "").strip()
            for g in self.lucky_draw_eligible_guests
            if str(g.get("name") or "").strip()
        ]

        self.wheel_names = names[:24]

    def spin_wheel_visual(self):
        """Advance the visual wheel rotation."""
        self.wheel_rotation = (self.wheel_rotation + 18) % 360

    def set_predraw_page_size(self, page_size: str):
        """Change pre-draw display page size and reset pagination to page 1."""
        try:
            size = int(page_size)
        except (TypeError, ValueError):
            return

        if size not in (10, 25, 50, 100):
            return

        self.predraw_page_size = size
        self.predraw_page = 0

    def open_pre_draw_upload_dialog(self):
        """Open the pre-draw winner upload dialog."""
        self.pre_draw_upload_dialog_open = True

    def close_pre_draw_upload_dialog(self):
        """Close the pre-draw winner upload dialog."""
        self.pre_draw_upload_dialog_open = False

    def set_pre_draw_upload_dialog_open(self, value: bool):
        """Synchronize the pre-draw upload dialog open state."""
        self.pre_draw_upload_dialog_open = bool(value)

    def advance_predraw_page(self):
        """
        Backward-compatible alias for advancing the public pre-draw display.
        """
        self.predraw_next_page()

    async def predraw_auto_rotate(self):
        """Advance the public pre-draw display by one page."""
        self.predraw_next_page()
        yield

    def clear_pre_draw_winner_file(self):
        """Clear the staged preliminary-winner upload."""
        self.pre_draw_winner_selected_file_name = ""
        self._pre_draw_winner_file_content = b""
        self._pre_draw_winner_filename = ""

        return rx.toast.info(
            "Pre-draw winner file selection cleared."
        )

    def _set_current_prize(self):
        """Synchronize UI prize fields with the current prize."""

        if not self.current_prizes:
            self.lucky_draw_prize_name = ""
            self.lucky_draw_prize_value = ""
            self.lucky_draw_prize_picture = ""
            return False

        if not (
                0 <= self.current_prize_index < len(self.current_prizes)
        ):
            return False

        prize = self.current_prizes[self.current_prize_index]

        self.lucky_draw_prize_name = str(
            prize.get("name", "")
        )

        self.lucky_draw_prize_value = str(
            prize.get("value", "")
        )

        self.lucky_draw_prize_picture = str(
            prize.get("image_url", "")
        )

        return True

    def _guest_id(self, guest: Dict[str, Any]) -> str:
        """Return a normalized guest ID."""
        return str(
            guest.get("guest_id")
            or guest.get("id")
            or ""
        ).strip()

    def _available_draw_candidates(self) -> List[Dict[str, Any]]:
        """
        Return guests available for the current draw.

        A guest is unavailable if:
        - they were marked as absent,
        - they are the current pending candidate,
        - they have already won a prize.
        """

        excluded_ids = {
            str(guest_id).strip()
            for guest_id in self.excluded_guest_ids
            if str(guest_id).strip()
        }

        pending_id = self._guest_id(
            self.pending_candidate
        )

        winner_ids = {
            str(winner.get("guest_id") or "").strip()
            for winner in self.winners_list
            if str(winner.get("guest_id") or "").strip()
        }

        candidates: List[Dict[str, Any]] = []

        for guest in self.lucky_draw_eligible_guests:
            guest_id = self._guest_id(guest)

            if not guest_id:
                continue

            # Already marked absent.
            if guest_id in excluded_ids:
                continue

            # Currently pending candidate.
            if pending_id and guest_id == pending_id:
                continue

            # Already won a previous prize.
            if guest_id in winner_ids:
                continue

            candidates.append(dict(guest))

        return candidates

    def _candidate_is_valid(
            self,
            candidate: Dict[str, Any],
    ) -> bool:
        """Validate a candidate immediately before confirmation."""
        if not candidate:
            return False

        guest_id = self._guest_id(candidate)

        if not guest_id:
            return False

        if guest_id in {
            str(value).strip()
            for value in self.excluded_guest_ids
        }:
            return False

        winner_ids = {
            str(winner.get("guest_id") or "").strip()
            for winner in self.winners_list
        }

        if guest_id in winner_ids:
            return False

        return any(
            self._guest_id(guest) == guest_id
            for guest in self.lucky_draw_eligible_guests
        )

    def _set_candidate(self, candidate: Dict[str, Any]) -> None:
        """Set the currently selected candidate without confirming them."""
        candidate = dict(candidate or {})

        self.pending_candidate = candidate
        self.lucky_draw_winner = {}
        self.lucky_draw_current_name = str(
            candidate.get("name") or "Guest"
        )
        self.lucky_draw_current_id = str(
            candidate.get("guest_id") or ""
        )

        self.draw_status = "CANDIDATE"
        self.draw_locked = False

    async def confirm_candidate_winner(self):
        """
        Confirm the current candidate and persist the winner.
        """
        if self.draw_status != "CANDIDATE":
            yield rx.toast.error(
                "There is no winner candidate to confirm."
            )
            return

        candidate = dict(self.pending_candidate or {})

        if not candidate:
            yield rx.toast.error(
                "No winner candidate selected."
            )
            return

        if not self._candidate_is_valid(candidate):
            yield rx.toast.error(
                "This candidate is no longer eligible."
            )
            return

        self.draw_locked = True

        # finalize_winner() is the authoritative persistence path.
        async for update in self.finalize_winner(candidate):
            yield update

        # Only transition after finalize_winner has run.
        self.pending_candidate = {}

        if self.lucky_draw_winner:
            self.draw_status = "CONFIRMED"
        else:
            self.draw_status = "CANDIDATE"

        self.draw_locked = False

        yield

    async def initialize_lucky_draw_event(self):
        """
        Initialize Lucky Draw from /lucky-draw/{event_id}.

        The event ID in the route is authoritative.
        """
        try:
            import re

            path = getattr(self.router.url, "path", "") or ""

            match = re.search(
                r"/lucky-draw/(\d+)",
                path,
            )

            if not match:
                self.current_event_id = ""
                self.current_event = None
                self.lucky_draw_event_name = ""
                self.lucky_draw_eligible_guests = []
                yield rx.toast.error("No Lucky Draw event selected.")
                return

            event_id = int(match.group(1))


            auth = await self.get_state(AuthState)

            if not auth.user_id:
                yield rx.redirect("/login")
                return

            try:
                event = EventService().get_event(
                    event_id,
                    auth.user_id,
                    auth.user,
                )
            except (AuthorizationError, EventNotFoundError):
                self.current_event_id = ""
                self.current_event = None
                self.lucky_draw_eligible_guests = []

                yield rx.toast.error(
                    "Event not found or access denied."
                )
                yield rx.redirect("/events")
                return

            if not event:
                self.current_event_id = ""
                self.current_event = None
                self.lucky_draw_eligible_guests = []

                yield rx.toast.error(
                    "Event not found or access denied."
                )
                yield rx.redirect("/events")
                return

            event_type = str(
                event.get("event_type") or "company_dinner"
            ).strip().lower()
            event_config = EVENT_TYPES.get(event_type)

            if not event_config or not event_config.get("features", {}).get("lucky_draw", False):
                yield rx.toast.error(
                    "Lucky Draw is not enabled for this event type."
                )
                yield rx.redirect(
                    f"/dashboard/{event_id}"
                )
                return

            self.current_event_id = str(event_id)
            self.current_event = dict(event)
            self.lucky_draw_event_name = str(
                event.get("name", "")
            )

            self.lucky_draw_event_type = event_type

            # Standalone Lucky Draw has no attendance filter. Company Dinner
            # and Sports Day default to attending guests only, but the operator
            # can switch between attending guests and all guests on the dashboard.
            if event_type == "lucky_draw":
                self.lucky_draw_only_present = False
            else:
                self.lucky_draw_only_present = True

            await self.load_lucky_draw_eligible_guests()

            yield

        except Exception:
            logger.exception(
                "Failed to initialize Lucky Draw event"
            )

            self.current_event_id = ""
            self.current_event = None
            self.lucky_draw_eligible_guests = []

            yield rx.toast.error(
                "Unable to load Lucky Draw event."
            )

    async def initialize_pre_draw_display(self):
        """Initialize the pre-draw presentation from its event_id query parameter."""
        import urllib.parse

        try:
            query_str = str(self.router.url.query or "")
            if query_str.startswith("?"):
                query_str = query_str[1:]

            params = urllib.parse.parse_qs(query_str)
            event_id_raw = str(params.get("event_id", [""])[0] or "").strip()

            if not event_id_raw:
                self.current_event_id = ""
                self.current_event = None
                self.lucky_draw_event_name = ""
                yield rx.toast.error("No Lucky Draw event selected.")
                return

            event_id = int(event_id_raw)
            auth = await self.get_state(AuthState)
            if not auth.user_id:
                yield rx.redirect("/login")
                return

            event = EventService().get_event(
                event_id,
                auth.user_id,
                auth.user,
            )
            if not event:
                self.current_event_id = ""
                self.current_event = None
                self.lucky_draw_event_name = ""
                yield rx.toast.error("Event not found or access denied.")
                yield rx.redirect("/events")
                return

            event_type = str(event.get("event_type") or "company_dinner").strip().lower()
            event_config = EVENT_TYPES.get(event_type)
            if not event_config or not event_config.get("features", {}).get("lucky_draw", False):
                yield rx.toast.error("Lucky Draw is not enabled for this event type.")
                yield rx.redirect(f"/dashboard/{event_id}")
                return

            self.current_event_id = str(event_id)
            self.current_event = dict(event)
            self.lucky_draw_event_name = str(event.get("name") or "")
            self.lucky_draw_event_type = event_type

            # Pre-draw presentation is event-scoped and independent of check-in.
            self.lucky_draw_only_present = False if event_type == "lucky_draw" else True
            await self.load_pre_draw_display_participants()
            yield

        except (TypeError, ValueError):
            self.current_event_id = ""
            self.current_event = None
            yield rx.toast.error("Invalid Lucky Draw event selected.")
        except Exception:
            logger.exception("Failed to initialize pre-draw display")
            self.current_event_id = ""
            self.current_event = None
            yield rx.toast.error("Unable to load Lucky Draw event.")

    async def redraw_missing_candidate(self):
        """
        Reject the current candidate because the guest is not present.

        The guest is permanently excluded from this event's draw session,
        while the current prize remains unchanged.
        """
        if self.draw_status != "CANDIDATE":
            yield rx.toast.error(
                "There is no candidate to redraw."
            )
            return

        candidate = dict(self.pending_candidate or {})

        if not candidate:
            yield rx.toast.error(
                "No candidate selected."
            )
            return

        guest_id = self._guest_id(candidate)

        if not guest_id:
            yield rx.toast.error(
                "Candidate has no guest ID."
            )
            return

        # Permanently exclude this guest from the current draw session.
        if guest_id not in self.excluded_guest_ids:
            self.excluded_guest_ids.append(guest_id)

        self.redraw_count += 1

        # Clear candidate state.
        self.pending_candidate = {}
        self.lucky_draw_winner = {}
        self.lucky_draw_current_name = ""
        self.lucky_draw_current_id = ""

        self.draw_status = "REDRAW"
        self.draw_locked = False

        yield

        # Immediately draw another candidate for the SAME prize.
        async for update in self.draw_current_prize():
            yield update

    def _exclude_guest_for_redraw(
            self,
            guest: Dict[str, Any],
            reason: str = "absent",
    ) -> bool:
        """
        Permanently exclude a guest from the current draw session.

        The exclusion is intentionally in-memory for the active Lucky Draw
        session. It does not modify the guest/check-in database.
        """

        guest_id = self._guest_id(guest)

        if not guest_id:
            return False

        guest_id = str(guest_id).strip()

        if guest_id not in self.excluded_guest_ids:
            self.excluded_guest_ids.append(guest_id)

        self.redraw_count += 1
        self.redraw_reason = str(reason or "absent").strip()

        self.redraw_history.append(
            {
                "guest_id": guest_id,
                "name": str(
                    guest.get("name")
                    or guest.get("Name")
                    or ""
                ).strip(),
                "prize_name": str(
                    self.lucky_draw_prize_name or ""
                ).strip(),
                "redraw_number": self.redraw_count,
                "reason": self.redraw_reason,
                "timestamp": datetime.now().isoformat(),
            }
        )

        return True


    def reset_draw_lifecycle(self):
        """Reset runtime draw state without deleting configured prizes."""

        self.draw_status = DRAW_IDLE

        self.pending_candidate = {}
        self.redraw_count = 0
        self.draw_attempt = 0
        self.draw_locked = False
        self.candidate_rejected = False

        self.excluded_guest_ids = []

        self.lucky_draw_spinning = False
        self.lucky_draw_spinner_open = False
        self.lucky_draw_winner = {}

        self.lucky_draw_current_name = ""
        self.lucky_draw_current_id = ""
        self.wheel_names = []

        self.waiting_for_next_prize = False
        self.prize_transitioning = False
        self.draw_finished = False

        self.lucky_draw_redraw_count = 0
        self.lucky_draw_redraw_guest_id = ""
        self.lucky_draw_redraw_guest_name = ""
        self.draw_status = "IDLE"

    async def redraw_current_prize(self):
        """
        Backward-compatible alias for the operator's
        NOT PRESENT action.
        """

        async for update in self.reject_candidate_as_absent():
            yield update

    async def open_participant_import(self):
        """Prepare the existing Guest Upload dialog for standalone Lucky Draw."""
        from ..state.auth_state import AuthState

        if self.lucky_draw_event_type != "lucky_draw":
            yield rx.toast.error(
                "Participant import is only available for standalone Lucky Draw."
            )
            return

        if not self.current_event_id:
            yield rx.toast.error("No Lucky Draw event selected.")
            return

        auth = await self.get_state(AuthState)

        if not auth.user_id:
            yield rx.redirect("/login")
            return

        guest_state = await self.get_state(GuestState)

        # Synchronize the existing guest-upload workflow with this event.
        guest_state.current_event_id = str(self.current_event_id)
        guest_state.current_event = dict(self.current_event or {})
        guest_state.event_type = "lucky_draw"
        guest_state.user_id = auth.user_id
        guest_state.is_authenticated = True

        guest_state.open_upload_dialog()

        yield

    async def set_lucky_draw_only_present(self, value: bool):
        """Set the Lucky Draw eligibility filter for the current event."""
        value = bool(value)

        if self.lucky_draw_event_type == "lucky_draw":
            self.lucky_draw_only_present = False
            await self.load_lucky_draw_eligible_guests()
            yield
            return

        self.lucky_draw_only_present = value
        await self.load_lucky_draw_eligible_guests()
        yield

    async def set_lucky_draw_excluded(self, value: str):
        """Update the Lucky Draw exclusion filter."""
        value = str(value or "").strip()

        self.lucky_draw_excluded = value



        guest_state = await self.get_state(GuestState)

        guest_state.lucky_draw_excluded = value
        guest_state.load_lucky_draw_eligible_guests()

        self.lucky_draw_eligible_guests = list(
            guest_state.lucky_draw_eligible_guests
        )

        yield

    async def load_lucky_draw_eligible_guests(self):
        """Load the complete eligible pool from the repository.

        The pool is intentionally loaded in pages so a 500-4000 participant
        event is not limited by the dashboard's visible table page.
        ``lucky_draw_only_present=False`` makes the module usable as a
        standalone lucky-draw product without check-in.
        """
        try:


            guest_state = await self.get_state(GuestState)
            event_id = int(
                self.current_event_id
                or getattr(guest_state, "current_event_id", 0)
                or 0
            )
            await self.load_pre_draw_winners()
            if not event_id:
                self.lucky_draw_eligible_guests = []
                return

            self.current_event_id = str(event_id)
            if not self.current_event:
                self.current_event = getattr(guest_state, "current_event", None)

            event_type = str(
                (self.current_event or {}).get("event_type") or
                self.lucky_draw_event_type or
                "company_dinner"
            ).strip().lower()
            self.lucky_draw_event_type = event_type
            if event_type == "lucky_draw":
                self.lucky_draw_only_present = False

            excluded = {
                item.strip().lower()
                for item in str(self.lucky_draw_excluded or "").split(",")
                if item.strip()
            }

            repo = GuestRepository()
            eligible: List[Dict[str, Any]] = []
            page = 0
            page_size = 200

            while True:
                rows, _total = repo.get_by_event(
                    event_id,
                    limit=page_size,
                    offset=page * page_size,
                )
                if not rows:
                    break

                for guest in rows:
                    guest_id = str(guest.get("guest_id") or "").strip()
                    if not guest_id or guest_id.lower() in excluded:
                        continue

                    status = str(guest.get("status") or "").strip().lower()
                    if self.lucky_draw_only_present and status != "present":
                        continue

                    eligible.append({
                        "name": str(guest.get("name") or "Guest"),
                        "guest_id": guest_id,
                        "table_number": guest.get("table_number") or "TBD",
                        "email": guest.get("email") or "",
                        "photo": guest.get("photo") or guest.get("photo_url") or "",
                        "company": guest.get("company") or "",
                    })

                if len(rows) < page_size:
                    break
                page += 1

            self.lucky_draw_eligible_guests = eligible
            if self.current_event:
                self.lucky_draw_event_name = str(
                    self.current_event.get("name") or self.lucky_draw_event_name or ""
                )

        except Exception:
            logger.exception(
                "Unable to load lucky draw guests for event %s",
                self.current_event_id,
            )
            self.lucky_draw_eligible_guests = []

    async def set_pre_draw_winner_file(
        self,
        files: List[rx.UploadFile],
    ):
        """Stage a preliminary-winner Excel file selected by the upload widget."""
        if not files:
            self.pre_draw_winner_selected_file_name = ""
            self._pre_draw_winner_file_content = b""
            self._pre_draw_winner_filename = ""
            return

        file = files[0]
        filename = str(getattr(file, "filename", "") or getattr(file, "name", "") or "").strip()
        extension = filename.lower()

        if not extension.endswith((".xlsx", ".xls", ".xlsm")):
            self.pre_draw_winner_selected_file_name = ""
            self._pre_draw_winner_file_content = b""
            self._pre_draw_winner_filename = ""
            yield rx.toast.error("Please upload a valid Excel file (.xlsx, .xls, or .xlsm).")
            return

        try:
            content = await file.read()
            if not content:
                raise ValueError("The uploaded file is empty.")

            self._pre_draw_winner_file_content = content
            self._pre_draw_winner_filename = filename
            self.pre_draw_winner_selected_file_name = filename
            yield rx.toast.success(f"Pre-draw winner file selected: {filename}")
        except Exception as exc:
            logger.exception("Unable to read pre-draw winner file")
            self.pre_draw_winner_selected_file_name = ""
            self._pre_draw_winner_file_content = b""
            self._pre_draw_winner_filename = ""
            yield rx.toast.error(f"Unable to read the file: {exc}")

    async def import_pre_draw_winners(self, files: List[rx.UploadFile]):
        """One-step, production-safe pre-draw winner import."""
        if not files:
            yield rx.toast.error("Please select a pre-draw winner Excel file.")
            return

        file = files[0]
        filename = str(getattr(file, "filename", "") or getattr(file, "name", "") or "").strip()
        if not filename.lower().endswith((".xlsx", ".xls", ".xlsm")):
            yield rx.toast.error("Please upload a valid Excel file (.xlsx, .xls, or .xlsm).")
            return

        if not self.current_event_id:
            yield rx.toast.error("No Lucky Draw event selected.")
            return

        try:
            content = await file.read()
            if not content:
                raise ValueError("The uploaded file is empty.")

            persisted = PreDrawWinnerService().import_file(
                int(self.current_event_id),
                content,
                event_type=self.lucky_draw_event_type,
            )

            self.pre_draw_winner_filename = filename
            self.pre_draw_winner_selected_file_name = ""
            self._pre_draw_winner_file_content = b""
            self._pre_draw_winner_filename = ""
            self.pre_draw_upload_dialog_open = False

            await self.load_pre_draw_winners()
            self._rebuild_pre_draw_display_rows()
            self.predraw_page = 0
            await self.load_lucky_draw_eligible_guests()

            yield rx.toast.success(
                f"{len(persisted)} pre-draw winner(s) imported successfully."
            )
        except ValueError as exc:
            logger.warning("Pre-draw winner validation failed for event %s: %s", self.current_event_id, exc)
            yield rx.toast.error(str(exc))
        except Exception as exc:
            logger.exception("Pre-draw winner import failed for event %s", self.current_event_id)
            yield rx.toast.error(f"Unable to import preliminary winners: {exc}")

    async def process_pre_draw_winner_upload(self):
        """Import the staged preliminary-winner file."""
        if not self._pre_draw_winner_file_content:
            yield rx.toast.error("No pre-draw winner file selected.")
            return
        if not self.current_event_id:
            yield rx.toast.error("No Lucky Draw event selected.")
            return
        try:
            persisted = PreDrawWinnerService().import_file(
                int(self.current_event_id),
                self._pre_draw_winner_file_content,
                event_type=self.lucky_draw_event_type,
            )
            filename = self._pre_draw_winner_filename
            self.pre_draw_winner_filename = filename
            self._pre_draw_winner_file_content = b""
            self._pre_draw_winner_filename = ""
            self.pre_draw_winner_selected_file_name = ""
            self.pre_draw_upload_dialog_open = False
            await self.load_pre_draw_winners()
            self._rebuild_pre_draw_display_rows()
            self.predraw_page = 0
            await self.load_lucky_draw_eligible_guests()
            yield rx.toast.success(f"{len(persisted)} pre-draw winner(s) imported successfully.")
        except ValueError as exc:
            logger.warning("Pre-draw winner validation failed for event %s: %s", self.current_event_id, exc)
            yield rx.toast.error(str(exc))
        except Exception as exc:
            logger.exception("Pre-draw winner import failed for event %s", self.current_event_id)
            yield rx.toast.error(f"Unable to import preliminary winners: {exc}")

    def load_current_prize(self):
        """Synchronize the UI fields with ``current_prizes[current_prize_index]``."""
        return self._set_current_prize()

    def set_prize_list(self, prizes: List[Dict[str, Any]]):
        """Set the manual prize list and synchronize the active list."""
        normalized = [dict(prize) for prize in (prizes or []) if isinstance(prize, dict)]
        self.prize_list = normalized
        self.multiple_prizes_list = [dict(prize) for prize in normalized]
        if self.prize_mode == "multiple":
            self.current_prizes = [
                dict(prize)
                for prize in normalized
                if str(prize.get("name") or "").strip()
            ]
            self.current_prize_index = 0
            self._set_current_prize()

    def set_lucky_draw_prize_name(self, value: str):
        """Set the displayed/current prize name."""
        self.lucky_draw_prize_name = str(value or "")

    def set_lucky_draw_prize_value(self, value: str):
        """Set the displayed/current prize value."""
        self.lucky_draw_prize_value = str(value or "")

    def set_lucky_draw_prize_picture(self, value: str):
        """Set the displayed/current prize image URL."""
        self.lucky_draw_prize_picture = str(value or "")

    def set_lucky_draw_event_name(self, name: str):
        """Set the event name used by the live display."""
        self.lucky_draw_event_name = str(name or "")

    def set_prize_mode(self, mode: str):
        """Set the active prize input mode.

        Supported modes:
            - single
            - multiple
            - excel
        """
        mode = str(mode or "").strip().lower()

        if mode not in {"single", "multiple", "excel"}:
            logger.warning("Ignoring invalid prize mode: %s", mode)
            return

        self.prize_mode = mode

        # Keep the active prize list synchronized with the selected mode.
        if mode == "single":
            if self.single_prize_name.strip():
                self.current_prizes = [{
                    "name": self.single_prize_name.strip(),
                    "value": self.single_prize_value.strip(),
                    "image_url": self.single_prize_picture.strip(),
                }]
            else:
                self.current_prizes = []

        elif mode == "multiple":
            source = self.multiple_prizes_list or self.prize_list
            self.current_prizes = [
                dict(prize)
                for prize in source
                if str(prize.get("name") or "").strip()
            ]
            self.prize_list = [dict(prize) for prize in source]

        elif mode == "excel":
            self.current_prizes = [
                dict(prize)
                for prize in self.excel_prizes_list
                if str(prize.get("name") or "").strip()
            ]

        self.current_prize_index = 0

    # Single Prize
    single_prize_name: str = ""
    single_prize_value: str = ""
    single_prize_picture: str = ""

    # Multiple Prizes (manual entry)
    multiple_prizes_list: List[Dict[str, Any]] = []

    # Excel Prizes
    excel_prizes_list: List[Dict[str, Any]] = []
    excel_filename: str = ""

    # Event name for display


    is_loading: bool = False

    # --- Computed Properties ---

    @rx.var
    def lucky_draw_eligible_count(self) -> int:
        """Get eligible guests count."""
        return len(self.lucky_draw_eligible_guests)

    @rx.var
    def lucky_draw_uses_attendance(self) -> bool:
        """Whether this event has an attendance-linked guest list."""
        return self.lucky_draw_event_type != "lucky_draw"

    @rx.var
    def lucky_draw_source_label(self) -> str:
        """Describe the participant source and eligibility model."""
        if self.lucky_draw_event_type == "lucky_draw":
            return "Client-supplied participant list (no check-in required)"
        if self.lucky_draw_only_present:
            return "Event guest list — attending guests only"
        return "Event guest list — all guests"

    @rx.var
    def lucky_draw_eligibility_label(self) -> str:
        """Return the current eligibility selection label."""
        if self.lucky_draw_event_type == "lucky_draw":
            return "All participants"
        return "Attending guests only" if self.lucky_draw_only_present else "All guests"

    @rx.var
    def pre_draw_event_venue(self) -> str:
        """Return the current event venue for the public display."""
        return str(
            (self.current_event or {}).get("venue")
            or ""
        )

    @rx.var
    def pre_draw_event_date(self) -> str:
        """Return the current event date for the public display."""
        return str(
            (self.current_event or {}).get("date")
            or ""
        )

    @rx.var
    def pre_draw_event_time(self) -> str:
        """Return the current event time for the public display."""
        return str(
            (self.current_event or {}).get("time")
            or ""
        )

    @rx.var
    def pre_draw_event_logo(self) -> str:
        """Return the current event logo for the public display."""
        event = self.current_event or {}

        return str(
            event.get("logo")
            or event.get("event_logo")
            or ""
        )

    @rx.var
    def pre_draw_winner_count(self) -> int:
        """Return the number of persisted preliminary winners."""
        return len(self.pre_draw_winners)

    async def refresh_pre_draw_display(self):
        """
        Refresh the public pre-draw display without unnecessarily
        resetting the operator's current page.
        """
        try:
            current_page = self.predraw_page

            await self.load_pre_draw_winners()

            self._rebuild_pre_draw_display_rows()

            page_count = self.predraw_page_count

            if page_count <= 0:
                self.predraw_page = 0
            else:
                self.predraw_page = min(
                    current_page,
                    page_count - 1,
                )

        except Exception:
            logger.exception(
                "Unable to refresh pre-draw display for event %s",
                self.current_event_id,
            )

    async def load_pre_draw_winners(self):
        """
        Load preliminary winners from the authoritative database.

        Preliminary winners are completely separate from live Lucky Draw
        winners and must never be copied into winners_list.
        """
        try:
            event_id = int(self.current_event_id or 0)

            if not event_id:
                self.pre_draw_winners = []
                return

            service = PreDrawWinnerService()

            self.pre_draw_winners = [
                dict(winner)
                for winner in service.get_by_event(event_id)
            ]

            logger.info(
                "Loaded %d pre-draw winners for event %s",
                len(self.pre_draw_winners),
                event_id,
            )

        except Exception:
            logger.exception(
                "Unable to load pre-draw winners for event %s",
                self.current_event_id,
            )

            self.pre_draw_winners = []

    def _rebuild_pre_draw_display_rows(self):
        """
        Build the public presentation dataset from PRE-DRAW WINNERS ONLY.

        Important:
            This intentionally does NOT use lucky_draw_eligible_guests.

        The pre-draw screen is a presentation of the preliminary winners
        supplied by the client. It is therefore independent of attendance
        filtering and the live Lucky Draw candidate pool.
        """
        display_rows: List[Dict[str, Any]] = []

        for index, winner in enumerate(
                self.pre_draw_winners,
                start=1,
        ):
            guest_id = str(
                winner.get("guest_id")
                or winner.get("id")
                or ""
            ).strip()

            if not guest_id:
                continue

            display_rows.append(
                {
                    "display_number": index,
                    "name": str(
                        winner.get("name")
                        or "Winner"
                    ).strip(),
                    "guest_id": guest_id,
                    "table_number": str(
                        winner.get("table_number")
                        or "TBD"
                    ),
                    "is_pre_draw_winner": True,
                    "pre_draw_prize": str(
                        winner.get("prize_name")
                        or "Pre-Draw Prize"
                    ).strip(),
                    "pre_draw_value": str(
                        winner.get("prize_value")
                        or ""
                    ).strip(),
                    "pre_draw_image": str(
                        winner.get("image_url")
                        or ""
                    ).strip(),
                }
            )

        self.pre_draw_display_participants = display_rows

    async def load_pre_draw_display_participants(self):
        """
        Prepare the public pre-draw presentation.

        Only persisted preliminary winners are displayed.

        This method intentionally does not depend on:
            - attendance status
            - lucky_draw_only_present
            - lucky_draw_eligible_guests
            - winners_list
            - live draw lifecycle
        """
        try:
            await self.load_pre_draw_winners()

            self._rebuild_pre_draw_display_rows()

            # Opening the display always starts from page 1.
            self.predraw_page = 0

            logger.info(
                "Prepared %d pre-draw winners for public display "
                "for event %s",
                len(self.pre_draw_display_participants),
                self.current_event_id,
            )

        except Exception:
            logger.exception(
                "Unable to prepare pre-draw display for event %s",
                self.current_event_id,
            )

            self.pre_draw_display_participants = []
            self.predraw_page = 0

    def _pre_draw_winner_ids(self) -> set[str]:
        """Return normalized Guest IDs that already won a preliminary prize."""
        return {
            str(
                winner.get("guest_id")
                or ""
            ).strip()
            for winner in self.pre_draw_winners
            if str(
                winner.get("guest_id")
                or ""
            ).strip()
        }

    @rx.var
    def predraw_page_count(self) -> int:
        """Return the number of public pre-draw display pages."""
        total = len(self.pre_draw_display_participants)

        if total <= 0:
            return 0

        return (
                total + self.predraw_page_size - 1
        ) // self.predraw_page_size

    @rx.var
    def predraw_visible_participants(
            self,
    ) -> List[Dict[str, Any]]:
        """
        Return exactly one page of preliminary winners.

        The page size represents the TOTAL number of winners shown on
        one presentation page. The UI splits this list into two tables.
        """
        start = (
                self.predraw_page *
                self.predraw_page_size
        )

        end = start + self.predraw_page_size

        return list(
            self.pre_draw_display_participants[
                start:end
            ]
        )

    @rx.var
    def predraw_left_participants(
            self,
    ) -> List[Dict[str, Any]]:
        """
        Return the left table from the current page.

        The current page remains controlled entirely by
        predraw_visible_participants.
        """
        visible = self.predraw_visible_participants

        split = (
                        len(visible) + 1
                ) // 2

        return list(
            visible[:split]
        )

    @rx.var
    def predraw_right_participants(
            self,
    ) -> List[Dict[str, Any]]:
        """
        Return the right table from the current page.
        """
        visible = self.predraw_visible_participants

        split = (
                        len(visible) + 1
                ) // 2

        return list(
            visible[split:]
        )

    @rx.var
    def predraw_is_last_page(self) -> bool:
        """Whether the current public display page is the final page."""
        page_count = self.predraw_page_count

        if page_count <= 0:
            return True

        return self.predraw_page >= page_count - 1

    @rx.var
    def predraw_page_indicator(self) -> str:
        """Return the current public display page indicator."""
        page_count = self.predraw_page_count

        if page_count <= 0:
            return "PAGE 0 / 0"

        return (
            f"PAGE {self.predraw_page + 1} / "
            f"{page_count}"
        )

    @rx.var
    def predraw_range_label(self) -> str:
        """Return the winner range shown on the current page."""
        total = len(
            self.pre_draw_display_participants
        )

        if total <= 0:
            return "No winners"

        start = (
                        self.predraw_page *
                        self.predraw_page_size
                ) + 1

        end = min(
            start + self.predraw_page_size - 1,
            total,
        )

        return (
            f"Winners {start}–{end} of {total}"
        )

    def predraw_next_page(self):
        """Move the public pre-draw display forward one page."""
        page_count = self.predraw_page_count

        if page_count <= 0:
            self.predraw_page = 0
            return

        if self.predraw_page < page_count - 1:
            self.predraw_page += 1

    def predraw_previous_page(self):
        """Move the public pre-draw display backward one page."""
        page_count = self.predraw_page_count

        if page_count <= 0:
            self.predraw_page = 0
            return

        if self.predraw_page > 0:
            self.predraw_page -= 1

    def reset_predraw_presentation(self):
        """Return the pre-draw presentation to its first page."""
        self.predraw_page = 0

    @rx.var
    def predraw_display_mode_label(self) -> str:
        """Return a human-readable pre-draw display mode."""
        if self.predraw_display_mode == "different":
            return "Different slides per screen"
        return "Same synchronized presentation"

    def set_predraw_display_mode(self, mode: str):
        """Set the pre-draw presentation mode."""
        mode = str(mode or "").strip().lower()
        if mode not in {"same", "different"}:
            logger.warning("Ignoring invalid pre-draw display mode: %s", mode)
            return
        self.predraw_display_mode = mode

    def set_predraw_screen_count(self, value):
        """Set the number of physical pre-draw screens/feeds required."""
        try:
            count = int(value)
        except (TypeError, ValueError):
            count = 1
        self.predraw_screen_count = max(1, min(count, 20))

    # --- Guest Loading ---
    async def set_excel_prize_file(self, files: List[rx.UploadFile]):
        if files and len(files) > 0:
            file = files[0]
            if file.filename.endswith(('.xlsx', '.xls', '.xlsm')):
                self._prize_file_content = await file.read()
                self._prize_filename = file.filename
                self.prize_selected_file_name = file.filename
                yield rx.toast.info(f"File loaded: {file.filename}")
            else:
                yield rx.toast.error("Please upload a valid Excel file")

    async def process_excel_prize_upload(self):
        """Process the selected prize Excel file through ExcelService."""
        if not self._prize_file_content:
            yield rx.toast.error("No file selected")
            return

        self.is_loading = True
        yield

        try:
            from ..services.excel_service_ranked import ExcelService

            service = ExcelService()

            prizes = service.parse_prize_file(
                self._prize_file_content
            )

            if not prizes:
                self.is_loading = False
                yield rx.toast.error(
                    "No valid prizes found in the Excel file"
                )
                return

            # An uploaded Excel file is itself a complete prize configuration.
            # Activate it immediately instead of depending on the previously
            # selected prize mode (which may still be "multiple" by default).
            normalized_prizes = [dict(prize) for prize in prizes]
            self.excel_prizes_list = normalized_prizes
            self.excel_filename = self._prize_filename
            self.prize_list = [dict(prize) for prize in normalized_prizes]
            self.prize_mode = "excel"
            self.current_prizes = [
                dict(prize)
                for prize in normalized_prizes
                if str(prize.get("name") or "").strip()
            ]
            self.current_prize_index = 0

            if self.current_prizes:
                first_prize = self.current_prizes[0]
                self.lucky_draw_prize_name = str(first_prize.get("name") or "")
                self.lucky_draw_prize_value = str(first_prize.get("value") or "")
                self.lucky_draw_prize_picture = str(first_prize.get("image_url") or "")

            self.is_loading = False

            yield rx.toast.success(
                f"Loaded {len(prizes)} prize(s) from "
                f"{self._prize_filename}"
            )

        except ValueError as exc:
            self.is_loading = False

            logger.warning(
                "Prize Excel validation failed: %s",
                exc,
            )

            yield rx.toast.error(str(exc))

        except Exception as exc:
            self.is_loading = False

            logger.exception(
                "Error processing prize Excel file"
            )

            yield rx.toast.error(
                f"Unable to process prize file: {str(exc)}"
            )

    # --- Prize CRUD ---

    def set_single_prize_name(self, value: str):
        self.single_prize_name = value
        if self.prize_mode == "single":
            self.lucky_draw_prize_name = value
            self.current_prizes = [{"name": value, "value": self.single_prize_value,
                                    "image_url": self.single_prize_picture}] if value else []

    def set_single_prize_value(self, value: str):
        self.single_prize_value = value
        if self.prize_mode == "single":
            self.lucky_draw_prize_value = value
            self.current_prizes = [{"name": self.single_prize_name, "value": value,
                                    "image_url": self.single_prize_picture}] if self.single_prize_name else []

    def set_single_prize_picture(self, value: str):
        self.single_prize_picture = value
        if self.prize_mode == "single":
            self.lucky_draw_prize_picture = value
            self.current_prizes = [{"name": self.single_prize_name, "value": self.single_prize_value,
                                    "image_url": value}] if self.single_prize_name else []

    def add_multiple_prize(self):
        self.multiple_prizes_list.append({"name": "", "value": "", "image_url": ""})

    def remove_multiple_prize(self, index: int):
        if 0 <= index < len(self.multiple_prizes_list):
            self.multiple_prizes_list.pop(index)

    def update_multiple_prize_field(self, index: int, field: str, value: str):
        if 0 <= index < len(self.multiple_prizes_list):
            self.multiple_prizes_list[index][field] = value

    def clear_multiple_prizes(self):
        self.multiple_prizes_list = []
        if self.prize_mode == "multiple":
            self.current_prizes = []
            self.lucky_draw_prize_name = ""
            self.lucky_draw_prize_value = ""
            self.lucky_draw_prize_picture = ""

    def clear_single_prize(self):
        self.single_prize_name = ""
        self.single_prize_value = ""
        self.single_prize_picture = ""
        if self.prize_mode == "single":
            self.lucky_draw_prize_name = ""
            self.lucky_draw_prize_value = ""
            self.lucky_draw_prize_picture = ""
            self.current_prizes = []

    def clear_excel_prize_file(self):
        """Clear the currently selected Excel prize upload."""
        self.prize_selected_file_name = ""
        self._prize_file_content = b""
        self._prize_filename = ""

    def clear_excel_prizes(self):
        """Clear the imported Excel prize list."""
        self.excel_prizes_list = []
        self.excel_filename = ""
        self.prize_excel_filename = ""

        self.current_prizes = []
        self.current_prize_index = 0

        self.lucky_draw_prize_name = ""
        self.lucky_draw_prize_value = ""
        self.lucky_draw_prize_picture = ""

        self.prize_selected_file_name = ""
        self._prize_file_content = b""
        self._prize_filename = ""

        return rx.toast.success("Prize list cleared.")

    def clear_all_prizes(self):
        """Clear all prizes."""
        self.prize_list = []
        self.prize_excel_filename = ""
        self.prize_selected_file_name = ""
        self.current_prizes = []
        self.current_prize_index = 0
        self.lucky_draw_prize_name = ""
        self.lucky_draw_prize_value = ""
        self.lucky_draw_prize_picture = ""
        return rx.toast.success("All prizes cleared!")

    def add_prize(self):
        self.prize_list.append({"name": "", "value": "", "image_url": ""})

    def remove_prize(self, index: int):
        if 0 <= index < len(self.prize_list):
            self.prize_list.pop(index)

    def update_prize_field(self, index: int, field: str, value: str):
        if 0 <= index < len(self.prize_list):
            self.prize_list[index][field] = value

    def clear_prize_list(self):
        self.prize_list = []

    def clear_prize_image(self):
        self.lucky_draw_prize_picture = ""
        return rx.toast.success("Image cleared")

    # --- UI Controls ---

    def open_new_draw_dialog(self):
        self.lucky_draw_show_new_draw_dialog = True

    def close_new_draw_dialog(self):
        self.lucky_draw_show_new_draw_dialog = False

    def cancel_clear_winners(self):
        self.show_clear_confirm = False

    async def clear_winners_history(self):
        self.show_clear_confirm = True
        yield

    async def load_winners(self):
        """Load winner history for the current event through WinnerService."""

        if not self.current_event_id:
            self.winners_list = []
            return

        try:
            service = WinnerService()

            winners = service.get_by_event(
                int(self.current_event_id)
            )

            self.winners_list = winners

        except Exception as exc:
            logger.exception(
                "Error loading winners for event %s",
                self.current_event_id,
            )

    async def confirm_clear_winners(self):
        """Clear all winners for the current event."""
        self.is_loading = True
        yield

        try:
            if not self.current_event_id:
                self.is_loading = False
                self.show_clear_confirm = False
                yield rx.toast.error(
                    "No event selected."
                )
                return

            service = WinnerService()

            service.delete_by_event(
                int(self.current_event_id)
            )

            self.winners_list = []
            self.drawn_winners = []
            self.pending_candidate = {}
            self.lucky_draw_winner = {}
            self.excluded_guest_ids = []
            self.draw_locked = False
            self.is_loading = False
            self.show_clear_confirm = False

            await self.load_lucky_draw_eligible_guests()

            yield rx.toast.success("Winners history cleared!")

        except Exception as e:
            self.is_loading = False
            logger.exception(
                "Error clearing winners for event %s",
                self.current_event_id,
            )
            yield rx.toast.error(
                f"Error: {str(e)}"
            )

    def download_winner_list(self):
        """Generates and downloads a CSV of the winners list."""
        if not self.winners_list:
            return rx.toast.error("No winners to export")

        import pandas as pd
        df = pd.DataFrame(self.winners_list)

        export_columns = ["name", "guest_id", "prize_name", "prize_value", "created_at"]
        available_cols = [c for c in export_columns if c in df.columns]
        df = df[available_cols]

        column_names = {
            "name": "Winner Name",
            "guest_id": "Guest ID",
            "prize_name": "Prize",
            "prize_value": "Prize Value",
            "created_at": "Date & Time"
        }
        df = df.rename(columns={k: v for k, v in column_names.items() if k in df.columns})

        if "Date & Time" in df.columns:
            df["Date & Time"] = df["Date & Time"].apply(
                lambda x: x.split("T")[0] if x and "T" in str(x) else x
            )

        csv_data = df.to_csv(index=False)

        return rx.download(
            data=csv_data,
            filename=f"winners_event_{self.current_event_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        )

    # --- Draw Methods ---

    async def finalize_winner(self, winner):
        """Compatibility API that confirms a selected candidate.

        New UI code should use ``confirm_candidate``. Keeping this method
        prevents older pages/components from breaking while ensuring there is
        still exactly one persistence path for a live winner.
        """
        if not winner:
            yield rx.toast.error("No winner selected.")
            return

        candidate_id = str(winner.get("guest_id") or "").strip()
        if not candidate_id:
            yield rx.toast.error("Winner has no guest ID.")
            return

        self.pending_candidate = dict(winner)
        self.lucky_draw_current_name = str(winner.get("name") or "")
        self.lucky_draw_current_id = candidate_id
        self.draw_status = CANDIDATE

        async for update in self.confirm_candidate():
            yield update

    async def draw_current_prize(self):
        """Compatibility entry point for drawing the current prize.

        The production lifecycle intentionally separates candidate selection
        from winner confirmation. This method therefore delegates to
        ``start_lucky_draw`` instead of persisting a winner automatically.
        """
        async for update in self.start_lucky_draw():
            yield update

    async def draw_next_prize(self):
        """Advance to the next prize."""

        if self.draw_locked:
            yield rx.toast.warning(
                "Please finish the current draw first."
            )
            return

        if self.draw_status != CONFIRMED:
            yield rx.toast.warning(
                "Please confirm the current winner first."
            )
            return

        if (
                self.current_prize_index + 1
                >= len(self.current_prizes)
        ):
            self.draw_status = DONE
            self.draw_finished = True
            self.lucky_draw_spinner_open = False
            self.waiting_for_next_prize = False

            yield rx.toast.success(
                "All prizes have been awarded!"
            )
            yield self.broadcast_lucky_draw_state()
            return

        self.draw_status = NEXT_PRIZE
        self.prize_transitioning = True
        self.pending_candidate = {}
        self.redraw_count = 0
        self.candidate_rejected = False
        self.lucky_draw_winner = {}

        yield

        await asyncio.sleep(0.4)

        self.current_prize_index += 1

        self._set_current_prize()

        self.prize_transitioning = False
        self.waiting_for_next_prize = False
        self.draw_status = READY

        yield

    async def show_next_prize(self):
        """Compatibility alias for the lifecycle-safe next-prize transition."""
        async for update in self.draw_next_prize():
            yield update

    # ========================================================================
    # PRODUCTION LUCKY DRAW LIFECYCLE
    # ========================================================================


    def _reset_candidate_state(self):
        """Clear the current pending candidate."""
        self.pending_candidate = {}
        self.lucky_draw_winner = {}
        self.lucky_draw_current_name = ""
        self.lucky_draw_current_id = ""

    async def setup_complete_and_go_to_display(self):
        """
        Finalize Lucky Draw setup and open the LIVE Lucky Draw display.

        The live display receives a compact configuration payload through
        the URL. Large participant lists are NOT sent through the URL;
        the display reloads them from the repository.
        """
        if not self.current_event_id:
            yield rx.toast.error(
                "No event selected."
            )
            return

        # ------------------------------------------------------------------
        # Build current_prizes from the selected configuration mode.
        # ------------------------------------------------------------------
        if not self.current_prizes:

            if self.prize_mode == "single":

                if not self.single_prize_name.strip():
                    yield rx.toast.error(
                        "Please set a prize first."
                    )
                    return

                self.current_prizes = [
                    {
                        "name": self.single_prize_name.strip(),
                        "value": self.single_prize_value.strip(),
                        "image_url": self.single_prize_picture.strip(),
                    }
                ]

            elif self.prize_mode == "multiple":

                self.current_prizes = [
                    dict(prize)
                    for prize in self.multiple_prizes_list
                    if str(
                        prize.get("name")
                        or ""
                    ).strip()
                ]

            elif self.prize_mode == "excel":

                self.current_prizes = [
                    dict(prize)
                    for prize in self.excel_prizes_list
                    if str(
                        prize.get("name")
                        or ""
                    ).strip()
                ]

        # ------------------------------------------------------------------
        # Validate prizes.
        # ------------------------------------------------------------------
        if not self.current_prizes:
            yield rx.toast.error(
                "No valid prizes configured."
            )
            return

        # ------------------------------------------------------------------
        # Refresh the live participant pool.
        # ------------------------------------------------------------------
        await self.load_lucky_draw_eligible_guests()

        if not self.lucky_draw_eligible_guests:
            yield rx.toast.error(
                "No eligible guests available for the lucky draw."
            )
            return

        # ------------------------------------------------------------------
        # Reset live draw lifecycle.
        # ------------------------------------------------------------------
        self.current_prize_index = 0
        self.redraw_count = 0
        self.current_prize_redraw_count = 0
        self.excluded_guest_ids = []

        self._reset_candidate_state()

        self.draw_locked = False
        self.draw_status = READY
        self.lucky_draw_setup_complete = True
        self.draw_finished = False
        self.waiting_for_next_prize = False
        self.prize_transitioning = False

        # ------------------------------------------------------------------
        # Synchronize first prize.
        # ------------------------------------------------------------------
        first_prize = self.current_prizes[0]

        self.lucky_draw_prize_name = str(
            first_prize.get("name")
            or ""
        )

        self.lucky_draw_prize_value = str(
            first_prize.get("value")
            or ""
        )

        self.lucky_draw_prize_picture = str(
            first_prize.get("image_url")
            or ""
        )

        # ------------------------------------------------------------------
        # Build compact live-display payload.
        #
        # We intentionally do NOT include participant lists here.
        # ------------------------------------------------------------------
        display_payload = {
            "current_event_id": str(
                self.current_event_id
            ),
            "current_event_name": str(
                self.lucky_draw_event_name
                or ""
            ),
            "event_type": str(
                self.lucky_draw_event_type
                or ""
            ),
            "prize_mode": str(
                self.prize_mode
                or "multiple"
            ),
            "current_prizes": [
                dict(prize)
                for prize in self.current_prizes
            ],
            "current_prize_index": 0,
            "lucky_draw_excluded": str(
                self.lucky_draw_excluded
                or ""
            ),
            "lucky_draw_only_present": bool(
                self.lucky_draw_only_present
            ),
            "winners": [
                dict(winner)
                for winner in self.winners_list
                if isinstance(winner, dict)
            ],
        }

        # ------------------------------------------------------------------
        # Encode payload safely for the URL.
        # ------------------------------------------------------------------
        payload_json = json.dumps(
            display_payload,
            separators=(",", ":"),
            ensure_ascii=False,
        )

        encoded_payload = base64.urlsafe_b64encode(
            payload_json.encode("utf-8")
        ).decode("ascii")

        # ------------------------------------------------------------------
        # IMPORTANT:
        # The actual registered route is /lucky-draw-display.
        # ------------------------------------------------------------------
        yield self.broadcast_lucky_draw_state()
        yield rx.redirect(
            f"/lucky-draw-display"
            f"?event_id={self.current_event_id}"
            f"&data={encoded_payload}"
        )

    async def _select_new_candidate(self):
        """
        Select one candidate for the current prize.

        This method does not persist a winner. Persistence only happens after
        the operator confirms that the candidate is present.
        """
        candidates = self._available_draw_candidates()

        if not candidates:
            return None

        return random.choice(candidates)

    async def draw_candidate(self):
        """
        Start a new candidate selection for the current prize.

        A candidate is provisional until explicitly confirmed.
        """
        if self.draw_locked:
            yield rx.toast.warning(
                "The draw is locked while the current candidate is being reviewed."
            )
            return

        if self.draw_status not in {"READY", "CANDIDATE", "REDRAW"}:
            yield rx.toast.warning(
                f"Cannot draw a candidate while status is {self.draw_status}."
            )
            return

        candidates = self._available_draw_candidates()

        if not candidates:
            self.draw_status = "DONE"
            yield rx.toast.error(
                "There are no eligible guests remaining."
            )
            return

        self.draw_locked = True
        self.draw_status = "DRAWING"
        self.lucky_draw_spinning = True
        self.prepare_wheel_names()
        self.spin_wheel_visual()


        yield

        # Keep the existing visual animation delay.
        await asyncio.sleep(1.0)

        candidate = await self._select_new_candidate()

        if not candidate:
            self.draw_locked = False
            self.lucky_draw_spinning = False
            self.draw_status = "READY"

            yield rx.toast.error(
                "Unable to select a valid candidate."
            )
            return

        self.pending_candidate = dict(candidate)

        self.lucky_draw_current_name = str(
            candidate.get("name")
            or candidate.get("Name")
            or ""
        )

        self.lucky_draw_current_id = self._guest_id(candidate)

        self.lucky_draw_winner = dict(candidate)

        self.lucky_draw_spinning = False
        self.draw_locked = False
        self.draw_status = "CANDIDATE"

        yield

    async def confirm_current_winner(self):
        """
        Confirm that the displayed candidate is present.

        Only this operation turns a candidate into an official winner.
        """
        if self.draw_locked:
            yield rx.toast.warning(
                "Please wait until the current draw operation finishes."
            )
            return

        if self.draw_status != "CANDIDATE":
            yield rx.toast.warning(
                "There is no candidate waiting for confirmation."
            )
            return

        candidate = dict(self.pending_candidate)

        if not self._candidate_is_valid(candidate):
            yield rx.toast.error(
                "The current candidate is no longer valid."
            )
            return

        self.draw_locked = True

        yield

        try:
            async for update in self.finalize_winner(candidate):
                yield update

            # finalize_winner removes the guest from the eligible pool.
            self.pending_candidate = {}

            self.draw_status = "CONFIRMED"

            self.draw_locked = False

            yield

        except Exception as exc:
            self.draw_locked = False
            logger.exception(
                "Unable to confirm lucky draw candidate."
            )

            yield rx.toast.error(
                f"Unable to confirm winner: {exc}"
            )

    async def redraw_current_candidate(self):
        """
        Reject the current candidate as absent and redraw the SAME prize.

        The rejected guest is permanently removed from the current draw
        session and cannot be selected again.
        """
        if self.draw_locked:
            yield rx.toast.warning(
                "Please wait until the current operation finishes."
            )
            return

        if self.draw_status != "CANDIDATE":
            yield rx.toast.warning(
                "There is no candidate to redraw."
            )
            return

        candidate_id = self._guest_id(
            self.pending_candidate
        )

        if not candidate_id:
            yield rx.toast.error(
                "Current candidate has no guest ID."
            )
            return

        # Permanently exclude this guest from the current draw session.
        if candidate_id not in self.excluded_guest_ids:
            self.excluded_guest_ids.append(candidate_id)

        # Also remove from the active in-memory pool.
        self.lucky_draw_eligible_guests = [
            guest
            for guest in self.lucky_draw_eligible_guests
            if self._guest_id(guest) != candidate_id
        ]

        self.pending_candidate = {}
        self.lucky_draw_winner = {}
        self.lucky_draw_current_name = ""
        self.lucky_draw_current_id = ""

        self.redraw_count += 1
        self.current_prize_redraw_count += 1

        self.draw_status = "REDRAW"

        yield rx.toast.info(
            "Candidate marked absent. Redrawing the same prize."
        )

        await asyncio.sleep(0.3)

        # The prize index intentionally does NOT change.
        async for update in self.draw_candidate():
            yield update

    async def proceed_to_next_prize(self):
        """
        Advance only after the current prize has an official winner.
        """
        # CONFIRMED is the safe boundary for this transition. An active
        # draw cannot legitimately be CONFIRMED, so a stale UI lock must
        # not block the operator from moving to the next prize.
        if self.draw_status != "CONFIRMED":
            yield rx.toast.warning(
                "The current prize must be confirmed before proceeding."
            )
            return

        next_index = self.current_prize_index + 1

        if next_index >= len(self.current_prizes):
            self.draw_status = "DONE"
            self.draw_finished = True
            self.waiting_for_next_prize = False

            yield rx.toast.success(
                "All prizes have been awarded."
            )
            return

        self.current_prize_index = next_index

        self.current_prize_redraw_count = 0
        self.pending_candidate = {}
        self.lucky_draw_winner = {}
        self.lucky_draw_current_name = ""
        self.lucky_draw_current_id = ""

        self.draw_status = "READY"
        self.waiting_for_next_prize = False

        prize = self.current_prizes[
            self.current_prize_index
        ]

        self.lucky_draw_prize_name = str(
            prize.get("name") or ""
        )

        self.lucky_draw_prize_value = str(
            prize.get("value") or ""
        )

        self.lucky_draw_prize_picture = str(
            prize.get("image_url") or ""
        )

        yield self.broadcast_lucky_draw_state()

        yield


    async def start_lucky_draw(self):
        """Start the draw animation for the current prize."""

        if self.draw_locked:
            yield rx.toast.warning(
                "A draw is already in progress."
            )
            return

        if self.draw_status not in {
            DRAW_IDLE,
            "READY",
            CONFIRMED,
            "REDRAW",
        }:
            yield rx.toast.warning(
                "The current draw cannot be started yet."
            )
            return

        # Normalize any supported prize upload source into current_prizes.
        if not self.current_prizes:
            source = (
                self.prize_list
                or self.multiple_prizes_list
                or self.excel_prizes_list
            )
            self.current_prizes = [
                dict(prize)
                for prize in (source or [])
                if isinstance(prize, dict)
                and str(prize.get("name") or "").strip()
            ]
            if self.current_prizes:
                self.current_prize_index = max(
                    0,
                    min(self.current_prize_index, len(self.current_prizes) - 1),
                )
                self._set_current_prize()

        if not self.current_prizes:
            yield rx.toast.error(
                "No prizes configured. Please configure at least one prize."
            )
            return

        if not (
                0 <= self.current_prize_index
                < len(self.current_prizes)
        ):
            yield rx.toast.error(
                "Invalid prize selection."
            )
            return

        if not self._available_draw_candidates():
            yield rx.toast.error(
                "No eligible guests available."
            )
            return

        self._set_current_prize()

        self.draw_locked = True
        self.draw_status = DRAWING
        self.lucky_draw_spinning = True
        self.lucky_draw_spinner_open = True

        self.pending_candidate = {}
        self.candidate_rejected = False
        self.waiting_for_next_prize = False

        self.draw_attempt += 1

        yield

        try:
            candidates = self._available_draw_candidates()

            if not candidates:
                raise RuntimeError(
                    "No eligible candidates remain."
                )

            # Presentation-only names. Final winner selection remains backend authoritative.
            shuffled = list(candidates)
            random.shuffle(shuffled)
            self.wheel_names = [
                str(guest.get("name") or "Guest")
                for guest in shuffled[:min(12, len(shuffled))]
            ]

            # Deliberately longer visual roll for a live audience.
            # The timing eases out so the roll starts quickly and slows
            # naturally before revealing the final candidate.
            animation_count = min(
                52,
                max(32, len(candidates) * 2),
            )

            for step in range(animation_count):
                guest = random.choice(candidates)

                self.lucky_draw_current_name = str(
                    guest.get("name") or ""
                )

                self.lucky_draw_current_id = (
                    self._guest_id(guest)
                )

                yield self.broadcast_lucky_draw_state()

                progress = step / max(1, animation_count - 1)
                delay = 0.045 + (0.18 * (progress ** 2))
                await asyncio.sleep(delay)

            # IMPORTANT:
            # _select_candidate() is an async generator.
            # It must NOT be awaited directly.
            async for update in self._select_candidate():
                yield update


        except Exception as exc:
            logger.exception(
                "Lucky Draw start failed for event %s",
                self.current_event_id,
            )

            self.draw_locked = False
            self.draw_status = READY
            self.lucky_draw_spinning = False
            self.lucky_draw_spinner_open = False

            yield rx.toast.error(
                f"Unable to start draw: {exc}"
            )


    async def _select_candidate(self):
        """
        Select one candidate without awarding the prize.

        This method is intentionally an async generator because the
        UI needs the state update after the candidate is selected.
        """

        available = self._available_draw_candidates()

        if not available:
            self.pending_candidate = {}
            self.lucky_draw_spinning = False
            self.draw_locked = False
            self.draw_status = DONE

            yield rx.toast.error(
                "No eligible guests remain for this prize."
            )
            return

        candidate = random.choice(available)

        candidate_id = self._guest_id(candidate)

        if not candidate_id:
            self.draw_locked = False
            self.draw_status = READY

            yield rx.toast.error(
                "Selected guest has no Guest ID."
            )
            return

        self.pending_candidate = dict(candidate)

        self.lucky_draw_current_name = str(
            candidate.get("name") or ""
        )

        self.lucky_draw_current_id = candidate_id

        self.lucky_draw_spinning = False
        self.draw_locked = False
        self.draw_status = CANDIDATE
        self.candidate_rejected = False

        yield self.broadcast_lucky_draw_state()
        yield

    async def confirm_candidate(self):
        """Confirm and persist the current candidate."""

        if self.draw_locked:
            yield rx.toast.warning(
                "Please wait for the current operation."
            )
            return

        if self.draw_status != CANDIDATE:
            yield rx.toast.warning(
                "There is no candidate awaiting confirmation."
            )
            return

        candidate = dict(
            self.pending_candidate
        )

        if not self._candidate_is_valid(candidate):
            self.pending_candidate = {}
            self.draw_status = REDRAW

            yield rx.toast.warning(
                "This candidate is no longer eligible. "
                "Please redraw."
            )
            return

        guest_id = self._guest_id(candidate)

        if not self.current_event_id:
            yield rx.toast.error(
                "No event selected."
            )
            return

        prize_name = str(
            self.lucky_draw_prize_name or ""
        ).strip()

        if not prize_name:
            yield rx.toast.error(
                "Prize name is required."
            )
            return

        self.draw_locked = True

        yield

        try:
            saved_winner = WinnerService().create(
                event_id=int(self.current_event_id),
                guest_id=guest_id,
                name=str(
                    candidate.get("name") or ""
                ).strip(),
                prize_name=prize_name,
                prize_value=str(
                    self.lucky_draw_prize_value or ""
                ).strip(),
                prize_image=str(
                    self.lucky_draw_prize_picture or ""
                ).strip(),
            )

        except ValueError as exc:

            self.draw_locked = False

            if "already won" in str(exc).lower():
                self.excluded_guest_ids.append(
                    guest_id
                )

                self.pending_candidate = {}
                self.candidate_rejected = True
                self.draw_status = REDRAW

                yield rx.toast.warning(
                    "This guest has already won. "
                    "Please redraw."
                )
                return

            self.draw_status = CANDIDATE

            yield rx.toast.error(
                str(exc)
            )
            return

        except Exception as exc:

            logger.exception(
                "Failed to confirm candidate %s "
                "for event %s",
                guest_id,
                self.current_event_id,
            )

            self.draw_locked = False
            self.draw_status = CANDIDATE

            yield rx.toast.error(
                f"Unable to confirm winner: {exc}"
            )
            return

        winner_record = {
            **candidate,
            **(saved_winner or {}),
            "prize_name": prize_name,
            "prize_value": str(
                self.lucky_draw_prize_value or ""
            ),
            "prize_image": str(
                self.lucky_draw_prize_picture or ""
            ),
        }

        # Database persistence succeeded.
        # Only now mutate local state.
        self.lucky_draw_winner = winner_record

        self.lucky_draw_current_name = str(
            candidate.get("name") or ""
        )

        self.lucky_draw_current_id = guest_id

        self.lucky_draw_eligible_guests = [
            guest
            for guest in self.lucky_draw_eligible_guests
            if self._guest_id(guest) != guest_id
        ]

        self.winners_list.insert(
            0,
            winner_record,
        )

        self.pending_candidate = {}
        self.redraw_count = 0
        self.lucky_draw_redraw_count = 0
        self.candidate_rejected = False

        self.draw_locked = False
        self.draw_status = CONFIRMED

        if (
                self.current_prize_index + 1
                < len(self.current_prizes)
        ):
            self.waiting_for_next_prize = True
            self.draw_finished = False
        else:
            self.waiting_for_next_prize = False
            self.draw_finished = True

        yield self.broadcast_lucky_draw_state()
        yield rx.toast.success(
            f"{candidate.get('name', 'Winner')} "
            f"won {prize_name}!"
        )

    async def reject_candidate_as_absent(self):
        """
        Mark the current candidate as absent.

        The candidate is permanently removed from the CURRENT
        draw pool, but no winner record is created.

        The same prize is immediately redrawn.
        """

        if self.draw_locked:
            yield rx.toast.warning(
                "Please wait for the current operation."
            )
            return

        if self.draw_status != CANDIDATE:
            yield rx.toast.warning(
                "There is no candidate to reject."
            )
            return

        candidate = dict(
            self.pending_candidate
        )

        if not candidate:
            yield rx.toast.error(
                "No candidate selected."
            )
            return

        guest_id = self._guest_id(candidate)

        if not guest_id:
            yield rx.toast.error(
                "Candidate has no Guest ID."
            )
            return

        # Prevent duplicates.
        if guest_id not in self.excluded_guest_ids:
            self.excluded_guest_ids.append(
                guest_id
            )

        self.lucky_draw_redraw_guest_id = guest_id
        self.lucky_draw_redraw_guest_name = str(
            candidate.get("name") or ""
        )

        # Remove from local candidate pool.
        self.lucky_draw_eligible_guests = [
            guest
            for guest in self.lucky_draw_eligible_guests
            if self._guest_id(guest) != guest_id
        ]

        self.pending_candidate = {}
        self.candidate_rejected = True

        self.redraw_count += 1
        self.lucky_draw_redraw_count = self.redraw_count
        self.draw_attempt += 1

        # IMPORTANT:
        # current_prize_index DOES NOT CHANGE.
        self.draw_status = REDRAW

        self.lucky_draw_winner = {}
        self.lucky_draw_current_name = ""
        self.lucky_draw_current_id = ""

        yield

        # Automatically redraw the SAME prize.
        async for update in self.start_lucky_draw():
            yield update

    async def advance_to_next_prize(self):
        """Move to the next prize after confirmation."""

        if self.draw_locked:
            yield rx.toast.warning(
                "Please finish the current operation first."
            )
            return

        if self.draw_status != CONFIRMED:
            yield rx.toast.warning(
                "Please confirm the current winner first."
            )
            return

        if not self.current_prizes:
            yield rx.toast.error(
                "No prizes configured."
            )
            return

        if (
                self.current_prize_index + 1
                >= len(self.current_prizes)
        ):
            self.draw_status = DONE
            self.draw_finished = True
            self.waiting_for_next_prize = False
            self.lucky_draw_spinner_open = False

            yield self.broadcast_lucky_draw_state()
            yield rx.toast.success(
                "All prizes have been awarded!"
            )


        self.draw_status = NEXT_PRIZE
        self.prize_transitioning = True
        self.waiting_for_next_prize = False

        self.pending_candidate = {}
        self.lucky_draw_winner = {}

        self.redraw_count = 0
        self.lucky_draw_redraw_count = 0

        yield

        await asyncio.sleep(0.4)

        self.current_prize_index += 1

        self._set_current_prize()

        self.prize_transitioning = False
        self.draw_status = READY

        self.lucky_draw_current_name = ""
        self.lucky_draw_current_id = ""

        # Clear the confirmed winner on the hall before the next draw starts,
        # while retaining winners_list as history.
        yield self.broadcast_lucky_draw_state()
        yield

    def close_lucky_draw_spinner(self):
        """Close the fullscreen spinning wheel dialog."""
        self.lucky_draw_spinner_open = False
        self.lucky_draw_spinning = False
        self.lucky_draw_winner = {}
        self.lucky_draw_current_name = ""
        self.lucky_draw_current_id = ""

        return rx.call_script("""
            if (window.opener) {
                window.close();
            } else {
                window.location.href = '/lucky-draw';
            }
        """)

    def close_spinner_and_open_new_draw(self):
        """Close spinner and open new draw dialog."""
        self.lucky_draw_spinner_open = False
        self.lucky_draw_spinning = False
        self.lucky_draw_winner = {}
        self.lucky_draw_current_name = ""
        self.lucky_draw_current_id = ""
        self.lucky_draw_show_new_draw_dialog = True


    def redirect_to_lucky_draw(self):
        """Redirect back to lucky draw setup page."""
        return rx.redirect(f"/lucky-draw")

    def broadcast_lucky_draw_state(self):
        """Broadcast live draw state to hall-screen tabs in the same browser."""
        import json

        payload = {
            "event_id": str(self.current_event_id or ""),
            "event_name": str(self.lucky_draw_event_name or ""),
            "prize_name": str(self.lucky_draw_prize_name or ""),
            "prize_value": str(self.lucky_draw_prize_value or ""),
            "prize_picture": str(self.lucky_draw_prize_picture or ""),
            "current_name": str(self.lucky_draw_current_name or ""),
            "current_id": str(self.lucky_draw_current_id or ""),
            "status": str(self.draw_status or ""),
            "spinning": bool(self.lucky_draw_spinning),
            "winners": [dict(w) for w in self.winners_list[:10] if isinstance(w, dict)],
            "prize_index": int(self.current_prize_index or 0),
            "prize_count": len(self.current_prizes),
            "wheel_names": [str(n) for n in self.wheel_names[:24]],
        }
        encoded = json.dumps(payload, ensure_ascii=False).replace("\\", "\\\\").replace("'", "\\'")
        return rx.call_script(
            f"(() => {{ const state = JSON.parse('{encoded}'); localStorage.setItem('eventlah-lucky-draw-state', JSON.stringify(state)); const c = new BroadcastChannel('eventlah-lucky-draw'); c.postMessage(state); c.close(); }})()"
        )

    def open_hall_screen(self):
        """Open the audience-only display in a separate browser window."""
        event_id = str(self.current_event_id or "").strip()
        if not event_id:
            return rx.toast.error("No Lucky Draw event selected.")
        open_script = rx.call_script(
            f"(() => {{ const w = window.open('/lucky-draw/external-display/{event_id}', 'eventlahLuckyDrawExternal', 'popup=yes,width=1600,height=1000,resizable=yes,scrollbars=no'); if (w) w.focus(); }})()"
        )
        return [open_script, self.broadcast_lucky_draw_state()]

    async def refresh_display_data(self):
        """Refresh authoritative winner history without resetting live draw state."""
        await self._fetch_display_data_from_api()

    async def _fetch_display_data_from_api(self):
        """
        Refresh authoritative display data without resetting the live
        draw lifecycle or current prize.

        The operator's live draw state remains authoritative while the
        display is open.
        """
        try:
            await self.load_winners()

        except Exception:
            logger.exception(
                "Unable to refresh live Lucky Draw winners "
                "for event %s",
                self.current_event_id,
            )

    async def load_lucky_draw_display_data(self):
        """
        Initialize the LIVE Lucky Draw display.

        The URL contains:
            event_id
            compact prize/session configuration

        Participant lists are loaded from the repository rather than
        placed into the URL.
        """
        import urllib.parse

        try:
            query_str = str(
                self.router.url.query or ""
            )

            if query_str.startswith("?"):
                query_str = query_str[1:]

            if not query_str:
                logger.warning(
                    "Live Lucky Draw display opened without query parameters."
                )
                yield rx.toast.error(
                    "No Lucky Draw session was provided."
                )
                return

            params = urllib.parse.parse_qs(
                query_str
            )

            event_id = str(
                params.get(
                    "event_id",
                    [""],
                )[0]
                or ""
            ).strip()

            data_param = params.get(
                "data",
                [None],
            )[0]

            if not event_id:
                yield rx.toast.error(
                    "No Lucky Draw event selected."
                )
                return

            # The display is now the same synchronized browser/state as the
            # operator screen.  Do not re-apply the URL payload on every route
            # lifecycle event; that would reset the current prize and candidate.
            if (
                str(self.current_event_id or "").strip() == event_id
                and self.current_prizes
            ):
                await self.load_winners()
                yield
                return

            self.current_event_id = event_id

            # ---------------------------------------------------------------
            # Decode the compact setup payload for direct display URLs.
            # ---------------------------------------------------------------
            if data_param:
                try:
                    padded = (
                            data_param
                            + (
                                    "="
                                    * (
                                            -len(data_param)
                                            % 4
                                    )
                            )
                    )

                    decoded = (
                        base64
                        .urlsafe_b64decode(
                            padded.encode("ascii")
                        )
                        .decode("utf-8")
                    )

                    data = json.loads(
                        decoded
                    )

                except Exception:
                    # Backward compatibility.
                    data = json.loads(
                        urllib.parse.unquote(
                            data_param
                        )
                    )

                # -----------------------------------------------------------
                # Prize configuration
                # -----------------------------------------------------------
                self.prize_mode = str(
                    data.get(
                        "prize_mode",
                        self.prize_mode,
                    )
                )

                self.current_prizes = [
                    dict(prize)
                    for prize in data.get(
                        "current_prizes",
                        [],
                    )
                    if isinstance(
                        prize,
                        dict,
                    )
                       and str(
                        prize.get("name")
                        or ""
                    ).strip()
                ]

                if not self.current_prizes:
                    yield rx.toast.error(
                        "No prizes are configured for this Lucky Draw."
                    )
                    return

                # -----------------------------------------------------------
                # Current prize
                # -----------------------------------------------------------
                try:
                    self.current_prize_index = int(
                        data.get(
                            "current_prize_index",
                            0,
                        )
                        or 0
                    )
                except (
                        TypeError,
                        ValueError,
                ):
                    self.current_prize_index = 0

                self.current_prize_index = max(
                    0,
                    min(
                        self.current_prize_index,
                        len(
                            self.current_prizes
                        ) - 1,
                    ),
                )

                # -----------------------------------------------------------
                # Event information
                # -----------------------------------------------------------
                self.current_event_id = str(
                    data.get(
                        "current_event_id",
                        self.current_event_id,
                    )
                    or self.current_event_id
                )

                self.lucky_draw_event_name = str(
                    data.get(
                        "current_event_name",
                        self.lucky_draw_event_name,
                    )
                    or self.lucky_draw_event_name
                )

                event_type = str(
                    data.get(
                        "event_type",
                        "",
                    )
                    or ""
                ).strip().lower()

                if event_type in EVENT_TYPES:
                    self.lucky_draw_event_type = (
                        event_type
                    )

                    if event_type == "lucky_draw":
                        self.lucky_draw_only_present = False

                else:
                    self.lucky_draw_only_present = bool(
                        data.get(
                            "lucky_draw_only_present",
                            self.lucky_draw_only_present,
                        )
                    )

                self.lucky_draw_excluded = str(
                    data.get(
                        "lucky_draw_excluded",
                        self.lucky_draw_excluded,
                    )
                    or self.lucky_draw_excluded
                )

                # -----------------------------------------------------------
                # Existing winners
                # -----------------------------------------------------------
                self.winners_list = [
                    dict(winner)
                    for winner in data.get(
                        "winners",
                        [],
                    )
                    if isinstance(
                        winner,
                        dict,
                    )
                ]

                # Keep the compatibility prize lists synchronized.
                self.prize_list = [
                    dict(prize)
                    for prize in self.current_prizes
                ]

                self.excel_prizes_list = [
                    dict(prize)
                    for prize in self.current_prizes
                ]

                # Synchronize:
                # lucky_draw_prize_name
                # lucky_draw_prize_value
                # lucky_draw_prize_picture
                self._set_current_prize()

            # ---------------------------------------------------------------
            # Load authoritative winner history only.
            # ---------------------------------------------------------------
            await self._fetch_display_data_from_api()

            yield

        except Exception as exc:
            logger.exception(
                "Unable to initialize live Lucky Draw display "
                "for event %s",
                self.current_event_id,
            )

            yield rx.toast.error(
                f"Unable to load Lucky Draw display: {exc}"
            )

    async def clear_pre_draw_winners(self):
        """Clear the persisted pre-draw winner list for the current event."""
        if not self.current_event_id:
            yield rx.toast.error("No Lucky Draw event selected.")
            return

        try:
            event_id = int(self.current_event_id)

            PreDrawWinnerService().delete_by_event(event_id)

            self.pre_draw_winners = []
            self.pre_draw_winner_filename = ""
            self.pre_draw_winner_selected_file_name = ""
            self._pre_draw_winner_file_content = b""
            self._pre_draw_winner_filename = ""

            self.predraw_page = 0
            self._rebuild_pre_draw_display_rows()

            yield rx.toast.success("Pre-draw winner list cleared.")

        except Exception as exc:
            logger.exception(
                "Unable to clear pre-draw winners for event %s",
                self.current_event_id,
            )
            yield rx.toast.error(
                f"Unable to clear pre-draw winner list: {exc}"
            )

    def start_new_draw(self):
        """Reset the complete draw session and return to the dashboard."""
        self.reset_draw_lifecycle()
        self.lucky_draw_setup_complete = False
        self.lucky_draw_ready = False
        self.lucky_draw_prize_name = ""
        self.lucky_draw_prize_value = ""
        self.lucky_draw_prize_picture = ""
        self.prize_list = []
        self.multiple_prizes_list = []
        self.excel_prizes_list = []
        self.excel_filename = ""
        self.prize_selected_file_name = ""
        self._prize_file_content = b""
        self._prize_filename = ""
        self.lucky_draw_excluded = ""
        self.lucky_draw_only_present = self.lucky_draw_event_type != "lucky_draw"
        self.lucky_draw_show_new_draw_dialog = False
        self.current_prizes = []
        self.current_prize_index = 0
        self.drawn_winners = []
        return rx.redirect(f"/dashboard/{self.current_event_id}")