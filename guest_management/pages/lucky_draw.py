# pages/.py
import reflex as rx
from guest_management.state import State, GuestState, UIState, LuckyDrawState, EventState
from guest_management.utils.constants import GOLD, BLACK , DARK_GRAY
from guest_management.components.lucky_draw_manager import lucky_draw_manager


def render_winner_item(winner):
    """Render a single winner item - Responsive"""
    return rx.card(
        rx.hstack(
            rx.vstack(
                rx.hstack(
                    rx.icon(tag="crown", size=12, color=GOLD),
                    rx.text(
                        winner.get("name", "Unknown"),
                        color=GOLD,
                        weight="bold",
                        font_size=["0.7rem", "0.8rem", "0.9rem"],
                    ),
                    spacing="1",
                ),
                rx.text(
                    f"ID: {winner.get('guest_id', 'Unknown')}",
                    color="gray",
                    font_size=["0.6rem", "0.7rem", "0.8rem"],
                ),
                rx.text(
                    f"Prize: {winner.get('prize_name', '')}",
                    color="white",
                    font_size=["0.6rem", "0.7rem", "0.8rem"],
                ),
                spacing="1",
                align="start",
            ),
            rx.spacer(),
            rx.cond(
                winner.get("formatted_date", ""),
                rx.text(
                    winner.get("formatted_date", ""),
                    color="gray",
                    font_size=["0.55rem", "0.65rem", "0.75rem"],
                ),
                rx.fragment(),
            ),
            spacing="2",
            width="100%",
        ),
        bg=BLACK,
        padding="0.6em",
        border_radius="8px",
        width="100%",
    )


def clear_history_dialog():
    """Confirmation dialog for clearing winners history"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.icon(tag="triangle_alert", size=40, color="red"),
                rx.heading("Clear Winners History", size="5", color="red", font_size=["1.2em", "1.5em"]),
                rx.text(
                    "Are you sure you want to clear all winners history?",
                    color="white",
                    text_align="center",
                    font_size=["0.8em", "0.9em"],
                ),
                rx.text(
                    "This action cannot be undone.",
                    color="gray",
                    size="2",
                    text_align="center",
                    font_size=["0.7em", "0.8em"],
                ),
                rx.hstack(
                    rx.button(
                        "Cancel",
                        on_click=LuckyDrawState.cancel_clear_winners,
                        variant="outline",
                        border_color=GOLD,
                        color=GOLD,
                        flex="1",
                        size="2",
                    ),
                    rx.button(
                        rx.hstack(
                            rx.cond(
                                UIState.is_loading,
                                rx.spinner(size="2", color="white"),
                                rx.icon(tag="trash-2", size=14),
                            ),
                            rx.text("Clear All", font_size=["0.8em", "0.9em"]),
                        ),
                        on_click=LuckyDrawState.confirm_clear_winners,
                        bg="red.500",
                        color="white",
                        flex="1",
                        is_loading=UIState.is_loading,
                        size="2",
                    ),
                    spacing="3",
                    width="100%",
                ),
                spacing="4",
                padding="1.5em",
                align="center",
            ),
            bg=DARK_GRAY,
            border="2px solid red",
            border_radius="15px",
            max_width="400px",
            width="90%",
        ),
        open=UIState.show_clear_confirm,
    )


def new_draw_dialog():
    """Dialog for setting up a new draw - Responsive"""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.hstack(
                    rx.icon(tag="gift", size=24, color=GOLD),
                    rx.heading("New Lucky Draw", size="5", color=GOLD, font_size=["1.3em", "1.5em"]),
                    spacing="2",
                ),
                rx.divider(),
                lucky_draw_manager(),
                rx.divider(),
                # Guest Filter Section
                rx.hstack(
                    rx.switch(
                        checked=LuckyDrawState.lucky_draw_only_present,
                        on_change=LuckyDrawState.set_lucky_draw_only_present,
                        color_scheme="gold",
                    ),
                    rx.cond(
                        LuckyDrawState.lucky_draw_only_present,
                        rx.text("Only include guests who have checked in", color="red", font_size=["0.7em", "0.8em"]),
                        rx.text("Include all guests", color="gray", font_size=["0.7em", "0.8em"]),
                    ),
                    spacing="2",
                    wrap="wrap",
                ),
                # Exclude Guests Input
                rx.vstack(
                    rx.hstack(
                        rx.icon(tag="user-x", size=14, color="red"),
                        rx.text("Exclude Guests (comma-separated names or IDs)", color="white", font_size=["0.7em", "0.8em"]),
                        spacing="2",
                    ),
                    rx.input(
                        placeholder="e.g., John Doe, Jane Smith, GUEST_001",
                        value=LuckyDrawState.lucky_draw_excluded,
                        on_change=LuckyDrawState.set_lucky_draw_excluded,
                        width="100%",
                        bg=BLACK,
                        border_color="red",
                        color="white",
                        size="2",
                    ),
                    width="100%",
                ),
                # Eligible Count Preview
                rx.hstack(
                    rx.icon(tag="users", size=16, color=GOLD),
                    rx.text("Eligible Guests:", color="white", font_size=["0.8em", "0.9em"]),
                    rx.badge(
                        LuckyDrawState.lucky_draw_eligible_count,
                        color_scheme="gold",
                        size="2",
                    ),
                    spacing="2",
                ),
                rx.divider(),
                rx.hstack(
                    rx.button(
                        "Cancel",
                        on_click=LuckyDrawState.close_new_draw_dialog,
                        variant="outline",
                        border_color=GOLD,
                        color=GOLD,
                        flex="1",
                        size="2",
                    ),
                    rx.button(
                        rx.hstack(rx.icon(tag="play", size=14), rx.text("Start New Draw", font_size=["0.8em", "0.9em"])),
                        on_click=LuckyDrawState.start_new_draw,
                        bg=GOLD,
                        color=BLACK,
                        flex="2",
                        size="2",
                    ),
                    spacing="3",
                    width="100%",
                ),
                spacing="4",
                padding="1.5em",
                width="100%",
            ),
            bg=DARK_GRAY,
            border=f"2px solid {GOLD}",
            border_radius="15px",
            max_width="700px",
            width="95%",
        ),
        open=LuckyDrawState.lucky_draw_show_new_draw_dialog,
    )


def lucky_draw_page():
    """Lucky draw page with spinning wheel animation - Fully Responsive"""
    return rx.center(
        rx.vstack(
            # Header
            rx.hstack(
                rx.icon(tag="gift", size=30, color=GOLD),
                rx.heading("Lucky Draw", size="7", color=GOLD, font_size=["1.8em", "2.2em", "2.5em"]),
                spacing="3",
            ),

            # Prize Setup Card
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.icon(tag="settings", size=20, color=GOLD),
                        rx.heading("Prize Setup", size="4", color=GOLD, font_size=["1.1em", "1.3em"]),
                        spacing="2",
                    ),
                    lucky_draw_manager(),
                    spacing="4",
                    width="100%",
                ),
                bg=DARK_GRAY,
                border=f"1px solid {GOLD}",
                padding="1em",
                width="100%",
            ),

            # Guest Selection Card
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.icon(tag="users", size=20, color=GOLD),
                        rx.heading("Guest Selection", size="4", color=GOLD, font_size=["1.1em", "1.3em"]),
                        spacing="2",
                    ),
                    # Guest Filter Toggle
                    rx.hstack(
                        rx.switch(
                            checked=LuckyDrawState.lucky_draw_only_present,
                            on_change=LuckyDrawState.set_lucky_draw_only_present,
                            color_scheme="gold",
                        ),
                        rx.cond(
                            LuckyDrawState.lucky_draw_only_present,
                            rx.text("Only include guests who have checked in", color=GOLD, font_size=["0.7em", "0.8em"]),
                            rx.text("Include all guests", color="gray", font_size=["0.7em", "0.8em"]),
                        ),
                        spacing="2",
                        wrap="wrap",
                    ),
                    # Exclude Guests Input
                    rx.vstack(
                        rx.hstack(
                            rx.icon(tag="user-x", size=14, color=GOLD),
                            rx.text("Exclude Guests (comma-separated names or IDs)", color="white", font_size=["0.7em", "0.8em"]),
                            spacing="2",
                        ),
                        rx.input(
                            placeholder="e.g., John Doe, Jane Smith, GUEST_001",
                            value=LuckyDrawState.lucky_draw_excluded,
                            on_change=LuckyDrawState.set_lucky_draw_excluded,
                            width="100%",
                            bg=BLACK,
                            border_color="red",
                            color="white",
                            size="2",
                        ),
                        width="100%",
                    ),
                    # Eligible Count
                    rx.hstack(
                        rx.icon(tag="users", size=16, color=GOLD),
                        rx.text("Eligible Guests:", color="white", font_size=["0.8em", "0.9em"]),
                        rx.badge(
                            LuckyDrawState.lucky_draw_eligible_count,
                            color_scheme="gold",
                            size="2",
                        ),
                        spacing="2",
                    ),
                    spacing="4",
                    width="100%",
                ),
                bg=DARK_GRAY,
                border=f"1px solid {GOLD}",
                padding="1em",
                width="100%",
            ),

            # Action Buttons
            rx.vstack(
                # Set Up Complete Button - Opens display page
                rx.button(
                    rx.hstack(
                        rx.icon(tag="circle_check", size=16),
                        rx.text("✓ Set Up Complete - Open Display Screen", font_size=["0.8em", "0.9em", "1em"]),
                    ),
                    on_click=LuckyDrawState.setup_complete_and_go_to_display,
                    bg=GOLD,
                    color=BLACK,
                    width="100%",
                    size="3",
                    padding="1em",
                    _hover={"bg": "#FFD700", "transform": "scale(1.02)"},
                ),
                rx.text(
                    "Click this when ready to project to attendees. This will open the display screen.",
                    color="gray",
                    font_size=["0.65em", "0.75em"],
                    text_align="center",
                ),
                rx.divider(),
                rx.button(
                    rx.hstack(rx.icon(tag="arrow-left", size=14), rx.text("Back to Dashboard", font_size=["0.8em", "0.9em"])),
                    on_click=rx.redirect(f"/dashboard/{EventState.current_event_id}"),
                    variant="outline",
                    border_color=GOLD,
                    color=GOLD,
                    width="100%",
                    padding="0.8em",
                    _hover={"bg": GOLD, "color": BLACK},
                ),
                spacing="3",
                width="100%",
            ),

            # Winners History
            rx.cond(
                LuckyDrawState.winners_list.length() > 0,
                rx.card(
                    rx.vstack(
                        rx.hstack(
                            rx.hstack(
                                rx.icon(tag="history", size=16, color=GOLD),
                                rx.heading("Recent Winners", size="3", color="white", font_size=["1em", "1.2em"]),
                                spacing="2",
                            ),
                            rx.spacer(),
                            rx.button(
                                rx.hstack(
                                    rx.icon(tag="download", size=12),
                                    rx.text("Export", font_size=["0.7em", "0.8em"]),
                                ),
                                on_click=LuckyDrawState.download_winner_list,
                                size="2",
                                variant="outline",
                                border_color=GOLD,
                                color=GOLD,
                                _hover={"bg": GOLD, "color": BLACK},
                            ),
                            rx.button(
                                rx.hstack(
                                    rx.icon(tag="trash-2", size=12),
                                    rx.text("Clear History", font_size=["0.7em", "0.8em"]),
                                ),
                                on_click=LuckyDrawState.clear_winners_history,
                                size="2",
                                variant="outline",
                                border_color="red.500",
                                color="red.500",
                                _hover={"bg": "red.500", "color": "white"},
                            ),
                            spacing="2",
                            width="100%",
                            wrap="wrap",
                        ),
                        rx.vstack(
                            rx.foreach(
                                LuckyDrawState.winners_list[:10],
                                lambda winner: render_winner_item(winner),
                            ),
                            width="100%",
                            max_height="250px",
                            overflow="auto",
                            spacing="2",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    bg=DARK_GRAY,
                    border=f"1px solid {GOLD}",
                    padding="0.8em",
                    width="100%",
                ),
                rx.fragment(),
            ),

            # Dialogs
            clear_history_dialog(),
            new_draw_dialog(),

            spacing="6",
            width="100%",
            padding=["1em", "1.5em", "2em"],
            max_width="1200px",
        ),
        width="100%",
        min_height="100vh",
        bg=BLACK,
        padding="0.5em",
    )