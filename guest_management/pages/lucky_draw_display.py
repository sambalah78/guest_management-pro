# guest_management/pages/lucky_draw_display.py
"""Lucky Draw Display page - Full-screen display for events."""

import reflex as rx
from guest_management.state import State, GOLD, BLACK, DARK_GRAY
from guest_management.state.lucky_draw_state import LuckyDrawState

# CSS Animations
ANIMATIONS_CSS = """
@keyframes fadeOutLeft {
    0% { opacity: 1; transform: translateX(0); }
    100% { opacity: 0; transform: translateX(-30px); }
}
@keyframes fadeInRight {
    0% { opacity: 0; transform: translateX(30px); }
    100% { opacity: 1; transform: translateX(0); }
}
@keyframes wheelSpin {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
}
@keyframes pulse {
    0%, 100% { opacity: 1; }
    50% { opacity: 0.5; }
}
@keyframes bounce {
    0%, 100% { transform: translateY(0); }
    50% { transform: translateY(-10px); }
}
@keyframes slideIn {
    0% { opacity: 0; transform: translateY(20px); }
    100% { opacity: 1; transform: translateY(0); }
}
.fade-out { animation: fadeOutLeft 0.5s ease-in-out forwards; }
.fade-in { animation: fadeInRight 0.5s ease-in-out forwards; }
.wheel-spin { animation: wheelSpin 0.05s linear infinite; }
.pulse { animation: pulse 1s ease-in-out infinite; }
.bounce { animation: bounce 0.5s ease-in-out; }
.slide-in { animation: slideIn 0.5s ease-out; }
"""


def render_winner_item(winner):
    """Render a single winner item for history - compact."""
    return rx.hstack(
        rx.vstack(
            rx.hstack(
                rx.icon(tag="crown", size=10, color=GOLD),
                rx.text(
                    winner.get("name", "Unknown"),
                    color=GOLD,
                    weight="bold",
                    font_size=["0.65rem", "0.7rem", "0.75rem"],
                ),
                spacing="1",
            ),
            rx.text(
                f"Prize: {winner.get('prize_name', '')}",
                color="gray",
                font_size=["0.55rem", "0.6rem", "0.65rem"],
            ),
            spacing="0",
            align="start",
        ),
        rx.spacer(),
        rx.text(
            winner.get("formatted_date", ""),
            color="gray",
            font_size=["0.5rem", "0.55rem", "0.6rem"],
        ),
        spacing="2",
        width="100%",
        padding=["0.2em", "0.3em", "0.4em"],
        border_bottom="1px solid rgba(212, 175, 55, 0.1)",
        _hover={"bg": f"{GOLD}11"},
    )


def lucky_draw_display_page():
    """Full-screen responsive display page."""
    return rx.fragment(
        rx.el.style(ANIMATIONS_CSS),
        rx.center(
            rx.vstack(
                # Top Header
                rx.vstack(
                    rx.text(
                        "LUCKY DRAW",
                        font_size=["1.2rem", "1.4rem", "1.6rem", "1.8rem"],
                        color=GOLD,
                        letter_spacing="0.15em",
                        weight="bold",
                        text_align="center",
                    ),
                    rx.heading(
                        LuckyDrawState.lucky_draw_event_name,
                        font_size=["0.9rem", "1rem", "1.1rem", "1.2rem"],
                        color="white",
                        weight="bold",
                        text_align="center",
                    ),
                    spacing="0",
                    width="100%",
                    padding=["0.3em", "0.5em", "0.5em"],
                ),

                # Main Content
                rx.grid(
                    # LEFT COLUMN - Prize Information
                    rx.vstack(
                        # Prize Image/Icon
                        rx.cond(
                            LuckyDrawState.lucky_draw_prize_picture,
                            rx.image(
                                src=LuckyDrawState.lucky_draw_prize_picture,
                                width=["100px", "120px", "140px", "160px"],
                                height=["100px", "120px", "140px", "160px"],
                                border_radius="15px",
                                border=f"2px solid {GOLD}",
                                box_shadow=f"0 0 20px {GOLD}",
                                object_fit="cover",
                                class_name=rx.cond(LuckyDrawState.prize_transitioning, "fade-out", "fade-in"),
                            ),
                            rx.box(
                                rx.icon(tag="gift", size=50, color=GOLD),
                                width=["100px", "120px", "140px", "160px"],
                                height=["100px", "120px", "140px", "160px"],
                                display="flex",
                                align_items="center",
                                justify_content="center",
                                bg=f"linear-gradient(135deg, {DARK_GRAY}, {BLACK})",
                                border_radius="15px",
                                border=f"1px dashed {GOLD}",
                                class_name=rx.cond(LuckyDrawState.prize_transitioning, "fade-out", "fade-in"),
                            ),
                        ),

                        # Prize Name
                        rx.cond(
                            LuckyDrawState.lucky_draw_prize_name,
                            rx.text(
                                LuckyDrawState.lucky_draw_prize_name,
                                font_size=["1rem", "1.2rem", "1.4rem", "1.6rem"],
                                color=GOLD,
                                weight="bold",
                                text_align="center",
                                class_name=rx.cond(LuckyDrawState.prize_transitioning, "fade-out", "fade-in"),
                            ),
                            rx.text(
                                "Ready for Draw",
                                font_size=["1rem", "1.2rem", "1.4rem", "1.6rem"],
                                color=GOLD,
                                weight="bold",
                                text_align="center",
                                class_name=rx.cond(LuckyDrawState.prize_transitioning, "fade-out", "fade-in"),
                            ),
                        ),

                        # Prize Value
                        rx.cond(
                            LuckyDrawState.lucky_draw_prize_value,
                            rx.text(
                                f"RM {LuckyDrawState.lucky_draw_prize_value}",
                                font_size=["0.8rem", "0.9rem", "1rem"],
                                color="white",
                                text_align="center",
                                padding="0.2em 1em",
                                bg=f"{GOLD}22",
                                border_radius="full",
                                class_name=rx.cond(LuckyDrawState.prize_transitioning, "fade-out", "fade-in"),
                            ),
                            rx.fragment(),
                        ),

                        # Prize Progress
                        rx.cond(
                            LuckyDrawState.prize_mode != "single",
                            rx.cond(
                                LuckyDrawState.current_prizes.length() > 0,
                                rx.vstack(
                                    rx.text("Progress", color="gray", font_size="0.6rem", letter_spacing="0.1em"),
                                    rx.progress(
                                        value=(LuckyDrawState.current_prize_index + 1) / LuckyDrawState.current_prizes.length() * 100,
                                        size="1",
                                        color_scheme="gold",
                                        width="100%",
                                        max_width="150px",
                                    ),
                                    rx.text(
                                        f"{LuckyDrawState.current_prize_index + 1}/{LuckyDrawState.current_prizes.length()}",
                                        color=GOLD,
                                        font_size="0.65rem",
                                        weight="bold",
                                    ),
                                    spacing="0",
                                    align="center",
                                    width="100%",
                                ),
                                rx.fragment(),
                            ),
                            rx.fragment(),
                        ),
                        spacing="2",
                        align="center",
                        width="100%",
                        padding=["0.5em", "0.8em", "1em"],
                    ),

                    # RIGHT COLUMN - Winner Display
                    rx.vstack(
                        rx.cond(
                            LuckyDrawState.lucky_draw_spinning,
                            # Spinning State
                            rx.vstack(
                                rx.box(
                                    rx.vstack(
                                        rx.cond(
                                            LuckyDrawState.lucky_draw_current_name,
                                            rx.text(
                                                LuckyDrawState.lucky_draw_current_name,
                                                font_size=["1rem", "1.2rem", "1.4rem"],
                                                weight="bold",
                                                color=GOLD,
                                                text_align="center",
                                            ),
                                            rx.text(
                                                "?????",
                                                font_size=["1rem", "1.2rem", "1.4rem"],
                                                weight="bold",
                                                color=GOLD,
                                                text_align="center",
                                            ),
                                        ),
                                        rx.cond(
                                            LuckyDrawState.lucky_draw_current_id,
                                            rx.text(
                                                f"ID: {LuckyDrawState.lucky_draw_current_id}",
                                                font_size=["0.65rem", "0.7rem", "0.75rem"],
                                                color="gray",
                                            ),
                                            rx.text(
                                                "ID: ???",
                                                font_size=["0.65rem", "0.7rem", "0.75rem"],
                                                color="gray",
                                            ),
                                        ),
                                        spacing="1",
                                        align="center",
                                    ),
                                    width=["220px", "240px", "260px", "280px"],
                                    height=["220px", "240px", "260px", "280px"],
                                    border_radius="50%",
                                    background=f"conic-gradient(from 0deg, {GOLD}11, {GOLD}33, {GOLD}66, {GOLD}99, {GOLD}66, {GOLD}33, {GOLD}11)",
                                    display="flex",
                                    align_items="center",
                                    justify_content="center",
                                    class_name="wheel-spin",
                                    style={"boxShadow": f"0 0 20px {GOLD}"},
                                ),
                                rx.text(
                                    "SPINNING",
                                    font_size=["0.7rem", "0.8rem", "0.9rem"],
                                    color=GOLD,
                                    letter_spacing="0.2em",
                                    class_name="pulse",
                                ),
                                spacing="3",
                                align="center",
                                width="100%",
                            ),
                            rx.cond(
                                LuckyDrawState.lucky_draw_winner,
                                # Winner Display State
                                rx.vstack(
                                    rx.card(
                                        rx.vstack(
                                            rx.hstack(
                                                rx.icon(tag="sparkles", size=12, color=GOLD),
                                                rx.icon(tag="crown", size=18, color=GOLD),
                                                rx.icon(tag="sparkles", size=12, color=GOLD),
                                                spacing="2",
                                                justify="center",
                                                class_name="bounce",
                                            ),
                                            rx.text(
                                                "WINNER!",
                                                font_size=["0.9rem", "1rem", "1.1rem"],
                                                color=GOLD,
                                                weight="bold",
                                            ),
                                            rx.heading(
                                                LuckyDrawState.lucky_draw_winner.get("name", ""),
                                                font_size=["1.1rem", "1.3rem", "1.5rem"],
                                                color="white",
                                                weight="bold",
                                                text_align="center",
                                            ),
                                            rx.hstack(
                                                rx.badge(
                                                    f"ID: {LuckyDrawState.lucky_draw_winner.get('guest_id', '')}",
                                                    color_scheme="gold",
                                                    size="1",
                                                ),
                                                rx.badge(
                                                    f"Table: {LuckyDrawState.lucky_draw_winner.get('table_number', 'TBD')}",
                                                    color_scheme="gray",
                                                    size="1",
                                                ),
                                                spacing="1",
                                                wrap="wrap",
                                            ),
                                            rx.text(
                                                f"Prize: {LuckyDrawState.lucky_draw_prize_name}",
                                                font_size=["0.7rem", "0.8rem", "0.9rem"],
                                                color=GOLD,
                                                weight="bold",
                                            ),
                                            spacing="2",
                                            align="center",
                                            width="100%",
                                        ),
                                        bg=DARK_GRAY,
                                        border=f"1px solid {GOLD}",
                                        border_radius="15px",
                                        padding="0.8em",
                                        width="100%",
                                    ),

                                    # NEXT button
                                    rx.cond(
                                        LuckyDrawState.waiting_for_next_prize,
                                        rx.button(
                                            rx.hstack(
                                                rx.icon(tag="arrow-right", size=14),
                                                rx.text("NEXT", font_size="0.85rem", weight="bold"),
                                            ),
                                            on_click=LuckyDrawState.show_next_prize,
                                            bg=GOLD,
                                            color=BLACK,
                                            size="2",
                                            padding="0.4em 1.2em",
                                        ),
                                        rx.button(
                                            rx.hstack(
                                                rx.icon(tag="play", size=14),
                                                rx.text("DRAW AGAIN", font_size="0.85rem", weight="bold"),
                                            ),
                                            on_click=LuckyDrawState.draw_current_prize,
                                            bg=GOLD,
                                            color=BLACK,
                                            size="2",
                                            padding="0.4em 1.2em",
                                            is_disabled=LuckyDrawState.lucky_draw_eligible_count == 0,
                                        ),
                                    ),

                                    # Eligible Count
                                    rx.hstack(
                                        rx.icon(tag="users", size=10, color=GOLD),
                                        rx.text(
                                            f"{LuckyDrawState.lucky_draw_eligible_count} Eligible",
                                            font_size=["0.65rem", "0.7rem", "0.75rem"],
                                            color="white",
                                        ),
                                        spacing="1",
                                        bg=f"{GOLD}22",
                                        padding="0.2em 0.8em",
                                        border_radius="full",
                                    ),
                                    spacing="2",
                                    align="center",
                                    width="100%",
                                ),
                                # Ready State - Shows START DRAW button
                                rx.vstack(
                                    rx.button(
                                        rx.hstack(
                                            rx.icon(tag="play", size=16),
                                            rx.text("START DRAW", font_size=["0.9rem", "1rem", "1.1rem"], weight="bold"),
                                        ),
                                        on_click=LuckyDrawState.draw_current_prize,
                                        bg=GOLD,
                                        color=BLACK,
                                        size="3",
                                        padding="0.5em 1.2em",
                                        is_disabled=LuckyDrawState.lucky_draw_eligible_count == 0,
                                    ),
                                    rx.cond(
                                        LuckyDrawState.lucky_draw_eligible_count == 0,
                                        rx.text("No eligible guests", color="red", font_size="0.7rem"),
                                        rx.fragment(),
                                    ),
                                    spacing="2",
                                    align="center",
                                ),
                            ),
                        ),
                        width="100%",
                        align="center",
                    ),
                    columns="2",
                    spacing="3",
                    width="100%",
                    align="center",
                    justify="between",
                    gap=["1em", "1.5em", "2em"],
                ),

                # Winners History
                rx.cond(
                    LuckyDrawState.winners_list.length() > 0,
                    rx.card(
                        rx.vstack(
                            rx.hstack(
                                rx.hstack(
                                    rx.icon(tag="history", size=12, color=GOLD),
                                    rx.heading("Recent Winners", size="3", color=GOLD, font_size=["0.9em", "1em", "1.1em"]),
                                    spacing="2",
                                ),
                                rx.spacer(),
                                rx.hstack(
                                    rx.button(
                                        rx.hstack(
                                            rx.icon(tag="download", size=10),
                                            rx.text("Export", font_size="0.7rem"),
                                        ),
                                        on_click=LuckyDrawState.download_winner_list,
                                        bg=GOLD,
                                        color=BLACK,
                                        size="1",
                                        padding="0.2em 0.6em",
                                        _hover={"bg": "#FFD700", "transform": "scale(1.02)"},
                                    ),
                                    rx.badge(
                                        f"{LuckyDrawState.winners_list.length()}",
                                        color_scheme="gold",
                                        size="1",
                                    ),
                                    spacing="2",
                                ),
                                spacing="2",
                                width="100%",
                            ),
                            rx.divider(margin="0.2em"),
                            rx.grid(
                                rx.foreach(
                                    LuckyDrawState.winners_list[:6],
                                    lambda winner: render_winner_item(winner),
                                ),
                                columns=rx.breakpoints(initial="1", md="2"),
                                spacing="1",
                                width="100%",
                                max_height="120px",
                                overflow="auto",
                            ),
                            spacing="1",
                            width="100%",
                        ),
                        bg=DARK_GRAY,
                        border=f"1px solid {GOLD}33",
                        border_radius="12px",
                        padding="0.5em",
                        width="100%",
                        margin_top="0.5em",
                        class_name="slide-in",
                    ),
                    rx.fragment(),
                ),

                # Back Button
                rx.button(
                    rx.hstack(
                        rx.icon(tag="arrow-left", size=10),
                        rx.text("Back", font_size=["0.65rem", "0.7rem"]),
                    ),
                    on_click=LuckyDrawState.redirect_to_lucky_draw,
                    variant="ghost",
                    color="gray",
                    size="1",
                    opacity="0.5",
                    _hover={"opacity": "1", "color": GOLD},
                    margin_top="0.5em",
                ),

                spacing="1",
                width="100%",
                max_width="900px",
                padding="0.8em",
            ),
            width="100%",
            height="100vh",
            bg=BLACK,
            style={
                "overflow": "hidden",
                "background": f"radial-gradient(circle at center, {DARK_GRAY}05, {BLACK} 100%)",
            },
        ),
    )