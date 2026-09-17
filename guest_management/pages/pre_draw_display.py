# guest_management/pages/pre_draw_display.py
"""Fullscreen preliminary-winner presentation display."""

import re
import reflex as rx

from ..state.lucky_draw_state import LuckyDrawState
from ..utils.constants import GOLD, BLACK, DARK_GRAY, LIGHT_GRAY


def _participant_card(guest):
    """Render one attending participant with preliminary-winner status."""

    guest_id = guest.get("guest_id", "")
    name = guest.get("name", "Guest")

    return rx.box(
        rx.hstack(
            rx.box(
                rx.text(
                    guest.get("display_number", ""),
                    color=GOLD,
                    font_size="0.65em",
                    font_weight="800",
                ),
                width="28px",
                height="28px",
                display="flex",
                align_items="center",
                justify_content="center",
                background=BLACK,
                border_radius="50%",
            ),
            rx.vstack(
                rx.text(
                    name,
                    color="white",
                    font_size=["0.9em", "1em", "1.1em"],
                    font_weight="700",
                    overflow="hidden",
                    text_overflow="ellipsis",
                    white_space="nowrap",
                    width="100%",
                ),
                rx.text(
                    guest_id,
                    color="gray",
                    font_size=["0.62em", "0.7em"],
                ),
                spacing="0",
                align="start",
                flex="1",
                min_width="0",
            ),
            rx.cond(
                guest.get("is_pre_draw_winner", False),
                rx.box(
                    rx.vstack(
                        rx.hstack(
                            rx.icon(
                                tag="trophy",
                                size=14,
                                color=BLACK,
                            ),
                            rx.text(
                                "PRE-DRAW WINNER",
                                color=BLACK,
                                font_size="0.58em",
                                font_weight="900",
                            ),
                            spacing="1",
                        ),
                        rx.text(
                            guest.get("pre_draw_prize", "Prize"),
                            color=BLACK,
                            font_size="0.72em",
                            font_weight="800",
                            text_align="right",
                        ),
                        rx.cond(
                            guest.get("pre_draw_value", "") != "",
                            rx.text(
                                guest.get("pre_draw_value", ""),
                                color=BLACK,
                                font_size="0.62em",
                                font_weight="700",
                            ),
                            rx.fragment(),
                        ),
                        spacing="0",
                        align="end",
                    ),
                    background=GOLD,
                    border_radius="9px",
                    padding="0.45em 0.6em",
                    min_width="150px",
                ),
                rx.box(
                    rx.text(
                        "ELIGIBLE",
                        color=LIGHT_GRAY,
                        font_size="0.55em",
                        font_weight="700",
                    ),
                    border="1px solid rgba(255,255,255,0.15)",
                    border_radius="999px",
                    padding="0.35em 0.55em",
                ),
            ),
            spacing="3",
            align="center",
            width="100%",
        ),

        background=rx.cond(
            guest.get("is_pre_draw_winner", False),
            "rgba(212, 175, 55, 0.18)",
            DARK_GRAY,
        ),
        border=rx.cond(
            guest.get("is_pre_draw_winner", False),
            f"2px solid {GOLD}",
            "1px solid rgba(255,255,255,0.10)",
        ),
        border_radius="12px",
        padding=["0.65em", "0.8em"],
        width="100%",
        min_height="64px",
    )


def _legend():
    """Explain preliminary-winner status to the audience."""
    return rx.hstack(
        rx.hstack(
            rx.box(
                width="12px",
                height="12px",
                background=GOLD,
                border_radius="3px",
            ),
            rx.text(
                "Pre-draw winner",
                color="white",
                font_size="0.7em",
                font_weight="600",
            ),
            spacing="2",
        ),
        rx.hstack(
            rx.box(
                width="12px",
                height="12px",
                background=DARK_GRAY,
                border="1px solid rgba(255,255,255,0.15)",
                border_radius="3px",
            ),
            rx.text(
                "Eligible participant",
                color="gray",
                font_size="0.7em",
            ),
            spacing="2",
        ),
        spacing="5",
        justify="center",
        width="100%",
        wrap="wrap",
    )


def pre_draw_display_page():
    """Fullscreen presentation of all attending participants."""

    return rx.box(
        rx.vstack(
            # Header
            rx.hstack(
                rx.vstack(
                    rx.text(
                        "EVENTLAH",
                        color=GOLD,
                        font_size=["0.7em", "0.8em"],
                        font_weight="900",
                        letter_spacing="0.2em",
                    ),
                    rx.heading(
                        LuckyDrawState.lucky_draw_event_name,
                        color="white",
                        size=rx.breakpoints(
                            initial="5",
                            md="6",
                            lg="7",
                        ),
                        margin="0",
                    ),
                    rx.text(
                        "PRE-DRAW WINNERS",
                        color=GOLD,
                        font_size=["0.8em", "0.95em"],
                        font_weight="800",
                        letter_spacing="0.12em",
                    ),
                    spacing="1",
                    align="start",
                ),
                rx.spacer(),
                rx.vstack(
                    rx.text(
                        LuckyDrawState.pre_draw_winner_count,
                        color=GOLD,
                        font_size=["1.8em", "2.2em"],
                        font_weight="900",
                    ),
                    rx.text(
                        "Pre-Draw Winners",
                        color=LIGHT_GRAY,
                        font_size="0.65em",
                    ),
                    spacing="0",
                    align="center",
                ),
                width="100%",
                align="center",
            ),

            # Description
            rx.box(
                rx.text(
                    "Please look for your name below. "
                    "Guests highlighted in gold have already won a preliminary prize.",
                    color=LIGHT_GRAY,
                    font_size=["0.78em", "0.9em", "1em"],
                    text_align="center",
                ),
                background=DARK_GRAY,
                border_radius="10px",
                padding="0.8em 1em",
                width="100%",
            ),

            # Participant list
            rx.box(
                rx.hstack(
                    rx.vstack(
                        rx.text(
                            "ATTENDING PARTICIPANTS",
                            color=GOLD,
                            font_size="0.72em",
                            font_weight="900",
                            letter_spacing="0.12em",
                        ),
                        rx.text(
                            LuckyDrawState.predraw_range_label,
                            color="gray",
                            font_size="0.68em",
                        ),
                        spacing="1",
                        align="start",
                    ),
                    rx.spacer(),
                    rx.text(
                        LuckyDrawState.predraw_page_indicator,
                        color="white",
                        font_size="0.7em",
                        font_weight="700",
                    ),
                    width="100%",
                    align="center",
                ),

                rx.grid(
                    rx.foreach(
                        LuckyDrawState.predraw_visible_participants,
                        _participant_card,
                    ),
                    columns=rx.breakpoints(
                        initial="1",
                        sm="2",
                        md="3",
                        lg="4",
                    ),
                    spacing="3",
                    width="100%",
                    margin_top="0.8em",
                ),

                background=BLACK,
                border_radius="14px",
                padding=["0.8em", "1em"],
                width="100%",
            ),

            _legend(),

            # Footer
            rx.hstack(
                rx.text(
                    "PRE-DRAW DISPLAY",
                    color=GOLD,
                    font_size="0.6em",
                    font_weight="800",
                    letter_spacing="0.12em",
                ),
                rx.spacer(),
                rx.text(
                    "Live presentation • Database synchronized",
                    color="gray",
                    font_size="0.6em",
                ),
                width="100%",
                align="center",
            ),


            spacing="4",
            width="100%",
            max_width="1800px",
            padding=["1em", "1.5em", "2em"],

        ),
        background=BLACK,
        min_height="100vh",
        width="100%",
        color="white",
    )