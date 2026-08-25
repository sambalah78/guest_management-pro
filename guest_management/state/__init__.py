# guest_management/state/__init__.py
"""State management module - all states exported individually."""

from .auth_state import AuthState
from .event_state import EventState
from .guest_state import GuestState
from .scanner_state import ScannerState
from .voucher_state import VoucherState
from .ui_state import UIState
from .success_state import SuccessState
from .lucky_draw_state import LuckyDrawState
from .email_state import EmailState
from .app_state import KioskScannerState

# Constants
GOLD = "#D4AF37"
BLACK = "#000000"
DARK_GRAY = "#696969"
LIGHT_GRAY = "#D3D3D3"
WHITE = "#FFFFFF"

# For backward compatibility - GuestState is the most commonly used
State = GuestState

__all__ = [
    "State",
    "AuthState",
    "EventState",
    "GuestState",
    "ScannerState",
    "VoucherState",
    "UIState",
    "SuccessState",
    "LuckyDrawState",
    "EmailState",
    "KioskScannerState",

]