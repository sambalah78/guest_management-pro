# guest_management/components/event_action_buttons.py
import reflex as rx
from guest_management.state import State, GOLD, BLACK, EventState


def manage_event_button(event_id) -> rx.Component:
    """Manage Event button that properly handles event_id."""
    return rx.button(
        "Manage Event",
        on_click=EventState.navigate_to_event(event_id),
        bg=GOLD,
        color=BLACK,
        padding="0.4em 0.8em",
        font_size="0.8rem",
        width="100%",
        _hover={
            "bg": "#FFD700",
            "transform": "scale(1.02)",
        },
    )


def delete_event_button(event_id) -> rx.Component:
    """Delete Event button that properly handles event_id."""
    return rx.button(
        rx.icon("trash-2", size=14),
        on_click=EventState.delete_event(event_id),
        bg="#333333",
        color="white",
        padding="0.4em 0.8em",
        font_size="0.8rem",
        width="100%",
        _hover={
            "bg": "#444444",
            "transform": "scale(1.02)",
        },
    )