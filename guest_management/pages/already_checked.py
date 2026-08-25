# guest_management/pages/already_checked.py
"""Page shown when guest is already checked in."""

import reflex as rx
from guest_management.utils.constants import GOLD, BLACK, DARK_GRAY, LIGHT_GRAY
from guest_management.state import SuccessState, ScannerState


def already_checked_page():
    """Page shown when guest is already checked in."""
    return rx.center(
        rx.vstack(
            # Elegant decorative line
            rx.hstack(

                # Info Icon
                rx.box(
                    rx.icon(
                        tag="info",
                        size=30,
                        color=GOLD,
                    ),
                    padding="0.25em",
                    border_radius="50%",
                    bg=f"{GOLD}10",
                    border=f"1px solid {GOLD}",
                    margin_bottom="0.5em",
                ),

                # Title
                rx.heading(
                    "Already Checked In",
                    size="5",
                    color=GOLD,
                    weight="bold",
                    font_size=["1.3em", "1.5em", "1.7em", "1.8em"],
                    text_align="center",
                ),
                align="center",
            ),

            # Guest Information Card
            rx.card(
                rx.vstack(
                    rx.text(
                        "GUEST INFORMATION",
                        font_size=["0.4em", "0.6em", "0.8em", "1em"],
                        color=LIGHT_GRAY,
                        weight="medium",
                        letter_spacing="0.1em",
                        text_align="center",
                    ),
                    rx.divider(width="100%", border_color=f"{GOLD}50", margin_y="0.3em"),

                    # Guest Name
                    rx.vstack(
                        rx.text(
                            "Name",
                            font_size=["0.2em", "0.4em", "0.6em", "0.8em"],
                            color=LIGHT_GRAY,
                            letter_spacing="0.1em",
                        ),
                        rx.heading(
                            SuccessState.guest_name,
                            size="4",
                            color="white",
                            weight="bold",
                            font_size=["1.2em", "1.3em", "1.4em", "1.5em"],
                            text_align="center",
                        ),
                        spacing="1",
                        align="center",
                    ),

                    # Table Number (if available)
                    rx.cond(
                        SuccessState.table_number != "TBD",
                        rx.vstack(
                            rx.text(
                                "Table Number",
                                font_size=["0.2em", "0.4em", "0.6em", "0.8em"],
                                color=LIGHT_GRAY,
                                letter_spacing="0.1em",
                                margin_top="0.5em",
                            ),
                            rx.text(
                                SuccessState.table_number,
                                font_size=["2.5em", "3em", "3.5em", "4em"],
                                color=GOLD,
                                weight="bold",
                                font_family="monospace",
                                text_align="center",
                                line_height="1.2",
                            ),
                            spacing="1",
                            align="center",
                            width="100%",
                        ),
                        rx.text(
                            "Table assignment pending",
                            size="1",
                            color="gray",
                            text_align="center",
                            margin_top="0.5em",
                        ),
                    ),
                    rx.cond(
                        SuccessState.team_name,
                        rx.text(SuccessState.team_name, color=GOLD, size="2", weight="bold"),
                        rx.fragment(),
                    ),

                    spacing="3",
                    align="center",
                    width="100%",
                ),
                width="100%",
                max_width="350px",
                padding="1.5em",
                bg=DARK_GRAY,
                border=f"1px solid {GOLD}33",
                border_radius="20px",
                box_shadow="0 10px 30px rgba(0,0,0,0.3)",
            ),

            # Status Message
            rx.text(
                "This guest has already completed check-in.",
                color=LIGHT_GRAY,
                size="1",
                text_align="center",
                font_size=["0.7em", "0.75em", "0.8em", "0.85em"],
            ),

            # Single Button - Scan Next Guest
            rx.button(
                rx.hstack(
                    rx.icon(tag="qr_code", size=16),
                    rx.text("SCAN NEXT GUEST", size="2", weight="bold"),
                    rx.icon(tag="arrow-right", size=14),
                    spacing="2",
                ),
                on_click=ScannerState.reset_scanner_for_next_guest,
                bg=GOLD,
                color=BLACK,
                width="100%",
                max_width="300px",
                padding="0.8em 1.5em",
                font_size="0.9rem",
                border_radius="40px",
                margin_top="0.5em",
                _hover={
                    "bg": "#FFD700",
                    "transform": "scale(1.02)",
                    "box_shadow": f"0 0 20px {GOLD}",
                },
                transition="all 0.2s ease",
            ),

            spacing="3",
            padding="1.5em",
            width="100%",
            max_width="480px",
        ),
        width="100%",
        height="100vh",
        bg=BLACK,
        style={
            "overflow": "hidden",
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center",
        },
    )