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

import reflex as rx

from guest_management.core.exceptions import EventLahError, GuestAlreadyCheckedInError, GuestNotFoundError
from guest_management.services.checkin_service import CheckinService
from guest_management.services.event_service import EventService
from guest_management.services.scanner_service import ScannerService

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
    present_count: int = 0
    total_guests: int = 0
    absent_count: int = 0
    is_loading: bool = False
    last_scanned_code: str = ""
    last_checkin_time: float = 0.0

    @rx.var
    def scanner_devices_active(self) -> int:
        return sum(1 for active in self.active_scanners.values() if active)

    def enable_guest_scanner(self):
        if not self.current_event_id:
            self.scanner_status = "No event selected"
            self.scanner_status_icon = "error"
            return rx.toast.error("Scanner is not bound to an event")
        self.scanner_ready = True
        self.scanner_status = "Scanner active - Ready for QR code"
        self.scanner_status_icon = "idle"
        self.scanner_mode = "external"
        return rx.call_script("""
            window.scannerActive = true;
            const input = document.querySelector('.scanner-hidden-input, .reflex-scan-bridge input');
            if (input) input.focus();
            if (typeof activateAllScanners === 'function') activateAllScanners();
            else if (typeof enableAllScanners === 'function') enableAllScanners();
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
        return await self._process_checkin(raw_code, self.current_event_id)

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
            result = CheckinService().check_in(int(event_id), raw_code, scanner_id)
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

    async def handle_scan(self, guest_id: str = "", event_id: str = ""):
        target_event = event_id or self.current_event_id
        async for item in self._process_checkin(guest_id, target_event):
            yield item

    async def handle_multi_scanner_input(self, device_id: str, scanned_data: str):
        device_id = (device_id or "UNKNOWN").strip()[:100]
        async for item in self._process_checkin(scanned_data, self.current_event_id, device_id):
            yield item
        try:
            ScannerService().record_scan(device_id)
        except Exception:
            logger.exception("Failed to record scanner metric for %s", device_id)

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
            self.scanner_devices = ScannerService().initialize_scanners(int(self.current_event_id), 8)
            self.active_scanners = {str(d.get("device_id")): False for d in self.scanner_devices}
            self.scanner_scan_status = {str(d.get("device_id")): "idle" for d in self.scanner_devices}
        except Exception:
            logger.exception("Failed to initialize scanners")
            self.scanner_devices = []

    async def _create_memory_scanners(self):
        await self.initialize_scanners()

    async def _create_scanner_devices(self):
        await self.initialize_scanners()

    def activate_scanner(self, device_id: str):
        device_id = str(device_id)
        self.active_scanners[device_id] = True
        self.scanner_scan_status[device_id] = "ready"

    def deactivate_scanner(self, device_id: str):
        device_id = str(device_id)
        self.active_scanners[device_id] = False
        self.scanner_scan_status[device_id] = "idle"

    async def kiosk_on_load(self):
        await self.set_current_event_from_url()
        self.kiosk_state = "idle"

    def kiosk_start_scan(self):
        self.kiosk_state = "scanning"

    def kiosk_cancel_scan(self):
        self.kiosk_state = "idle"
        return rx.call_script("if (typeof stopKioskQR === 'function') stopKioskQR();")

    async def kiosk_handle_scan(self, scanned_data: str):
        self.kiosk_state = "processing"
        async for item in self._process_checkin(scanned_data, self.current_event_id, "KIOSK"):
            yield item
        self.kiosk_state = "success" if self.scanner_status_icon == "success" else "error"

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
