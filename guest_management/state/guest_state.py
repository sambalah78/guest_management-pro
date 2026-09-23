# guest_management/state/guest_state.py
"""Guest management state - fully self-contained with all methods."""

import reflex as rx
from typing import List, Optional, Dict, Any
from datetime import datetime
import json
import base64
import re
import hashlib
import time
import os
from io import BytesIO
import io
import pandas as pd
import qrcode
from PIL import Image

from guest_management.database_client import get_db
import logging
from guest_management.services.checkin_service import CheckinService
from guest_management.services.qr_service import QRService
from guest_management.repositories import GuestRepository

logger = logging.getLogger(__name__)
from guest_management.repositories import EventRepository
from guest_management.services.guest_service import GuestService
from guest_management.services.storage_service import StorageService
from guest_management.state.auth_state import AuthState
from guest_management.services.event_service import EventService
from guest_management.core.exceptions import (
    AuthorizationError,
    EventNotFoundError, GuestAlreadyCheckedInError,
)

class GuestState(rx.State):
    """Guest management state - fully self-contained."""

    # ========================================================================
    # AUTH DATA
    # ========================================================================
    user_id: str = ""
    is_authenticated: bool = False

    # ========================================================================
    # EVENT DATA
    # ========================================================================
    current_event: Optional[Dict[str, Any]] = None
    current_event_id: str = ""
    event_type: str = "company_dinner"
    events: List[Dict[str, Any]] = []
    new_event_name: str = ""
    new_event_company_name: str = ""
    new_event_date: str = ""
    new_event_time: str = ""
    new_event_venue: str = ""
    new_event_theme: str = ""
    event_logo: str = ""
    wedding_invitation_card: str = ""

    # ========================================================================
    # GUEST DATA
    # ========================================================================
    guest_data: List[Dict[str, Any]] = []
    filtered_data: List[Dict[str, Any]] = []
    columns: List[str] = ["Name", "Email", "ID", "Table", "Status", "Email Sent"]
    total_guests: int = 0
    present_count: int = 0
    absent_count: int = 0
    present_percentage: float = 0
    absent_percentage: float = 0
    has_amounts: bool = False

    # ========================================================================
    # PAGINATION
    # ========================================================================
    current_page: int = 1
    items_per_page: int = 10
    total_pages: int = 0
    screen_height: int = 0

    # ========================================================================
    # SEARCH
    # ========================================================================
    search_query: str = ""
    search_name: str = ""
    search_id: str = ""

    # ========================================================================
    # CHECK-IN
    # ========================================================================
    checkin_guest_name: str = ""
    checkin_table_number: str = ""
    checkin_team_name: str = ""
    manual_name: str = ""
    manual_guest_id: str = ""
    checkin_message: str = ""
    checkin_success: bool = False
    manual_checkin_open: bool = False
    no_id_verification_open: bool = False
    no_id_name: str = ""
    no_id_email: str = ""
    no_id_phone: str = ""
    no_id_table_number: str = "TBD"
    no_id_team_name: str = ""
    no_id_client_confirmed: bool = False
    use_camera: bool = True

    # ========================================================================
    # UPLOAD
    # ========================================================================
    show_upload_dialog: bool = False
    uploaded_filename: str = ""
    selected_file_name: str = ""
    _selected_file_content: bytes = b""
    _selected_filename: str = ""
    show_clear_table_confirm: bool = False

    # ========================================================================
    # COMPANY LOGO
    # ========================================================================
    company_logo: str = ""
    company_logo_filename: str = ""
    logo_dialog_open: bool = False

    # ========================================================================
    # QR
    # ========================================================================
    guest_qr_dialog_open: bool = False
    selected_guest_qr: str = ""
    selected_guest_name: str = ""
    qr_dialog_open: bool = False
    show_qr_dialog: bool = False

    # ========================================================================
    # LUCKY DRAW
    # ========================================================================

    # ========================================================================
    # LOADING
    # ========================================================================
    is_loading: bool = False

    # ========================================================================
    # EMAIL
    # ========================================================================
    email_sending: bool = False
    email_progress: int = 0
    email_total: int = 0
    sending_email_guest_id: str = ""
    email_dialog_open: bool = False
    selected_guest_for_email: Optional[dict] = None

    # ========================================================================
    # CONTACT FORM
    # ========================================================================
    contact_name: str = ""
    contact_email: str = ""
    contact_message: str = ""
    contact_success: bool = False

    # ========================================================================
    # SCANNER UI (copied from UIState for accessibility)
    # ========================================================================
    scanner_status_icon: str = "idle"
    scanner_status: str = "Ready to check in"

    # ========================================================================
    # COMPUTED PROPERTIES
    # ========================================================================

    @rx.var
    def formatted_events(self) -> List[dict]:
        from guest_management.utils.formatting import format_date
        formatted = []
        for event in self.events:
            event_copy = event.copy()
            created_at = event.get("created_at", "")
            event_copy["formatted_created_at"] = format_date(created_at) if created_at else ""
            formatted.append(event_copy)
        return formatted

    @rx.var
    def event_config_name(self) -> str:
        from guest_management.utils.constants import EVENT_TYPES
        event_type = self.event_type if self.event_type else "company_dinner"
        config = EVENT_TYPES.get(event_type, EVENT_TYPES["company_dinner"])
        return config["name"]

    @rx.var
    def event_config_icon(self) -> str:
        from guest_management.utils.constants import EVENT_TYPES
        event_type = self.event_type if self.event_type else "company_dinner"
        config = EVENT_TYPES.get(event_type, EVENT_TYPES["company_dinner"])
        return config["icon"]

    @rx.var
    def show_lucky_draw(self) -> bool:
        from guest_management.utils.constants import EVENT_TYPES
        config = EVENT_TYPES.get(self.event_type, EVENT_TYPES["company_dinner"])
        return config["features"].get("lucky_draw", False)

    @rx.var
    def show_food_vouchers(self) -> bool:
        from guest_management.utils.constants import EVENT_TYPES
        config = EVENT_TYPES.get(self.event_type, EVENT_TYPES["company_dinner"])
        return config["features"].get("food_vouchers", False)

    @rx.var
    def qr_url(self) -> str:
        from guest_management.utils.url import get_app_url
        base_url = get_app_url()
        event_id = self.current_event_id if self.current_event_id else "0"
        return f"{base_url}/checkin?event_id={event_id}"

    @rx.var
    def host_url(self) -> str:
        from guest_management.utils.url import get_app_url
        return get_app_url()

    @rx.var
    def email_sent_count(self) -> int:
        return len([g for g in self.guest_data if g.get("email_sent", False)])

    @rx.var
    def paginated_guests(self) -> List[dict]:
        """Return paginated guests."""
        if not self.filtered_data:
            return []
        start = (self.current_page - 1) * self.items_per_page
        end = start + self.items_per_page
        result = self.filtered_data[start:end]
        logger.info(f"paginated_guests: {len(result)} guests from {len(self.filtered_data)} total")
        return result

    # ========================================================================
    # LOAD GUESTS
    # ========================================================================

    # guest_management/state/guest_state.py - Update load_guests method

    # In guest_state.py, update the load_guests method:

    # In guest_state.py - Fix the load_guests method

    # In guest_state.py - Complete updated load_guests method

    async def load_guests(self):
        """Load one page of guests through the production repository layer."""
        try:


            auth = await self.get_state(AuthState)
            if not auth.user_id:
                self.guest_data = []
                self.filtered_data = []
                yield rx.redirect("/login")
                return
            self.user_id = auth.user_id
            self.is_authenticated = True


            path = getattr(self.router.url, "path", "") or ""
            match = re.search(r"/dashboard/(\d+)", path)
            if match:
                self.current_event_id = match.group(1)

            if not self.current_event_id:
                self.guest_data = []
                self.filtered_data = []
                yield
                return

            event_id = int(self.current_event_id)



            try:
                event = EventService().get_event(
                    event_id,
                    auth.user_id,
                    auth.user,
                )
            except (AuthorizationError, EventNotFoundError):
                self.guest_data = []
                self.filtered_data = []
                yield rx.toast.error("Event not found or access denied")
                yield rx.redirect("/events")
                return

            self.current_event = event
            self.event_type = event.get("event_type", "company_dinner")
            repo = GuestRepository()
            guests, total = repo.get_by_event(event_id, limit=min(max(self.items_per_page, 1), 200),
                                              offset=max(0, (self.current_page - 1) * self.items_per_page))

            processed = []
            has_amount = False
            has_team = False
            for guest in guests:
                full_data = self._parse_full_data(guest.get("full_data"))
                amount = float(guest.get("amount") or 0)
                team = str(guest.get("team_name") or "")
                if not team and self.event_type == "sports_day":
                    for key in ("team", "Team", "team_name", "TeamName", "group", "Group", "squad", "Squad"):
                        if full_data.get(key):
                            team = str(full_data[key])
                            break
                if amount > 0:
                    has_amount = True
                if team:
                    has_team = True

                item = {
                    "Name": guest.get("name", ""),
                    "Email": guest.get("email", ""),
                    "ID": guest.get("guest_id", ""),
                    "Table": guest.get("table_number") or full_data.get("table") or full_data.get("Table") or "TBD",
                    "Status": guest.get("status", "Absent"),
                    "Email Sent": "✅" if guest.get("email_sent") else "❌",
                    "email_sent": bool(guest.get("email_sent")),
                    "guest_id": guest.get("guest_id", ""),
                    "amount_value": amount,
                }
                if self.event_type == "sports_day":
                    item["Amount"] = f"RM {amount:.2f}"
                    if team:
                        item["Team"] = team
                if self.event_type == "wedding_dinner":
                    diet = full_data.get("dietary_restrictions") or full_data.get("Diet")
                    if diet:
                        item["Diet"] = str(diet)
                processed.append(item)

            self.guest_data = processed
            self.filtered_data = processed
            self.total_guests = int(total)
            self.total_pages = max(1, (self.total_guests + self.items_per_page - 1) // self.items_per_page)
            self._set_columns(self.event_type, has_team, processed)
            self.has_amounts = has_amount

            stats_response = repo.db.rpc("get_event_stats", {"p_event_id": event_id}).execute()
            stats = (stats_response.data or [{}])[0]
            self.present_count = int(stats.get("present_count", 0))
            self.absent_count = int(stats.get("absent_count", self.total_guests - self.present_count))
            self.present_percentage = round(self.present_count / self.total_guests * 100) if self.total_guests else 0
            self.absent_percentage = round(self.absent_count / self.total_guests * 100) if self.total_guests else 0
            yield
        except Exception:
            logger.exception("Error loading guests")
            self.guest_data = []
            self.filtered_data = []
            yield rx.toast.error("Unable to load guests. Please try again.")

    def _parse_full_data(self, full_data):
        if not full_data:
            return {}
        try:
            if isinstance(full_data, str):
                return json.loads(full_data)
            return full_data if isinstance(full_data, dict) else {}
        except:
            return {}

    def _set_columns(self, event_type, has_team, processed_guests):
        if event_type == "sports_day":
            base = ["Name", "Email", "ID", "Table"]
            if has_team:
                base.append("Team")
            base.extend(["Amount", "Status", "Email Sent"])
            self.columns = base
        elif event_type == "wedding_dinner":
            has_dietary = any("Diet" in g for g in processed_guests)
            if has_dietary:
                self.columns = ["Name", "Email", "ID", "Table", "Diet", "Status", "Email Sent"]
            else:
                self.columns = ["Name", "Email", "ID", "Table", "Status", "Email Sent"]
        else:
            self.columns = ["Name", "Email", "ID", "Table", "Status", "Email Sent"]

    def _default_columns(self, event_type):
        if event_type == "sports_day":
            return ["Name", "Email", "ID", "Table", "Amount", "Status", "Email Sent"]
        return ["Name", "Email", "ID", "Table", "Status", "Email Sent"]

    async def _authorize_current_event(self) -> int:
        """Authorize the authenticated user for the current event."""
        from guest_management.state.auth_state import AuthState

        event_id = int(self.current_event_id or 0)
        if not event_id:
            raise AuthorizationError("Event ID is required.")

        auth = await self.get_state(AuthState)
        user_id = str(auth.user_id or "").strip()

        if not user_id:
            raise AuthorizationError("Authentication required.")

        EventService().get_event(
            event_id,
            user_id,
            auth.user,
        )

        return event_id

    async def update_dashboard_stats(self):
        """Refresh dashboard counts from the database, never from page length."""
        try:
            event_id = await self._authorize_current_event()

            from guest_management.repositories import GuestRepository

            response = GuestRepository().db.rpc(
                "get_event_stats",
                {"p_event_id": event_id},
            ).execute()

            row = (response.data or [{}])[0]
            self.total_guests = int(row.get("total_guests", 0))
            self.present_count = int(row.get("present_count", 0))
            self.absent_count = int(
                row.get(
                    "absent_count",
                    max(
                        0,
                        self.total_guests - self.present_count,
                    ),
                )
            )
            self.present_percentage = (
                round(
                    self.present_count
                    / self.total_guests
                    * 100
                )
                if self.total_guests
                else 0
            )
            self.absent_percentage = (
                round(
                    self.absent_count
                    / self.total_guests
                    * 100
                )
                if self.total_guests
                else 0
            )
        except Exception:
            logger.exception("Unable to update dashboard stats")
        yield

    # ========================================================================
    # REDIRECT
    # ========================================================================

    async def redirect_after_delay(self):
        import asyncio
        await asyncio.sleep(2.5)
        return rx.redirect("/home")

    # ========================================================================
    # SEARCH METHODS
    # ========================================================================

    def set_search_query(self, value: str):
        self.search_query = value
        if not value:
            self.filtered_data = self.guest_data
        else:
            term = value.lower()
            self.filtered_data = [
                g for g in self.guest_data
                if any(term in str(v).lower() for v in g.values())
            ]
        self.current_page = 1
        self.calculate_total_pages()

    async def search_guests(self, value: str):
        """Search the entire event on the server, not just the visible page."""
        self.search_query = value.strip()
        if len(self.search_query) < 2:
            self.current_page = 1
            async for update in self.load_guests():
                yield update
            return
        try:

            auth = await self.get_state(AuthState)

            if not auth.user_id:
                yield rx.toast.error("Please log in again.")
                yield rx.redirect("/login")
                return

            try:
                event_id = int(self.current_event_id)
            except (TypeError, ValueError):
                yield rx.toast.error("Invalid event.")
                return

            from guest_management.services.event_service import EventService
            from guest_management.core.exceptions import (
                AuthorizationError,
                EventNotFoundError,
            )

            try:
                EventService().get_event(
                    event_id,
                    auth.user_id,
                    auth.user,
                )
            except (AuthorizationError, EventNotFoundError):
                yield rx.toast.error("Event not found or access denied")
                return

            rows = GuestRepository().search(
                event_id,
                self.search_query,
                limit=50,
            )
            self.guest_data = [
                {
                    "Name": row.get("name", ""),
                    "Email": row.get("email", ""),
                    "ID": row.get("guest_id", ""),
                    "Table": row.get("table_number") or "TBD",
                    "Status": row.get("status", "Absent"),
                    "Email Sent": "✅" if row.get("email_sent") else "❌",
                    "email_sent": bool(row.get("email_sent")),
                    "guest_id": row.get("guest_id", ""),
                    "amount_value": float(row.get("amount") or 0),
                    "Team": row.get("team_name", ""),
                }
                for row in rows
            ]
            self.filtered_data = self.guest_data
            self.current_page = 1
            self.total_pages = 1
            self.total_guests = len(self.guest_data)
            self.present_count = sum(1 for row in self.guest_data if row.get("Status") == "Present")
            self.absent_count = self.total_guests - self.present_count
            yield
        except Exception:
            logger.exception("Guest search failed")
            yield rx.toast.error("Search failed. Please try again.")

    def set_search_name(self, value: str):
        self.search_name = value

    def set_search_id(self, value: str):
        self.search_id = value

    # ========================================================================
    # PAGINATION METHODS
    # ========================================================================

    def calculate_total_pages(self):
        if not self.filtered_data:
            self.total_pages = 1
        else:
            self.total_pages = (len(self.filtered_data) + self.items_per_page - 1) // self.items_per_page
        if self.current_page > self.total_pages:
            self.current_page = self.total_pages
        if self.current_page < 1:
            self.current_page = 1

    def go_to_page(self, page: int):
        if 1 <= page <= self.total_pages:
            self.current_page = page

    def next_page(self):
        if self.current_page < self.total_pages:
            self.current_page += 1

    def prev_page(self):
        if self.current_page > 1:
            self.current_page -= 1

    def set_items_per_page(self, value: str):
        try:
            self.items_per_page = int(value)
            self.current_page = 1
            self.calculate_total_pages()
        except:
            pass

    def set_screen_height(self, height: int):
        self.screen_height = height
        available_height = height - 350
        calculated_items = max(15, min(25, available_height // 60))
        if self.items_per_page != calculated_items:
            self.items_per_page = calculated_items
            self.current_page = 1
            self.calculate_total_pages()

    # ========================================================================
    # MANUAL CHECK-IN
    # ========================================================================

    async def handle_manual_checkin(self):
        """Handle event-day manual check-in for missing QR/email/ID cases.

        Existing guests are always resolved from the uploaded guest list.
        A new guest is created only through the explicit no-ID verification flow.
        """
        name = self.manual_name.strip()
        guest_id = self.manual_guest_id.strip()

        if not name and not guest_id:
            yield rx.toast.error("Please enter a Name or ID")
            return
        if not self.current_event_id:
            yield rx.toast.error("No event selected")
            return

        self.is_loading = True
        yield
        try:
            auth = await self.get_state(AuthState)
            EventService().get_event(
                int(self.current_event_id),
                auth.user_id,
                auth.user,
            )

            event_id = int(self.current_event_id)
            repo = GuestRepository()
            guest = None

            # ID is authoritative when supplied. Never create a replacement
            # guest when an entered ID does not exist in the uploaded list.
            if guest_id:
                guest = repo.get_by_guest_id(guest_id, event_id)
                if not guest:
                    yield rx.toast.error(
                        f"Guest ID '{guest_id}' was not found in the uploaded guest list."
                    )
                    return

            # Name lookup is only for the missing-QR / no-email cases.
            if not guest and name:
                matches = repo.search(event_id, name, limit=10)
                if len(matches) == 1:
                    guest = matches[0]
                elif len(matches) > 1:
                    yield rx.toast.warning(
                        "Multiple guests match this name. Please enter the Guest ID."
                    )
                    return

            # No matching uploaded guest: only a name-only request may enter
            # the explicit client-verification flow.
            if not guest:
                if guest_id:
                    yield rx.toast.error("Guest ID was not found in the uploaded guest list.")
                    return
                self.no_id_name = name
                self.no_id_email = ""
                self.no_id_phone = ""
                self.no_id_table_number = "TBD"
                self.no_id_team_name = ""
                self.no_id_client_confirmed = False
                self.no_id_verification_open = True
                yield rx.toast.warning(
                    "This person is not in the uploaded guest list. Client/staff verification is required before registration."
                )
                return

            result = CheckinService().check_in(
                event_id,
                guest["guest_id"],
                "MANUAL",
                manual=True,
            )
            self._apply_manual_checkin_result(result, guest)

            # Use the server-generated signed receipt token so the success
            # page can verify the manual check-in just like a QR check-in.
            receipt_token = str(result.get("receipt_token") or "").strip()
            if not receipt_token:
                receipt_token = create_qr_token(event_id, guest["guest_id"])

            from urllib.parse import quote

            yield rx.redirect(
                f"/success/{event_id}"
                f"?guest_id={quote(str(guest['guest_id']))}"
                f"&token={quote(receipt_token)}"
            )
            return
        except (AuthorizationError, EventNotFoundError):
            logger.exception("Manual check-in authorization failed")
            yield rx.toast.error("Event not found or access denied")
        except Exception:
            logger.exception("Manual check-in failed")
            yield rx.toast.error("Check-in failed. Please try again.")
        finally:
            self.is_loading = False
            yield

    def _apply_manual_checkin_result(self, result: dict, guest: dict):
        """Apply a successful manual check-in result to state."""
        self.checkin_guest_name = str(
            result.get("guest_name") or guest.get("name") or "Guest"
        )
        self.checkin_table_number = str(
            result.get("table_number") or guest.get("table_number") or "TBD"
        )
        self.checkin_team_name = str(
            result.get("team_name") or guest.get("team_name") or ""
        )
        self.present_count = int(result.get("present_count") or self.present_count)
        self.total_guests = int(result.get("total_guests") or self.total_guests)
        self.absent_count = max(0, self.total_guests - self.present_count)
        self.manual_name = ""
        self.manual_guest_id = ""

    async def confirm_no_id_guest(self):
        """Register and check in a person whose client-issued ID is unavailable."""
        name = self.no_id_name.strip()
        if not name:
            yield rx.toast.error("Please enter the person's full name")
            return
        if not self.no_id_client_confirmed:
            yield rx.toast.error("Please confirm with the client that this is their staff member")
            return
        if not self.current_event_id:
            yield rx.toast.error("No event selected")
            return

        self.is_loading = True
        yield
        try:
            auth = await self.get_state(AuthState)
            EventService().get_event(
                int(self.current_event_id),
                auth.user_id,
                auth.user,
            )
            event_id = int(self.current_event_id)
            repo = GuestRepository()

            # Re-check by name immediately before insert to reduce accidental
            # duplicate registrations if another operator registered the person.
            matches = repo.search(event_id, name, limit=10)
            if matches:
                if len(matches) == 1:
                    guest = matches[0]
                    result = CheckinService().check_in(
                        event_id,
                        guest["guest_id"],
                        "MANUAL",
                        manual=True,
                    )
                    self._apply_manual_checkin_result(result, guest)
                    self.no_id_verification_open = False
                    yield rx.toast.warning(
                        f"Existing guest found. {self.checkin_guest_name} checked in."
                    )
                    async for update in self.load_guests():
                        yield update
                    return
                yield rx.toast.error(
                    "Multiple guests with this name already exist. Do not create another record; use the Guest ID."
                )
                return

            import uuid
            internal_guest_id = f"NO-ID-{uuid.uuid4().hex[:10].upper()}"
            guest_url = QRService().guest_url(internal_guest_id, event_id)
            full_data = {
                "source": "manual_no_id_registration",
                "id_status": "NO_ID",
                "client_staff_verified": True,
                "client_verification_note": "Verified by event staff with client",
            }

            new_guest = {
                "event_id": event_id,
                "guest_id": internal_guest_id,
                "name": name,
                "email": self.no_id_email.strip(),
                "phone": self.no_id_phone.strip(),
                "status": "Absent",
                "table_number": self.no_id_table_number.strip() or "TBD",
                "amount": 0,
                "team_name": self.no_id_team_name.strip() or None,
                "qr_code": guest_url,
                "qr_url": guest_url,
                "email_sent": False,
                "full_data": json.dumps(full_data, ensure_ascii=False),
            }

            created = repo.create_batch([new_guest], batch_size=1)
            if created != 1:
                raise ValueError("Unable to register the no-ID guest")

            guest = repo.get_by_guest_id(internal_guest_id, event_id)
            if not guest:
                raise ValueError("No-ID guest registration could not be verified")

            result = CheckinService().check_in(
                event_id,
                internal_guest_id,
                "MANUAL",
                manual=True,
            )
            self._apply_manual_checkin_result(result, guest)
            self.no_id_verification_open = False
            self.no_id_name = ""
            self.no_id_email = ""
            self.no_id_phone = ""
            self.no_id_table_number = "TBD"
            self.no_id_team_name = ""
            self.no_id_client_confirmed = False

            if result.get("result") == "already_checked_in":
                yield rx.toast.warning(f"{self.checkin_guest_name} is already checked in")
            else:
                yield rx.toast.success(
                    f"{self.checkin_guest_name} registered and checked in successfully."
                )
            async for update in self.load_guests():
                yield update
        except (AuthorizationError, EventNotFoundError):
            logger.exception("No-ID guest authorization failed")
            yield rx.toast.error("Event not found or access denied")
        except Exception:
            logger.exception("No-ID guest registration failed")
            yield rx.toast.error("Unable to register and check in this guest.")
        finally:
            self.is_loading = False
            yield

    def cancel_no_id_verification(self):
        self.no_id_verification_open = False
        self.no_id_name = ""
        self.no_id_email = ""
        self.no_id_phone = ""
        self.no_id_table_number = "TBD"
        self.no_id_team_name = ""
        self.no_id_client_confirmed = False

    def set_manual_name(self, value: str):
        self.manual_name = value

    def set_manual_guest_id(self, value: str):
        self.manual_guest_id = value

    def set_no_id_email(self, value: str):
        self.no_id_email = value

    def set_no_id_phone(self, value: str):
        self.no_id_phone = value

    def set_no_id_table_number(self, value: str):
        self.no_id_table_number = value

    def set_no_id_team_name(self, value: str):
        self.no_id_team_name = value

    def set_no_id_client_confirmed(self, value: bool):
        self.no_id_client_confirmed = value

    def open_manual_checkin(self):
        self.manual_checkin_open = True

    def close_manual_checkin(self):
        self.manual_checkin_open = False
        self.manual_name = ""
        self.manual_guest_id = ""
        self.checkin_message = ""
        self.checkin_success = False
        self.cancel_no_id_verification()

    def toggle_checkin_mode(self):
        self.use_camera = not self.use_camera

    # ========================================================================
    # UPLOAD METHODS
    # ========================================================================

    def open_upload_dialog(self):
        self.show_upload_dialog = True

    def close_upload_dialog(self):
        self.show_upload_dialog = False
        self.uploaded_filename = ""
        self.selected_file_name = ""

    def clear_selected_file(self):
        self.selected_file_name = ""
        self._selected_file_content = b""
        self._selected_filename = ""
        return rx.toast.info("File selection cleared")

    async def set_selected_file(self, files: List[rx.UploadFile]):
        if files and len(files) > 0:
            file = files[0]
            self.selected_file_name = file.filename
            self._selected_file_content = await file.read()
            self._selected_filename = file.filename
        else:
            self.selected_file_name = ""
            self._selected_file_content = b""
            self._selected_filename = ""

    async def handle_upload(self):
        """
        Import a guest list into the database and archive the original
        uploaded file in Supabase Storage.

        Architecture:
        Uploaded file
        +--> Database -> live guest records
        +--> Supabase Storage -> original uploaded file

        The database remains the operational source of truth.
        Supabase Storage is used as the original-file archive.
        """

        if (
                not self.selected_file_name
                or not self._selected_file_content
        ):
            yield rx.toast.error(
                "No file selected. Please select a file first."
            )
            return

        if not self.current_event_id:
            yield rx.toast.error(
                "Please select an event first."
            )
            return

        if not self.is_authenticated:
            yield rx.toast.error(
                "You must be logged in."
            )
            yield rx.redirect("/login")
            return

        self.is_loading = True
        yield

        try:



            # ==============================================================
            # AUTHENTICATION
            # ==============================================================

            auth = await self.get_state(AuthState)

            if not auth.user_id:
                yield rx.redirect("/login")
                return

            event_id = int(self.current_event_id)

            # ==============================================================
            # VERIFY EVENT ACCESS
            # ==============================================================



            try:
                event = EventService().get_event(
                    event_id,
                    auth.user_id,
                    auth.user,
                )
            except (AuthorizationError, EventNotFoundError) as exc:
                raise ValueError(
                    "Event not found or access denied"
                ) from exc

            event_repo = EventRepository()
            event_type = event.get(
                "event_type",
                "company_dinner",
            )

            # Preserve original upload information before
            # clearing the state later.
            original_filename = (
                    self._selected_filename
                    or self.selected_file_name
            )

            original_content = (
                self._selected_file_content
            )

            # ==============================================================
            # PARSE FILE
            # ==============================================================

            try:
                if original_filename.lower().endswith(".csv"):
                    df = pd.read_csv(
                        io.BytesIO(original_content)
                    )
                else:
                    df = pd.read_excel(
                        io.BytesIO(original_content)
                    )

            except Exception as exc:
                raise ValueError(
                    "Could not read file. "
                    "Please upload a valid Excel or CSV file."
                ) from exc

            if df.empty:
                raise ValueError(
                    "The uploaded spreadsheet is empty."
                )

            # Normalize column names.
            df.columns = [
                str(column).strip()
                for column in df.columns
            ]

            df = df.fillna("")

            rows = df.to_dict(
                orient="records"
            )

            # ==============================================================
            # IMPORT INTO DATABASE
            # ==============================================================

            created, skipped = (
                GuestService()
                .process_guests_from_data(
                    rows,
                    event_id,
                    event_type,
                    user_id=auth.user_id,
                    user=auth.user,
                )
            )
            # ==============================================================
            # ARCHIVE ORIGINAL FILE TO SUPABASE STORAGE
            # ==============================================================
            #
            # The guest import has already succeeded.
            #
            # Storage archival is intentionally handled separately so a
            # temporary Storage problem does NOT destroy an otherwise
            # successful guest import.
            # ==============================================================

            storage_asset = None
            storage_error = None

            try:
                storage_service = StorageService()

                # ----------------------------------------------------------
                # Upload the original guest-list file.
                # ----------------------------------------------------------

                storage_asset = storage_service.upload(
                    event_id=event_id,
                    asset_type="guest-list",
                    content=original_content,
                    filename=original_filename,
                    mime_type=self._detect_upload_mime_type(
                        original_filename
                    ),
                    upsert=True,
                )

                # ----------------------------------------------------------
                # Store Storage metadata against the event.
                # ----------------------------------------------------------

                updated_event = event_repo.update_guest_list_asset(
                    event_id=event_id,
                    storage_path=storage_asset.path,
                    filename=storage_asset.filename,
                    mime_type=storage_asset.mime_type,
                )

                if not updated_event:
                    logger.warning(
                        "Guest list uploaded to Supabase Storage but "
                        "event metadata could not be updated. "
                        "event_id=%s storage_path=%s",
                        event_id,
                        storage_asset.path,
                    )

            except Exception as exc:
                storage_error = exc

                logger.exception(
                    "Guest list imported successfully but "
                    "Supabase Storage archival failed. "
                    "event_id=%s filename=%s",
                    event_id,
                    original_filename,
                )
            # ==============================================================
            # USER FEEDBACK
            # ==============================================================
            storage_metadata_updated = False
            if updated_event:
                storage_metadata_updated = True
            else:
                logger.error(
                    "Guest list uploaded to Supabase Storage, "
                    "but event metadata update returned no row. "
                    "event_id=%s storage_path=%s",
                    event_id,
                    storage_asset.path,
                )
            if storage_asset and storage_metadata_updated:
                yield rx.toast.success(
                    f"Imported {created} guests successfully. "
                    "Guest list archived to Supabase Storage."
                )
            elif storage_asset:
                yield rx.toast.warning(
                    f"Imported {created} guests successfully. "
                    "Guest list uploaded to Storage, but event metadata "
                    "could not be updated."
                )
            else:
                yield rx.toast.warning(
                    f"Imported {created} guests successfully. "
                    "Guest list was not archived to Supabase Storage."
                )
            if storage_asset:
                if skipped:
                    yield rx.toast.warning(
                        f"Imported {created} guests. "
                        f"Skipped {skipped} duplicate IDs. "
                        "Original guest list archived to Supabase Storage."
                    )
                else:
                    yield rx.toast.success(
                        f"Imported {created} guests successfully. "
                        "Original guest list archived to Supabase Storage."
                    )

            else:
                # Database import succeeded, but Storage backup failed.
                if skipped:
                    yield rx.toast.warning(
                        f"Imported {created} guests. "
                        f"Skipped {skipped} duplicate IDs. "
                        "Guest list was not archived to Supabase Storage."
                    )
                else:
                    yield rx.toast.warning(
                        f"Imported {created} guests successfully. "
                        "Guest list was not archived to Supabase Storage."
                    )

            # ==============================================================
            # CLOSE UPLOAD DIALOG
            # ==============================================================

            self.close_upload_dialog()

            # Clear the uploaded file bytes and filename so the previous
            # file cannot accidentally be reused on the next upload.
            self._selected_file_content = b""
            self._selected_filename = ""

            yield

            # ==============================================================
            # REFRESH DASHBOARD
            # ==============================================================

            async for update in self.load_guests():
                yield update

            # ==============================================================
            # RETURN TO EVENT DASHBOARD
            # ==============================================================

            yield rx.redirect(
                f"/dashboard/{event_id}"
            )

        except Exception as exc:
            logger.exception(
                "Guest import failed"
            )

            yield rx.toast.error(
                str(exc)
                if isinstance(exc, ValueError)
                else (
                    "Guest import failed. "
                    "Please check the file and try again."
                )
            )

        finally:
            self.is_loading = False
            yield

    @staticmethod
    def _detect_upload_mime_type(
            filename: str,
    ) -> str:
        """
        Determine MIME type for uploaded guest-list files.
        """

        filename = (
            str(filename or "")
            .strip()
            .lower()
        )

        if filename.endswith(".csv"):
            return "text/csv"

        if filename.endswith(".xlsx"):
            return (
                "application/vnd.openxmlformats-officedocument."
                "spreadsheetml.sheet"
            )

        if filename.endswith(".xls"):
            return "application/vnd.ms-excel"

        # Safe fallback for unknown spreadsheet formats.
        return "application/octet-stream"

    # ========================================================================
    # QR GENERATION METHODS
    # ========================================================================

    def generate_branded_qr(self, guest_id: str, event_id: str) -> str:
        from guest_management.services.qr_service import QRService
        service = QRService()
        url = service.guest_url(guest_id, int(event_id))
        return service.generate_qr_with_logo(url, self.company_logo if self.company_logo else None)

    def generate_secure_token(self, guest_id: str, event_id: str) -> str:
        from guest_management.core.security import create_qr_token
        return create_qr_token(int(event_id), guest_id)


    def show_guest_qr_dialog(self, guest_id: str, guest_name: str, event_id: str):
        qr_image = self.generate_branded_qr(guest_id, event_id)
        self.selected_guest_qr = qr_image
        self.selected_guest_name = guest_name
        self.guest_qr_dialog_open = True

    def close_guest_qr_dialog(self):
        self.guest_qr_dialog_open = False
        self.selected_guest_qr = ""
        self.selected_guest_name = ""

    def open_qr_dialog(self):
        self.qr_dialog_open = True

    def close_qr_dialog(self):
        self.qr_dialog_open = False
        self.show_qr_dialog = False

    # ========================================================================
    # LOGO METHODS
    # ========================================================================

    async def handle_logo_upload(self, files: List[rx.UploadFile]):
        if not files or len(files) == 0:
            yield rx.toast.error("No file selected.")
            return
        file = files[0]
        self.company_logo_filename = file.filename
        content = await file.read()
        encoded = base64.b64encode(content).decode()
        if file.filename.lower().endswith('.png'):
            img_type = 'png'
        elif file.filename.lower().endswith(('.jpg', '.jpeg')):
            img_type = 'jpeg'
        elif file.filename.lower().endswith('.gif'):
            img_type = 'gif'
        else:
            img_type = 'png'
        self.company_logo = f"data:image/{img_type};base64,{encoded}"
        yield rx.toast.success("Logo uploaded successfully!")

    def clear_logo(self):
        self.company_logo = ""
        self.company_logo_filename = ""
        return rx.toast.success("Logo cleared")

    def show_logo_dialog(self):
        self.logo_dialog_open = True

    def close_logo_dialog(self):
        self.logo_dialog_open = False

    # ========================================================================
    # DOWNLOAD / EXPORT METHODS
    # ========================================================================

    def download_guest_list(self):
        if not self.guest_data:
            return rx.toast.error("No data to download")

        df = pd.DataFrame(self.guest_data)
        columns_to_export = ["Name", "Email", "ID", "Table", "Status", "Email Sent"]
        if "Dietary" in df.columns:
            columns_to_export.insert(4, "Dietary")
        if "Amount" in df.columns:
            columns_to_export.insert(4, "Amount")

        available_cols = [c for c in columns_to_export if c in df.columns]
        df = df[available_cols]
        csv_data = df.to_csv(index=False)

        return rx.download(
            data=csv_data,
            filename=f"guest_list_event_{self.current_event_id}.csv",
        )

    def export_guest_data_to_excel(self):
        if not self.guest_data or len(self.guest_data) == 0:
            return rx.toast.error("No guest data to export")

        try:
            df = pd.DataFrame(self.guest_data)
            columns_to_drop = ['email_sent', 'amount_value']
            for col in columns_to_drop:
                if col in df.columns:
                    df = df.drop(columns=[col])

            column_mapping = {
                'Name': 'Name', 'Email': 'Email', 'ID': 'Guest ID',
                'Table': 'Table Number', 'Status': 'Check-in Status',
                'Email Sent': 'Email Sent', 'Amount': 'Voucher Amount',
                'Team': 'Team Name', 'Diet': 'Dietary Restrictions'
            }
            rename_dict = {k: v for k, v in column_mapping.items() if k in df.columns}
            if rename_dict:
                df = df.rename(columns=rename_dict)

            output = BytesIO()
            with pd.ExcelWriter(output, engine='openpyxl') as writer:
                df.to_excel(writer, sheet_name='Guests', index=False)
                worksheet = writer.sheets['Guests']
                for column in worksheet.columns:
                    max_length = 0
                    column_letter = column[0].column_letter
                    for cell in column:
                        try:
                            if len(str(cell.value)) > max_length:
                                max_length = len(str(cell.value))
                        except:
                            pass
                    adjusted_width = min(max_length + 2, 50)
                    worksheet.column_dimensions[column_letter].width = adjusted_width

            output.seek(0)
            excel_data = output.read()
            encoded_data = base64.b64encode(excel_data).decode()

            event_name = self.current_event.get("name", "event") if self.current_event else "event"
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"guest_list_{event_name}_{timestamp}.xlsx"

            return rx.download(
                data=f"data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{encoded_data}",
                filename=filename,
            )

        except Exception as e:
            logger.error(f"Export error: {e}")
            return rx.toast.error(f"Error exporting data: {str(e)}")

    # ========================================================================
    # CLEAR TABLE
    # ========================================================================

    def clear_table_dialog(self):
        if not self.guest_data:
            return rx.toast.error("No guests to clear")
        self.show_clear_table_confirm = True

    def cancel_clear_table(self):
        self.show_clear_table_confirm = False
        self.close_upload_dialog()

    async def confirm_clear_table(self):
        self.is_loading = True
        yield
        try:

            auth = await self.get_state(AuthState)
            event_id = int(self.current_event_id)

            try:
                EventService().get_event(
                    event_id,
                    auth.user_id,
                    auth.user,
                )
            except (AuthorizationError, EventNotFoundError):
                yield rx.toast.error("Permission denied")
                return

            GuestRepository().delete_by_event(event_id)
            EventRepository().update_counts(event_id, 0, 0)
            self.guest_data = []
            self.filtered_data = []
            self.columns = []
            self.uploaded_filename = ""
            self.selected_file_name = ""
            self.show_clear_table_confirm = False
            yield rx.toast.success("Guest list cleared successfully")
            async for update in self.update_dashboard_stats():
                yield update
        except Exception:
            logger.exception("Unable to clear guest list")
            yield rx.toast.error("Unable to clear guest list")
        finally:
            self.is_loading = False
            yield

    # ========================================================================
    # LUCKY DRAW METHODS
    # ========================================================================

    # ========================================================================
    # CONTACT METHODS
    # ========================================================================

    def set_contact_name(self, value: str):
        self.contact_name = value

    def set_contact_email(self, value: str):
        self.contact_email = value

    def set_contact_message(self, value: str):
        self.contact_message = value

    async def submit_contact(self):
        if not self.contact_name or not self.contact_email or not self.contact_message:
            yield rx.toast.error("Please fill all fields")
            return

        self.contact_success = True
        yield rx.toast.success("Thank you! We'll get back to you soon.")

        self.contact_name = ""
        self.contact_email = ""
        self.contact_message = ""

        import asyncio
        await asyncio.sleep(3)
        self.contact_success = False
        yield

    # ========================================================================
    # EMAIL METHODS
    # ========================================================================

    def open_email_dialog(self, guest: dict):
        self.selected_guest_for_email = guest
        self.email_dialog_open = True

    def close_email_dialog(self):
        self.email_dialog_open = False
        self.selected_guest_for_email = None

    # ========================================================================
    # CHECK HAS AMOUNTS
    # ========================================================================

    def check_has_amounts(self):
        self.has_amounts = any(g.get("amount", 0) > 0 for g in self.guest_data)

    # guest_management/state/guest_state.py - Complete method

    def set_current_event_from_url(self):
        """Set current event ID from URL path - works for all routes."""
        try:
            current_path = self.router.url.path
            logger.info(f"Setting event from URL path: {current_path}")

            # Only process if we're on a route that should have an event ID
            if "/dashboard/" not in current_path and "/scanner/" not in current_path and "/checkin/" not in current_path:
                logger.info(f"Skipping event extraction for: {current_path}")
                return

            # Match all routes that contain an event_id
            import re
            # Patterns for different routes
            patterns = [
                r"/dashboard/([^/?#]+)",
                r"/scanner/([^/?#]+)",
                r"/scanner_guest/([^/?#]+)",
                r"/scanner-guest/([^/?#]+)",
                r"/checkin/([^/?#]+)",
                r"/success/([^/?#]+)",
                r"/already-checked/([^/?#]+)",
                r"/already_checked/([^/?#]+)",
            ]

            for pattern in patterns:
                match = re.search(pattern, current_path)
                if match:
                    event_id = match.group(1)
                    try:
                        int(event_id)
                        self.current_event_id = event_id
                        logger.info(f"Set current_event_id to: {self.current_event_id}")

                        # Try to load event details
                        db = get_db()
                        event_response = db.table("events") \
                            .select("*") \
                            .eq("id", int(event_id)) \
                            .execute()

                        if event_response.data:
                            self.current_event = event_response.data[0]
                            self.event_type = self.current_event.get("event_type", "company_dinner")
                            logger.info(f"Loaded event: {self.current_event.get('name')}")
                        return
                    except ValueError:
                        continue

            logger.info(f"No valid event_id found in URL path: {current_path}")

        except Exception as e:
            logger.error(f"Error setting event from URL: {e}")

    # Add this method to GuestState class in guest_state.py

    async def on_load_dashboard(self):
        """Called when dashboard page loads - sets event from URL and loads data."""
        logger.info("Dashboard on_load triggered")

        # Check if we're on a dashboard route with an event ID
        current_path = self.router.url.path
        logger.info(f"Current path: {current_path}")

        # Only proceed if we're on a dashboard route
        if not current_path.startswith("/dashboard/"):
            logger.info(f"Skipping event load for non-dashboard route: {current_path}")
            return

        # Set event from URL - this will extract the ID from the path
        self.set_current_event_from_url()

        # If still no event ID, try to get it from the router using regex
        if not self.current_event_id:
            try:
                import re
                match = re.search(r"/dashboard/([^/?#]+)", current_path)
                if match:
                    event_id = match.group(1)
                    self.current_event_id = event_id
                    logger.info(f"Set current_event_id from dashboard route: {self.current_event_id}")

                    # Load event details
                    db = get_db()
                    event_response = db.table("events") \
                        .select("*") \
                        .eq("id", int(event_id)) \
                        .execute()
                    if event_response.data:
                        self.current_event = event_response.data[0]
                        self.event_type = self.current_event.get("event_type", "company_dinner")
            except Exception as e:
                logger.error(f"Error extracting event from URL: {e}")

        # Load guests if we have an event
        if self.current_event_id:
            logger.info(f"Loading guests for event: {self.current_event_id}")
            async for update in self.load_guests():
                yield update

        else:
            logger.warning("No event ID found, cannot load guests")


# For backward compatibility
State = GuestState
