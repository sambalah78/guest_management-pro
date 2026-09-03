# guest_management/pages/lucky_draw_display.py
"""Fullscreen Lucky Draw presentation and live control screen."""

import reflex as rx

from ..state.lucky_draw_state import LuckyDrawState
from ..utils.constants import GOLD, BLACK, DARK_GRAY, LIGHT_GRAY


def _participant_card(guest):
    """Render one participant for the preliminary 30-name presentation."""
    return rx.box(
        rx.text(
            guest.get("name", "Unknown"),
            color="white",
            font_size=["0.8em", "0.95em", "1.05em"],
            font_weight="600",
            text_align="center",
            overflow="hidden",
            text_overflow="ellipsis",
            white_space="nowrap",
            width="100%",
        ),
        rx.text(
            guest.get("guest_id", guest.get("id", "")),
            color="gray",
            font_size=["0.6em", "0.7em"],
            text_align="center",
        ),
        background=DARK_GRAY,
        border=f"1px solid {GOLD}",
        border_radius="10px",
        padding=["0.65em", "0.8em"],
        width="100%",
        min_height="70px",
        display="flex",
        flex_direction="column",
        justify_content="center",
        align_items="center",
    )


def _winner_card(winner):
    """Render one confirmed winner for the live audience."""
    prize_value = str(winner.get("prize_value", "") | "").strip()
    return rx.box(
        rx.hstack(
            rx.box(
                rx.text(
                    "WINNER",
                    color=BLACK,
                    font_size="0.58em",
                    font_weight="800",
                    letter_spacing="0.05em",
                ),
                background=GOLD,
                border_radius="999px",
                padding_x="0.7em",
                padding_y="0.25em",
            ),
            rx.spacer(),
            rx.text(
                winner.get("prize_name", "") | "Prize",
                color=GOLD,
                font_size="0.72em",
                font_weight="700",
                text_align="right",
                overflow="hidden",
                text_overflow="ellipsis",
                white_space="nowrap",
                max_width="60%",
            ),
            width="100%",
            align="center",
        ),
        rx.text(
            winner.get("name", "Unknown"),
            color="white",
            font_size=["1em", "1.1em"],
            font_weight="800",
            margin_top="0.55em",
            overflow="hidden",
            text_overflow="ellipsis",
            white_space="nowrap",
            width="100%",
        ),
        rx.text(
            winner.get("guest_id", winner.get("id", "")),
            color="gray",
            font_size="0.68em",
            margin_top="0.1em",
        ),
        rx.cond(
            prize_value != "",
            rx.text(
                prize_value,
                color=GOLD,
                font_size="0.72em",
                font_weight="700",
                margin_top="0.35em",
            ),
            rx.fragment(),
        ),
        background=DARK_GRAY,
        border=f"1px solid {GOLD}",
        border_radius="12px",
        padding=["0.75em", "0.9em"],
        width="100%",
        min_height="105px",
        display="flex",
        flex_direction="column",
        justify_content="center",
    )


def _current_prize():
    """Render the current prize prominently for the live audience."""
    return rx.box(
        rx.hstack(
            rx.text(
                "CURRENT PRIZE",
                color=GOLD,
                font_size="0.7em",
                font_weight="800",
                letter_spacing="0.12em",
            ),
            rx.spacer(),
            rx.box(
                rx.text(
                    f"PRIZE {LuckyDrawState.current_prize_index + 1}",
                    color=BLACK,
                    font_size="0.58em",
                    font_weight="800",
                    letter_spacing="0.08em",
                ),
                background=GOLD,
                border_radius="999px",
                padding_x="0.75em",
                padding_y="0.3em",
            ),
            width="100%",
            align="center",
        ),
        rx.cond(
            LuckyDrawState.lucky_draw_prize_picture != "",
            rx.image(
                src=LuckyDrawState.lucky_draw_prize_picture,
                width=["125px", "155px", "190px"],
                height=["125px", "155px", "190px"],
                object_fit="contain",
                border_radius="14px",
                margin_top="0.9em",
                background=BLACK,
                padding="0.4em",
            ),
            rx.box(
                rx.icon(tag="gift", size=58),
                width=["125px", "155px", "190px"],
                height=["125px", "155px", "190px"],
                display="flex",
                align_items="center",
                justify_content="center",
                background=BLACK,
                border_radius="14px",
                margin_top="0.9em",
            ),
        ),
        rx.heading(
            LuckyDrawState.lucky_draw_prize_name,
            color="white",
            size=rx.breakpoints(initial="5", md="6", lg="7"),
            text_align="center",
            margin_top="0.7em",
            line_height="1.1",
        ),
        rx.cond(
            LuckyDrawState.lucky_draw_prize_value != "",
            rx.text(
                LuckyDrawState.lucky_draw_prize_value,
                color=GOLD,
                font_size=["1em", "1.2em"],
                font_weight="700",
                text_align="center",
                margin_top="0.25em",
            ),
            rx.fragment(),
        ),
        background=DARK_GRAY,
        border=f"2px solid {GOLD}",
        border_radius="18px",
        padding=["1em", "1.3em"],
        width="100%",
        min_height=["300px", "340px", "390px"],
        display="flex",
        flex_direction="column",
        align_items="center",
        justify_content="flex-start",
    )

def _candidate_panel():
    """Render the live candidate area and operator controls."""
    return rx.box(
        rx.hstack(
            rx.text(
                "DRAW RESULT",
                color=GOLD,
                font_size="0.7em",
                font_weight="800",
                letter_spacing="0.12em",
            ),
            rx.spacer(),
            rx.cond(
                LuckyDrawState.lucky_draw_spinning,
                rx.box(
                    rx.text(
                        "DRAWING",
                        color=BLACK,
                        font_size="0.58em",
                        font_weight="800",
                        letter_spacing="0.08em",
                    ),
                    background=GOLD,
                    border_radius="999px",
                    padding_x="0.75em",
                    padding_y="0.3em",
                ),
                rx.cond(
                    LuckyDrawState.draw_status == "CANDIDATE",
                    rx.box(
                        rx.text(
                            "AWAITING CONFIRMATION",
                            color=BLACK,
                            font_size="0.58em",
                            font_weight="800",
                            letter_spacing="0.06em",
                        ),
                        background=GOLD,
                        border_radius="999px",
                        padding_x="0.75em",
                        padding_y="0.3em",
                    ),
                    rx.cond(
                        LuckyDrawState.draw_status == "CONFIRMED",
                        rx.box(
                            rx.text(
                                "CONFIRMED",
                                color=BLACK,
                                font_size="0.58em",
                                font_weight="800",
                                letter_spacing="0.08em",
                            ),
                            background=GOLD,
                            border_radius="999px",
                            padding_x="0.75em",
                            padding_y="0.3em",
                        ),
                        rx.box(
                            rx.text(
                                "READY",
                                color="white",
                                font_size="0.58em",
                                font_weight="800",
                                letter_spacing="0.08em",
                            ),
                            border=f"1px solid {GOLD}",
                            border_radius="999px",
                            padding_x="0.75em",
                            padding_y="0.3em",
                        ),
                    ),
                ),
            ),
            width="100%",
            align="center",
        ),
        rx.cond(
            LuckyDrawState.lucky_draw_spinning,
            rx.vstack(
                rx.spinner(size="3", color=GOLD),
                rx.text(
                    "Selecting a participant...",
                    color="white",
                    font_size=["1em", "1.2em"],
                    font_weight="600",
                ),
                rx.text(
                    "Please wait",
                    color="gray",
                    font_size="0.75em",
                ),
                spacing="3",
                align="center",
                justify="center",
                padding=["2em", "1em"],
                min_height="190px",
            ),
            rx.cond(
                LuckyDrawState.draw_status == "CANDIDATE",
                rx.vstack(
                    rx.text(
                        "CANDIDATE SELECTED",
                        color=GOLD,
                        font_size="0.72em",
                        font_weight="800",
                        letter_spacing="0.12em",
                    ),
                    rx.box(
                        rx.text(
                            LuckyDrawState.lucky_draw_current_name,
                            color="white",
                            font_size=["2em", "3em", "4em"],
                            font_weight="800",
                            text_align="center",
                            line_height="1.05",
                        ),
                        width="100%",
                        padding_x="0.5em",
                    ),
                    rx.text(
                        LuckyDrawState.lucky_draw_current_id,
                        color=GOLD,
                        font_size=["0.9em", "1em"],
                        font_weight="600",
                    ),
                    rx.text(
                        "Please confirm whether the participant is present.",
                        color="gray",
                        font_size=["0.75em", "0.85em"],
                        text_align="center",
                    ),
                    rx.hstack(
                        rx.button(
                            rx.hstack(
                                rx.icon(tag="circle_check", size=18),
                                rx.text("CONFIRM WINNER"),
                                spacing="2",
                            ),
                            on_click=LuckyDrawState.confirm_current_winner,
                            background=GOLD,
                            color=BLACK,
                            size="3",
                            padding_x="1.4em",
                            _hover={"transform": "scale(1.02)"},
                        ),
                        rx.button(
                            rx.hstack(
                                rx.icon(tag="user_x", size=18),
                                rx.text("ABSENT / REDRAW"),
                                spacing="2",
                            ),
                            on_click=LuckyDrawState.reject_candidate_as_absent,
                            variant="outline",
                            border_color="red.500",
                            color="red.400",
                            size="3",
                            padding_x="1.4em",
                        ),
                        spacing="3",
                        justify="center",
                        wrap="wrap",
                        width="100%",
                    ),
                    spacing="3",
                    align="center",
                    padding=["1.2em", "2em"],
                ),
                rx.cond(
                    LuckyDrawState.draw_status == "CONFIRMED",
                    rx.vstack(
                        rx.text(
                            "WINNER CONFIRMED",
                            color=GOLD,
                            font_size="0.75em",
                            font_weight="800",
                            letter_spacing="0.12em",
                        ),
                        rx.text(
                            LuckyDrawState.lucky_draw_current_name,
                            color="white",
                            font_size=["2em", "3em", "4em"],
                            font_weight="800",
                            text_align="center",
                            line_height="1.05",
                        ),
                        rx.text(
                            LuckyDrawState.lucky_draw_current_id,
                            color=GOLD,
                            font_size=["0.9em", "1em"],
                            font_weight="600",
                        ),
                        rx.cond(
                            LuckyDrawState.draw_finished,
                            rx.button(
                                "DRAW COMPLETE",
                                disabled=True,
                                variant="outline",
                                border_color=GOLD,
                                color=GOLD,
                                size="3",
                            ),
                            rx.button(
                                rx.hstack(
                                    rx.icon(tag="chevron_right", size=18),
                                    rx.text("NEXT PRIZE"),
                                    spacing="2",
                                ),
                                on_click=LuckyDrawState.advance_to_next_prize,
                                background=GOLD,
                                color=BLACK,
                                size="3",
                                padding_x="2em",
                            ),
                        ),
                        spacing="3",
                        align="center",
                        padding=["1.2em", "2em"],
                    ),
                    rx.vstack(
                        rx.text(
                            "Ready for the next draw",
                            color="gray",
                            font_size=["0.9em", "1.1em"],
                        ),
                        rx.button(
                            rx.hstack(
                                rx.icon(tag="play", size=20),
                                rx.text("START DRAW"),
                                spacing="2",
                            ),
                            on_click=LuckyDrawState.draw_candidate,
                            background=GOLD,
                            color=BLACK,
                            size="4",
                            padding_x=["2em", "3em"],
                            _hover={"transform": "scale(1.03)"},
                        ),
                        rx.cond(
                            LuckyDrawState.draw_status == "DONE",
                            rx.text(
                                "All prizes have been awarded.",
                                color=GOLD,
                                font_weight="700",
                            ),
                            rx.fragment(),
                        ),
                        spacing="3",
                        align="center",
                        justify="center",
                        padding=["1.2em", "2em"],
                        min_height="190px",
                    ),
                ),
            ),
        ),
        background=DARK_GRAY,
        border=f"1px solid {GOLD}",
        border_radius="18px",
        padding=["1em", "1.3em"],
        width="100%",
        min_height=["250px", "300px"],
        display="flex",
        flex_direction="column",
        align_items="center",
    )

def _prize_progress():
    """Show prize progress without duplicating prize data."""
    return rx.box(
        rx.hstack(
            rx.text(
                "PRIZE PROGRESS",
                color=GOLD,
                font_size="0.7em",
                font_weight="800",
                letter_spacing="0.1em",
            ),
            rx.spacer(),
            rx.text(
                f"{LuckyDrawState.current_prize_index + 1} / {LuckyDrawState.current_prizes.length()}",
                color="white",
                font_size="0.8em",
                font_weight="700",
            ),
            width="100%",
        ),
        rx.progress(
            value=LuckyDrawState.current_prize_index + 1,
            max=LuckyDrawState.current_prizes.length(),
            width="100%",
            color_scheme="amber",
            margin_top="0.6em",
        ),
        background=DARK_GRAY,
        border_radius="10px",
        padding="0.8em",
        width="100%",
    )


def lucky_draw_display_page():
    """Render the fullscreen Lucky Draw display."""
    return rx.box(
        rx.vstack(
            # Header
            rx.hstack(
                rx.vstack(
                    rx.text(
                        "EVENTLAH",
                        color=GOLD,
                        font_size=["0.75em", "0.85em"],
                        font_weight="800",
                        letter_spacing="0.18em",
                    ),
                    rx.heading(
                        LuckyDrawState.lucky_draw_event_name,
                        color="white",
                        size=rx.breakpoints(initial="4", md="5"),
                    ),
                    spacing="1",
                    align="start",
                ),
                rx.spacer(),
                rx.box(
                    rx.text(
                        "LIVE",
                        color=BLACK,
                        font_size="0.7em",
                        font_weight="800",
                    ),
                    background=GOLD,
                    border_radius="999px",
                    padding_x="1em",
                    padding_y="0.45em",
                ),
                width="100%",
                align="center",
            ),

            # Main prize/result area
            rx.grid(
                _current_prize(),
                _candidate_panel(),
                columns="repeat(2, minmax(0, 1fr))",
                spacing="4",
                width="100%",
            ),

            _prize_progress(),

            # Preliminary participant display
            rx.box(
                rx.hstack(
                    rx.vstack(
                        rx.text(
                            "PARTICIPANTS",
                            color=GOLD,
                            font_size="0.7em",
                            font_weight="800",
                            letter_spacing="0.1em",
                        ),
                        rx.text(
                            "Eligible participants",
                            color="gray",
                            font_size="0.75em",
                        ),
                        spacing="1",
                        align="start",
                    ),
                    rx.spacer(),
                    rx.text(
                        f"{LuckyDrawState.lucky_draw_eligible_guests.length()} eligible",
                        color="white",
                        font_size="0.8em",
                        font_weight="700",
                    ),
                    width="100%",
                    align="center",
                ),
                rx.grid(
                    rx.foreach(
                        LuckyDrawState.lucky_draw_eligible_guests[:30],
                        _participant_card,
                    ),
                    columns=rx.breakpoints(initial="2", md="3", lg="5"),
                    spacing="2",
                    width="100%",
                    margin_top="0.8em",
                ),
                background=DARK_GRAY,
                border_radius="14px",
                padding="1em",
                width="100%",
            ),

            # Winner history
            rx.cond(
                LuckyDrawState.winners_list.length() > 0,
                rx.box(
                    rx.hstack(
                        rx.vstack(
                            rx.text(
                                "WINNER HISTORY",
                                color=GOLD,
                                font_size="0.7em",
                                font_weight="800",
                                letter_spacing="0.1em",
                            ),
                            rx.text(
                                "Confirmed winners",
                                color="gray",
                                font_size="0.7em",
                            ),
                            spacing="1",
                            align="start",
                        ),
                        rx.spacer(),
                        rx.box(
                            rx.text(
                                f"{LuckyDrawState.winners_list.length()} CONFIRMED",
                                color=BLACK,
                                font_size="0.58em",
                                font_weight="800",
                                letter_spacing="0.06em",
                            ),
                            background=GOLD,
                            border_radius="999px",
                            padding_x="0.7em",
                            padding_y="0.3em",
                        ),
                        width="100%",
                        align="center",
                    ),
                    rx.grid(
                        rx.foreach(
                            LuckyDrawState.winners_list[:6],
                            _winner_card,
                        ),
                        columns=rx.breakpoints(initial="1", md="2", lg="3"),
                        spacing="2",
                        width="100%",
                        margin_top="0.8em",
                    ),
                    rx.cond(
                        LuckyDrawState.winners_list.length() > 6,
                        rx.text(
                            "Showing the latest 6 winners",
                            color="gray",
                            font_size="0.65em",
                            text_align="center",
                            width="100%",
                            margin_top="0.6em",
                        ),
                        rx.fragment(),
                    ),
                    background=DARK_GRAY,
                    border=f"1px solid {GOLD}",
                    border_radius="14px",
                    padding="1em",
                    width="100%",
                ),
                rx.fragment(),
            ),

            # Footer controls
            rx.hstack(
                rx.button(
                    rx.hstack(
                        rx.icon(tag="arrow_left", size=15),
                        rx.text("BACK TO LUCKY DRAW"),
                        spacing="2",
                    ),
                    on_click=rx.redirect(
                        f"/lucky-draw/{LuckyDrawState.current_event_id}"
                    ),
                    variant="outline",
                    border_color=GOLD,
                    color=GOLD,
                ),
                rx.spacer(),
                rx.text(
                    "ESC / browser controls can be used to exit fullscreen.",
                    color="gray",
                    font_size="0.65em",
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
