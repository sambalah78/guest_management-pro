# components/guest_qr_dialog.py
import reflex as rx
from guest_management.state import State, GOLD, BLACK, DARK_GRAY

def guest_qr_dialog():
    """Guest QR code dialog."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.heading(State.selected_guest_name, size="5", color=GOLD),
                rx.cond(
                    State.selected_guest_qr != "",
                    rx.image(src=State.selected_guest_qr, width="200px", height="200px", border=f"2px solid {GOLD}",
                             border_radius="8px"),
                    rx.text("QR Code not available", color="gray"),
                ),
                rx.text("Present this QR code at the entrance", color="gray"),
                rx.button("Close", on_click=State.close_guest_qr_dialog, bg=GOLD, color=BLACK),
                spacing="4",
                padding="2em",
            ),
            bg=DARK_GRAY,
            border=f"2px solid {GOLD}",
        ),
        open=State.guest_qr_dialog_open,
    )