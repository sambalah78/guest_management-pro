# guest_management/pages/contact.py
import reflex as rx
from guest_management.state import State, GOLD, WHITE, BLACK, DARK_GRAY, UIState
from guest_management.styles.theme import button_style, card_style
from guest_management.pages import page_layout


def contact_page() -> rx.Component:
    """Contact us page with form"""
    return page_layout(
        rx.center(
            rx.grid(
                # Contact Form
                rx.card(
                    rx.vstack(
                        rx.heading("Send us a message", size="4", color=GOLD),
                        rx.vstack(
                            rx.text("Name", color=WHITE, size="2"),
                            rx.input(
                                placeholder="Your name",
                                on_change=UIState.set_contact_name,
                                value=UIState.contact_name,
                                width="100%",
                                bg=BLACK,
                                border_color=GOLD,
                                color=WHITE,
                            ),
                            width="100%",
                            spacing="1",
                        ),
                        rx.vstack(
                            rx.text("Email", color=WHITE, size="2"),
                            rx.input(
                                placeholder="Your email",
                                on_change=UIState.set_contact_email,
                                value=UIState.contact_email,
                                type="email",
                                width="100%",
                                bg=BLACK,
                                border_color=GOLD,
                                color=WHITE,
                            ),
                            width="100%",
                            spacing="1",
                        ),
                        rx.vstack(
                            rx.text("Message", color=WHITE, size="2"),
                            rx.text_area(
                                placeholder="Your message",
                                on_change=UIState.set_contact_message,
                                value=UIState.contact_message,
                                width="100%",
                                rows="4",
                                bg=BLACK,
                                border_color=GOLD,
                                color=WHITE,
                            ),
                            width="100%",
                            spacing="1",
                        ),
                        rx.cond(
                            UIState.contact_success,
                            rx.text("✓ Message sent successfully!", color=GOLD),
                        ),
                        rx.button(
                            "Send Message",
                            on_click=UIState.submit_contact,
                            **button_style(),
                            width="100%",
                            is_loading=State.is_loading,
                        ),
                        spacing="4",
                        align="start",
                        width="100%",
                    ),
                    **card_style(),
                ),

                # Contact Info
                rx.card(
                    rx.vstack(
                        rx.heading("Contact Information", size="4", color=GOLD),
                        rx.divider(bg=GOLD),
                        rx.hstack(
                            rx.icon("map-pin", size=20, color=GOLD),
                            rx.vstack(
                                rx.text("Visit Us", weight="bold", color=WHITE),
                                rx.text("123 Event Street, KLCC, Kuala Lumpur", color=DARK_GRAY, size="2"),
                                spacing="0",
                            ),
                            spacing="3",
                            align="start",
                        ),
                        rx.hstack(
                            rx.icon("phone", size=20, color=GOLD),
                            rx.vstack(
                                rx.text("Call Us", weight="bold", color=WHITE),
                                rx.text("+60 12-345 6789", color=DARK_GRAY, size="2"),
                                spacing="0",
                            ),
                            spacing="3",
                            align="start",
                        ),
                        rx.hstack(
                            rx.icon("mail", size=20, color=GOLD),
                            rx.vstack(
                                rx.text("Email Us", weight="bold", color=WHITE),
                                rx.text("hello@eventlah.com", color=DARK_GRAY, size="2"),
                                spacing="0",
                            ),
                            spacing="3",
                            align="start",
                        ),
                        rx.hstack(
                            rx.icon("clock", size=20, color=GOLD),
                            rx.vstack(
                                rx.text("Business Hours", weight="bold", color=WHITE),
                                rx.text("Mon-Fri: 9AM - 6PM", color=DARK_GRAY, size="2"),
                                rx.text("Sat: 10AM - 2PM", color=DARK_GRAY, size="2"),
                                spacing="0",
                            ),
                            spacing="3",
                            align="start",
                        ),
                        spacing="4",
                        align="start",
                        width="100%",
                    ),
                    **card_style(),
                ),
                columns="2",
                spacing="4",
                width="90%",
                max_width="1000px",
            ),
            width="100%",
            padding="0.5em",
        )
    )