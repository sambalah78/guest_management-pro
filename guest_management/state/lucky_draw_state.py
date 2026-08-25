# guest_management/state/lucky_draw_state.py
"""Lucky draw state."""

import reflex as rx
from typing import List, Dict, Any, Optional
from datetime import datetime
import random
import json
import base64
import asyncio

from guest_management.database_client import get_db
import logging

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
        """Process Excel file and store in excel_prizes_list only"""
        if not self._prize_file_content:
            yield rx.toast.error("No file selected")
            return

        self.is_loading = True
        yield

        try:
            import pandas as pd
            import io

            df = pd.read_excel(io.BytesIO(self._prize_file_content), engine='openpyxl')

            # Auto-detect columns - MORE FLEXIBLE
            name_col = None
            value_col = None
            image_col = None

            for col in df.columns:
                col_lower = str(col).lower().strip()
                # Name detection
                if any(keyword in col_lower for keyword in ["name", "prize", "title", "prize name", "item"]):
                    if name_col is None:
                        name_col = col
                # Value detection
                if any(keyword in col_lower for keyword in ["value", "price", "amount", "rm", "worth"]):
                    if value_col is None:
                        value_col = col
                # Image URL detection
                if any(keyword in col_lower for keyword in
                       ["image", "url", "picture", "photo", "img", "image url", "link"]):
                    if image_col is None:
                        image_col = col

            # Fallback: use first column for names if none found
            if name_col is None and len(df.columns) > 0:
                name_col = df.columns[0]
                yield rx.toast.warning(f"Using '{name_col}' as prize name column")

            if name_col is None:
                yield rx.toast.error("Could not find a column for prize names")
                self.is_loading = False
                return

            # Parse prizes
            prizes = []
            skipped = 0

            for idx, row in df.iterrows():
                prize_name = str(row[name_col]) if pd.notna(row[name_col]) else None
                if not prize_name or prize_name == "nan" or prize_name == "None" or prize_name == "":
                    skipped += 1
                    continue

                # Get value (optional)
                prize_value = ""
                if value_col and pd.notna(row[value_col]):
                    prize_value = str(row[value_col])
                    prize_value = prize_value.replace("RM", "").replace("rm", "").replace("$", "").strip()
                    if prize_value == "nan" or prize_value == "None":
                        prize_value = ""

                # Get image URL (optional)
                prize_image = ""
                if image_col and pd.notna(row[image_col]):
                    prize_image = str(row[image_col])
                    if prize_image == "nan" or prize_image == "None":
                        prize_image = ""

                prizes.append({
                    "name": prize_name,
                    "value": prize_value,
                    "image_url": prize_image
                })

            if prizes:
                # Store ONLY in excel_prizes_list
                self.excel_prizes_list = prizes.copy()
                self.excel_filename = self._prize_filename

                # If excel mode is active, update display
                if self.prize_mode == "excel":
                    self.current_prizes = prizes.copy()
                    self.current_prize_index = 0
                    if prizes:
                        self.lucky_draw_prize_name = prizes[0]["name"]
                        self.lucky_draw_prize_value = prizes[0]["value"]
                        self.lucky_draw_prize_picture = prizes[0]["image_url"]

                self.prize_selected_file_name = ""
                self._prize_file_content = b""
                self.is_loading = False

                msg = f"Loaded {len(prizes)} prizes from Excel!"
                if skipped > 0:
                    msg += f" (skipped {skipped} invalid rows)"
                yield rx.toast.success(msg)
            else:
                yield rx.toast.error(f"No valid prizes found. Found {skipped} invalid rows.")
                self.is_loading = False

        except Exception as e:
            rx.toast(f"Excel prize upload error: {e}")
            yield rx.toast.error(f"Error: {str(e)}")
            self.is_loading = False

    def clear_excel_prize_file(self):
        self.prize_selected_file_name = ""
        self._prize_file_content = b""
        self._prize_filename = ""

    async def setup_complete_and_go_to_display(self):
        """Validate setup and redirect to display page"""
        self._prize_transitioning = False
        await self.load_lucky_draw_eligible_guests()

        import asyncio
        await asyncio.sleep(0.2)

        # IMPORTANT: Check mode-specific prize data
        if self.prize_mode == "single":
            if not self.single_prize_name and not self.lucky_draw_prize_name:
                yield rx.toast.error("Please enter a prize name first")
                return
            self.current_prizes = [{
                "name": self.single_prize_name or self.lucky_draw_prize_name,
                "value": self.single_prize_value or self.lucky_draw_prize_value,
                "image_url": self.single_prize_picture or self.lucky_draw_prize_picture
            }]
            self.current_prize_index = 0

        elif self.prize_mode == "multiple":
            if not self.multiple_prizes_list or len(self.multiple_prizes_list) == 0:
                yield rx.toast.error("Please add at least one prize")
                return
            # Filter out empty prizes
            valid_prizes = [p for p in self.multiple_prizes_list if p.get("name")]
            if not valid_prizes:
                yield rx.toast.error("Please add prizes with names")
                return
            self.current_prizes = valid_prizes.copy()
            self.current_prize_index = 0

        elif self.prize_mode == "excel":
            if not self.excel_prizes_list or len(self.excel_prizes_list) == 0:
                yield rx.toast.error("Please upload an Excel file with prizes first")
                return
            self.current_prizes = self.excel_prizes_list.copy()
            self.current_prize_index = 0

        # Set current prize display
        if self.current_prizes and len(self.current_prizes) > 0:
            self.lucky_draw_prize_name = self.current_prizes[0].get("name", "")
            self.lucky_draw_prize_value = self.current_prizes[0].get("value", "")
            self.lucky_draw_prize_picture = self.current_prizes[0].get("image_url", "")
        else:
            yield rx.toast.error("No prizes available")
            return

        if len(self.lucky_draw_eligible_guests) == 0:
            yield rx.toast.error("No eligible guests for lucky draw")
            return

        # Prepare data for URL
        import json
        import urllib.parse

        eligible_guests_data = [{
            "name": g["name"],
            "guest_id": g["guest_id"],
            "table_number": g.get("table_number", "TBD"),
            "email": g.get("email", "")
        } for g in self.lucky_draw_eligible_guests]

        display_data = {
            "prize_mode": self.prize_mode,
            "current_prizes": self.current_prizes,
            "current_prize_index": self.current_prize_index,
            "lucky_draw_prize_name": self.lucky_draw_prize_name,
            "lucky_draw_prize_value": self.lucky_draw_prize_value,
            "lucky_draw_prize_picture": self.lucky_draw_prize_picture,
            "lucky_draw_excluded": self.lucky_draw_excluded,
            "lucky_draw_only_present": self.lucky_draw_only_present,
            "current_event_id": self.current_event_id,
            "current_event_name": self.current_event.get("name", "") if self.current_event else "",
            "eligible_guests": eligible_guests_data,
            "eligible_count": len(eligible_guests_data),
            "winners": self.winners_list
        }

        data_json = json.dumps(display_data)
        data_encoded = urllib.parse.quote(data_json)

        yield rx.call_script(f"""
            window.open('/lucky-draw-display?data={data_encoded}', '_blank', 'width=1400,height=900,resizable=yes,scrollbars=yes');
        """)


    async def load_lucky_draw_eligible_guests(self):
        """Load eligible guests from the database, never from a page-sized UI list."""
        try:
            from guest_management.repositories import GuestRepository
            from guest_management.state.guest_state import GuestState
            guest_state = await self.get_state(GuestState)
            event_id = int(self.current_event_id or guest_state.current_event_id or 0)
            if not event_id:
                self.lucky_draw_eligible_guests = []
                return
            self.current_event_id = str(event_id)
            self.current_event = guest_state.current_event

            excluded = {item.strip().lower() for item in self.lucky_draw_excluded.split(",") if item.strip()}
            repo = GuestRepository()
            eligible: list[dict] = []
            page = 0
            while True:
                rows, total = repo.get_by_event(event_id, limit=200, offset=page * 200)
                if not rows:
                    break
                for guest in rows:
                    guest_id = str(guest.get("guest_id") or "")
                    if guest_id.lower() in excluded:
                        continue
                    if self.lucky_draw_only_present and guest.get("status") != "Present":
                        continue
                    eligible.append({
                        "name": guest.get("name", "Guest"),
                        "guest_id": guest_id,
                        "table_number": guest.get("table_number") or "TBD",
                        "email": guest.get("email", ""),
                    })
                if len(rows) < 200:
                    break
                page += 1
            self.lucky_draw_eligible_guests = eligible
            self.lucky_draw_event_name = str((self.current_event or {}).get("name") or "")
        except Exception:
            logger.exception("Unable to load lucky draw guests")
            self.lucky_draw_eligible_guests = []

    async def load_winners(self):
        """Load winners from database for current event."""
        try:
            db = get_db()
            if not self.current_event_id:
                return

            res = db.table("winners") \
                .select("*") \
                .eq("event_id", int(self.current_event_id)) \
                .order("created_at", desc=True) \
                .execute()

            winners = res.data if res.data else []

            for w in winners:
                if w.get("created_at"):
                    w["formatted_date"] = w["created_at"].split("T")[0]

            self.winners_list = winners

        except Exception as e:
            logger.error(f"Error loading winners: {e}")
            rx.toast.error(f"Error loading winners: {str(e)}")

    # --- Prize Management ---

    def load_current_prize(self):
        """Set current prize details."""
        if not self.current_prizes:
            self.lucky_draw_prize_name = ""
            self.lucky_draw_prize_value = ""
            self.lucky_draw_prize_picture = ""
            return

        prize = self.current_prizes[self.current_prize_index]
        self.lucky_draw_prize_name = prize.get("name", "")
        self.lucky_draw_prize_value = prize.get("value", "")
        self.lucky_draw_prize_picture = prize.get("image_url", "")

    def set_prize_mode(self, mode: str):
        """Switch between prize modes."""
        self.prize_mode = mode
        if mode == "single":
            self.current_prizes = [{
                "name": self.single_prize_name,
                "value": self.single_prize_value,
                "image_url": self.single_prize_picture
            }] if self.single_prize_name else []
            self.current_prize_index = 0
            if self.current_prizes:
                self.lucky_draw_prize_name = self.single_prize_name
                self.lucky_draw_prize_value = self.single_prize_value
                self.lucky_draw_prize_picture = self.single_prize_picture
        elif mode == "multiple":
            self.current_prizes = self.multiple_prizes_list.copy()
            self.current_prize_index = 0
            if self.current_prizes:
                self.lucky_draw_prize_name = self.current_prizes[0].get("name", "")
                self.lucky_draw_prize_value = self.current_prizes[0].get("value", "")
                self.lucky_draw_prize_picture = self.current_prizes[0].get("image_url", "")
        elif mode == "excel":
            self.current_prizes = self.excel_prizes_list.copy()
            self.current_prize_index = 0
            if self.current_prizes:
                self.lucky_draw_prize_name = self.current_prizes[0].get("name", "")
                self.lucky_draw_prize_value = self.current_prizes[0].get("value", "")
                self.lucky_draw_prize_picture = self.current_prizes[0].get("image_url", "")

    def set_prize_list(self, prizes: List[Dict[str, Any]]):
        """Set the prize list."""
        self.prize_list = prizes

    def set_lucky_draw_prize_name(self, value: str):
        self.lucky_draw_prize_name = value

    def set_lucky_draw_prize_value(self, value: str):
        self.lucky_draw_prize_value = value

    def set_lucky_draw_prize_picture(self, value: str):
        self.lucky_draw_prize_picture = value

    def set_lucky_draw_excluded(self, value: str):
        self.lucky_draw_excluded = value

    def set_lucky_draw_only_present(self, value: bool):
        """Set filter for only present guests."""
        self.lucky_draw_only_present = value
        self.load_lucky_draw_eligible_guests()

    def set_lucky_draw_event_name(self, name: str):
        """Set event name for display."""
        self.lucky_draw_event_name = name

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

    async def confirm_clear_winners(self):
        """Clear all winners for current event."""
        self.is_loading = True
        yield
        try:
            db = get_db()
            db.table("winners").delete().eq("event_id", int(self.current_event_id)).execute()
            self.winners_list = []
            self.is_loading = False
            self.show_clear_confirm = False
            self.load_lucky_draw_eligible_guests()
            yield rx.toast.success("Winners history cleared!")
        except Exception as e:
            self.is_loading = False
            yield rx.toast.error(f"Error: {str(e)}")

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
        from datetime import datetime
        db = get_db()
        prize_name = self.lucky_draw_prize_name

        db.table("winners").insert({
            "event_id": int(self.current_event_id),
            "guest_id": winner["guest_id"],
            "name": winner["name"],
            "prize_name": prize_name,
            "created_at": datetime.now().isoformat()
        }).execute()

        self.winners_list.insert(0, {
            **winner,
            "prize_name": prize_name,
            "formatted_date": datetime.now().strftime("%H:%M:%S")
        })

        self.lucky_draw_eligible_guests = [
            g for g in self.lucky_draw_eligible_guests
            if g["guest_id"] != winner["guest_id"]
        ]

        yield

    async def draw_current_prize(self):
        """Draw the current prize."""
        if self.current_prize_index >= len(self.current_prizes):
            self.lucky_draw_spinner_open = False
            await self.load_winners()
            yield rx.toast.success(f"All {len(self.current_prizes)} prizes awarded!")
            return

        prize = self.current_prizes[self.current_prize_index]
        self.lucky_draw_prize_name = prize.get("name", "")
        self.lucky_draw_prize_value = prize.get("value", "")
        self.lucky_draw_prize_picture = prize.get("image_url", "")

        self.lucky_draw_spinner_open = True
        await asyncio.sleep(0.1)

        self.lucky_draw_spinning = True
        self.lucky_draw_winner = {}
        self.waiting_for_next_prize = False
        yield

        try:
            steps = 35
            for i in range(steps):
                if self.lucky_draw_eligible_guests:
                    guest = random.choice(self.lucky_draw_eligible_guests)
                    self.lucky_draw_current_name = guest["name"]
                    self.lucky_draw_current_id = guest["guest_id"]
                    yield
                    await asyncio.sleep(0.07)

            if self.lucky_draw_eligible_guests:
                winner = random.choice(self.lucky_draw_eligible_guests)
                self.lucky_draw_winner = winner
                self.lucky_draw_current_name = winner["name"]
                self.lucky_draw_current_id = winner["guest_id"]
                self.lucky_draw_spinning = False

                db = get_db()
                try:
                    from datetime import datetime
                    db.table("winners").insert({
                        "event_id": int(self.current_event_id),
                        "guest_id": winner["guest_id"],
                        "name": winner["name"],
                        "prize_name": prize.get("name", ""),
                        "prize_value": prize.get("value", ""),
                        "created_at": datetime.now().isoformat()
                    }).execute()
                except Exception as e:
                    logger.error(f"Error saving winner: {e}")

                self.lucky_draw_eligible_guests = [g for g in self.lucky_draw_eligible_guests
                                                   if g["guest_id"] != winner["guest_id"]]

                await self.load_winners()

                if self.current_prize_index + 1 < len(self.current_prizes):
                    self.waiting_for_next_prize = True
                else:
                    self.waiting_for_next_prize = False

                yield

        except Exception as e:
            logger.error(f"Lucky draw error: {e}")
            self.lucky_draw_spinning = False
            self.waiting_for_next_prize = False
            yield rx.toast.error(f"Error: {str(e)}")

    async def draw_next_prize(self):
        """Draw the next prize."""
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