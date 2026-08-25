# pages/select_event_type.py
import reflex as rx
from guest_management.state import State, GOLD, BLACK, DARK_GRAY, EventState


def select_event_type_page():
    """Event type selection page before creating an event."""
    return rx.center(
        rx.vstack(
            # Header with back button
            rx.hstack(
                rx.button(
                    rx.hstack(rx.icon(tag="arrow-left", size=16), rx.text("Back to Events")),
                    on_click=rx.redirect("/events"),
                    variant="outline",
                    border_color=GOLD,
                    color=GOLD,
                    size="1",
                    _hover={"bg": GOLD, "color": BLACK},
                ),
                rx.spacer(),
                rx.heading("Select Event Type", size="5", color=GOLD),
                rx.spacer(),
                rx.box(width="100px"),
                width="100%",
                padding="0.5em 1em",
            ),
            rx.divider(),
            rx.text("Choose the type of event you want to organize", color="gray", size="2", text_align="center"),
            rx.grid(
                # Company Dinner Card
                rx.card(
                    rx.vstack(
                        rx.text("🏢", font_size="3em"),
                        rx.heading("Company Dinner", size="4", color=GOLD, text_align="center"),
                        rx.text("Corporate events, annual dinners, team building", color="gray", size="1", text_align="center"),
                        rx.hstack(
                            rx.badge("QR Check-in", color_scheme="green", size="1"),
                            rx.badge("Email", color_scheme="green", size="1"),
                            rx.badge("Lucky Draw", color_scheme="green", size="1"),
                            wrap="wrap",
                            spacing="1",
                            justify="center",
                        ),
                        rx.spacer(),
                        rx.button(
                            "Select",
                            on_click=EventState.select_event_type("company_dinner"),
                            bg=GOLD,
                            color=BLACK,
                            width="100%",
                            _hover={"bg": DARK_GRAY, "color": GOLD},
                        ),
                        spacing="3",
                        align="center",
                        height="100%",
                    ),
                    bg=DARK_GRAY,
                    border=f"1px solid {GOLD}",
                    border_radius="15px",
                    padding="1.5em",
                    _hover={"transform": "translateY(-5px)", "transition": "0.3s"},
                ),
                # Wedding Dinner Card
                rx.card(
                    rx.vstack(
                        rx.text("💒", font_size="3em"),
                        rx.heading("Wedding Dinner", size="4", color=GOLD, text_align="center"),
                        rx.text("Wedding receptions, engagement parties", color="gray", size="1", text_align="center"),
                        rx.hstack(
                            rx.badge("QR Check-in", color_scheme="green", size="1"),
                            rx.badge("Email", color_scheme="green", size="1"),
                            rx.badge("Plus-One", color_scheme="green", size="1"),
                            rx.badge("Dietary", color_scheme="green", size="1"),
                            wrap="wrap",
                            spacing="1",
                            justify="center",
                        ),
                        rx.spacer(),
                        rx.button(
                            "Select",
                            on_click=EventState.select_event_type("wedding_dinner"),
                            bg=GOLD,
                            color=BLACK,
                            width="100%",
                            _hover={"bg": DARK_GRAY, "color": GOLD},
                        ),
                        spacing="3",
                        align="center",
                        height="100%",
                    ),
                    bg=DARK_GRAY,
                    border=f"1px solid {GOLD}",
                    border_radius="15px",
                    padding="1.5em",
                    _hover={"transform": "translateY(-5px)", "transition": "0.3s"},
                ),
                # Sports Day Card
                rx.card(
                    rx.vstack(
                        rx.text("⚽", font_size="3em"),
                        rx.heading("Sports Day", size="4", color=GOLD, text_align="center"),
                        rx.text("Sports events, tournaments, family day", color="gray", size="1", text_align="center"),
                        rx.hstack(
                            rx.badge("QR Check-in", color_scheme="green", size="1"),
                            rx.badge("Food Vouchers", color_scheme="green", size="1"),
                            rx.badge("Stalls", color_scheme="green", size="1"),
                            rx.badge("Lucky Draw", color_scheme="green", size="1"),
                            wrap="wrap",
                            spacing="1",
                            justify="center",
                        ),
                        rx.spacer(),
                        rx.button(
                            "Select",
                            on_click=EventState.select_event_type("sports_day"),
                            bg=GOLD,
                            color=BLACK,
                            width="100%",
                            _hover={"bg": DARK_GRAY, "color": GOLD},
                        ),
                        spacing="3",
                        align="center",
                        height="100%",
                    ),
                    bg=DARK_GRAY,
                    border=f"1px solid {GOLD}",
                    border_radius="15px",
                    padding="1.5em",
                    _hover={"transform": "translateY(-5px)", "transition": "0.3s"},
                ),
                columns=rx.breakpoints(initial="1", sm="1", md="2", lg="3"),
                spacing="4",
                width="100%",
                padding="1em",
            ),
            spacing="4",
            width="100%",
            max_width="1200px",
            padding="2em",
        ),
        width="100%",
        min_height="100vh",
        bg=BLACK,
    )