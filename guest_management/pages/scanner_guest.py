from guest_management.components.loading_overlay import eventlah_viewport_page
# guest_management/pages/scanner_guest.py
import reflex as rx
from guest_management.state import EventState, ScannerState
from guest_management.utils.constants import GOLD, BLACK, DARK_GRAY, LIGHT_GRAY


def scanner_guest_page() -> rx.Component:
    """Scanner-only guest check-in workstation. No admin controls."""
    return eventlah_viewport_page(rx.center(
        rx.vstack(
            rx.hstack(
                rx.vstack(
                    rx.text(
                        "SCANNER WORKSTATION",
                        size="2",
                        color=GOLD,
                        weight="bold",
                        letter_spacing="0.12em",
                    ),
                    rx.cond(
                        EventState.current_event,
                        rx.text(
                            EventState.current_event.get(
                                "name",
                                "Event Check-In",
                            ),
                            size="4",
                            color="white",
                            weight="bold",
                        ),
                        rx.text(
                            "Event Check-In",
                            size="4",
                            color="white",
                            weight="bold",
                        ),
                    ),
                    spacing="0",
                    align="start",
                ),
                rx.spacer(),
                rx.button(
                    rx.hstack(
                        rx.icon(tag="x", size=16),
                        rx.text("Close", size="1"),
                        spacing="1",
                    ),
                    on_click=ScannerState.close_scanner_workstation,
                    variant="ghost",
                    color="gray",
                    size="1",
                ),
                width="100%",
                align="center",
            ),

            rx.card(
                rx.hstack(
                    rx.icon(tag="badge-check", size=20, color="green"),
                    rx.vstack(
                        rx.text(
                            "AUTHENTICATED STATION",
                            size="1",
                            color="green",
                            weight="bold",
                        ),
                        rx.text(
                            ScannerState.current_scanner_name,
                            size="3",
                            color="white",
                            weight="bold",
                        ),
                        rx.text(
                            ScannerState.current_scanner_id,
                            size="1",
                            color="gray",
                            style={"fontFamily": "monospace"},
                        ),
                        spacing="0",
                        align="start",
                    ),
                    spacing="2",
                    width="100%",
                    align="center",
                ),
                bg=DARK_GRAY,
                border="1px solid rgba(34,197,94,0.35)",
                border_radius="14px",
                padding="0.9em 1em",
                width="100%",
            ),

            rx.card(
                rx.vstack(
                    rx.cond(
                        ScannerState.scanner_status_icon == "success",
                        rx.vstack(
                            rx.icon(tag="circle-check", size=68, color="green"),
                            rx.text(
                                "CHECK-IN SUCCESSFUL",
                                size="4",
                                color="green",
                                weight="bold",
                                text_align="center",
                            ),
                            rx.text(
                                ScannerState.checkin_guest_name,
                                size="4",
                                color="white",
                                weight="bold",
                                text_align="center",
                            ),
                            rx.text(
                                "TABLE",
                                size="1",
                                color="gray",
                                weight="bold",
                                letter_spacing="0.15em",
                            ),
                            rx.text(
                                ScannerState.checkin_table_number,
                                font_size="clamp(3rem, 10vw, 5rem)",
                                color=GOLD,
                                weight="bold",
                                font_family="monospace",
                                text_align="center",
                                line_height="1",
                            ),
                            rx.cond(
                                ScannerState.checkin_team_name,
                                rx.text(
                                    f"Team: {ScannerState.checkin_team_name}",
                                    size="2",
                                    color=GOLD,
                                ),
                                rx.fragment(),
                            ),
                            spacing="2",
                            align="center",
                        ),
                        rx.cond(
                            ScannerState.scanner_status_icon == "warning",
                            rx.vstack(
                                rx.icon(
                                    tag="triangle-alert",
                                    size=68,
                                    color="orange",
                                ),
                                rx.text(
                                    "ALREADY CHECKED IN",
                                    size="4",
                                    color="orange",
                                    weight="bold",
                                    text_align="center",
                                ),
                                rx.text(
                                    ScannerState.scanner_status,
                                    size="2",
                                    color="white",
                                    text_align="center",
                                ),
                                spacing="2",
                                align="center",
                            ),
                            rx.cond(
                                ScannerState.scanner_status_icon == "error",
                                rx.vstack(
                                    rx.icon(
                                        tag="circle-x",
                                        size=68,
                                        color="red",
                                    ),
                                    rx.text(
                                        "CHECK-IN FAILED",
                                        size="4",
                                        color="red",
                                        weight="bold",
                                    ),
                                    rx.text(
                                        ScannerState.scanner_status,
                                        size="2",
                                        color="white",
                                        text_align="center",
                                    ),
                                    spacing="2",
                                    align="center",
                                ),
                                rx.vstack(
                                    rx.icon(
                                        tag="qr-code",
                                        size=68,
                                        color=GOLD,
                                    ),
                                    rx.cond(
                                        ScannerState.scanner_ready,
                                        rx.vstack(
                                            rx.text(
                                                "READY TO SCAN",
                                                size="4",
                                                color="green",
                                                weight="bold",
                                            ),
                                            rx.text(
                                                "Present the guest QR code to the connected scanner.",
                                                size="2",
                                                color="gray",
                                                text_align="center",
                                            ),
                                            spacing="1",
                                            align="center",
                                        ),
                                        rx.vstack(
                                            rx.text(
                                                "SCANNER STANDBY",
                                                size="4",
                                                color="gray",
                                                weight="bold",
                                            ),
                                            rx.text(
                                                "Press START SCAN to activate the scanner.",
                                                size="2",
                                                color="gray",
                                                text_align="center",
                                            ),
                                            spacing="1",
                                            align="center",
                                        ),
                                    ),
                                    spacing="2",
                                    align="center",
                                ),
                            ),
                        ),
                    ),
                    spacing="3",
                    align="center",
                    width="100%",
                ),
                bg=DARK_GRAY,
                border=f"2px solid {GOLD}",
                border_radius="18px",
                padding="2em 1.5em",
                width="100%",
            ),

            rx.cond(
                (~ScannerState.scanner_ready)
                & (ScannerState.scanner_status_icon == "idle"),
                rx.button(
                    rx.hstack(
                        rx.icon(tag="play", size=22),
                        rx.text("START SCAN", size="3", weight="bold"),
                        spacing="2",
                    ),
                    on_click=ScannerState.enable_guest_scanner,
                    bg=GOLD,
                    color=BLACK,
                    width="100%",
                    height="58px",
                    border_radius="30px",
                    is_disabled=~ScannerState.station_authenticated,
                ),
                rx.fragment(),
            ),

            rx.cond(
                ScannerState.scanner_ready,
                rx.hstack(
                    rx.hstack(
                        rx.icon(tag="activity", size=18, color="green"),
                        rx.text(
                            "Scanner active",
                            size="2",
                            color="green",
                            weight="bold",
                        ),
                        spacing="1",
                    ),
                    rx.spacer(),
                    rx.button(
                        "Pause",
                        on_click=ScannerState.disable_guest_scanner,
                        variant="outline",
                        color="red",
                        border_color="red",
                        size="1",
                    ),
                    width="100%",
                    align="center",
                ),
                rx.fragment(),
            ),

            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.icon(tag="keyboard", size=18, color=GOLD),
                        rx.text(
                            "Manual Check-In",
                            size="2",
                            color="white",
                            weight="bold",
                        ),
                        spacing="2",
                    ),
                    rx.text(
                        "Enter the guest ID if the QR code cannot be scanned.",
                        size="1",
                        color="gray",
                    ),
                    rx.hstack(
                        rx.input(
                            placeholder="Guest ID",
                            value=ScannerState.scanner_manual_guest_id,
                            on_change=ScannerState.set_scanner_manual_guest_id,
                            width="100%",
                            size="3",
                            bg=BLACK,
                            color="white",
                            border_color=GOLD,
                        ),
                        rx.button(
                            "Check In",
                            on_click=ScannerState.handle_manual_checkin(
                                ScannerState.scanner_manual_guest_id
                            ),
                            bg=GOLD,
                            color=BLACK,
                            height="46px",
                            min_width="120px",
                            border_radius="23px",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                ),
                bg="#111111",
                border="1px solid #333333",
                border_radius="14px",
                padding="1em",
                width="100%",
            ),

            rx.cond(
                (
                    (ScannerState.scanner_status_icon == "success")
                    | (ScannerState.scanner_status_icon == "warning")
                    | (ScannerState.scanner_status_icon == "error")
                ),
                rx.button(
                    rx.hstack(
                        rx.icon(tag="refresh-cw", size=19),
                        rx.text(
                            "SCAN NEXT GUEST",
                            size="2",
                            weight="bold",
                        ),
                        spacing="2",
                    ),
                    on_click=ScannerState.reset_scanner_for_next_guest,
                    bg=GOLD,
                    color=BLACK,
                    width="100%",
                    height="54px",
                    border_radius="28px",
                ),
                rx.fragment(),
            ),

            rx.box(
                rx.input(
                    on_change=ScannerState.handle_high_volume_scan,
                    value="",
                    id="scanner-bridge-input",
                ),
                class_name="reflex-scan-bridge",
                style={
                    "position": "absolute",
                    "left": "-9999px",
                    "opacity": "0",
                    "width": "1px",
                    "height": "1px",
                },
            ),

            spacing="3",
            width="100%",
            max_width="620px",
            padding="1em",
            align="center",
        ),
        rx.script(src="/js/usb_scanner.js"),
        width="100vw",
        min_height="100vh",
        bg=BLACK,
        padding="0.5em",
    ),
        loading=ScannerState.is_loading,
        message='Loading scanner...',
    )
