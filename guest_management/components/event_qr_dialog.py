# guest_management/components/event_qr_dialog.py
import reflex as rx
from guest_management.state import State, UIState
from guest_management.utils.constants import GOLD, BLACK, DARK_GRAY

def event_qr_dialog():
    """Event QR code dialog."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.heading("Event QR Code", size="5", color=GOLD),
                rx.cond(
                    State.qr_url,
                    rx.image(
                        src=State.qr_url,
                        width="250px",
                        height="250px",
                        border=f"2px solid {GOLD}",
                        border_radius="8px"
                    ),
                    rx.text("QR Code not available", color="gray")
                ),
                rx.text("Scan to access check-in page", color="gray"),
                rx.button(
                    "Close",
                    on_click=UIState.close_qr_dialog,
                    bg=GOLD,
                    color=BLACK
                ),
                spacing="4",
                padding="2em",
            ),
            bg=DARK_GRAY,
            border=f"2px solid {GOLD}",
        ),
        open=UIState.qr_dialog_open,
    )