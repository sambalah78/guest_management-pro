# guest_management/state/event_state.py
"""Event management state."""

import reflex as rx
from typing import List, Optional, Dict, Any
from datetime import datetime
import base64
import os

from guest_management.core.config import settings
from guest_management.utils.constants import EVENT_TYPES
from guest_management.database_client import get_db
import logging

logger = logging.getLogger(__name__)


class EventState(rx.State):
    """Event management state."""

    # Events
    events: List[Dict[str, Any]] = []
    current_event: Optional[Dict[str, Any]] = None
    current_event_id: str = ""
    event_type: str = "company_dinner"

    # New event form
    new_event_name: str = ""
    new_event_company_name: str = ""
    new_event_date: str = ""
    new_event_time: str = ""
    new_event_venue: str = ""
    new_event_theme: str = ""
    event_logo: str = ""
    wedding_invitation_card: str = ""

    # Loading
    is_loading: bool = False

    # ========================================================================
    # AUTH STATE - SHARED VIA REFERENCE
    # ========================================================================
    # Store user_id and auth status directly in EventState
    # These will be synced from AuthState
    user_id: str = ""
    is_authenticated: bool = False

    # Event type configuration is centralized in utils.constants.EVENT_TYPES.

    # --- Computed Properties ---

    @rx.var
    def formatted_events(self) -> List[Dict[str, Any]]:
        """Return events with formatted dates."""
        formatted = []
        for event in self.events:
            event_copy = event.copy()
            created_at = event.get("created_at", "")
            if created_at:
                try:
                    dt = datetime.fromisoformat(created_at.replace("Z", "+00:00"))
                    event_copy["formatted_created_at"] = dt.strftime("%d %b %Y")
                except:
                    event_copy["formatted_created_at"] = created_at
            else:
                event_copy["formatted_created_at"] = ""
            formatted.append(event_copy)
        return formatted

    @rx.var
    def event_config_name(self) -> str:
        """Get event type name."""
        event_type = (
            self.current_event.get("event_type")
            if self.current_event
            else self.event_type
        ) or "company_dinner"

        config = EVENT_TYPES.get(
            event_type,
            EVENT_TYPES["company_dinner"],
        )
        return config["name"]

    @rx.var
    def event_config_icon(self) -> str:
        """Get event type icon."""
        event_type = (
            self.current_event.get("event_type")
            if self.current_event
            else self.event_type
        ) or "company_dinner"

        config = EVENT_TYPES.get(
            event_type,
            EVENT_TYPES["company_dinner"],
        )
        return config["icon"]

    @rx.var
    def show_lucky_draw(self) -> bool:
        """Check if lucky draw should be shown."""
        config = EVENT_TYPES.get(self.event_type, EVENT_TYPES["company_dinner"])
        return config["features"].get("lucky_draw", False)

    @rx.var
    def show_food_vouchers(self) -> bool:
        """Check if food vouchers should be shown."""
        config = EVENT_TYPES.get(self.event_type, EVENT_TYPES["company_dinner"])
        return config["features"].get("food_vouchers", False)

    @rx.var
    def show_plus_one(self) -> bool:
        """Check if plus-one management should be shown."""
        config = EVENT_TYPES.get(self.event_type, EVENT_TYPES["company_dinner"])
        return config["features"].get("plus_one_management", False)

    @rx.var
    def show_parent_guardian(self) -> bool:
        """Check if parent/guardian info should be shown."""
        config = EVENT_TYPES.get(self.event_type, EVENT_TYPES["company_dinner"])
        return config["features"].get("parent_guardian_info", False)

    @rx.var
    def show_dietary_restrictions(self) -> bool:
        """Check if dietary restrictions should be shown."""
        config = EVENT_TYPES.get(self.event_type, EVENT_TYPES["company_dinner"])
        return config["features"].get("dietary_restrictions", False)

    # --- Actions ---

    # In event_state.py - Make sure load_events is working

    async def load_events(self):
        """Load events through EventService, scoped to the authenticated user."""
        try:
            from guest_management.state.auth_state import AuthState
            auth = await self.get_state(AuthState)
            if not auth.user_id:
                self.events = []
                yield rx.redirect("/login")
                return
            self.user_id = auth.user_id
            self.is_authenticated = True
            from guest_management.services.event_service import EventService
            self.events = EventService().get_user_events(auth.user_id)
        except Exception:
            logger.exception("Unable to load events")
            self.events = []
            yield rx.toast.error("Could not load events")
        finally:
            self.is_loading = False
            yield

    # ========================================================================
    # SYNC AUTH DATA - Called from AuthState after login
    # ========================================================================

    def sync_auth_data(self, user_id: str, is_authenticated: bool, access_token: str = ""):
        """Backward-compatible auth sync without persisting tokens."""
        self.user_id = user_id
        self.is_authenticated = is_authenticated

    # ========================================================================
    # CREATE EVENT
    # ========================================================================
    async def create_event(self):
        if not self.new_event_name.strip():
            yield rx.toast.error("Event name is required")
            return

        self.is_loading = True
        yield

        try:
            from guest_management.state.auth_state import AuthState
            from guest_management.services.event_service import EventService
            from guest_management.services.google_drive_asset_service import (
                GoogleDriveAssetService,
            )

            auth = await self.get_state(AuthState)

            if not auth.user_id:
                yield rx.redirect("/login")
                return

            event_data = {
                "name": self.new_event_name.strip(),
                "company_name": self.new_event_company_name or None,
                "date": self.new_event_date or None,
                "time": self.new_event_time or None,
                "venue": self.new_event_venue or None,
                "theme": self.new_event_theme or None,
                "event_type": self.event_type or "company_dinner",
            }

            if self.event_logo:
                event_data["logo"] = self.event_logo

            if self.wedding_invitation_card:
                event_data["wedding_invitation"] = (
                    self.wedding_invitation_card
                )

            # Create a Google Drive service using the authenticated
            # user's Google OAuth context.
            drive_service = GoogleDriveAssetService(
                user_id=auth.user_id
            )

            # EventService handles:
            # 1. DB event creation
            # 2. Google Drive event folder creation
            # 3. Drive folder ID persistence
            # 4. Logo/invitation upload
            new_event = EventService(
                drive_service=drive_service
            ).create_event(
                event_data,
                auth.user_id,
            )

            self.current_event = new_event
            self.current_event_id = str(new_event["id"])
            self.event_type = new_event.get(
                "event_type",
                "company_dinner",
            )

            self.new_event_name = ""
            self.new_event_company_name = ""
            self.new_event_date = ""
            self.new_event_time = ""
            self.new_event_venue = ""
            self.new_event_theme = ""
            self.event_logo = ""
            self.wedding_invitation_card = ""

            yield rx.toast.success(
                "Event created successfully"
            )

            yield rx.redirect(
                f"/dashboard/{new_event['id']}"
            )

        except Exception:
            logger.exception("Create event failed")
            yield rx.toast.error(
                "Unable to create event. Please try again."
            )

        finally:
            self.is_loading = False
            yield

    # ========================================================================
    # DELETE EVENT
    # ========================================================================

    async def delete_event(self, event_id):
        try:
            event_id = int(event_id)
        except (TypeError, ValueError):
            yield rx.toast.error("Invalid event ID")
            return
        try:
            from guest_management.state.auth_state import AuthState
            from guest_management.services.event_service import EventService
            auth = await self.get_state(AuthState)

            if not auth.user_id:
                yield rx.redirect("/login")
                return

            # Only approved EventLah accounts can create events.
            if not settings.is_event_creator(auth.user_email):
                yield rx.toast.error(
                    "Your Google account is not authorized to create events."
                )
                return
            EventService().delete_event(event_id, auth.user_id)
            yield rx.toast.success("Event deleted successfully")
            async for _ in self.load_events():
                yield _
        except Exception:
            logger.exception("Delete event failed")
            yield rx.toast.error("Unable to delete event")

    # ========================================================================
    # SELECT EVENT
    # ========================================================================

    async def select_event(self, event_id):
        try:
            event_id = int(event_id)
        except (TypeError, ValueError):
            yield rx.toast.error("Invalid event ID")
            return
        self.is_loading = True
        yield
        try:
            from guest_management.state.auth_state import AuthState
            from guest_management.services.event_service import EventService
            auth = await self.get_state(AuthState)
            event = EventService().get_event(event_id, auth.user_id)
            self.current_event = event
            self.current_event_id = str(event_id)
            self.event_type = event.get("event_type", "company_dinner")
            yield rx.redirect(f"/dashboard/{event_id}")
        except Exception:
            logger.exception("Select event failed")
            yield rx.toast.error("Event not found or access denied")
            yield rx.redirect("/events")
        finally:
            self.is_loading = False
            yield

    # ========================================================================
    # REFRESH EVENT TYPE
    # ========================================================================

    async def refresh_current_event_type(self):
        if not self.current_event_id:
            return
        try:
            from guest_management.services.event_service import EventService
            self.event_type = EventService().get_event_type(int(self.current_event_id)) or "company_dinner"
            if self.current_event:
                self.current_event["event_type"] = self.event_type
        except Exception:
            logger.exception("Unable to refresh event type")

    # ========================================================================
    # UI HELPERS
    # ========================================================================

    def set_event_type(self, event_type: str):
        self.event_type = event_type

    def set_event_field(self, field: str, value: str):
        field_mapping = {
            "name": "new_event_name",
            "company_name": "new_event_company_name",
            "date": "new_event_date",
            "time": "new_event_time",
            "venue": "new_event_venue",
            "theme": "new_event_theme"
        }
        if field in field_mapping:
            setattr(self, field_mapping[field], value)

    def select_event_type(self, event_type: str):
        self.event_type = event_type
        self.new_event_name = ""
        self.new_event_company_name = ""
        self.new_event_date = ""
        self.new_event_time = ""
        self.new_event_venue = ""
        self.new_event_theme = ""
        self.event_logo = ""
        self.wedding_invitation_card = ""
        return rx.redirect("/create-event")

    def go_back_to_event_types(self):
        self.event_type = ""
        return rx.redirect("/select-event-type")

    def clear_event_logo(self):
        self.event_logo = ""
        return rx.toast.success("Logo removed")

    def clear_wedding_invitation(self):
        self.wedding_invitation_card = ""
        return rx.toast.success("Invitation removed")

    async def handle_logo_upload_for_event(self, files: List[rx.UploadFile]):
        if not files or len(files) == 0:
            return
        file = files[0]
        content = await file.read()
        encoded = base64.b64encode(content).decode()
        ext = file.filename.split('.')[-1].lower()
        self.event_logo = f"data:image/{ext};base64,{encoded}"
        yield rx.toast.success("Logo uploaded successfully!")

    async def handle_invitation_upload(self, files: List[rx.UploadFile]):
        if not files or len(files) == 0:
            return
        file = files[0]
        content = await file.read()
        encoded = base64.b64encode(content).decode()
        ext = file.filename.split('.')[-1].lower()
        self.wedding_invitation_card = f"data:image/{ext};base64,{encoded}"
        yield rx.toast.success("Invitation card uploaded successfully!")

    def navigate_to_event(self, event_id):
        event_id_str = str(event_id) if event_id else ""
        if event_id_str:
            return rx.redirect(f"/dashboard/{event_id_str}")
        return rx.toast.error("Invalid event ID")

    def handle_select_event(self, event_id: str):
        if not event_id:
            yield rx.toast.error("Invalid event ID")
            return
        event_id_str = str(event_id).strip()
        try:
            int(event_id_str)
        except ValueError:
            yield rx.toast.error("Invalid event ID format")
            return
        yield self.select_event(event_id_str)

    def handle_delete_event(self, event_id: str):
        if not event_id:
            yield rx.toast.error("Invalid event ID")
            return
        event_id_str = str(event_id).strip()
        try:
            int(event_id_str)
        except ValueError:
            yield rx.toast.error("Invalid event ID format")
            return
        yield self.delete_event(event_id_str)

