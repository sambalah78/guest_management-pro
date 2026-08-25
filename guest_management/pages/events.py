# pages/events.py
import reflex as rx
from guest_management.state import State, AuthState, EventState
from guest_management.components.event_card import event_card
from guest_management.styles.theme import button_style, GOLD, BLACK , LIGHT_GRAY


def events_page():
    """Events page showing all user events."""
    return rx.center(
        rx.vstack(
            # Header
            rx.hstack(
                rx.heading("My Events", size="5", color=GOLD),
                rx.spacer(),
                rx.button(
                    rx.hstack(rx.icon(tag="plus", size=14), rx.text("Create Event")),
                    on_click=rx.redirect("/select-event-type"),
                    **button_style()
                    # bg=GOLD,
                    # color=BLACK,
                    # size="1",
                    # _hover={"bg": DARK_GRAY, "color": GOLD},
                ),

                rx.button(rx.hstack(
                        rx.icon("log-out", size=14),
                        rx.text("Logout", size="1", color="red"),
                        spacing="2",
                    ),on_click=AuthState.logout,**button_style()),

                width="100%",
                padding="0.5em 1em",
                align="center",

            ),

            rx.divider(),

            # Events List - Use formatted_events for better date formatting
            rx.cond(
                EventState.formatted_events.length() > 0,
                rx.vstack(
                    rx.foreach(
                        EventState.formatted_events,
                        event_card
                    ),
                    width="100%",
                    spacing="4",
                ),
                # Empty state
                rx.center(
                    rx.vstack(
                        rx.icon(tag="calendar", size=60, color=GOLD),
                        rx.heading("No Events Yet", size="4", color="white"),
                        rx.text("Click 'Create Event' to get started", color=LIGHT_GRAY, size="2"),
                        spacing="4",
                        padding="2em",
                    ),
                    width="100%",
                    height="50vh",
                ),
            ),

            width="100%",
            max_width="1000px",
            padding="1em",
        ),
        width="100%",
        min_height="100vh",
        bg=BLACK,
        padding="1em",
    )