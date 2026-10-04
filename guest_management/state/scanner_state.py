"""Production multi-scanner state.

Reflex state only manages workstation/UI state. Database concurrency is handled
by CheckinService -> PostgreSQL check_in_guest RPC.
"""

from __future__ import annotations

import logging
import inspect
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
    station_access_token: str = ""  # compatibility alias; UI no longer exposes tokens
    station_pin: str = ""
    station_session_token: str = rx.SessionStorage(name="eventlah_scanner_station_session")

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
    scanner_manual_guest_id: str = ""
    last_checkin_time: float = 0.0

    scanner_provisioning: bool = False
    scanner_provision_error: str = ""
    new_scanner_name: str = ""
    new_scanner_token: str = ""  # compatibility alias
    def set_new_scanner_pin(self, value: str):
        """Update the PIN entered in the scanner provisioning form."""
        value = str(value or "").strip()

        # Keep only numeric characters and limit to four digits.
        value = "".join(ch for ch in value if ch.isdigit())[:4]

        self.new_scanner_pin = value
    new_scanner_pin: str = ""
    new_scanner_device_id: str = ""
    scanner_management_open: bool = False



    # --------------------------------------------------------
    # Admin-only scanner PIN recovery state.
    # These are Reflex State fields and MUST remain at class
    # scope, before any ScannerState methods.
    # --------------------------------------------------------

    scanner_pin_recovery_visible: bool = False
    scanner_pin_recovery_device_id: str = ""
    scanner_pin_recovery_name: str = ""
    scanner_pin_recovery_value: str = ""
    async def provision_scanner(self):
        """Provision a scanner station with an admin-assigned 4-digit PIN."""
        if not self.current_event_id:
            self.scanner_provision_error = "No event selected."
            return rx.toast.error("No event selected")

        scanner_name = self.new_scanner_name.strip()
        scanner_pin = self.new_scanner_pin.strip()

        if not scanner_name:
            self.scanner_provision_error = "Please enter a scanner station name."
            return rx.toast.error("Enter a scanner station name")

        if not re.fullmatch(r"\d{4}", scanner_pin):
            self.scanner_provision_error = "Scanner PIN must be exactly 4 digits."
            return rx.toast.error("Enter a 4-digit scanner PIN")

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
        self.new_scanner_pin = ""
        self.new_scanner_device_id = ""

        try:
            provision_method = ScannerStationAuthService().provision_station
            params = inspect.signature(provision_method).parameters
            kwargs = {
                "event_id": int(self.current_event_id),
                "device_name": scanner_name,
                "assigned_by": auth.user_id,
                "actor_user_id": auth.user_id,
                "actor_user": auth.user,
                "pin": scanner_pin,
            }
            kwargs = {k: v for k, v in kwargs.items() if k in params}

            scanner, returned_pin = provision_method(**kwargs)

            self.new_scanner_pin = str(returned_pin or scanner_pin)
            self.new_scanner_token = self.new_scanner_pin
            self.new_scanner_device_id = str(scanner.get("device_id") or "")

            await self.initialize_scanners()

            return rx.toast.success(
                "Scanner station provisioned. Give the scanner agent the 4-digit PIN."
            )

        except ValueError as exc:
            self.scanner_provision_error = str(exc)
            return rx.toast.error(str(exc))
        except Exception:
            logger.exception("Failed to provision scanner station")
            self.scanner_provision_error = "Unable to provision scanner station."
            return rx.toast.error("Unable to provision scanner station")
        finally:
            self.scanner_provisioning = False
    async def reveal_scanner_pin(self, device_id: str):
        """Reveal a scanner PIN only to an authenticated event admin."""
        device_id = str(device_id or "").strip()
        if not device_id:
            return rx.toast.error("Scanner station not found")

        auth = await self.get_state(AuthState)
        if not auth.user_id or not auth.is_event_admin:
            return rx.toast.error("Not authorized")

        if not self.current_event_id:
            return rx.toast.error("No event selected")

        try:
            scanner = self._scanner_service_call(
                "get_scanner",
                event_id=int(self.current_event_id),
                device_id=device_id,
                user_id=auth.user_id,
                user=auth.user,
            )
            if not scanner:
                return rx.toast.error("Scanner station not found")

            ciphertext = str(scanner.get("pin_ciphertext") or "").strip()
            if not ciphertext:
                return rx.toast.error(
                    "This scanner has no recoverable PIN. Re-provision it with a new PIN."
                )

            pin = ScannerStationAuthService.decrypt_pin(ciphertext)
            self.scanner_pin_recovery_device_id = device_id
            self.scanner_pin_recovery_name = str(
                scanner.get("device_name") or device_id
            )
            self.scanner_pin_recovery_value = pin
            self.scanner_pin_recovery_visible = True
            return rx.toast.success("Scanner PIN revealed to the administrator")
        except Exception:
            logger.exception("Failed to reveal scanner PIN")
            self.hide_scanner_pin()
            return rx.toast.error("Unable to recover scanner PIN")




    async def toggle_scanner_pin(self, device_id: str):
        """Toggle scanner PIN visibility as a proper async Reflex event handler."""
        device_id = str(device_id or "").strip()

        if not device_id:
            return rx.toast.error("Scanner station not found")

        if (
            self.scanner_pin_recovery_visible
            and self.scanner_pin_recovery_device_id == device_id
        ):
            self.hide_scanner_pin()
            return rx.toast.info("Scanner PIN hidden")

        return await self.reveal_scanner_pin(device_id)
    def hide_scanner_pin(self):
        self.scanner_pin_recovery_device_id = ""
        self.scanner_pin_recovery_name = ""
        self.scanner_pin_recovery_value = ""
        self.scanner_pin_recovery_visible = False

    def set_station_access_token(self, token: str):
        self.station_access_token = str(token or "")

    def set_scanner_manual_guest_id(self, value: str):
        self.scanner_manual_guest_id = str(value or "").strip()
    def set_station_pin(self, pin: str):
        self.station_pin = str(pin or "")




    @rx.var
    def scanner_devices_active(self) -> int:
        return sum(1 for active in self.active_scanners.values() if active)

    def set_new_scanner_name(self, value: str):
        self.new_scanner_name = str(value or "")

    def clear_scanner_provisioning(self):
        self.new_scanner_name = ""
        self.new_scanner_token = ""
        self.new_scanner_pin = ""
        self.new_scanner_device_id = ""
        self.scanner_provision_error = ""

    def _bind_event_from_route(self) -> bool:
        """Bind scanner state to the event in the current dashboard/scanner route."""
        if self.current_event_id:
            return True

        try:
            path = str(getattr(self.router.url, "path", "") or "")
            match = re.search(
                r"/(?:dashboard|scanner|scanner_guest|scanner-guest)/(\d+)(?:/|$)",
                path,
            )
            if not match:
                return False

            event_id = match.group(1)
            self.current_event_id = str(event_id)

            event = EventService().get_event_public(int(event_id))
            if event:
                self.current_event = event
                self.total_guests = int(event.get("guest_count") or 0)
                self.present_count = int(event.get("present_count") or 0)
                self.absent_count = max(
                    0,
                    self.total_guests - self.present_count,
                )
            return True
        except Exception:
            logger.exception("Unable to bind scanner state to route event")
            return False



    def open_scanner_pin_recovery(self, scanner_id: str) -> None:
        """Open the admin-only PIN recovery display for a scanner station."""
        self.scanner_pin_recovery_station_id = str(scanner_id or "")
        self.scanner_pin_recovery_name = ""
        self.scanner_pin_recovery_pin = ""
        self.scanner_pin_recovery_visible = True

        # Populate from the already-loaded scanner list where possible.
        for scanner in self.scanner_devices:
            if str(scanner.get("id", "")) == str(scanner_id):
                self.scanner_pin_recovery_name = str(
                    scanner.get("device_name")
                    or scanner.get("name")
                    or ""
                )
                self.scanner_pin_recovery_pin = str(
                    scanner.get("pin")
                    or scanner.get("access_pin")
                    or ""
                )
                break

    def close_scanner_pin_recovery(self) -> None:
        """Close the admin-only PIN recovery display."""
        self.scanner_pin_recovery_visible = False
        self.scanner_pin_recovery_station_id = ""
        self.scanner_pin_recovery_name = ""
        self.scanner_pin_recovery_pin = ""

    async def open_scanner_management(self):
        """Open Scanner Stations only for an authenticated event admin."""
        if not self._bind_event_from_route():
            self.scanner_provision_error = "No event selected."
            return rx.toast.error("Unable to determine the current event")

        auth = await self.get_state(AuthState)
        if not auth.user_id:
            self.scanner_provision_error = (
                "Your admin session is not authenticated."
            )
            return rx.toast.error("Authentication required")

        if not auth.is_event_admin:
            self.scanner_provision_error = (
                "You are not authorized to manage scanners."
            )
            return rx.toast.error("Not authorized")

        self.scanner_management_open = True
        self.scanner_provision_error = ""
        self.new_scanner_token = ""
        self.new_scanner_pin = ""
        self.new_scanner_device_id = ""

        if hasattr(self, "scanner_pin_recovery_device_id"):
            self.scanner_pin_recovery_device_id = ""
            self.scanner_pin_recovery_name = ""
            self.scanner_pin_recovery_value = ""
            self.scanner_pin_recovery_visible = False

        try:
            self.scanner_devices = self._scanner_service_call(
                "get_scanners",
                event_id=int(self.current_event_id),
                user_id=auth.user_id,
                user=auth.user,
            )

            self.active_scanners = {
                str(d.get("device_id") or ""): bool(d.get("is_active", False))
                for d in self.scanner_devices
                if d.get("device_id")
            }

            self.scanner_scan_status = {
                str(d.get("device_id") or ""): (
                    "ready" if d.get("is_active", False) else "inactive"
                )
                for d in self.scanner_devices
                if d.get("device_id")
            }

        except Exception:
            logger.exception("Unable to load scanner stations")
            self.scanner_devices = []
            self.scanner_provision_error = "Unable to load scanner stations."
            return rx.toast.error("Unable to load scanner stations")

    def set_scanner_management_open(self, is_open: bool):
        self.scanner_management_open = bool(is_open)
        if not is_open:
            self.clear_scanner_provisioning()

    def close_scanner_management(self):
        self.scanner_management_open = False
        self.clear_scanner_provisioning()

    async def authenticate_station(self):
        """Authenticate this browser tab once with the assigned 4-digit PIN."""
        if not self.current_event_id:
            self.station_auth_error = "No event selected"
            return rx.toast.error("Scanner is not bound to an event")

        pin = str(self.station_pin or "").strip()
        if not re.fullmatch(r"\d{4}", pin):
            self.station_auth_error = "Enter the 4-digit scanner PIN"
            self.station_authenticated = False
            return rx.toast.error("Enter the 4-digit scanner PIN")

        self.station_authenticating = True
        self.station_auth_error = ""

        try:
            scanner = ScannerStationAuthService().authenticate(
                int(self.current_event_id),
                pin,
            )

            if not scanner:
                self.station_authenticated = False
                self.current_scanner_id = ""
                self.current_scanner_name = ""
                self.station_session_token = ""
                self.station_auth_error = (
                    "Invalid, inactive, or incorrectly assigned scanner PIN"
                )
                return rx.toast.error("Scanner PIN authentication failed")

            self.current_scanner_id = str(
                scanner.get("device_id") or ""
            )
            self.current_scanner_name = str(
                scanner.get("device_name")
                or self.current_scanner_id
            )
            self.station_session_token = (
                ScannerStationAuthService.issue_session(scanner)
            )
            self.station_pin = ""
            self.station_access_token = ""
            self.station_authenticated = True
            self.station_auth_error = ""
            self.scanner_status = (
                f"Station authenticated: {self.current_scanner_name}"
            )
            self.scanner_status_icon = "idle"
            self.scanner_ready = False

            return [
                rx.toast.success(
                    f"Station {self.current_scanner_name} authenticated"
                ),
                rx.redirect(
                    f"/scanner-guest/{self.current_event_id}"
                ),
            ]

        except Exception:
            logger.exception(
                "Scanner station authentication failed"
            )
            self.station_authenticated = False
            self.current_scanner_id = ""
            self.current_scanner_name = ""
            self.station_session_token = ""
            self.station_auth_error = (
                "Unable to authenticate scanner station"
            )
            self.scanner_status = (
                "Unable to authenticate scanner station"
            )
            self.scanner_status_icon = "error"
            return rx.toast.error(
                "Unable to authenticate scanner station"
            )
        finally:
            self.station_authenticating = False
    async def restore_station_session(self):
        """Restore the scanner session after navigation/refresh in this tab."""
        if not self.current_event_id:
            return

        token = str(self.station_session_token or "").strip()
        if not token:
            self.station_authenticated = False
            return

        try:
            scanner = ScannerStationAuthService().authenticate(
                int(self.current_event_id),
                token,
            )
            if not scanner:
                self.station_session_token = ""
                self.station_authenticated = False
                self.current_scanner_id = ""
                self.current_scanner_name = ""
                return

            self.current_scanner_id = str(scanner.get("device_id") or "")
            self.current_scanner_name = str(
                scanner.get("device_name") or self.current_scanner_id
            )
            self.station_authenticated = True
            self.station_auth_error = ""
            self.scanner_status_icon = "idle"
            self.scanner_status = f"Station authenticated: {self.current_scanner_name}"
        except Exception:
            logger.exception("Unable to restore scanner station session")
            self.station_session_token = ""
            self.station_authenticated = False

    async def scanner_login_on_load(self):
        self.is_loading = True
        yield
        await self.set_current_event_from_url()
        await self.restore_station_session()
        if self.station_authenticated and self.current_event_id:
            self.is_loading = False
            yield rx.redirect(f"/scanner-guest/{self.current_event_id}")
            return
        self.is_loading = False

    async def scanner_guest_on_load(self):
        """Bind event and restore the per-browser scanner session."""
        self.is_loading = True
        yield
        await self.set_current_event_from_url()
        await self.restore_station_session()

        if (
            not self.station_authenticated
            and self.current_event_id
        ):
            self.is_loading = False
            yield rx.redirect(
                f"/scanner-login/{self.current_event_id}"
            )
            return
        self.is_loading = False
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
        self.scanner_manual_guest_id = ""
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

    def close_scanner_workstation(self):
        """End this scanner workstation session and close/fallback safely."""
        event_id = str(self.current_event_id or "").strip()

        self.scanner_ready = False
        self.scanner_status_icon = "idle"
        self.scanner_status = "Scanner workstation closed"
        self.station_session_token = ""
        self.station_authenticated = False
        self.current_scanner_id = ""
        self.current_scanner_name = ""
        self.station_pin = ""
        self.station_access_token = ""
        self.scanner_mode = ""
        self.camera_on = False

        if not event_id:
            return rx.call_script("""
                window.scannerActive = false;
                if (typeof deactivateAllScanners === 'function') deactivateAllScanners();
                else if (typeof disableAllScanners === 'function') disableAllScanners();

                if (window.opener && !window.opener.closed) {
                    window.close();
                }
            """)

        return rx.call_script(f"""
            window.scannerActive = false;
            if (typeof deactivateAllScanners === 'function') deactivateAllScanners();
            else if (typeof disableAllScanners === 'function') disableAllScanners();

            if (window.opener && !window.opener.closed) {{
                window.close();
            }} else {{
                window.location.href = '/scanner-login/{event_id}';
            }}
        """)
    def close_scanner_and_go_to_dashboard(self):
        if not self.current_event_id:
            return rx.redirect("/events")
        return rx.redirect(f"/dashboard/{self.current_event_id}")

    async def set_current_event_from_url(self):
        try:
            path = getattr(self.router.url, "path", "") or ""
            match = re.search(r"/(?:scanner-login|scanner|scanner_guest|scanner-guest|dashboard|success|already-checked|already_checked)/(\d+)", path)
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

    @rx.var
    def scanner_login_url(self) -> str:
        if not self.current_event_id:
            return ""
        origin = str(getattr(self.router.url, "origin", "") or "").rstrip("/")
        return f"{origin}/scanner-login/{self.current_event_id}"

    def open_scanner_login(self):
        if not self.current_event_id:
            return rx.toast.error("Select an event first")
        return rx.redirect(
            f"/scanner-login/{self.current_event_id}"
        )
    def copy_scanner_login_link(self):
        event_id = str(self.current_event_id or "").strip()
        if not event_id:
            return rx.toast.error("Select an event first")
        return rx.call_script(
            f"navigator.clipboard.writeText(window.location.origin + '/scanner-login/{event_id}')"
        )
    def clear_scanner_station_session(self):
        self.station_session_token = ""
        self.station_authenticated = False
        self.current_scanner_id = ""
        self.current_scanner_name = ""
        self.station_pin = ""
        return rx.toast.success("Scanner station logged out")
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
        """Process a scan from the authenticated scanner workstation."""
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

        async for item in self._process_checkin(
            raw_code,
            self.current_event_id,
            self.current_scanner_id,
        ):
            yield item
    async def _process_checkin(
        self,
        raw_code: str,
        event_id: str,
        scanner_id: str = "",
        manual: bool = False,
    ):
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
                scanner_access_token=str(self.station_session_token or ""),
                manual=manual,
            )

            self.checkin_guest_name = str(
                result.get("guest_name") or "Guest"
            )
            self.checkin_table_number = str(
                result.get("table_number") or "TBD"
            )
            self.checkin_team_name = str(
                result.get("team_name") or ""
            )
            self.present_count = int(
                result.get("present_count") or self.present_count
            )
            self.total_guests = int(
                result.get("total_guests") or self.total_guests
            )
            self.absent_count = max(
                0,
                self.total_guests - self.present_count,
            )
            self.last_checkin_name = self.checkin_guest_name
            self.last_checkin_table = self.checkin_table_number
            self.scanner_status = "CHECK-IN SUCCESSFUL"
            self.scanner_status_icon = "success"
            self.last_checkin_time = time.time()
            self.scanner_ready = True
            yield rx.toast.success(
                f"Welcome, {self.checkin_guest_name}"
            )

        except GuestAlreadyCheckedInError as exc:
            self.scanner_status = str(exc)
            self.scanner_status_icon = "warning"
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
            self.scanner_status = (
                "Temporary check-in error. Please try again."
            )
            self.scanner_status_icon = "error"
            yield rx.toast.error(self.scanner_status)

        finally:
            self.is_loading = False
            yield
    async def handle_manual_checkin(self, guest_id: str = ""):
        """Check in a guest by ID from the authenticated scanner workstation."""
        target = str(
            guest_id or self.scanner_manual_guest_id or ""
        ).strip()

        if not self.current_event_id:
            yield rx.toast.error("No event selected")
            return
        if not self.station_authenticated:
            yield rx.toast.error("Authenticate this scanner station first")
            return
        if not self.current_scanner_id:
            yield rx.toast.error("Scanner station not assigned")
            return
        if not target:
            yield rx.toast.error("Enter the guest ID")
            return

        async for item in self._process_checkin(
            target,
            self.current_event_id,
            self.current_scanner_id,
            manual=True,
        ):
            yield item
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

    def _scanner_service_call(self, method_name: str, **kwargs):
        """Call ScannerService using only supported parameters."""
        method = getattr(ScannerService(), method_name)
        params = inspect.signature(method).parameters
        filtered = {k: v for k, v in kwargs.items() if k in params}
        return method(**filtered)


    def _scanner_service_call(self, method_name: str, **kwargs):
        """Call scanner service across compatible service signatures."""
        method = getattr(ScannerService(), method_name)
        params = inspect.signature(method).parameters
        filtered = {k: v for k, v in kwargs.items() if k in params}
        return method(**filtered)

    def _scanner_service_call(self, method_name: str, **kwargs):
        """Call scanner service across compatible service signatures."""
        method = getattr(ScannerService(), method_name)
        params = inspect.signature(method).parameters
        filtered = {k: v for k, v in kwargs.items() if k in params}
        return method(**filtered)

    def _scanner_service_call(self, method_name: str, **kwargs):
        """Call scanner service across compatible service signatures."""
        method = getattr(ScannerService(), method_name)
        params = inspect.signature(method).parameters
        filtered = {k: v for k, v in kwargs.items() if k in params}
        return method(**filtered)

    async def initialize_scanners(self):
        """Load scanner stations for the current event."""
        if not self.current_event_id:
            self.scanner_devices = []
            return

        try:
            auth = await self.get_state(AuthState)
            if not auth.user_id or not auth.is_event_admin:
                raise PermissionError("Event administrator access required")

            self.scanner_devices = self._scanner_service_call(
                "get_scanners",
                event_id=int(self.current_event_id),
                user_id=auth.user_id,
                user=auth.user,
            )

            self.active_scanners = {
                str(d.get("device_id") or ""): bool(d.get("is_active", False))
                for d in self.scanner_devices
                if d.get("device_id")
            }
            self.scanner_scan_status = {
                str(d.get("device_id") or ""): (
                    "ready" if d.get("is_active", False) else "inactive"
                )
                for d in self.scanner_devices
                if d.get("device_id")
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
        try:
            auth = await self.get_state(AuthState)
            if not auth.user_id or not auth.is_event_admin:
                return rx.toast.error("Not authorized")

            scanner = self._scanner_service_call(
                "activate_scanner",
                event_id=int(self.current_event_id),
                device_id=device_id,
                user_id=auth.user_id,
                user=auth.user,
            )
            if not scanner:
                scanner = self._scanner_service_call(
                    "get_scanner",
                    event_id=int(self.current_event_id),
                    device_id=device_id,
                    user_id=auth.user_id,
                    user=auth.user,
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
        """Deactivate one scanner station for the current event."""
        device_id = str(device_id or "").strip()

        if not device_id or device_id.startswith("(isTrue("):
            return rx.toast.error("Scanner station not found")

        if not self.current_event_id:
            self._bind_event_from_route()

        if not self.current_event_id:
            return rx.toast.error("No event selected")

        try:
            auth = await self.get_state(AuthState)
            if not auth.user_id or not auth.is_event_admin:
                return rx.toast.error("Not authorized")

            event_id = int(self.current_event_id)

            scanner = self._scanner_service_call(
                "get_scanner",
                event_id=event_id,
                device_id=device_id,
                user_id=auth.user_id,
                user=auth.user,
            )

            if not scanner:
                return rx.toast.error("Scanner station not found")

            result = self._scanner_service_call(
                "deactivate_scanner",
                event_id=event_id,
                device_id=device_id,
                user_id=auth.user_id,
                user=auth.user,
            )

            self.scanner_devices = self._scanner_service_call(
                "get_scanners",
                event_id=event_id,
                user_id=auth.user_id,
                user=auth.user,
            ) or []

            self.active_scanners = {
                str(item.get("device_id") or ""): bool(item.get("is_active", False))
                for item in self.scanner_devices
                if item.get("device_id")
            }

            self.scanner_scan_status = {
                str(item.get("device_id") or ""): (
                    "ready" if item.get("is_active", False) else "inactive"
                )
                for item in self.scanner_devices
                if item.get("device_id")
            }

            if self.current_scanner_id == device_id:
                self.scanner_ready = False

            refreshed = next(
                (
                    item for item in self.scanner_devices
                    if str(item.get("device_id") or "").strip() == device_id
                ),
                None,
            )

            if refreshed is not None and not bool(refreshed.get("is_active", False)):
                return rx.toast.success("Scanner station deactivated")

            if result is not None:
                return rx.toast.success("Scanner station deactivated")

            return rx.toast.error("Scanner station could not be deactivated")

        except Exception:
            logger.exception("Failed to deactivate scanner %s", device_id)
            return rx.toast.error("Unable to deactivate scanner station")

    async def remove_scanner(self, device_id: str):
        """Permanently remove a scanner station from the current event."""
        device_id = str(device_id or "").strip()

        if not device_id or device_id.startswith("(isTrue("):
            return rx.toast.error("Scanner station not found")

        if not self.current_event_id:
            self._bind_event_from_route()

        if not self.current_event_id:
            return rx.toast.error("No event selected")

        try:
            auth = await self.get_state(AuthState)
            if not auth.user_id or not auth.is_event_admin:
                return rx.toast.error("Not authorized")

            event_id = int(self.current_event_id)

            scanner = self._scanner_service_call(
                "get_scanner",
                event_id=event_id,
                device_id=device_id,
                user_id=auth.user_id,
                user=auth.user,
            )

            if not scanner:
                return rx.toast.error("Scanner station not found")

            # A DELETE operation may return no representation rows even when
            # the database deletion succeeded. Treat absence of the row after
            # DELETE as the authoritative success check.
            self._scanner_service_call(
                "delete_scanner",
                event_id=event_id,
                device_id=device_id,
                user_id=auth.user_id,
                user=auth.user,
            )

            remaining = self._scanner_service_call(
                "get_scanner",
                event_id=event_id,
                device_id=device_id,
                user_id=auth.user_id,
                user=auth.user,
            )

            if remaining:
                return rx.toast.error("Scanner station could not be removed")

            if self.current_scanner_id == device_id:
                self.station_session_token = ""
                self.station_authenticated = False
                self.current_scanner_id = ""
                self.current_scanner_name = ""
                self.station_pin = ""
                self.scanner_ready = False
                self.scanner_status = "Scanner station removed"
                self.scanner_status_icon = "idle"

            self.scanner_pin_recovery_device_id = ""
            self.scanner_pin_recovery_name = ""
            self.scanner_pin_recovery_value = ""
            self.scanner_pin_recovery_visible = False

            self.scanner_devices = [
                item
                for item in self.scanner_devices
                if str(item.get("device_id") or "").strip() != device_id
            ]

            self.active_scanners.pop(device_id, None)
            self.scanner_buffers.pop(device_id, None)
            self.scanner_scan_status.pop(device_id, None)

            return rx.toast.success("Scanner station removed")

        except Exception:
            logger.exception("Failed to remove scanner %s", device_id)
            return rx.toast.error("Unable to remove scanner station")
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
