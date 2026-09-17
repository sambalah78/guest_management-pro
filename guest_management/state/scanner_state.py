"""Production multi-scanner state.

Reflex state only manages workstation/UI state. Database concurrency is handled
by CheckinService -> PostgreSQL check_in_guest RPC.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Dict, List, Optional
from urllib.parse import urlparse, parse_qs
from guest_management.state.auth_state import AuthState
import reflex as rx

from guest_management.core.exceptions import EventLahError, GuestAlreadyCheckedInError, GuestNotFoundError
from guest_management.services.checkin_service import CheckinService
from guest_management.services.event_service import EventService
from guest_management.services.scanner_service import ScannerService
from guest_management.services.scanner_station_auth_service import (
    ScannerStationAuthService,
)

logger = logging.getLogger(__name__)


class ScannerState(rx.State):
    scanner_ready: bool = False
    scanner_status: str = "Ready to check in"
    scanner_status_icon: str = "idle"
    scanner_mode: str = "camera"
    camera_on: bool = True
    external_scanner_detected: bool = False
    scan_buffer: str = ""
    scan_timer_running: bool = False

    kiosk_state: str = "idle"
    last_checkin_name: str = ""
    last_checkin_table: str = ""
    checkin_guest_name: str = ""
    checkin_table_number: str = ""
    checkin_team_name: str = ""

    scanner_devices: List[Dict[str, Any]] = []
    active_scanners: Dict[str, bool] = {}
    scanner_buffers: Dict[str, str] = {}
    scanner_scan_status: Dict[str, str] = {}
    last_scanned_guest: Dict[str, str] = {}

    current_event_id: str = ""
    current_event: Optional[Dict[str, Any]] = None
    station_access_token: str = ""

    # The scanner station currently bound to this browser workstation.
    # This is deliberately separate from the logged-in admin identity.
    current_scanner_id: str = ""
    current_scanner_name: str = ""
    station_authenticated: bool = False
    station_authenticating: bool = False
    station_auth_error: str = ""
    present_count: int = 0
    total_guests: int = 0
    absent_count: int = 0
    is_loading: bool = False
    last_scanned_code: str = ""
    last_checkin_time: float = 0.0

    scanner_provisioning: bool = False
    scanner_provision_error: str = ""
    new_scanner_name: str = ""
    new_scanner_token: str = ""
    new_scanner_device_id: str = ""
    scanner_management_open: bool = False


    async def provision_scanner(self):
        """Provision a scanner station for the current event."""
        if not self.current_event_id:
            self.scanner_provision_error = "No event selected."
            return rx.toast.error("No event selected")

        scanner_name = self.new_scanner_name.strip()

        if not scanner_name:
            self.scanner_provision_error = "Please enter a scanner station name."
            return rx.toast.error("Enter a scanner station name")

        auth = await self.get_state(AuthState)

        if not auth.user_id:
            self.scanner_provision_error = "Your admin session is not authenticated."
            return rx.toast.error("Authentication required")

        if not auth.is_event_admin:
            self.scanner_provision_error = "You are not authorized to manage scanners."
            return rx.toast.error("Not authorized")

        self.scanner_provisioning = True
        self.scanner_provision_error = ""
        self.new_scanner_token = ""
        self.new_scanner_device_id = ""

        try:
            scanner, token = ScannerStationAuthService().provision_station(
                event_id=int(self.current_event_id),
                device_name=scanner_name,
                assigned_by=auth.user_id,
            )

            self.new_scanner_token = token
            self.new_scanner_device_id = str(
                scanner.get("device_id") or ""
            )

            await self.initialize_scanners()

            return rx.toast.success(
                "Scanner station provisioned. Save the credential now."
            )

        except Exception:
            logger.exception("Failed to provision scanner station")
            self.scanner_provision_error = (
                "Unable to provision scanner station."
            )
            return rx.toast.error("Unable to provision scanner station")

        finally:
            self.scanner_provisioning = False

    def set_station_access_token(self, token: str):
        self.station_access_token = str(token or "")

    @rx.var
    def scanner_devices_active(self) -> int:
        return sum(1 for active in self.active_scanners.values() if active)

    def set_new_scanner_name(self, value: str):
        self.new_scanner_name = str(value or "")

    def clear_scanner_provisioning(self):
        self.new_scanner_name = ""
        self.new_scanner_token = ""
        self.new_scanner_device_id = ""
        self.scanner_provision_error = ""

    def open_scanner_management(self):
        self.scanner_management_open = True
        self.scanner_provision_error = ""
        self.new_scanner_token = ""
        self.new_scanner_device_id = ""

    def set_scanner_management_open(self, is_open: bool):
        self.scanner_management_open = bool(is_open)
        if not is_open:
            self.clear_scanner_provisioning()

    def close_scanner_management(self):
        self.scanner_management_open = False
        self.clear_scanner_provisioning()

    async def authenticate_station(self):
        access_token = self.station_access_token
        """Authenticate this browser workstation to a scanner station."""

        if not self.current_event_id:
            self.station_auth_error = "No event selected"
            return rx.toast.error("Scanner is not bound to an event")

        token = str(access_token or "").strip()

        if not token:
            self.station_auth_error = "Scanner station access token is required"
            self.station_authenticated = False
            return rx.toast.error("Enter the scanner station access token")

        self.station_authenticating = True
        self.station_auth_error = ""

        try:
            scanner = ScannerStationAuthService().authenticate(
                int(self.current_event_id),
                token,
            )

            if not scanner:
                self.station_authenticated = False
                self.current_scanner_id = ""
                self.current_scanner_name = ""
                self.station_auth_error = (
                    "Invalid, inactive, or incorrectly assigned scanner station"
                )
                return rx.toast.error("Scanner station authentication failed")

            self.current_scanner_id = str(
                scanner.get("device_id") or ""
            )
            self.current_scanner_name = str(
                scanner.get("device_name")
                or self.current_scanner_id
            )

            self.station_authenticated = True
            self.station_auth_error = ""

            self.scanner_status = (
                f"Station authenticated: {self.current_scanner_name}"
            )
            self.scanner_status_icon = "idle"

            return rx.toast.success(
                f"Station {self.current_scanner_name} authenticated"
            )

        except Exception:
            logger.exception("Scanner station authentication failed")
            self.station_authenticated = False
            self.current_scanner_id = ""
            self.current_scanner_name = ""
            self.station_auth_error = (
                "Unable to authenticate scanner station"
            )
            self.scanner_status = "Unable to authenticate scanner station"
            self.scanner_status_icon = "error"
            return rx.toast.error(
                "Unable to authenticate scanner station"
            )

        finally:
            self.station_authenticating = False

    def enable_guest_scanner(self):
        """Enable the current workstation scanner only.

        Station authentication will bind current_scanner_id before this method
        is allowed to operate in production.
        """
        if not self.current_event_id:
            self.scanner_status = "No event selected"
            self.scanner_status_icon = "error"
            return rx.toast.error("Scanner is not bound to an event")

        if not self.current_scanner_id:
            self.scanner_status = "Scanner station not assigned"
            self.scanner_status_icon = "error"
            return rx.toast.error(
                "This workstation is not assigned to a scanner station."
            )
        if not self.station_authenticated:
            self.scanner_status = "Scanner station authentication required"
            self.scanner_status_icon = "error"
            return rx.toast.error(
                "Authenticate this workstation before starting the scanner"
            )

        self.scanner_ready = True
        self.scanner_status = "Scanner active - Ready for QR code"
        self.scanner_status_icon = "idle"
        self.scanner_mode = "external"

        return rx.call_script("""
            window.scannerActive = true;
            const input = document.querySelector(
                '.scanner-hidden-input, .reflex-scan-bridge input'
            );
            if (input) input.focus();

            if (typeof activateScanner === 'function') {
                activateScanner();
            }
        """)

    def disable_guest_scanner(self):
        self.scanner_ready = False
        self.scanner_status = "Scanner stopped"
        self.scanner_status_icon = "idle"
        return rx.call_script("""
            window.scannerActive = false;
            if (typeof deactivateAllScanners === 'function') deactivateAllScanners();
            else if (typeof disableAllScanners === 'function') disableAllScanners();
        """)

    def reset_scanner_for_next_guest(self):
        self.scanner_status_icon = "idle"
        self.scanner_status = "Ready for next attendee code..."
        self.checkin_guest_name = ""
        self.checkin_table_number = ""
        self.checkin_team_name = ""
        self.is_loading = False
        self.last_scanned_code = ""
        return rx.call_script("""
            const inp = document.querySelector('.reflex-scan-bridge input');
            if (inp) {
                const setter = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set;
                setter.call(inp, '');
                inp.dispatchEvent(new Event('input', {bubbles: true}));
                inp.focus();
            }
            window.scannerActive = true;
        """)

    def set_scanner_mode(self, mode: str):
        self.scanner_mode = mode
        self.camera_on = mode == "camera"

    def set_external_scanner_detected(self, detected: bool):
        self.external_scanner_detected = bool(detected)

    def toggle_camera_power(self):
        self.camera_on = not self.camera_on
        if self.camera_on:
            return rx.call_script("setTimeout(() => { if (typeof startCamera === 'function') startCamera(); }, 100);")
        return rx.call_script("if (typeof stopCamera === 'function') stopCamera();")

    def close_camera_scanner(self):
        self.scanner_mode = ""
        self.camera_on = False
        return rx.call_script("if (typeof stopCamera === 'function') stopCamera();")

    def dismiss_checkin_alert(self):
        self.last_checkin_name = ""
        self.last_checkin_table = ""

    def close_scanner_and_go_to_dashboard(self):
        if not self.current_event_id:
            return rx.redirect("/events")
        return rx.redirect(f"/dashboard/{self.current_event_id}")

    async def set_current_event_from_url(self):
        try:
            path = getattr(self.router.url, "path", "") or ""
            match = re.search(r"/(?:scanner|scanner_guest|scanner-guest|dashboard|success|already-checked|already_checked)/(\d+)", path)
            if not match:
                return
            event_id = int(match.group(1))
            event = EventService().get_event_public(event_id)
            self.current_event_id = str(event_id)
            self.current_event = event
            self.total_guests = int(event.get("guest_count") or 0)
            self.present_count = int(event.get("present_count") or 0)
            self.absent_count = max(0, self.total_guests - self.present_count)
        except Exception as exc:
            logger.exception("Unable to bind scanner to event")
            self.scanner_status = "Unable to load event"
            self.scanner_status_icon = "error"

    def open_guest_scanner(self):
        if not self.current_event_id:
            return rx.toast.error("Select an event first")
        return rx.call_script(
            f"window.open('/scanner-guest/{self.current_event_id}', '_blank', 'width=500,height=700,resizable=yes,scrollbars=yes');"
        )

    def open_kiosk_window(self):
        if not self.current_event_id:
            return rx.toast.error("Select an event first")
        return rx.call_script(
            f"window.open('/scanner-guest/{self.current_event_id}', '_blank', 'width=1080,height=1920,menubar=no,toolbar=no,location=no,status=no');"
        )

    async def handle_high_volume_scan(self, raw_code: str):
        """Process a scan from the authenticated workstation."""

        if not self.current_event_id:
            self.scanner_status = "No event selected"
            self.scanner_status_icon = "error"
            return

        if not self.station_authenticated:
            self.scanner_status = "Scanner station authentication required"
            self.scanner_status_icon = "error"
            return

        if not self.current_scanner_id:
            self.scanner_status = "Scanner station not assigned"
            self.scanner_status_icon = "error"
            return

        return await self._process_checkin(
            raw_code,
            self.current_event_id,
            self.current_scanner_id,
        )

    async def _process_checkin(self, raw_code: str, event_id: str, scanner_id: str = ""):
        if self.is_loading:
            return
        if not event_id:
            self.scanner_status = "No event selected"
            self.scanner_status_icon = "error"
            return
        raw_code = (raw_code or "").strip()
        if not raw_code:
            return

        self.is_loading = True
        self.scanner_status = "Checking..."
        self.scanner_status_icon = "processing"
        self.last_scanned_code = raw_code
        yield

        try:
            result = CheckinService().check_in(
                int(event_id),
                raw_code,
                scanner_id,
                scanner_access_token=self.station_access_token,
            )
            self.checkin_guest_name = str(result.get("guest_name") or "Guest")
            self.checkin_table_number = str(result.get("table_number") or "TBD")
            self.checkin_team_name = str(result.get("team_name") or "")
            self.present_count = int(result.get("present_count") or self.present_count)
            self.total_guests = int(result.get("total_guests") or self.total_guests)
            self.absent_count = max(0, self.total_guests - self.present_count)
            self.last_checkin_name = self.checkin_guest_name
            self.last_checkin_table = self.checkin_table_number
            self.scanner_status = "CHECK-IN SUCCESSFUL"
            self.scanner_status_icon = "success"
            self.last_checkin_time = time.time()
            self.scanner_ready = True
            yield rx.toast.success(f"Welcome, {self.checkin_guest_name}")
        except GuestAlreadyCheckedInError as exc:
            self.scanner_status = str(exc)
            self.scanner_status_icon = "error"
            yield rx.toast.warning(str(exc))
        except GuestNotFoundError:
            self.scanner_status = "Guest not found for this event"
            self.scanner_status_icon = "error"
            yield rx.toast.error(self.scanner_status)
        except EventLahError as exc:
            self.scanner_status = exc.message
            self.scanner_status_icon = "error"
            yield rx.toast.error(exc.message)
        except Exception:
            logger.exception("Unexpected check-in failure")
            self.scanner_status = "Temporary check-in error. Please try again."
            self.scanner_status_icon = "error"
            yield rx.toast.error(self.scanner_status)
        finally:
            self.is_loading = False
            yield

    async def handle_scan(
        self,
        guest_id: str = "",
        event_id: str = "",
    ):
        """Compatibility handler for authenticated scanner check-in."""

        target_event = event_id or self.current_event_id

        if not self.station_authenticated:
            self.scanner_status = (
                "Scanner station authentication required"
            )
            self.scanner_status_icon = "error"
            yield rx.toast.error(
                "Authenticate this scanner station before scanning"
            )
            return

        if not self.current_scanner_id:
            self.scanner_status = "Scanner station not assigned"
            self.scanner_status_icon = "error"
            yield rx.toast.error(
                "This workstation is not assigned to a scanner station"
            )
            return

        async for item in self._process_checkin(
            guest_id,
            target_event,
            self.current_scanner_id,
        ):
            yield item

    async def handle_multi_scanner_input(
            self,
            device_id: str,
            scanned_data: str,
    ):
        """Compatibility handler for scanner bridge input.

        The supplied device_id is intentionally ignored for identity.
        The browser workstation must already be authenticated.
        """

        event_id = self.current_event_id

        if not event_id:
            self.scanner_status = "No event selected"
            self.scanner_status_icon = "error"
            return

        if not self.station_authenticated:
            self.scanner_status = "Scanner station authentication required"
            self.scanner_status_icon = "error"
            return

        if not self.current_scanner_id:
            self.scanner_status = "Scanner station not assigned"
            self.scanner_status_icon = "error"
            return

        async for item in self._process_checkin(
                scanned_data,
                event_id,
                self.current_scanner_id,
        ):
            yield item

        try:
            ScannerService().record_scan(
                int(event_id),
                self.current_scanner_id,
            )
        except Exception:
            logger.exception(
                "Failed to record scanner metric for %s",
                self.current_scanner_id,
            )

    @staticmethod
    def _extract_table_number(guest: dict) -> str:
        return str(guest.get("table_number") or guest.get("Table") or "TBD")

    @staticmethod
    def _extract_team_name(guest: dict) -> str:
        return str(guest.get("team_name") or guest.get("Team") or guest.get("team") or "")

    async def initialize_scanners(self):
        if not self.current_event_id:
            return

        try:
            self.scanner_devices = ScannerService().get_scanners(
                int(self.current_event_id)
            )

            self.active_scanners = {
                str(d["device_id"]): bool(d.get("is_active", False))
                for d in self.scanner_devices
            }

            self.scanner_scan_status = {
                str(d["device_id"]): (
                    "ready"
                    if d.get("is_active", False)
                    else "inactive"
                )
                for d in self.scanner_devices
            }

        except Exception:
            logger.exception("Failed to load scanner stations")
            self.scanner_devices = []
            self.active_scanners = {}
            self.scanner_scan_status = {}

    async def _create_memory_scanners(self):
        await self.initialize_scanners()

    async def _create_scanner_devices(self):
        await self.initialize_scanners()

    async def activate_scanner(self, device_id: str):
        if not self.current_event_id:
            return rx.toast.error("No event selected")

        device_id = str(device_id).strip()
        auth = await self.get_state(AuthState)

        if not auth.user_id:
            return rx.toast.error("Authentication required")

        if not auth.is_event_admin:
            return rx.toast.error("Not authorized")

        try:
            scanner = ScannerService().activate_scanner(
                int(self.current_event_id),
                device_id,
            )

            if not scanner:
                return rx.toast.error("Scanner station not found")

            self.active_scanners[device_id] = True
            self.scanner_scan_status[device_id] = "ready"

            return rx.toast.success("Scanner station activated")

        except Exception:
            logger.exception("Failed to activate scanner %s", device_id)
            return rx.toast.error("Unable to activate scanner station")

    async def deactivate_scanner(self, device_id: str):
        if not self.current_event_id:
            return rx.toast.error("No event selected")

        device_id = str(device_id).strip()
        auth = await self.get_state(AuthState)

        if not auth.user_id:
            return rx.toast.error("Authentication required")

        if not auth.is_event_admin:
            return rx.toast.error("Not authorized")

        try:
            scanner = ScannerService().deactivate_scanner(
                int(self.current_event_id),
                device_id,
            )

            if not scanner:
                return rx.toast.error("Scanner station not found")

            self.active_scanners[device_id] = False
            self.scanner_scan_status[device_id] = "inactive"

            return rx.toast.success("Scanner station deactivated")

        except Exception:
            logger.exception("Failed to deactivate scanner %s", device_id)
            return rx.toast.error("Unable to deactivate scanner station")

    async def kiosk_on_load(self):
        await self.set_current_event_from_url()
        self.kiosk_state = "idle"

    def kiosk_start_scan(self):
        self.kiosk_state = "scanning"

    def kiosk_cancel_scan(self):
        self.kiosk_state = "idle"
        return rx.call_script("if (typeof stopKioskQR === 'function') stopKioskQR();")

    async def kiosk_handle_scan(self, scanned_data: str):
        # A scanner workstation must be authenticated before
        # it can perform a check-in.
        if (
                not self.current_event_id
                or not self.station_authenticated
                or not self.current_scanner_id
        ):
            self.kiosk_state = "error"
            self.scanner_status_icon = "error"
            return

        self.kiosk_state = "processing"

        scanner_id = self.current_scanner_id

        async for item in self._process_checkin(
                scanned_data,
                self.current_event_id,
                scanner_id,
        ):
            yield item

        self.kiosk_state = (
            "success"
            if self.scanner_status_icon == "success"
            else "error"
        )

    def kiosk_reset(self):
        self.kiosk_state = "idle"
        self.checkin_guest_name = ""
        self.checkin_table_number = ""
        self.checkin_team_name = ""

    async def poll_latest_checkin(self):
        # Realtime dashboard updates should eventually replace polling. This
        # method is retained as a safe compatibility hook.
        return

    def set_scanner_status(self, status: str, icon: str = ""):
        self.scanner_status = status
        if icon:
            self.scanner_status_icon = icon

    def set_scanner_ready(self, ready: bool):
        self.scanner_ready = bool(ready)

    def set_kiosk_state(self, state: str):
        self.kiosk_state = state

    def reset_kiosk(self):
        self.kiosk_state = "idle"
        self.checkin_guest_name = ""
        self.checkin_table_number = ""
