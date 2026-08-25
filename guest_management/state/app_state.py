# guest_management/state/app_state.py
"""AppState - Backward compatibility module."""

import reflex as rx

from .guest_state import GuestState as State
from .auth_state import AuthState
from .event_state import EventState
from .guest_state import GuestState
from .scanner_state import ScannerState
from .voucher_state import VoucherState
from .ui_state import UIState
from .success_state import SuccessState


# Define KioskScannerState here
class KioskScannerState(rx.State):
    """Isolate scanner properties into a localized sub-state."""
    scanner_ready: bool = False
    scanner_status_icon: str = "idle"
    scanner_status: str = "Ready"
    last_processed_checkin: dict = {
        "name": "",
        "table_no": "",
        "company": "",
        "timestamp": ""
    }

    def clear_session(self):
        self.last_processed_checkin = {"name": "", "table_no": "", "company": "", "timestamp": ""}
        self.scanner_status_icon = "idle"


__all__ = [
    "State",
    "AuthState",
    "EventState",
    "GuestState",
    "ScannerState",
    "VoucherState",
    "UIState",
    "SuccessState",
    "KioskScannerState",
]