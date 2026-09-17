# guest_management/pages/success.py
"""Successful check-in receipt page."""

import reflex as rx

from guest_management.state import SuccessState
from guest_management.utils.constants import GOLD, BLACK


def _detail(label: str, value):
    return rx.vstack(
        rx.text(
            label,
            size="1",
            color="gray",
            weight="medium",
            letter_spacing="0.08em",
            text_transform="uppercase",
        ),
        rx.text(
            value,
            size="3",
            color="white",
            weight="bold",
            text_align="center",
        ),
        spacing="1",
        align="center",
        width="100%",
    )


def success_page():
    """Premium event-day success receipt."""
    return rx.center(
        rx.cond(
            SuccessState.is_fetching,
            rx.vstack(
                rx.spinner(color=GOLD, size="3"),
                rx.text("Loading...", color="white", size="2"),
                spacing="2",
                align="center",
            ),
            rx.vstack(
                rx.box(
                    rx.icon(tag="circle_check", size=72, color=GOLD),
                    padding="0.75em",
                    border_radius="50%",
                    border=f"2px solid {GOLD}",
                    animation="bounce 0.5s ease-in-out",
                ),
                rx.heading(
                    "Check-In Successful!",
                    size="6",
                    color=GOLD,
                    weight="bold",
                    text_align="center",
                ),
                rx.text(
                    f"Welcome, {SuccessState.guest_name}!",
                    size="4",
                    color="white",
                    weight="medium",
                    text_align="center",
                ),
                rx.cond(
                    SuccessState.guest_id != "",
                    rx.text(
                        f"Guest ID: {SuccessState.guest_id}",
                        size="2",
                        color="gray",
                        text_align="center",
                    ),
                    rx.fragment(),
                ),

                # The table is the most important information for the guest.
                rx.card(
                    rx.vstack(
                        rx.text(
                            "YOUR TABLE",
                            size="2",
                            color="gray",
                            weight="medium",
                            letter_spacing="0.12em",
                        ),
                        rx.text(
                            SuccessState.table_number,
                            font_size="clamp(3.5rem, 12vw, 6rem)",
                            line_height="1",
                            color=GOLD,
                            weight="bold",
                            font_family="monospace",
                            text_align="center",
                        ),
                        spacing="2",
                        align="center",
                        width="100%",
                    ),
                    width="100%",
                    style={
                        "background": "#111111",
                        "border": f"2px solid {GOLD}",
                        "padding": "1.5rem",
                        "borderRadius": "20px",
                        "boxShadow": f"0 0 30px {GOLD}22",
                    },
                ),

                # Event details.
                rx.card(
                    rx.vstack(
                        rx.text(
                            "EVENT DETAILS",
                            size="2",
                            color=GOLD,
                            weight="bold",
                            letter_spacing="0.12em",
                        ),
                        rx.divider(width="100%", border_color=f"{GOLD}33"),
                        _detail("Event", SuccessState.event_name),
                        rx.cond(
                            SuccessState.company_name != "",
                            _detail("Company", SuccessState.company_name),
                            rx.fragment(),
                        ),
                        rx.hstack(
                            rx.cond(
                                SuccessState.event_date != "",
                                _detail("Date", SuccessState.event_date),
                                rx.fragment(),
                            ),
                            rx.cond(
                                SuccessState.event_time != "",
                                _detail("Time", SuccessState.event_time),
                                rx.fragment(),
                            ),
                            width="100%",
                            justify="center",
                            spacing="5",
                        ),
                        rx.cond(
                            SuccessState.venue != "",
                            _detail("Venue", SuccessState.venue),
                            rx.fragment(),
                        ),
                        rx.cond(
                            SuccessState.team_name != "Individual",
                            _detail("Team / Company", SuccessState.team_name),
                            rx.fragment(),
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    width="100%",
                    style={
                        "background": "#111111",
                        "border": "1px solid #333333",
                        "padding": "1.25rem",
                        "borderRadius": "16px",
                    },
                ),

                rx.hstack(
                    rx.button(
                        rx.hstack(
                            rx.icon(tag="refresh_cw", size=18),
                            rx.text("Scan Next", size="2", weight="bold"),
                        ),
                        on_click=rx.redirect(
                            f"/scanner-guest/{SuccessState.success_event_id}"
                        ),
                        bg=GOLD,
                        color=BLACK,
                        width="50%",
                        height="50px",
                        border_radius="30px",
                    ),
                    rx.button(
                        rx.hstack(
                            rx.icon(tag="layout_dashboard", size=18),
                            rx.text("Dashboard", size="2", weight="bold"),
                        ),
                        on_click=rx.redirect(
                            f"/dashboard/{SuccessState.success_event_id}"
                        ),
                        bg="#333333",
                        color="white",
                        width="50%",
                        height="50px",
                        border_radius="30px",
                    ),
                    spacing="3",
                    width="100%",
                ),

                rx.button(
                    rx.hstack(
                        rx.icon(tag="x", size=16),
                        rx.text("Close Window", size="2"),
                    ),
                    on_click=rx.call_script(
                        "if (window.opener) { window.close(); }"
                    ),
                    bg="#222222",
                    color="white",
                    width="100%",
                    height="40px",
                ),
                spacing="4",
                padding="1.25rem",
                width="100%",
                max_width="520px",
            ),
        ),
        width="100%",
        min_height="100vh",
        padding="1rem",
        bg=BLACK,
    )

