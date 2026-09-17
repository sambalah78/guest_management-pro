# guest_management/pages/scanner_guest.py
import reflex as rx
from guest_management.state import EventState, ScannerState
from guest_management.utils.constants import GOLD, BLACK, DARK_GRAY, LIGHT_GRAY


def scanner_guest_page() -> rx.Component:
    """Multi-scanner workstation layout supporting 5-8 USB scanners."""
    return rx.center(
        rx.vstack(
            # Top Window Bar
            rx.hstack(
                rx.spacer(),
                rx.button(
                    rx.hstack(
                        rx.icon(tag="x", size=18, color="white"),
                        rx.text("Close Window", size="1", color="white", weight="bold"),
                        spacing="1",
                    ),
                    on_click=rx.call_script("window.close();"),
                    bg="#FF4444",
                    color="white",
                    padding="0.3em 0.8em",
                    border_radius="8px",
                ),
                width="100%",
                padding="0.5em 1em",
            ),

            # Header
            rx.vstack(
                rx.heading(
                    rx.cond(
                        EventState.current_event,
                        EventState.current_event.get("name", "Event Check-In"),
                        "Event Check-In"
                    ),
                    size="5",
                    color=GOLD,
                    text_align="center",
                ),
                rx.text(
                    "Scanner Check-In Workstation",
                    color=LIGHT_GRAY,
                    size="2",
                    text_align="center",
                ),
                spacing="1",
                width="100%",
            ),

            rx.divider(margin_y="0.3em", size="4", color_scheme="gold"),
            # Scanner Station Authentication
            rx.cond(
                ~ScannerState.station_authenticated,
                rx.card(
                    rx.vstack(
                        rx.heading(
                            "Scanner Station Login",
                            size="4",
                            color=GOLD,
                            text_align="center",
                        ),

                        rx.text(
                            "Authenticate this workstation before starting check-in.",
                            size="2",
                            color=LIGHT_GRAY,
                            text_align="center",
                        ),

                        rx.input(
                            placeholder="Scanner station access token",
                            type="password",
                            value=ScannerState.station_access_token,
                            on_change=ScannerState.set_station_access_token,
                            width="100%",
                            size="3",
                        ),

                        rx.button(
                            rx.text(
                                "AUTHENTICATE STATION",
                                weight="bold",
                            ),
                            on_click=ScannerState.authenticate_station,
                            bg=GOLD,
                            color=BLACK,
                            width="100%",
                            height="50px",
                            border_radius="25px",
                        ),

                        rx.cond(
                            ScannerState.station_authenticating,
                            rx.text(
                                "Authenticating...",
                                size="2",
                                color=GOLD,
                            ),
                        ),

                        rx.cond(
                            ScannerState.station_auth_error != "",
                            rx.text(
                                ScannerState.station_auth_error,
                                size="2",
                                color="red",
                                text_align="center",
                            ),
                        ),

                        spacing="3",
                        width="100%",
                    ),
                    bg=DARK_GRAY,
                    border=f"2px solid {GOLD}",
                    border_radius="20px",
                    padding="2em",
                    width="100%",
                    max_width="500px",
                ),
            ),
            rx.cond(
                ScannerState.station_authenticated,
                rx.card(
                    rx.vstack(
                        rx.text(
                            "AUTHENTICATED STATION",
                            size="2",
                            color="green",
                            weight="bold",
                        ),
                        rx.text(
                            ScannerState.current_scanner_name,
                            size="4",
                            color=GOLD,
                            weight="bold",
                        ),
                        rx.text(
                            ScannerState.current_scanner_id,
                            size="1",
                            color="gray",
                            font_family="monospace",
                        ),
                        spacing="1",
                        align="center",
                    ),
                    bg=DARK_GRAY,
                    border="1px solid rgba(255,255,255,0.15)",
                    border_radius="12px",
                    padding="1em",
                    width="100%",
                    max_width="500px",
                ),
            ),

            # Status Card
            rx.card(
                rx.vstack(
                    rx.cond(
                        ScannerState.scanner_status_icon == "success",
                        rx.vstack(
                            rx.icon(tag="circle_check", size=70, color="green"),
                            rx.text("CHECK-IN SUCCESSFUL!", size="4", weight="bold", color="green"),
                            rx.text(f"Welcome, {ScannerState.checkin_guest_name}!", size="3", color="white", weight="medium"),
                            rx.text("Table:", size="2", color="gray", margin_top="1em"),
                            rx.text(
                                ScannerState.checkin_table_number,
                                font_size=["4em", "5em"],
                                color=GOLD,
                                weight="bold",
                                font_family="monospace",
                            ),
                            rx.cond(
                                ScannerState.checkin_team_name,
                                rx.text(f"Team: {ScannerState.checkin_team_name}", size="2", color=GOLD),
                            ),
                            spacing="2",
                            align="center",
                        ),
                        rx.cond(
                            ScannerState.scanner_status_icon == "error",
                            rx.vstack(
                                rx.icon(tag="circle_x", size=70, color="red"),
                                rx.text("CHECK-IN FAILURE", size="4", weight="bold", color="red"),
                                rx.text(ScannerState.scanner_status, size="2", color="white", text_align="center"),
                                rx.text("Please see registration desk for assistance.", size="2", color="gray", margin_top="1em"),
                                spacing="2",
                                align="center",
                            ),
                            # IDLE STATE
                            rx.vstack(
                                rx.icon(tag="qr_code", size=70, color=GOLD),
                                rx.cond(
                                    ScannerState.scanner_ready,
                                    rx.vstack(
                                        rx.text("SCANNERS ACTIVE", size="4", weight="bold", color="green"),
                                        rx.text("Ready for QR codes from the connected scanner", color="gray", size="2"),
                                        spacing="1",
                                        align="center",
                                    ),
                                    rx.vstack(
                                        rx.text("SCANNERS STANDBY", size="4", weight="bold", color="gray"),
                                        rx.text("Click START to activate this scanner workstation", color="gray", size="2"),
                                        spacing="1",
                                        align="center",
                                    ),
                                ),
                                spacing="2",
                                align="center",
                            ),
                        ),
                    ),
                    spacing="3",
                    align="center",
                ),
                bg=DARK_GRAY,
                border=f"2px solid {GOLD}",
                border_radius="20px",
                padding="2.5em",
                width="100%",
                max_width="500px",
            ),

            # Control Buttons
            rx.vstack(
                rx.cond(
                    (~ScannerState.scanner_ready) & (ScannerState.scanner_status_icon != "success") & (ScannerState.scanner_status_icon != "error"),
                    rx.button(
                        rx.hstack(
                            rx.icon(tag="play", size=24),
                            rx.text("START SCANNER", size="4", weight="bold"),
                            spacing="2",
                        ),
                        on_click=ScannerState.enable_guest_scanner,
                        bg=GOLD,
                        color=BLACK,
                        width="100%",
                        height="60px",
                        border_radius="30px",
                        _hover={"bg": "#C9A82C"},
                    ),
                ),
                rx.cond(
                    ScannerState.scanner_ready & (ScannerState.scanner_status_icon != "success") & (ScannerState.scanner_status_icon != "error"),
                    rx.vstack(
                        rx.hstack(
                            rx.icon(tag="activity", size=18, color="green"),
                            rx.text("Scanner workstation active", size="2", color="green"),
                            spacing="2",
                        ),
                        rx.hstack(
                            rx.button(
                                rx.hstack(
                                    rx.icon(tag="pause", size=20),
                                    rx.text("Pause", size="3"),
                                    spacing="2",
                                ),
                                on_click=ScannerState.disable_guest_scanner,
                                variant="outline",
                                border_color="red",
                                color="red",
                                width="50%",
                                border_radius="30px",
                                height="50px",
                                _hover={"bg": "rgba(255,0,0,0.1)"},
                            ),
                            rx.button(
                                rx.hstack(
                                    rx.icon(tag="layout_dashboard", size=20),
                                    rx.text("Dashboard", size="3"),
                                    spacing="2",
                                ),
                                on_click=ScannerState.close_scanner_and_go_to_dashboard,
                                bg="#333333",
                                color="white",
                                width="50%",
                                border_radius="30px",
                                height="50px",
                                _hover={"bg": "#444444"},
                            ),
                            spacing="3",
                            width="100%",
                        ),
                        spacing="2",
                        width="100%",
                        align="center",
                    ),
                ),
                rx.cond(
                    (ScannerState.scanner_status_icon == "success") | (ScannerState.scanner_status_icon == "error"),
                    rx.hstack(
                        rx.button(
                            rx.hstack(
                                rx.icon(tag="refresh_cw", size=20),
                                rx.text("Next Guest", size="3", weight="bold"),
                                spacing="2",
                            ),
                            on_click=ScannerState.reset_scanner_for_next_guest,
                            bg=GOLD,
                            color=BLACK,
                            width="50%",
                            height="55px",
                            border_radius="30px",
                            _hover={"bg": "#C9A82C"},
                        ),
                        rx.button(
                            rx.hstack(
                                rx.icon(tag="layout_dashboard", size=20),
                                rx.text("Dashboard", size="3", weight="bold"),
                                spacing="2",
                            ),
                            on_click=ScannerState.close_scanner_and_go_to_dashboard,
                            bg="#333333",
                            color="white",
                            width="50%",
                            height="55px",
                            border_radius="30px",
                            _hover={"bg": "#444444"},
                        ),
                        spacing="3",
                        width="100%",
                    ),
                ),
                width="100%",
            ),

            # Hidden bridge input - CRITICAL for scanner communication
            rx.box(
                rx.input(
                    on_change=ScannerState.handle_high_volume_scan,
                    value="",
                    id="scanner-bridge-input",
                ),
                class_name="reflex-scan-bridge",
                style={"position": "absolute", "left": "-9999px", "opacity": "0"}
            ),

            spacing="4",
            width="100%",
            max_width="600px",
            padding="1.5em",
            align="center",
        ),
        rx.script(src="/js/usb_scanner.js"),
        width="100vw",
        height="100vh",
        bg=BLACK,
    )