# guest_management/components/event_card.py
import reflex as rx
from guest_management.state import EventState
from guest_management.components.event_action_buttons import manage_event_button, delete_event_button
from guest_management.utils.constants import EVENT_TYPES, GOLD, BLACK, DARK_GRAY, LIGHT_GRAY


def event_card(event: dict) -> rx.Component:
    """Create a card for a single event."""
    event_type = event.get("event_type", "company_dinner")
    event_config = EVENT_TYPES.get(
        event_type,
        EVENT_TYPES["company_dinner"],
    )

    event_name = event.get("name", "Unnamed Event")
    company_name = event.get("company_name", "")
    event_date = event.get("date", "Date TBD")
    event_time = event.get("time", "Time TBD")
    event_venue = event.get("venue", "Venue TBD")
    event_id = event.get("id", "")
    guest_count = event.get("guest_count", 0)
    present_count = event.get("present_count", 0)
    created_at = event.get("created_at", "")

    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.text(event_config["icon"], font_size="2em"),
                rx.badge(
                    event_config["name"],
                    variant="soft",
                    padding="0.1em 0.6em",
                ),
                spacing="2",
                align="center",
            ),
            rx.heading(
                event_name,
                size="4",
                color="white",
                weight="bold",
                text_align="left",
                width="100%",
            ),
            rx.cond(
                company_name != "",
                rx.text(company_name, size="1", color=DARK_GRAY),
            ),
            rx.vstack(
                rx.hstack(
                    rx.icon("calendar", size=14, color=DARK_GRAY),
                    rx.text(event_date, size="1", color="white"),
                    spacing="1",
                    align="center",
                ),
                rx.hstack(
                    rx.icon("clock", size=14, color=LIGHT_GRAY),
                    rx.text(event_time, size="1", color="white"),
                    spacing="1",
                    align="center",
                ),
                rx.hstack(
                    rx.icon("map-pin", size=14, color=LIGHT_GRAY),
                    rx.text(event_venue, size="1", color="white"),
                    spacing="1",
                    align="center",
                ),
                spacing="1",
                align="start",
                width="100%",
            ),
            rx.hstack(
                rx.badge(
                    rx.hstack(
                        rx.icon("users", size=12),
                        rx.text(
                            f"{guest_count} Guests",
                            font_size="0.8em",
                        ),
                        spacing="1",
                    ),
                    variant="soft",
                    color_scheme="gray",
                ),
                rx.badge(
                    rx.hstack(
                        rx.icon("circle_check", size=12),
                        rx.text(
                            f"{present_count} Present",
                            font_size="0.8em",
                        ),
                        spacing="1",
                    ),
                    variant="soft",
                    color_scheme="green",
                ),
                spacing="2",
                wrap="wrap",
            ),
            rx.cond(
                created_at != "",
                rx.text(
                    f"Created: {created_at}",
                    font_size="0.7em",
                    color=LIGHT_GRAY,
                ),
            ),
            rx.hstack(
                manage_event_button(event_id),
                delete_event_button(event_id),
                spacing="2",
            ),
            spacing="3",
            align="start",
            width="100%",
        ),
        padding="1.2em",
        background=f"linear-gradient(135deg, {DARK_GRAY} 0%, {BLACK} 100%)",
        border=f"1px solid {GOLD}",
        border_radius="1em",
        width="100%",
        _hover={
            "transform": "translateY(-4px)",
            "box_shadow": "0 8px 25px rgba(0,0,0,0.3)",
            "transition": "all 0.3s ease",
        },
    )
