# guest_management/pages/lucky_draw_display.py
"""
Fullscreen LIVE Lucky Draw presentation and operator control screen.

This is the MAIN prize draw screen.

It is intentionally separate from:
    guest_management/pages/pre_draw_display.py

The pre-draw screen shows preliminary winners only.

This screen controls the actual live prize draw:
    READY
        ↓
    DRAWING
        ↓
    CANDIDATE
        ↓
    CONFIRMED
        ↓
    NEXT PRIZE
        ↓
    DONE
"""

import reflex as rx

from ..state.lucky_draw_state import LuckyDrawState
from ..utils.constants import GOLD, BLACK, DARK_GRAY, LIGHT_GRAY


# ============================================================================
# EVENT HEADER
# ============================================================================
def _wheel_styles():
    """Page-local CSS for the always-visible live Lucky Draw wheel."""
    return rx.html(
        """<style>
        @keyframes eventlahLuckyWheelSpin {
            from { transform: rotate(0deg); }
            to { transform: rotate(360deg); }
        }

        .eventlah-lucky-wheel {
            will-change: transform;
        }

        .eventlah-lucky-wheel-spinning {
            animation: eventlahLuckyWheelSpin 1.0s linear infinite;
        }

        .eventlah-wheel-pointer {
            position: absolute;
            top: -10px;
            left: 50%;
            transform: translateX(-50%);
            z-index: 20;
        }

        .eventlah-wheel-pointer-label {
            min-width: 220px;
            max-width: 360px;
            padding: 10px 18px;
            border-radius: 999px;
            background: #111111;
            border: 2px solid #D4AF37;
            color: #D4AF37;
            font-weight: 900;
            text-align: center;
            box-shadow: 0 0 20px rgba(212,175,55,.35);
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        </style>"""
    )


def _spinning_wheel():
    """Always-visible roulette wheel.

    The backend owns candidate selection. The browser owns only the visual
    rotation, so the wheel remains idle between draws and never generates
    backend traffic by itself.
    """
    spinning_class = rx.cond(
        LuckyDrawState.lucky_draw_spinning,
        "eventlah-lucky-wheel eventlah-lucky-wheel-spinning",
        "eventlah-lucky-wheel",
    )

    wheel_name = rx.cond(
        LuckyDrawState.lucky_draw_current_name != "",
        LuckyDrawState.lucky_draw_current_name,
        "READY",
    )

    pointer_name = rx.cond(
        LuckyDrawState.lucky_draw_current_name != "",
        LuckyDrawState.lucky_draw_current_name,
        "READY TO DRAW",
    )

    return rx.box(
        # Fixed winner/name pointer.
        rx.box(
            rx.text(
                pointer_name,
                font_size=["0.8em", "0.95em", "1.05em"],
                line_height="1.1",
            ),
            class_name="eventlah-wheel-pointer-label",
        ),
        rx.box(
            width="0",
            height="0",
            border_left="22px solid transparent",
            border_right="22px solid transparent",
            border_top=f"42px solid {GOLD}",
            margin="8px auto 0",
        ),
        # Rotating wheel.
        rx.box(
            rx.box(
                rx.vstack(
                    rx.text(
                        "LUCKY",
                        color=GOLD,
                        font_size=["0.7em", "0.85em"],
                        font_weight="900",
                        letter_spacing="0.18em",
                    ),
                    rx.text(
                        "DRAW",
                        color="white",
                        font_size=["1em", "1.35em"],
                        font_weight="900",
                        letter_spacing="0.08em",
                    ),
                    rx.text(
                        wheel_name,
                        color=GOLD,
                        font_size=["1em", "1.35em", "1.65em"],
                        font_weight="900",
                        text_align="center",
                        max_width=["150px", "190px", "220px"],
                        overflow="hidden",
                        text_overflow="ellipsis",
                        white_space="nowrap",
                    ),
                    spacing="1",
                    align="center",
                    justify="center",
                    width="100%",
                    height="100%",
                ),
                width=["100px", "120px", "145px"],
                height=["100px", "120px", "145px"],
                border_radius="50%",
                background=BLACK,
                border=f"5px solid {GOLD}",
                position="absolute",
                top="50%",
                left="50%",
                transform="translate(-50%, -50%)",
                z_index="4",
                display="flex",
                align_items="center",
                justify_content="center",
                box_shadow=f"0 0 25px {GOLD}55",
            ),
            width=["270px", "340px", "410px"],
            height=["270px", "340px", "410px"],
            border=f"10px solid {GOLD}",
            border_radius="50%",
            background=(
                "conic-gradient("
                "#D4AF37 0deg 30deg,"
                "#181818 30deg 60deg,"
                "#B8860B 60deg 90deg,"
                "#242424 90deg 120deg,"
                "#D4AF37 120deg 150deg,"
                "#181818 150deg 180deg,"
                "#B8860B 180deg 210deg,"
                "#242424 210deg 240deg,"
                "#D4AF37 240deg 270deg,"
                "#181818 270deg 300deg,"
                "#B8860B 300deg 330deg,"
                "#242424 330deg 360deg)"
            ),
            position="relative",
            overflow="hidden",
            class_name=spinning_class,
            box_shadow=f"0 0 40px {GOLD}40, inset 0 0 25px {GOLD}30",
        ),
        position="relative",
        width="100%",
        min_height=["380px", "470px", "540px"],
        display="flex",
        flex_direction="column",
        align_items="center",
        justify_content="center",
        padding_top="2.5em",
    )


def _current_prize():
    """Left-side operator panel: prize, image, readiness and start control."""
    return rx.box(
        rx.vstack(
            rx.text(
                "CURRENT PRIZE",
                color=GOLD,
                font_size="0.75em",
                font_weight="900",
                letter_spacing="0.16em",
            ),
            rx.heading(
                LuckyDrawState.lucky_draw_prize_name,
                color="white",
                size=rx.breakpoints(initial="5", md="6", lg="7"),
                text_align="center",
                margin="0",
            ),
            rx.cond(
                LuckyDrawState.lucky_draw_prize_value != "",
                rx.text(
                    LuckyDrawState.lucky_draw_prize_value,
                    color=GOLD,
                    font_size=["1em", "1.2em", "1.4em"],
                    font_weight="800",
                ),
                rx.fragment(),
            ),
            rx.cond(
                LuckyDrawState.lucky_draw_prize_picture != "",
                rx.image(
                    src=LuckyDrawState.lucky_draw_prize_picture,
                    width=["150px", "190px", "230px"],
                    height=["150px", "190px", "230px"],
                    object_fit="contain",
                    border_radius="16px",
                    border=f"1px solid {GOLD}55",
                    margin_top="0.5em",
                ),
                rx.box(
                    rx.icon(tag="gift", size=65, color=GOLD),
                    width=["150px", "190px", "230px"],
                    height=["150px", "190px", "230px"],
                    display="flex",
                    align_items="center",
                    justify_content="center",
                    border=f"1px dashed {GOLD}",
                    border_radius="16px",
                ),
            ),
            rx.text(
                rx.cond(
                    LuckyDrawState.lucky_draw_spinning,
                    "DRAWING...",
                    rx.cond(
                        LuckyDrawState.draw_status == "CONFIRMED",
                        "WINNER CONFIRMED",
                        "READY FOR DRAW",
                    ),
                ),
                color=rx.cond(
                    LuckyDrawState.lucky_draw_spinning,
                    GOLD,
                    "white",
                ),
                font_size="1.05em",
                font_weight="900",
                letter_spacing="0.08em",
            ),
            rx.cond(
                LuckyDrawState.draw_status != "CONFIRMED",
                rx.button(
                    rx.hstack(
                        rx.icon(tag="play", size=21),
                        rx.text("START DRAW"),
                        spacing="2",
                    ),
                    on_click=LuckyDrawState.start_lucky_draw,
                    background=GOLD,
                    color=BLACK,
                    size="4",
                    width="100%",
                    max_width="320px",
                    padding_y="1.15em",
                    disabled=LuckyDrawState.lucky_draw_spinning,
                    _hover={"transform": "scale(1.03)"},
                ),
                rx.fragment(),
            ),
            spacing="3",
            align="center",
            justify="center",
            width="100%",
            min_height=["420px", "500px", "560px"],
        ),
        background=DARK_GRAY,
        border=f"2px solid {GOLD}",
        border_radius="20px",
        padding=["1.2em", "1.5em", "2em"],
        width="100%",
        height="100%",
        display="flex",
        align_items="center",
        justify_content="center",
    )


def _candidate_panel():
    """Right-side wheel and candidate confirmation controls."""
    return rx.box(
        rx.vstack(
            rx.text(
                "LIVE DRAW",
                color=GOLD,
                font_size="0.75em",
                font_weight="900",
                letter_spacing="0.16em",
            ),
            _spinning_wheel(),
            rx.cond(
                LuckyDrawState.draw_status == "CANDIDATE",
                rx.vstack(
                    rx.text(
                        "IS THIS PARTICIPANT PRESENT?",
                        color=LIGHT_GRAY,
                        font_size="0.78em",
                        font_weight="800",
                        letter_spacing="0.08em",
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
                        ),
                        rx.button(
                            rx.hstack(
                                rx.icon(tag="user_x", size=18),
                                rx.text("ABSENT / REDRAW"),
                                spacing="2",
                            ),
                            on_click=LuckyDrawState.redraw_current_candidate,
                            variant="outline",
                            border_color="red.500",
                            color="red.400",
                            size="3",
                        ),
                        spacing="3",
                        justify="center",
                        wrap="wrap",
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.cond(
                    LuckyDrawState.draw_status == "CONFIRMED",
                    rx.button(
                        rx.hstack(
                            rx.icon(tag="chevron_right", size=18),
                            rx.text("NEXT PRIZE"),
                            spacing="2",
                        ),
                        on_click=LuckyDrawState.proceed_to_next_prize,
                        background=GOLD,
                        color=BLACK,
                        size="3",
                        padding_x="2em",
                    ),
                    rx.fragment(),
                ),
            ),
            spacing="2",
            width="100%",
            align="center",
        ),
        background=DARK_GRAY,
        border=f"1px solid {GOLD}",
        border_radius="20px",
        padding=["1em", "1.25em", "1.5em"],
        width="100%",
        height="100%",
        min_height=["500px", "600px", "660px"],
        display="flex",
        align_items="center",
        justify_content="center",
    )


# ============================================================================
# PRIZE PROGRESS
# ============================================================================

def _prize_progress():
    """Show the current prize position."""
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
                rx.cond(
                    LuckyDrawState.current_prizes.length() > 0,
                    (
                        LuckyDrawState.current_prize_index + 1
                    ).to_string()
                    + " / "
                    + LuckyDrawState.current_prizes.length().to_string(),
                    "0 / 0",
                ),
                color="white",
                font_size="0.8em",
                font_weight="700",
            ),

            width="100%",
            align="center",
        ),

        rx.progress(
            value=(
                LuckyDrawState.current_prize_index + 1
            ),
            max=rx.cond(
                LuckyDrawState.current_prizes.length() > 0,
                LuckyDrawState.current_prizes.length(),
                1,
            ),
            width="100%",
            color_scheme="amber",
            margin_top="0.6em",
        ),

        background=DARK_GRAY,
        border_radius="10px",
        padding="0.8em",
        width="100%",
    )


# ============================================================================
# WINNER HISTORY
# ============================================================================

def _winner_history():
    """Show recent confirmed winners."""
    return rx.cond(
        LuckyDrawState.winners_list.length() > 0,

        rx.box(
            rx.hstack(
                rx.hstack(
                    rx.icon(
                        tag="trophy",
                        size=17,
                        color=GOLD,
                    ),
                    rx.text(
                        "WINNER HISTORY",
                        color=GOLD,
                        font_size="0.72em",
                        font_weight="800",
                        letter_spacing="0.1em",
                    ),
                    spacing="2",
                ),

                rx.spacer(),

                rx.text(
                    LuckyDrawState.winners_list.length(),
                    " confirmed",
                    color=LIGHT_GRAY,
                    font_size="0.72em",
                ),

                width="100%",
                align="center",
            ),

            rx.grid(
                rx.foreach(
                    LuckyDrawState.winners_list[:6],
                    lambda winner: rx.box(
                        rx.hstack(
                            rx.icon(
                                tag="trophy",
                                size=13,
                                color=GOLD,
                            ),

                            rx.vstack(
                                rx.text(
                                    winner.get(
                                        "name",
                                        "Unknown",
                                    ),
                                    color="white",
                                    font_size="0.75em",
                                    font_weight="700",
                                ),

                                rx.text(
                                    winner.get(
                                        "prize_name",
                                        "",
                                    ),
                                    color=GOLD,
                                    font_size="0.65em",
                                ),

                                spacing="0",
                                align="start",
                            ),

                            spacing="2",
                            align="center",
                        ),

                        background=BLACK,
                        border_radius="8px",
                        padding="0.55em",
                        width="100%",
                    ),
                ),

                columns=rx.breakpoints(
                    initial="1",
                    md="2",
                    lg="3",
                ),

                spacing="2",
                width="100%",
                margin_top="0.7em",
            ),

            background=DARK_GRAY,
            border=f"1px solid {GOLD}40",
            border_radius="12px",
            padding="1em",
            width="100%",
        ),

        rx.fragment(),
    )


# ============================================================================
# FOOTER
# ============================================================================

def _footer():
    """Render display controls."""
    return rx.hstack(
        rx.button(
            rx.hstack(
                rx.icon(
                    tag="arrow_left",
                    size=15,
                ),
                rx.text(
                    "BACK TO LUCKY DRAW"
                ),
                spacing="2",
            ),
            on_click=rx.redirect(
                f"/lucky-draw/"
                f"{LuckyDrawState.current_event_id}"
            ),
            variant="outline",
            border_color=GOLD,
            color=GOLD,
            size="2",
        ),

        rx.spacer(),

        rx.text(
            "LIVE LUCKY DRAW",
            color=LIGHT_GRAY,
            font_size="0.65em",
            letter_spacing="0.08em",
        ),

        width="100%",
        align="center",
    )


# ============================================================================
# MAIN PAGE
# ============================================================================

def lucky_draw_display_page():
    """
    Render the MAIN live Lucky Draw display.

    This is the screen opened by:
        START DISPLAY SCREEN
    """
    return rx.box(
        _wheel_styles(),

        rx.vstack(
            _event_header(),

            # -----------------------------------------------------------
            # CURRENT PRIZE + DRAW RESULT
            # -----------------------------------------------------------
            rx.grid(
                _current_prize(),
                _candidate_panel(),
                columns=rx.breakpoints(initial="1", lg="minmax(420px, 0.9fr) minmax(520px, 1.1fr)"),
                spacing="4",
                width="100%",
                align_items="stretch",
            ),

            _prize_progress(),
            _winner_history(),

            _footer(),

            spacing="4",
            width="100%",
            max_width="1800px",
            padding=[
                "1em",
                "1.5em",
                "2em",
            ],
        ),

        background=BLACK,
        min_height="100vh",
        width="100%",
        color="white",
    )
