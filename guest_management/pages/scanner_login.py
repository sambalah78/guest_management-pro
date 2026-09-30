from guest_management.components.loading_overlay import eventlah_viewport_page
import reflex as rx

from guest_management.state import EventState, ScannerState
from guest_management.utils.constants import GOLD, BLACK, DARK_GRAY, LIGHT_GRAY


def scanner_login_page() -> rx.Component:
    """Dedicated scanner-agent login page. Admin dashboard is never exposed here."""
    return eventlah_viewport_page(rx.center(
        rx.vstack(
            rx.heading(
                rx.cond(
                    EventState.current_event,
                    EventState.current_event.get("name", "Event Check-In"),
                    "Event Check-In",
                ),
                size="7",
                color=GOLD,
                text_align="center",
            ),
            rx.text(
                "Scanner Station Login",
                size="4",
                color="white",
                weight="bold",
                text_align="center",
            ),
            rx.text(
                "Enter the 4-digit PIN assigned by the event administrator.",
                size="2",
                color=LIGHT_GRAY,
                text_align="center",
            ),
            rx.card(
                rx.vstack(
                    rx.input(
                        placeholder="4-digit PIN",
                        type="password",
                        max_length=4,
                        input_mode="numeric",
                        value=ScannerState.station_pin,
                        on_change=ScannerState.set_station_pin,
                        width="100%",
                        size="3",
                        text_align="center",
                    ),
                    rx.button(
                        rx.cond(
                            ScannerState.station_authenticating,
                            rx.spinner(size="2"),
                            rx.text("LOGIN TO SCANNER"),
                        ),
                        on_click=ScannerState.authenticate_station,
                        is_disabled=ScannerState.station_authenticating,
                        bg=GOLD,
                        color=BLACK,
                        width="100%",
                        height="54px",
                        border_radius="28px",
                        weight="bold",
                    ),
                    rx.cond(
                        ScannerState.station_auth_error != "",
                        rx.text(
                            ScannerState.station_auth_error,
                            size="2",
                            color="#ff6b6b",
                            text_align="center",
                        ),
                        rx.fragment(),
                    ),
                    spacing="3",
                    width="100%",
                ),
                bg=DARK_GRAY,
                border=f"1px solid {GOLD}66",
                border_radius="18px",
                padding="2em",
                width="100%",
                max_width="420px",
            ),
            rx.text(
                "This workstation remains signed in until its browser tab/session is closed.",
                size="1",
                color="gray",
                text_align="center",
                max_width="420px",
            ),
            spacing="4",
            width="100%",
            max_width="520px",
            padding="1.5em",
        ),
        width="100vw",
        min_height="100vh",
        bg=BLACK,
    ),
        loading=ScannerState.is_loading,
        message='Loading scanner...',
    )