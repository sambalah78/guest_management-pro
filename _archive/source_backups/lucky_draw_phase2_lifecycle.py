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
from guest_management.services.winner_service import WinnerService
from guest_management.state.guest_state import GuestState
logger = logging.getLogger(__name__)


class LuckyDrawState(rx.State):
    """Lucky draw management state."""

    # Setup
    lucky_draw_ready: bool = False
    lucky_draw_event_name: str = ""
    current_event_id: str = ""
    current_event: Optional[Dict[str, Any]] = None

    # Guests
    lucky_draw_only_present: bool = True
    lucky_draw_excluded: str = ""
    lucky_draw_eligible_guests: List[Dict[str, Any]] = []

    # Draw state
    lucky_draw_spinning: bool = False
    lucky_draw_current_name: str = ""
    lucky_draw_current_id: str = ""
    lucky_draw_winner: Dict[str, Any] = {}

    # Production draw lifecycle
    # IDLE -> DRAWING -> CANDIDATE -> CONFIRMED/REDRAW -> NEXT_PRIZE/DONE
    draw_status: str = "IDLE"
    pending_candidate: Dict[str, Any] = {}
    redraw_count: int = 0
    draw_locked: bool = False

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

    async def set_lucky_draw_only_present(self, value: bool):
        """Update the Lucky Draw eligibility filter."""
        value = bool(value)

        self.lucky_draw_only_present = value

        from guest_management.state.guest_state import GuestState

        guest_state = await self.get_state(GuestState)

        guest_state.lucky_draw_only_present = value
        guest_state.load_lucky_draw_eligible_guests()

        self.lucky_draw_eligible_guests = list(
            guest_state.lucky_draw_eligible_guests
        )

        yield
        
    async def set_lucky_draw_excluded(self, value: str):
        """Update the Lucky Draw exclusion filter."""
        value = str(value or "").strip()

        self.lucky_draw_excluded = value

        from guest_management.state.guest_state import GuestState

        guest_state = await self.get_state(GuestState)

        guest_state.lucky_draw_excluded = value
        guest_state.load_lucky_draw_eligible_guests()

        self.lucky_draw_eligible_guests = list(
            guest_state.lucky_draw_eligible_guests
        )

        yield

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
            self.current_prizes = [
                dict(prize)
                for prize in self.multiple_prizes_list
                if str(prize.get("name") or "").strip()
            ]

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
            from guest_management.services.excel_service import ExcelService

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

            self.excel_prizes_list = prizes.copy()
            self.excel_filename = self._prize_filename

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
            await guest_state.load_lucky_draw_eligible_guests()

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
        """Persist a confirmed Lucky Draw winner.

        This method is deliberately the only state-level path that turns a
        selected candidate into an official winner. The draw animation itself
        never writes to the winners table.
        """
        from datetime import datetime

        if self.draw_status != "CANDIDATE":
            yield rx.toast.error("No candidate is waiting for confirmation.")
            return

        if not winner:
            yield rx.toast.error("No winner candidate selected.")
            return

        guest_id = str(winner.get("guest_id") or "").strip()
        name = str(winner.get("name") or "").strip()
        if not guest_id or not name:
            yield rx.toast.error("Winner candidate is missing required information.")
            return

        prize_name = str(self.lucky_draw_prize_name or "").strip()
        prize_value = str(self.lucky_draw_prize_value or "").strip()
        prize_image = str(self.lucky_draw_prize_picture or "").strip()

        if not self.current_event_id:
            yield rx.toast.error("No event selected.")
            return
        if not prize_name:
            yield rx.toast.error("Prize name is required.")
            return

        try:
            saved_winner = WinnerService().create(
                event_id=int(self.current_event_id),
                guest_id=guest_id,
                name=name,
                prize_name=prize_name,
                prize_value=prize_value,
                prize_image=prize_image,
            )

            winner_record = {
                **winner,
                **(saved_winner or {}),
                "prize_name": prize_name,
                "prize_value": prize_value,
                "prize_image": prize_image,
                "formatted_date": datetime.now().strftime("%H:%M:%S"),
            }

            self.winners_list.insert(0, winner_record)
            winner_guest_id = guest_id
            self.lucky_draw_eligible_guests = [
                guest for guest in self.lucky_draw_eligible_guests
                if str(guest.get("guest_id") or "").strip() != winner_guest_id
            ]

            self.lucky_draw_winner = winner_record
            self.pending_candidate = {}
            self.lucky_draw_current_name = name
            self.lucky_draw_current_id = guest_id
            self.lucky_draw_spinning = False
            self.draw_locked = False
            self.draw_status = "CONFIRMED"
            self.waiting_for_next_prize = (
                self.current_prize_index + 1 < len(self.current_prizes)
            )

            await self.load_winners()
            yield rx.toast.success(f"Winner confirmed: {name}")
            yield

        except ValueError as exc:
            self.draw_locked = False
            yield rx.toast.error(str(exc))
        except Exception as exc:
            logger.exception("Error finalizing winner %s for event %s", guest_id, self.current_event_id)
            self.draw_locked = False
            yield rx.toast.error(f"Unable to save winner: {exc}")

    async def confirm_current_winner(self):
        """Confirm the currently displayed candidate as the official winner."""
        if not self.pending_candidate:
            yield rx.toast.error("No candidate selected.")
            return
        async for update in self.finalize_winner(dict(self.pending_candidate)):
            yield update

    async def draw_current_prize(self):
        """Run the animation and select a candidate for the current prize.

        IMPORTANT: selecting a candidate does not create a winner record.
        The operator must explicitly confirm or redraw.
        """
        if self.draw_locked:
            yield rx.toast.warning("A draw is already in progress.")
            return

        if self.current_prize_index >= len(self.current_prizes):
            self.draw_status = "DONE"
            self.lucky_draw_spinner_open = False
            yield rx.toast.success("All prizes have been completed.")
            return

        if not self.lucky_draw_eligible_guests:
            self.draw_status = "DONE"
            yield rx.toast.error("No eligible guests remain for this draw.")
            return

        prize = self.current_prizes[self.current_prize_index]
        self.lucky_draw_prize_name = str(prize.get("name", ""))
        self.lucky_draw_prize_value = str(prize.get("value", ""))
        self.lucky_draw_prize_picture = str(prize.get("image_url", ""))

        self.draw_locked = True
        self.draw_status = "DRAWING"
        self.pending_candidate = {}
        self.lucky_draw_winner = {}
        self.waiting_for_next_prize = False
        self.lucky_draw_spinner_open = True
        self.lucky_draw_spinning = True
        yield

        try:
            candidates = list(self.lucky_draw_eligible_guests)
            for _ in range(35):
                if not candidates:
                    break
                guest = random.choice(candidates)
                self.lucky_draw_current_name = str(guest.get("name", ""))
                self.lucky_draw_current_id = str(guest.get("guest_id", ""))
                yield
                await asyncio.sleep(0.07)

            if not candidates:
                self.draw_locked = False
                self.lucky_draw_spinning = False
                self.lucky_draw_spinner_open = False
                self.draw_status = "READY"
                yield rx.toast.error("No eligible guests remain.")
                return

            candidate = random.choice(candidates)
            self.pending_candidate = dict(candidate)
            self.lucky_draw_current_name = str(candidate.get("name", ""))
            self.lucky_draw_current_id = str(candidate.get("guest_id", ""))
            self.lucky_draw_winner = dict(candidate)
            self.lucky_draw_spinning = False
            self.draw_status = "CANDIDATE"
            # Keep locked until Confirm or Redraw is pressed.
            yield rx.toast.info("Candidate selected. Confirm presence or redraw.")
            yield

        except Exception as exc:
            logger.exception("Lucky Draw selection error for event %s", self.current_event_id)
            self.draw_locked = False
            self.lucky_draw_spinning = False
            self.lucky_draw_spinner_open = False
            self.draw_status = "READY"
            yield rx.toast.error(f"Error: {exc}")

    async def redraw_current_candidate(self):
        """Mark the displayed candidate absent and redraw the SAME prize."""
        if self.draw_status != "CANDIDATE" or not self.pending_candidate:
            yield rx.toast.error("There is no candidate to redraw.")
            return

        guest_id = str(self.pending_candidate.get("guest_id") or "").strip()
        if not guest_id:
            yield rx.toast.error("Candidate has no guest ID.")
            return

        # Remove only from the active in-memory pool. Never create a winner.
        self.lucky_draw_eligible_guests = [
            guest for guest in self.lucky_draw_eligible_guests
            if str(guest.get("guest_id") or "").strip() != guest_id
        ]

        self.redraw_count += 1
        self.pending_candidate = {}
        self.lucky_draw_winner = {}
        self.lucky_draw_current_name = ""
        self.lucky_draw_current_id = ""
        self.lucky_draw_spinning = False
        self.lucky_draw_spinner_open = False
        self.waiting_for_next_prize = False
        self.draw_locked = False
        self.draw_status = "READY"

        yield rx.toast.info("Candidate marked absent. Redrawing the same prize.")
        yield

        async for update in self.draw_current_prize():
            yield update

    async def draw_next_prize(self):
        """Advance only after the current prize has been confirmed."""
        if self.draw_status != "CONFIRMED":
            yield rx.toast.warning("Confirm the current winner before moving to the next prize.")
            return
        if self.current_prize_index + 1 >= len(self.current_prizes):
            await self.load_winners()
            self.lucky_draw_spinner_open = False
            self.waiting_for_next_prize = False
            yield rx.toast.success(f"All {len(self.current_prizes)} prizes awarded!")
            return

        self._prize_transitioning = True
        yield

        await asyncio.sleep(0.4)

        self.lucky_draw_winner = None
        self.lucky_draw_spinner_open = False
        self.lucky_draw_spinning = False

        self.current_prize_index += 1

        prize = self.current_prizes[self.current_prize_index]
        self.lucky_draw_prize_name = prize.get("name", "")
        self.lucky_draw_prize_value = prize.get("value", "")
        self.lucky_draw_prize_picture = prize.get("image_url", "")

        self.lucky_draw_winner = None
        self._prize_transitioning = False
        yield

        await asyncio.sleep(0.2)

        async for update in self.draw_current_prize():
            yield update

    async def show_next_prize(self):
        """Show next prize image."""
        if self.current_prize_index + 1 >= len(self.current_prizes):
            return

        self._prize_transitioning = True
        yield

        await asyncio.sleep(0.6)

        self.current_prize_index += 1
        prize = self.current_prizes[self.current_prize_index]

        self.lucky_draw_prize_name = prize.get("name", "")
        self.lucky_draw_prize_value = prize.get("value", "")
        self.lucky_draw_prize_picture = prize.get("image_url", "")

        self._prize_transitioning = False
        yield

        self.lucky_draw_winner = {}
        self.lucky_draw_spinner_open = False
        self.waiting_for_next_prize = False
        yield

    async def start_lucky_draw(self):
        """Start the lucky draw animation."""
        if not self.lucky_draw_eligible_guests:
            yield rx.toast.error("No eligible guests for lucky draw!")
            return

        if self.prize_mode == "single" and not self.lucky_draw_prize_name:
            yield rx.toast.error("Please set a prize name first!")
            return

        if self.prize_mode == "multiple" and not self.prize_list:
            yield rx.toast.error("Please add prizes first!")
            return

        self._prize_transitioning = False

        if self.prize_mode == "single":
            self.current_prizes = [{
                "name": self.lucky_draw_prize_name,
                "value": self.lucky_draw_prize_value,
                "image_url": self.lucky_draw_prize_picture
            }]
        else:
            self.current_prizes = self.prize_list.copy()

        self.current_prize_index = 0
        self.drawn_winners = []
        self.waiting_for_next_prize = False
        self.pending_candidate = {}
        self.redraw_count = 0
        self.draw_locked = False
        self.draw_status = "READY"

        if self.current_prizes:
            first_prize = self.current_prizes[0]
            self.lucky_draw_prize_name = first_prize.get("name", "")
            self.lucky_draw_prize_value = first_prize.get("value", "")
            self.lucky_draw_prize_picture = first_prize.get("image_url", "")

        async for update in self.draw_current_prize():
            yield update

        yield

    def close_lucky_draw_spinner(self):
        """Close the fullscreen spinning wheel dialog."""
        self.lucky_draw_spinner_open = False
        self.lucky_draw_spinning = False
        self.lucky_draw_winner = None
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
        self.lucky_draw_winner = None
        self.lucky_draw_current_name = ""
        self.lucky_draw_current_id = ""
        self.lucky_draw_show_new_draw_dialog = True

    async def setup_complete_and_go_to_display(self):
        """Mark Lucky Draw setup as complete and open the attendee display screen."""

        if not self.current_event_id:
            yield rx.toast.error("No event selected.")
            return

        if not self.lucky_draw_eligible_guests:
            yield rx.toast.error("No eligible guests available.")
            return

        if not self.current_prizes:
            # Build the prize list from the selected prize mode.
            if self.prize_mode == "single":
                if not self.single_prize_name.strip():
                    yield rx.toast.error("Please set a prize name first.")
                    return

                self.current_prizes = [{
                    "name": self.single_prize_name,
                    "value": self.single_prize_value,
                    "image_url": self.single_prize_picture,
                }]

            elif self.prize_mode == "multiple":
                if not self.multiple_prizes_list:
                    yield rx.toast.error("Please add at least one prize.")
                    return

                self.current_prizes = [
                    dict(prize)
                    for prize in self.multiple_prizes_list
                ]

            elif self.prize_mode == "excel":
                if not self.excel_prizes_list:
                    yield rx.toast.error(
                        "Please upload and process the prize Excel file first."
                    )
                    return

                self.current_prizes = [
                    dict(prize)
                    for prize in self.excel_prizes_list
                ]

        if not self.current_prizes:
            yield rx.toast.error("No prizes configured.")
            return

        self.current_prize_index = 0
        self.drawn_winners = []
        self.lucky_draw_winner = {}
        self.pending_candidate = {}
        self.redraw_count = 0
        self.draw_locked = False
        self.draw_status = "READY"
        self.lucky_draw_spinning = False
        self.lucky_draw_spinner_open = False
        self.waiting_for_next_prize = False
        self.prize_transitioning = False

        first_prize = self.current_prizes[0]

        self.lucky_draw_prize_name = str(
            first_prize.get("name", "")
        )
        self.lucky_draw_prize_value = str(
            first_prize.get("value", "")
        )
        self.lucky_draw_prize_picture = str(
            first_prize.get("image_url", "")
        )

        self.lucky_draw_setup_complete = True

        logger.info(
            "Lucky Draw setup completed for event %s; "
            "opening display screen.",
            self.current_event_id,
        )

        yield

        yield rx.call_script(
            f"""
            window.open(
                '/lucky-draw-display?event_id={int(self.current_event_id)}',
                '_blank'
            );
            """
        )

    def redirect_to_lucky_draw(self):
        """Redirect back to lucky draw setup page."""
        return rx.redirect(f"/lucky-draw")

    async def load_lucky_draw_display_data(self):
        """Load data from URL parameter (no JavaScript state issues)"""

        import urllib.parse
        import json

        # Get data from URL query parameter
        query_str = self.router.url.query

        if query_str:
            if query_str.startswith('?'):
                query_str = query_str[1:]
            params = urllib.parse.parse_qs(query_str)
            data_param = params.get("data", [None])[0]

            if data_param:
                try:
                    # Decode and parse the JSON data
                    data = json.loads(urllib.parse.unquote(data_param))

                    # Apply all settings directly to state
                    self.prize_mode = data.get("prize_mode", "single")
                    self.current_prizes = data.get("current_prizes", [])
                    self.current_prize_index = data.get("current_prize_index", 0)
                    self.lucky_draw_prize_name = data.get("lucky_draw_prize_name", "")
                    self.lucky_draw_prize_value = data.get("lucky_draw_prize_value", "")
                    self.lucky_draw_prize_picture = data.get("lucky_draw_prize_picture", "")
                    self.lucky_draw_excluded = data.get("lucky_draw_excluded", "")
                    self.lucky_draw_only_present = data.get("lucky_draw_only_present", True)
                    self.current_event_id = data.get("current_event_id", "")
                    self.lucky_draw_event_name = data.get("current_event_name", "")

                    # Set eligible guests directly
                    eligible_guests = data.get("eligible_guests", [])
                    self.lucky_draw_eligible_guests = eligible_guests

                    # Set winners
                    winners = data.get("winners", [])
                    self.winners_list = winners


                    # Also set prize list for multiple/excel mode
                    if self.current_prizes:
                        self.prize_list = self.current_prizes.copy()

                    # We already have eligible guests from URL, no need to fetch from API

                    yield
                    return


                except Exception as e:

                    rx.toast(f"Failed to parse URL: {e}")

        # Fallback: fetch from API if no URL data
        await self._fetch_display_data_from_api()
        yield


    def start_new_draw(self):
        """Reset for new draw and go back to dashboard."""
        self.lucky_draw_prize_name = ""
        self.lucky_draw_prize_value = ""
        self.lucky_draw_prize_picture = ""
        self.prize_list = []
        self.lucky_draw_excluded = ""
        self.lucky_draw_only_present = True
        self.lucky_draw_show_new_draw_dialog = False
        self.current_prizes = []
        self.current_prize_index = 0
        self.drawn_winners = []
        return rx.redirect(f"/dashboard/{self.current_event_id}")