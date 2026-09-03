# guest_management/pages/lucky_draw_predraw.py
"""Fullscreen pre-draw participant presentation."""

import reflex as rx

from ..state.lucky_draw_state import LuckyDrawState
from ..utils.constants import GOLD, BLACK, DARK_GRAY


PAGE_SIZE = 30


def _participant_card(guest):
    """Render one participant on the pre-draw presentation."""
    return rx.box(
        rx.vstack(
            rx.text(
                guest.get("name", "Unknown"),
                color="white",
                font_size=["1em", "1.15em", "1.3em"],
                font_weight="700",
                text_align="center",
                overflow="hidden",
                text_overflow="ellipsis",
                white_space="nowrap",
                width="100%",
            ),
            rx.text(
                guest.get(
                    "guest_id",
                    guest.get("id", ""),
                ),
                color=GOLD,
                font_size=["0.7em", "0.8em", "0.9em"],
                text_align="center",
                font_weight="600",
            ),
            spacing="1",
            align="center",
            justify="center",
            width="100%",
        ),
        background=DARK_GRAY,
        border=f"1px solid {GOLD}",
        border_radius="12px",
        padding=["0.8em", "1em", "1.15em"],
        width="100%",
        min_height=["90px", "105px", "120px"],
        display="flex",
        align_items="center",
        justify_content="center",
    )


def _participant_grid():
    """Render the current 30-participant page."""
    return rx.grid(
        rx.foreach(
            LuckyDrawState.predraw_visible_participants,
            _participant_card,
        ),
        columns=rx.breakpoints(
            initial="2",
            sm="3",
            md="4",
            lg="5",
            xl="5",
        ),
        spacing=rx.breakpoints(
            initial="2",
            md="3",
            lg="4",
        ),
        width="100%",
    )


def _navigation():
    """Render pre-draw page navigation."""
    return rx.hstack(
        rx.button(
            rx.hstack(
                rx.icon(
                    tag="chevron_left",
                    size=22,
                ),
                rx.text(
                    "PREVIOUS",
                    font_weight="700",
                ),
                spacing="2",
            ),
            on_click=LuckyDrawState.predraw_previous_page,
            disabled=LuckyDrawState.predraw_page <= 0,
            variant="outline",
            border_color=GOLD,
            color=GOLD,
            size="3",
            padding_x=["1em", "1.5em"],
        ),
        rx.spacer(),
        rx.vstack(
            rx.text(
                LuckyDrawState.predraw_page_indicator,
                color="white",
                font_size=["0.85em", "1em"],
                font_weight="700",
                text_align="center",
            ),
            rx.text(
                LuckyDrawState.predraw_range_label,
                color="gray",
                font_size=["0.65em", "0.75em"],
                text_align="center",
            ),
            spacing="1",
            align="center",
        ),
        rx.spacer(),
        rx.button(
            rx.hstack(
                rx.text(
                    "NEXT",
                    font_weight="700",
                ),
                rx.icon(
                    tag="chevron_right",
                    size=22,
                ),
                spacing="2",
            ),
            on_click=LuckyDrawState.predraw_next_page,
            disabled=LuckyDrawState.predraw_is_last_page,
            variant="outline",
            border_color=GOLD,
            color=GOLD,
            size="3",
            padding_x=["1em", "1.5em"],
        ),
        width="100%",
        align="center",
    )


def lucky_draw_predraw_page():
    """Render the fullscreen pre-draw presentation."""
    return rx.box(
        rx.vstack(
            # Header
            rx.hstack(
                rx.vstack(
                    rx.text(
                        "EVENTLAH",
                        color=GOLD,
                        font_size=["0.75em", "0.9em"],
                        font_weight="800",
                        letter_spacing="0.18em",
                    ),
                    rx.heading(
                        LuckyDrawState.lucky_draw_event_name,
                        color="white",
                        size=rx.breakpoints(
                            initial="5",
                            md="6",
                            lg="7",
                        ),
                    ),
                    rx.text(
                        "PRE-DRAW PARTICIPANTS",
                        color=GOLD,
                        font_size=["0.65em", "0.75em", "0.85em"],
                        font_weight="800",
                        letter_spacing="0.12em",
                    ),
                    spacing="1",
                    align="start",
                ),
                rx.spacer(),
                rx.box(
                    rx.text(
                        "LIVE PRESENTATION",
                        color=BLACK,
                        font_size=["0.6em", "0.7em"],
                        font_weight="800",
                        letter_spacing="0.06em",
                    ),
                    background=GOLD,
                    border_radius="999px",
                    padding_x="1em",
                    padding_y="0.45em",
                ),
                width="100%",
                align="center",
            ),

            # Participant count
            rx.hstack(
                rx.text(
                    "Participants",
                    color="gray",
                    font_size=["0.75em", "0.85em"],
                ),
                rx.badge(
                    LuckyDrawState.lucky_draw_eligible_count,
                    color_scheme="amber",
                    size="2",
                ),
                rx.spacer(),
                rx.text(
                    "30 participants per slide",
                    color=GOLD,
                    font_size=["0.7em", "0.8em"],
                    font_weight="600",
                ),
                width="100%",
                align="center",
            ),

            # Participant cards
            rx.box(
                _participant_grid(),
                background=BLACK,
                border=f"1px solid {GOLD}",
                border_radius="18px",
                padding=["1em", "1.5em", "2em"],
                width="100%",
                min_height=["500px", "600px", "700px"],
                display="flex",
                align_items="center",
                justify_content="center",
            ),

            # Navigation
            _navigation(),

            # Footer
            rx.hstack(
                rx.text(
                    "Pre-draw presentation • Main Lucky Draw remains independent",
                    color="gray",
                    font_size="0.65em",
                ),
                rx.spacer(),
                rx.text(
                    "Laptop 1 → AV Splitter → Venue Screens",
                    color=GOLD,
                    font_size="0.65em",
                    font_weight="600",
                ),
                width="100%",
                align="center",
            ),

            spacing="4",
            width="100%",
            max_width="1900px",
            padding=["1em", "1.5em", "2em"],
        ),
        background=BLACK,
        min_height="100vh",
        width="100%",
        color="white",
    )