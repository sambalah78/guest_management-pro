# components/lucky_draw_spinner.py
import reflex as rx
from ..state.lucky_draw_state import LuckyDrawState
from ..utils.constants import GOLD, BLACK, DARK_GRAY




def lucky_draw_spinner():
    """Production Lucky Draw spinner component using the current LuckyDrawState."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.grid(
                # Left Column - Prize Information
                rx.vstack(
                    # Prize Image with Glow Effect
                    rx.cond(
                        LuckyDrawState.lucky_draw_prize_picture,
                        rx.box(
                            rx.image(
                                src=LuckyDrawState.lucky_draw_prize_picture,
                                width="100%",
                                max_width="280px",
                                height="auto",
                                border_radius="20px",
                                border=f"3px solid {GOLD}",
                                object_fit="cover",
                                box_shadow=f"0 0 30px {GOLD}",
                            ),
                            style={
                                "animation": "pulseGlow 2s ease-in-out infinite",
                            },
                        ),
                        rx.box(
                            rx.icon(tag="gift", size=70, color=GOLD),
                            width="100%",
                            height="200px",
                            display="flex",
                            align_items="center",
                            justify_content="center",
                            bg=f"linear-gradient(135deg, {DARK_GRAY}, {BLACK})",
                            border_radius="20px",
                            border=f"2px dashed {GOLD}",
                        ),
                    ),

                    # Prize Name with Gradient
                    rx.cond(
                        LuckyDrawState.lucky_draw_prize_name,
                        rx.heading(
                            LuckyDrawState.lucky_draw_prize_name,
                            size="6",
                            background=f"linear-gradient(135deg, {GOLD}, #FFD700)",
                            background_clip="text",
                            weight="bold",
                            text_align="center",
                        ),
                        rx.heading(
                            "No Prize Set",
                            size="6",
                            color="gray",
                            weight="bold",
                            text_align="center",
                        ),
                    ),

                    # Prize Value Badge
                    rx.cond(
                        LuckyDrawState.lucky_draw_prize_value,
                        rx.badge(
                            f" RM {LuckyDrawState.lucky_draw_prize_value}",
                            color_scheme="gold",
                            size="3",
                            variant="soft",
                            padding="0.5em 1em",
                            border_radius="full",
                        ),
                        rx.fragment(),
                    ),

                    # Prize Progress
                    rx.cond(
                        (LuckyDrawState.prize_mode != "single") & (LuckyDrawState.current_prizes.length() > 0),
                        rx.hstack(
                            rx.text("Prize Progress", color="gray", size="1"),
                            rx.progress(
                                value=(LuckyDrawState.current_prize_index + 1) / LuckyDrawState.current_prizes.length() * 100,
                                size="2",
                                color_scheme="gold",
                                width="100%",
                            ),
                            rx.text(
                                f"{LuckyDrawState.current_prize_index + 1}/{LuckyDrawState.current_prizes.length()}",
                                color=GOLD,
                                size="1",
                                weight="bold",
                            ),
                            spacing="2",
                            width="100%",
                        ),
                        rx.fragment(),
                    ),

                    spacing="5",
                    align="center",
                    width="100%",
                    padding="2em",
                    bg=f"linear-gradient(135deg, {DARK_GRAY}, {BLACK})",
                    border_radius="25px",
                    box_shadow=f"0 10px 40px {GOLD}33",
                ),

                # Right Column - Spinning Wheel / Winner Display
                rx.vstack(
                    rx.cond(
                        LuckyDrawState.lucky_draw_spinning,
                        # Beautiful Spinning Wheel
                        rx.vstack(
                            # Wheel Container
                            rx.box(
                                rx.vstack(
                                    # Center Content
                                    rx.vstack(
                                        rx.cond(
                                            LuckyDrawState.lucky_draw_current_name,
                                            rx.text(
                                                LuckyDrawState.lucky_draw_current_name,
                                                font_size="1.8em",
                                                font_weight="bold",
                                                color=GOLD,
                                                text_align="center",
                                                style={
                                                    "textShadow": f"0 0 10px {GOLD}",
                                                }
                                            ),
                                            rx.text(
                                                "Ready...",
                                                font_size="1.8em",
                                                font_weight="bold",
                                                color=GOLD,
                                            ),
                                        ),
                                        rx.cond(
                                            LuckyDrawState.lucky_draw_current_id,
                                            rx.text(
                                                f"ID: {LuckyDrawState.lucky_draw_current_id}",
                                                font_size="1em",
                                                color="gray",
                                            ),
                                            rx.text(
                                                "ID: ...",
                                                font_size="1em",
                                                color="gray",
                                            ),
                                        ),
                                        spacing="2",
                                        align="center",
                                    ),
                                    width="100%",
                                    height="100%",
                                    display="flex",
                                    align_items="center",
                                    justify_content="center",
                                ),
                                width="320px",
                                height="320px",
                                border_radius="50%",
                                background=f"conic-gradient(from 0deg, {GOLD}33, {GOLD}66, {GOLD}99, {GOLD}CC, {GOLD}99, {GOLD}66, {GOLD}33)",
                                position="relative",
                                style={
                                    "animation": "wheelSpin 0.08s linear infinite",
                                    "boxShadow": f"0 0 40px {GOLD}, inset 0 0 20px {GOLD}",
                                    "backdropFilter": "blur(2px)",
                                },
                            ),

                            # Spinning Text
                            rx.text(
                                "🎲 SPINNING 🎲",
                                font_size="1.2em",
                                color=GOLD,
                                letter_spacing="0.2em",
                                margin_top="1.5em",
                                style={
                                    "animation": "pulse 1s ease-in-out infinite",
                                }
                            ),

                            # Decorative Rings
                            rx.hstack(
                                rx.box(
                                    width="8px",
                                    height="8px",
                                    border_radius="50%",
                                    bg=GOLD,
                                    style={"animation": "pulse 0.5s ease-in-out infinite"},
                                ),
                                rx.box(
                                    width="12px",
                                    height="12px",
                                    border_radius="50%",
                                    bg=GOLD,
                                    style={"animation": "pulse 0.5s ease-in-out infinite 0.1s"},
                                ),
                                rx.box(
                                    width="6px",
                                    height="6px",
                                    border_radius="50%",
                                    bg=GOLD,
                                    style={"animation": "pulse 0.5s ease-in-out infinite 0.2s"},
                                ),
                                spacing="2",
                            ),
                            spacing="4",
                            align="center",
                            padding="2em",
                            width="100%",
                        ),
                        rx.cond(
                            LuckyDrawState.lucky_draw_winner,
                            # Winner Display with Celebration
                            rx.vstack(
                                # Confetti Effect (simulated)
                                rx.box(
                                    rx.icon(tag="sparkles", size=40, color=GOLD),
                                    rx.icon(tag="crown", size=50, color=GOLD),
                                    rx.icon(tag="sparkles", size=40, color=GOLD),
                                    display="flex",
                                    gap="1em",
                                    justify="center",
                                    style={"animation": "bounce 0.5s ease-in-out"},
                                ),

                                rx.heading(
                                    "🎉 WINNER! 🎉",
                                    size="5",
                                    color=GOLD,
                                    style={"animation": "pulse 0.8s ease-in-out"},
                                ),

                                rx.heading(
                                    LuckyDrawState.lucky_draw_winner.get("name", ""),
                                    size="7",
                                    color="white",
                                    weight="bold",
                                    text_align="center",
                                    style={
                                        "textShadow": f"0 0 20px {GOLD}",
                                        "animation": "scaleIn 0.5s ease-out",
                                    }
                                ),

                                rx.hstack(
                                    rx.badge(
                                        f"ID: {LuckyDrawState.lucky_draw_winner.get('guest_id', '')}",
                                        color_scheme="gold",
                                        size="2",
                                    ),
                                    rx.badge(
                                        f"Table: {LuckyDrawState.lucky_draw_winner.get('table_number', 'TBD')}",
                                        color_scheme="gray",
                                        size="2",
                                    ),
                                    spacing="2",
                                ),

                                rx.divider(width="200px", border_color=GOLD),

                                rx.text(
                                    f"Prize: {LuckyDrawState.lucky_draw_prize_name}",
                                    size="4",
                                    color=GOLD,
                                    weight="bold",
                                ),

                                rx.cond(
                                    LuckyDrawState.lucky_draw_prize_value,
                                    rx.badge(
                                        f"💰 {LuckyDrawState.lucky_draw_prize_value}",
                                        color_scheme="gold",
                                        size="3",
                                    ),
                                    rx.fragment(),
                                ),

                                # Action Buttons
                                rx.cond(
                                    (LuckyDrawState.prize_mode != "single") & (
                                                LuckyDrawState.current_prize_index < LuckyDrawState.current_prizes.length() - 1),
                                    rx.vstack(
                                        rx.button(
                                            "🎲 Draw Next Prize 🎲",
                                            on_click=LuckyDrawState.draw_next_prize,
                                            bg=GOLD,
                                            color=BLACK,
                                            size="3",
                                            width="220px",
                                            _hover={"bg": "#FFD700", "transform": "scale(1.05)"},
                                        ),
                                        rx.text(
                                            f"Next: {LuckyDrawState.current_prizes[LuckyDrawState.current_prize_index + 1].get('name', 'Prize')}",
                                            color="gray",
                                            size="1",
                                        ),
                                        spacing="1",
                                        align="center",
                                    ),
                                    rx.hstack(
                                        rx.button(
                                            "✨ Close ✨",
                                            on_click=LuckyDrawState.close_lucky_draw_spinner,
                                            bg=GOLD,
                                            color=BLACK,
                                            size="3",
                                            _hover={"bg": "#FFD700", "transform": "scale(1.05)"},
                                        ),
                                        rx.button(
                                            "🔄 New Draw 🔄",
                                            on_click=LuckyDrawState.close_spinner_and_open_new_draw,
                                            variant="outline",
                                            border_color=GOLD,
                                            color=GOLD,
                                            size="3",
                                            _hover={"bg": GOLD, "color": BLACK, "transform": "scale(1.05)"},
                                        ),
                                        spacing="3",
                                    ),
                                ),
                                spacing="4",
                                align="center",
                                padding="2em",
                                width="100%",
                            ),
                            # Ready State
                            rx.vstack(
                                rx.box(
                                    rx.icon(tag="gift", size=70, color=GOLD),
                                    style={"animation": "float 3s ease-in-out infinite"},
                                ),
                                rx.heading(
                                    "Ready to Draw!",
                                    size="5",
                                    color="white",
                                ),
                                rx.text(
                                    f"{LuckyDrawState.lucky_draw_eligible_count} guests are eligible",
                                    size="2",
                                    color="gray",
                                ),
                                rx.text(
                                    "Click the button below to start",
                                    size="1",
                                    color="gray",
                                ),
                                spacing="4",
                                align="center",
                                padding="3em",
                                width="100%",
                            ),
                        ),
                    ),
                    width="100%",
                    min_height="550px",
                ),
                columns="2",
                spacing="4",
                width="100%",
                align="start",
                padding="2em",
            ),
            style={
                "background": f"linear-gradient(135deg, {BLACK}, {DARK_GRAY})",
                "border": f"2px solid {GOLD}",
                "border_radius": "30px",
                "max_width": "1200px",
                "width": "90vw",
                "margin": "auto",
                "overflow": "hidden",
            },
        ),
        open=LuckyDrawState.lucky_draw_spinner_open,
        style={
            "background": "rgba(0, 0, 0, 0.95)",
            "backdropFilter": "blur(10px)",
        },
    )