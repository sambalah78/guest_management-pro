# guest_management/pages/check_in.py
"""Manual check-in page for guests without QR codes."""

import reflex as rx
from guest_management.state import EventState, GuestState, UIState
from guest_management.utils.constants import GOLD, BLACK, DARK_GRAY


def checkin_page():
    """Manual check-in page for guests without QR codes."""
    return rx.center(
        rx.vstack(
            # Header with event info
            rx.hstack(
                rx.image(src="/logo.png", width="60px", height="60px", border_radius="50%"),
                rx.vstack(
                    rx.heading(EventState.current_event.get("name", "Event Check-In"), size="7", color=GOLD),
                    rx.text(EventState.current_event.get("company_name", ""), color="gray", size="3"),
                    spacing="0",
                    align="start",
                ),
                spacing="4",
                width="100%",
                padding="1em",
                bg=DARK_GRAY,
                border_bottom=f"2px solid {GOLD}",
            ),

            # Show processing message if scanning QR
            rx.cond(
                UIState.is_loading,
                rx.card(
                    rx.vstack(
                        rx.spinner(size="2", color=GOLD),
                        rx.heading("Processing Check-In", size="5", color=GOLD),
                        rx.text("Please wait...", color="gray"),
                        spacing="4",
                        align="center",
                    ),
                    bg=DARK_GRAY,
                    border=f"2px solid {GOLD}",
                    border_radius="15px",
                    width=["95%", "90%", "500px"],
                    padding="2em",
                ),
            ),

            # Manual Check-in Form (only show if not processing)
            rx.cond(
                ~UIState.is_loading,
                rx.card(
                    rx.vstack(
                        rx.icon(tag="user-check", size=50, color=GOLD),
                        rx.heading("Manual Check-In", size="6", color=GOLD),
                        rx.text("Enter your Name OR Guest ID below", color="gray", size="3"),

                        # Name Input
                        rx.vstack(
                            rx.hstack(
                                rx.icon(tag="user", size=16, color=GOLD),
                                rx.text("Full Name (optional if using ID)", color="white", weight="bold"),
                                spacing="2",
                                width="100%",
                            ),
                            rx.input(
                                placeholder="Enter your full name",
                                value=UIState.manual_name,
                                on_change=UIState.set_manual_name,
                                width="100%",
                                bg=BLACK,
                                border_color=GOLD,
                                color="white",
                                _placeholder={"color": "gray"},
                            ),
                            spacing="1",
                            width="100%",
                        ),

                        # Guest ID Input
                        rx.vstack(
                            rx.hstack(
                                rx.icon(tag="id-card", size=16, color=GOLD),
                                rx.text("Guest ID (optional if using name)", color="white", weight="bold"),
                                spacing="2",
                                width="100%",
                            ),
                            rx.input(
                                placeholder="Enter your ID",
                                value=UIState.manual_guest_id,
                                on_change=UIState.set_manual_guest_id,
                                width="100%",
                                bg=BLACK,
                                border_color=GOLD,
                                color="white",
                                _placeholder={"color": "gray"},
                            ),
                            spacing="1",
                            width="100%",
                        ),

                        # Helper text
                        rx.cond(
                            (~UIState.manual_name) & (~UIState.manual_guest_id),
                            rx.text(
                                "Please enter either Name or Guest ID",
                                color="orange",
                                size="1",
                            ),
                        ),

                        # Submit Button
                        rx.button(
                            rx.hstack(
                                rx.cond(
                                    UIState.is_loading,
                                    rx.spinner(size="2", color=BLACK),
                                    rx.icon(tag="circle_check", size=20),
                                ),
                                rx.text("Check In"),
                            ),
                            on_click=GuestState.handle_manual_checkin,
                            bg=GOLD,
                            color=BLACK,
                            width="100%",
                            size="3",
                            is_loading=UIState.is_loading,
                            is_disabled=(~UIState.manual_name) & (~UIState.manual_guest_id),
                            _hover={"opacity": 0.9},
                        ),

                        # Back to Dashboard Button
                        rx.button(
                            rx.hstack(
                                rx.icon(tag="arrow-left", size=20),
                                rx.text("Back to Dashboard"),
                            ),
                            on_click=rx.redirect(f"/dashboard/{EventState.current_event_id}"),
                            variant="outline",
                            border_color=GOLD,
                            color=GOLD,
                            width="100%",
                            size="3",
                            _hover={"bg": GOLD, "color": BLACK},
                        ),

                        spacing="4",
                        width="100%",
                        padding="2em",
                    ),
                    bg=DARK_GRAY,
                    border=f"2px solid {GOLD}",
                    border_radius="15px",
                    width=["95%", "90%", "500px"],
                ),
            ),

            # Alternative: Use QR Scanner
            rx.text(
                "Have a QR code? ",
                rx.link("Scan QR Code", href=f"/scanner/{EventState.current_event_id}", color=GOLD),
                color="gray",
                size="2",
            ),

            spacing="6",
            width="100%",
            align="center",
        ),
        width="100%",
        min_height="100vh",
        bg=BLACK,
        padding="1em",
    )