# guest_management/pages/scanner.py
import reflex as rx
from guest_management.state import ScannerState
from guest_management.utils.constants import GOLD, BLACK, LIGHT_GRAY


def scanner_page() -> rx.Component:
    """Production hardened camera layout containing leak safeguards."""
    return rx.center(
        rx.vstack(
            rx.heading("Camera QR Verification Lane", color=GOLD, size="4"),

            # Interactive Stream Display Field
            rx.box(
                id="qr-reader",
                width="100%",
                max_width="450px",
                min_height="300px",
                border=f"2px solid {GOLD}",
                border_radius="12px",
                background=BLACK,
            ),

            rx.hstack(
                rx.button("Initialize Camera", on_click=rx.call_script("window.initiateCameraInterface();"), bg="green",
                          color="white"),
                rx.button("Kill Camera Stream", on_click=rx.call_script("window.shutdownCameraInterface();"), bg="red",
                          color="white"),
                spacing="3"
            ),

            # Hidden Communication Gateway
            rx.box(
                rx.input(on_change=ScannerState.handle_high_volume_scan, value=""),
                class_name="reflex-scan-bridge",
                style={"position": "absolute", "left": "-9999px", "opacity": "0"}
            ),
            spacing="4",
            padding="2em"
        ),
        rx.script(src="/qr_scanner.js"),
        width="100vw",
        height="100vh",
        bg=BLACK
    )