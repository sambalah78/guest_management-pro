# components/clear_table_dialog.py
import reflex as rx
from guest_management.state import State, GOLD, BLACK, DARK_GRAY, UIState


def clear_table_dialog():
    """Clear table confirmation dialog."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.icon(tag="triangle_alert", size=50, color="red"),
                rx.heading("Clear Guest List", size="5", color="red"),
                rx.text(
                    "Are you sure you want to clear all guests from this event?",
                    color="white",
                    text_align="center",
                ),
                rx.text(
                    "This action cannot be undone.",
                    color="gray",
                    size="2",
                    text_align="center",
                ),
                rx.hstack(
                    rx.button(
                        "Cancel",
                        on_click=State.cancel_clear_table,
                        variant="outline",
                        border_color=GOLD,
                        color=GOLD,
                        flex="1",
                    ),
                    rx.button(
                        rx.hstack(
                            rx.cond(
                                UIState.is_loading,
                                rx.spinner(size="2", color="white"),
                                rx.icon(tag="trash-2", size=16),
                            ),
                            rx.text("Clear All"),
                        ),
                        on_click=State.confirm_clear_table,
                        bg="red.500",
                        color="white",
                        flex="1",
                        is_loading=UIState.is_loading,
                    ),
                    spacing="3",
                    width="100%",
                ),
                spacing="4",
                padding="2em",
                align="center",
            ),
            bg=DARK_GRAY,
            border="2px solid red",
            border_radius="15px",
            max_width="400px",
        ),
        open=State.show_clear_table_confirm,
    )