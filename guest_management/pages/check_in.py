# guest_management/pages/check_in.py
"""Manual check-in page for guests without QR codes."""

import reflex as rx
from guest_management.state import  GuestState, UIState
from guest_management.utils.constants import GOLD, BLACK, DARK_GRAY


def checkin_page():
    """Manual check-in page for guests without QR codes."""
    return rx.center(
        rx.vstack(
            # Header with event info
            rx.hstack(
                rx.image(src="/logo1.png", width="60px", height="60px", border_radius="50%"),
                rx.vstack(
                    rx.heading(GuestState.current_event.get("name", "Event Check-In"), size="7", color=GOLD),
                    rx.text(GuestState.current_event.get("company_name", ""), color="gray", size="3"),
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
                        rx.text("Missing QR / No Email: search uploaded list by Name or ID. No ID: verify with client.", color="gray", size="3"),

                        # Name Input
                        rx.vstack(
                            rx.hstack(
                                rx.icon(tag="user", size=16, color=GOLD),
                                rx.text("Full Name (for missing QR or No-ID)", color="white", weight="bold"),
                                spacing="2",
                                width="100%",
                            ),
                            rx.input(
                                placeholder="Enter your full name",
                                value=GuestState.manual_name,
                                on_change=GuestState.set_manual_name,
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
                                rx.text("Guest ID (use when available)", color="white", weight="bold"),
                                spacing="2",
                                width="100%",
                            ),
                            rx.input(
                                placeholder="Enter your ID",
                                value=GuestState.manual_guest_id,
                                on_change=GuestState.set_manual_guest_id,
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
                            (~GuestState.manual_name) & (~GuestState.manual_guest_id),
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
                            is_disabled=(~GuestState.manual_name) & (~GuestState.manual_guest_id),
                            _hover={"opacity": 0.9},
                        ),

                        # Back to Dashboard Button
                        rx.button(
                            rx.hstack(
                                rx.icon(tag="arrow-left", size=20),
                                rx.text("Back to Dashboard"),
                            ),
                            on_click=rx.redirect(f"/dashboard/{GuestState.current_event_id}"),
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


            # No-ID verification flow: shown only when the entered name is not
            # found in the uploaded guest list. A new record requires explicit
            # client/staff confirmation.
            rx.cond(
                GuestState.no_id_verification_open,
                rx.card(
                    rx.vstack(
                        rx.heading("Staff Verification â€” No ID", size="5", color=GOLD),
                        rx.text(
                            "This person was not found in the uploaded guest list. "
                            "Confirm with the client before registering them.",
                            color="orange",
                            size="2",
                        ),
                        rx.text(
                            GuestState.no_id_name,
                            color="white",
                            weight="bold",
                            size="4",
                        ),
                        rx.input(
                            placeholder="Email (optional)",
                            value=GuestState.no_id_email,
                            on_change=GuestState.set_no_id_email,
                            width="100%",
                            bg=BLACK,
                            border_color=GOLD,
                            color="white",
                        ),
                        rx.input(
                            placeholder="Phone (optional)",
                            value=GuestState.no_id_phone,
                            on_change=GuestState.set_no_id_phone,
                            width="100%",
                            bg=BLACK,
                            border_color=GOLD,
                            color="white",
                        ),
                        rx.input(
                            placeholder="Table number (optional)",
                            value=GuestState.no_id_table_number,
                            on_change=GuestState.set_no_id_table_number,
                            width="100%",
                            bg=BLACK,
                            border_color=GOLD,
                            color="white",
                        ),
                        rx.input(
                            placeholder="Team / Group (optional)",
                            value=GuestState.no_id_team_name,
                            on_change=GuestState.set_no_id_team_name,
                            width="100%",
                            bg=BLACK,
                            border_color=GOLD,
                            color="white",
                        ),
                        rx.checkbox(
                            "I have confirmed with the client that this is their staff member.",
                            checked=GuestState.no_id_client_confirmed,
                            on_change=GuestState.set_no_id_client_confirmed,
                            color_scheme="gold",
                        ),
                        rx.hstack(
                            rx.button(
                                "CANCEL",
                                on_click=GuestState.cancel_no_id_verification,
                                variant="outline",
                                border_color=GOLD,
                                color=GOLD,
                                width="50%",
                            ),
                            rx.button(
                                "REGISTER & CHECK IN",
                                on_click=GuestState.confirm_no_id_guest,
                                bg=GOLD,
                                color=BLACK,
                                width="50%",
                                is_loading=UIState.is_loading,
                            ),
                            spacing="3",
                            width="100%",
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    bg=DARK_GRAY,
                    border=f"2px solid {GOLD}",
                    border_radius="15px",
                    width=["95%", "90%", "600px"],
                    padding="2em",
                ),
            ),

            # Alternative: Use QR Scanner
            rx.text(
                "Have a QR code? ",
                rx.link("Scan QR Code", href=f"/scanner/{GuestState.current_event_id}", color=GOLD),
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
