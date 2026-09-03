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
from ..state.guest_state import GuestState
from ..utils.constants import EVENT_TYPES
from ..state.auth_state import AuthState
from ..repositories import EventRepository, GuestRepository
from ..services.excel_service import ExcelService




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

    # Guests
    lucky_draw_only_present: bool = True
    lucky_draw_excluded: str = ""
    lucky_draw_eligible_guests: List[Dict[str, Any]] = []

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
    prize_excel_filename: str = ""
    lucky_draw_spinner_open: bool = False
    lucky_draw_show_new_draw_dialog: bool = False
    show_clear_confirm: bool = False

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

            event = EventRepository().get_by_id(
                event_id,
                auth.user_id,
            )

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

    async def redraw_missing_candidate(self):
        """
        Reject the current candidate because they are not present,
        then select another candidate for the SAME prize.

        The prize does not advance.
        The rejected guest cannot be selected again during this session.
        """

        if self.draw_status != "CANDIDATE":
            yield rx.toast.error(
                "There is no candidate awaiting confirmation."
            )
            return

        candidate = dict(self.pending_candidate or {})

        if not candidate:
            yield rx.toast.error(
                "No pending candidate to redraw."
            )
            return

        guest_id = self._guest_id(candidate)

        if not guest_id:
            yield rx.toast.error(
                "Candidate has no guest ID."
            )
            return

        # ------------------------------------------------------------
        # Reject current candidate.
        # ------------------------------------------------------------

        self._exclude_guest_for_redraw(
            candidate,
            reason="absent",
        )

        logger.info(
            "Lucky Draw redraw requested: event=%s prize=%s "
            "excluded_guest=%s redraw_count=%s",
            self.current_event_id,
            self.lucky_draw_prize_name,
            guest_id,
            self.redraw_count,
        )

        # Clear the current candidate before selecting another one.
        self.pending_candidate = {}
        self.lucky_draw_winner = {}
        self.lucky_draw_current_name = ""
        self.lucky_draw_current_id = ""

        self.draw_status = "REDRAW"
        self.lucky_draw_spinning = False

        yield

        # ------------------------------------------------------------
        # Find another candidate.
        # ------------------------------------------------------------

        candidates = self._available_draw_candidates()

        if not candidates:
            self.draw_status = "NO_CANDIDATES"
            self.lucky_draw_spinner_open = False
            self.waiting_for_next_prize = False

            logger.warning(
                "Lucky Draw has no candidates after redraw: "
                "event=%s prize=%s",
                self.current_event_id,
                self.lucky_draw_prize_name,
            )

            yield rx.toast.error(
                "No eligible guests remain for this prize."
            )
            return

        # ------------------------------------------------------------
        # Randomly select a replacement.
        # ------------------------------------------------------------

        candidate = random.choice(candidates)

        self.pending_candidate = dict(candidate)

        self.lucky_draw_current_name = str(
            candidate.get("name")
            or candidate.get("Name")
            or ""
        )

        self.lucky_draw_current_id = self._guest_id(candidate)

        self.draw_status = "CANDIDATE"
        self.lucky_draw_spinning = False
        self.lucky_draw_spinner_open = True

        logger.info(
            "Lucky Draw replacement candidate selected: "
            "event=%s prize=%s guest=%s redraw_count=%s",
            self.current_event_id,
            self.lucky_draw_prize_name,
            self.lucky_draw_current_id,
            self.redraw_count,
        )

        yield rx.toast.success(
            "New candidate selected. Please verify their presence."
        )

        yield

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
        from guest_management.state.auth_state import AuthState

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
    lucky_draw_event_name: str = ""

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
            try:
                from guest_management.services.excel_service_ranked import ExcelService
            except ImportError:


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

            self.excel_prizes_list = [dict(prize) for prize in prizes]
            self.excel_filename = self._prize_filename
            self.prize_list = [dict(prize) for prize in prizes]

            if self.prize_mode == "excel":
                self.current_prizes = prizes.copy()
                self.current_prize_index = 0

                first_prize = prizes[0]

                self.lucky_draw_prize_name = first_prize.get(
                    "name",
                    "",
                )
                self.lucky_draw_prize_value = first_prize.get(
                    "value",
                    "",
                )
                self.lucky_draw_prize_picture = first_prize.get(
                    "image_url",
                    "",
                )

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
        self.excel_prizes_list = []
        self.excel_filename = ""
        if self.prize_mode == "excel":
            self.current_prizes = []
            self.lucky_draw_prize_name = ""
            self.lucky_draw_prize_value = ""
            self.lucky_draw_prize_picture = ""

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
            self.is_loading = False
            self.show_clear_confirm = False

            guest_state = await self.get_state(GuestState)
            guest_state.load_lucky_draw_eligible_guests()

            yield rx.toast.success(
                "Winners history cleared!"
            )

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

    def _normalise_guest_id(self, guest: Dict[str, Any]) -> str:
        """Return a stable guest ID."""
        return str(
            guest.get("guest_id")
            or guest.get("Guest ID")
            or guest.get("id")
            or ""
        ).strip()

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

        guest_id = str(guest_id).strip()

        # Already excluded because absent/redrawn.
        if guest_id in {
            str(value).strip()
            for value in self.excluded_guest_ids
        }:
            return False

        # Already a winner.
        winner_ids = {
            str(winner.get("guest_id") or "").strip()
            for winner in self.winners_list
            if str(winner.get("guest_id") or "").strip()
        }

        if guest_id in winner_ids:
            return False

        # Current pending candidate is valid only when explicitly
        # being validated for confirmation.
        return True

    def _reset_candidate_state(self):
        """Clear the current pending candidate."""
        self.pending_candidate = {}
        self.lucky_draw_winner = {}
        self.lucky_draw_current_name = ""
        self.lucky_draw_current_id = ""

    async def setup_complete_and_go_to_display(self):
        """
        Finalise setup and open the dedicated lucky draw display.

        This method deliberately does not start the draw. It only transitions
        the session from setup to READY.
        """
        if not self.current_event_id:
            yield rx.toast.error("No event selected.")
            return

        if not self.current_prizes:
            # Build the prize list from the selected input mode.
            if self.prize_mode == "single":
                if not self.single_prize_name.strip():
                    yield rx.toast.error("Please set a prize first.")
                    return

                self.current_prizes = [{
                    "name": self.single_prize_name.strip(),
                    "value": self.single_prize_value.strip(),
                    "image_url": self.single_prize_picture.strip(),
                }]

            elif self.prize_mode == "multiple":
                if not self.multiple_prizes_list:
                    yield rx.toast.error("Please add at least one prize.")
                    return

                self.current_prizes = [
                    dict(prize)
                    for prize in self.multiple_prizes_list
                    if str(prize.get("name") or "").strip()
                ]

            elif self.prize_mode == "excel":
                if not self.excel_prizes_list:
                    yield rx.toast.error(
                        "Please upload the prize Excel file."
                    )
                    return

                self.current_prizes = [
                    dict(prize)
                    for prize in self.excel_prizes_list
                    if str(prize.get("name") or "").strip()
                ]

        if not self.current_prizes:
            yield rx.toast.error("No valid prizes configured.")
            return

        # Refresh immediately before opening the display so Company Dinner and
        # Sports Day use the latest event-day attendance. Standalone Lucky Draw
        # remains independent of check-in because initialize_lucky_draw_event()
        # sets lucky_draw_only_present=False for that event type.
        await self.load_lucky_draw_eligible_guests()

        if not self.lucky_draw_eligible_guests:
            yield rx.toast.error(
                "No eligible guests available for the lucky draw."
            )
            return

        self.current_prize_index = 0
        self.redraw_count = 0
        self.current_prize_redraw_count = 0
        self.excluded_guest_ids = []
        self._reset_candidate_state()

        self.draw_locked = False
        self.draw_status = "READY"
        self.lucky_draw_setup_complete = True

        first_prize = self.current_prizes[0]

        self.lucky_draw_prize_name = str(
            first_prize.get("name") or ""
        )

        self.lucky_draw_prize_value = str(
            first_prize.get("value") or ""
        )

        self.lucky_draw_prize_picture = str(
            first_prize.get("image_url") or ""
        )

        yield rx.redirect(
            f"/lucky-draw/display/{self.current_event_id}"
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

        self.lucky_draw_current_id = self._normalise_guest_id(candidate)

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

        candidate_id = self._normalise_guest_id(
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
            if self._normalise_guest_id(guest) != candidate_id
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
        if self.draw_locked:
            yield rx.toast.warning(
                "The draw is currently locked."
            )
            return

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

        yield

    def reset_draw_lifecycle(self):
        """
        Reset only the live draw lifecycle.

        Prize configuration is intentionally preserved.
        """
        self.draw_status = "IDLE"
        self.pending_candidate = {}
        self.redraw_count = 0
        self.current_prize_redraw_count = 0
        self.excluded_guest_ids = []
        self.draw_locked = False

        self.lucky_draw_spinning = False
        self.lucky_draw_winner = {}
        self.lucky_draw_current_name = ""
        self.lucky_draw_current_id = ""

        self.current_prize_index = 0
        self.draw_finished = False
        self.waiting_for_next_prize = False

    async def start_lucky_draw(self):
        """Start the draw animation for the current prize."""

        if self.draw_locked:
            yield rx.toast.warning(
                "A draw is already in progress."
            )
            return

        if self.draw_status not in {
            IDLE,
            READY,
            CONFIRMED,
            REDRAW,
        }:
            yield rx.toast.warning(
                "The current draw cannot be started yet."
            )
            return

        if not self.current_prizes:
            yield rx.toast.error(
                "No prizes configured."
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

            # Run a short, visually engaging name-roll animation.
            # The timing eases out so the roll starts quickly and slows
            # naturally before revealing the final candidate.
            animation_count = min(
                30,
                max(12, len(candidates)),
            )

            for step in range(animation_count):
                guest = random.choice(candidates)

                self.lucky_draw_current_name = str(
                    guest.get("name") or ""
                )

                self.lucky_draw_current_id = (
                    self._guest_id(guest)
                )

                yield

                progress = step / max(1, animation_count - 1)
                delay = 0.04 + (0.20 * (progress ** 2))
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

    async def draw_candidate(self):
        """
        Public lifecycle handler.

        Starts the current prize draw and leaves the result in
        CANDIDATE state. No winner is persisted here.
        """

        async for update in self.start_lucky_draw():
            yield update

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

            yield rx.toast.success(
                "All prizes have been awarded!"
            )
            return

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

    async def setup_complete_and_go_to_display(self):
        """Complete setup and open the live display."""

        if not self.current_event_id:
            yield rx.toast.error(
                "No event selected."
            )
            return

        if not self.lucky_draw_eligible_guests:
            await self.load_lucky_draw_eligible_guests()

        if not self.lucky_draw_eligible_guests:
            yield rx.toast.error(
                "No eligible guests available."
            )
            return

        if not self.current_prizes:
            yield rx.toast.error(
                "No prizes configured."
            )
            return

        self.current_prize_index = 0

        self.reset_draw_lifecycle()

        self._set_current_prize()

        self.lucky_draw_setup_complete = True
        self.draw_status = READY

        logger.info(
            "Lucky Draw setup completed for event %s",
            self.current_event_id,
        )

        yield rx.toast.success(
            "Lucky Draw is ready."
        )

        display_payload = {
            "prize_mode": self.prize_mode,
            "current_prizes": self.current_prizes,
            "current_prize_index": self.current_prize_index,
            "lucky_draw_excluded": self.lucky_draw_excluded,
            "lucky_draw_only_present": self.lucky_draw_only_present,
            "current_event_id": self.current_event_id,
            "current_event_name": self.lucky_draw_event_name,
            "event_type": str(
                (self.current_event or {}).get("event_type") or ""
            ),
        }
        payload_json = json.dumps(
            display_payload,
            ensure_ascii=False,
            separators=(",", ":"),
        )
        payload_b64 = base64.urlsafe_b64encode(
            payload_json.encode("utf-8")
        ).decode("ascii").rstrip("=")

        yield rx.call_script(
            f"""
            window.open(
                '/lucky-draw-display?event_id={int(self.current_event_id)}&data={payload_b64}',
                '_blank'
            );
            """
        )

    def redirect_to_lucky_draw(self):
        """Redirect back to lucky draw setup page."""
        return rx.redirect(f"/lucky-draw")

    async def _fetch_display_data_from_api(self):
        """Load display-side participant/winner data from authoritative services."""
        try:
            await self.load_lucky_draw_eligible_guests()
            await self.load_winners()
        except Exception:
            logger.exception(
                "Unable to load fallback lucky draw display data for event %s",
                self.current_event_id,
            )

    async def load_lucky_draw_display_data(self):
        """Initialize the live display from the compact URL payload.

        The payload contains configuration only. Participant lists are loaded
        from the repository, avoiding enormous URLs for 500-4000 guests.
        """
        import urllib.parse

        query_str = str(self.router.url.query or "")
        if query_str.startswith("?"):
            query_str = query_str[1:]

        if query_str:
            params = urllib.parse.parse_qs(query_str)
            event_id = params.get("event_id", [""])[0]
            data_param = params.get("data", [None])[0]

            if event_id:
                self.current_event_id = str(event_id)

            if data_param:
                try:
                    padded = data_param + ("=" * (-len(data_param) % 4))
                    try:
                        decoded = base64.urlsafe_b64decode(padded.encode("ascii")).decode("utf-8")
                        data = json.loads(decoded)
                    except Exception:
                        # Backward compatibility with the previous URL format.
                        data = json.loads(urllib.parse.unquote(data_param))

                    self.prize_mode = str(data.get("prize_mode", self.prize_mode))
                    self.current_prizes = [
                        dict(prize)
                        for prize in data.get("current_prizes", [])
                        if isinstance(prize, dict)
                    ]
                    self.current_prize_index = int(data.get("current_prize_index", 0) or 0)
                    self.lucky_draw_excluded = str(data.get("lucky_draw_excluded", "") or "")
                    event_type = str(data.get("event_type", "") or "").strip().lower()
                    if event_type in EVENT_TYPES:
                        self.lucky_draw_event_type = event_type
                        if event_type == "lucky_draw":
                            self.lucky_draw_only_present = False
                    else:
                        self.lucky_draw_only_present = bool(
                            data.get("lucky_draw_only_present", self.lucky_draw_only_present)
                        )
                    self.current_event_id = str(
                        data.get("current_event_id", self.current_event_id) or self.current_event_id)
                    self.lucky_draw_event_name = str(data.get("current_event_name", "") or "")
                    self.winners_list = [
                        dict(w) for w in data.get("winners", []) if isinstance(w, dict)
                    ]

                    self.current_prize_index = max(
                        0,
                        min(
                            self.current_prize_index,
                            max(0, len(self.current_prizes) - 1),
                        ),
                    )
                    self.prize_list = [dict(prize) for prize in self.current_prizes]
                    self.excel_prizes_list = [dict(prize) for prize in self.current_prizes]
                    self._set_current_prize()

                except Exception as exc:
                    logger.warning("Failed to parse live display payload: %s", exc)

        await self._fetch_display_data_from_api()
        yield

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