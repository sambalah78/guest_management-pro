# guest_management/pages/about.py
import reflex as rx
from guest_management.state import GOLD, WHITE, DARK_GRAY, LIGHT_GRAY, BLACK
from guest_management.pages import page_layout
from guest_management.styles.theme import card_style


def about_page() -> rx.Component:
    """About us page for event management company"""
    return page_layout(
        rx.vstack(
            # Header
            rx.center(
                rx.vstack(
                    rx.text(
                        "About EventLah",
                        font_size="2.5rem",
                        font_weight="bold",
                        color=GOLD,
                        class_name="animate-fly-in",
                    ),
                    rx.text(
                        "We Make Events Magical",
                        font_size="1.2rem",
                        color=WHITE,
                        class_name="animate-fade-in",
                    ),
                    spacing="2",
                    align="center",
                ),
                width="100%",
                padding="1em 0",
            ),

            # Mission Section
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.icon("target", size=30, color=GOLD),
                        rx.heading("Our Mission", size="4", color=GOLD),
                        spacing="3",
                    ),
                    rx.text(
                        "To revolutionize event management by providing cutting-edge technology "
                        "that simplifies guest check-in, enhances engagement, and creates "
                        "unforgettable experiences for every attendee.",
                        font_size="1rem",
                        color=LIGHT_GRAY,
                        text_align="center",
                    ),
                    spacing="3",
                    align="center",
                ),
                **card_style(),
            ),

            # Vision Section
            rx.card(
                rx.vstack(
                    rx.hstack(
                        rx.icon("eye", size=30, color=GOLD),
                        rx.heading("Our Vision", size="4", color=GOLD),
                        spacing="3",
                    ),
                    rx.text(
                        "To become the leading event management platform in Southeast Asia, "
                        "empowering organizers with smart, intuitive, and reliable solutions "
                        "that make every event a resounding success.",
                        font_size="1rem",
                        color=LIGHT_GRAY,
                        text_align="center",
                    ),
                    spacing="3",
                    align="center",
                ),
                **card_style(),
            ),

            # Values Section
            rx.heading("Our Core Values", size="4", color=GOLD, text_align="center", padding_top="1em"),
            rx.grid(
                rx.card(
                    rx.vstack(
                        rx.icon("zap", size=30, color=GOLD),
                        rx.heading("Innovation", size="3", color=WHITE),
                        rx.text("Constantly evolving with technology", color=LIGHT_GRAY, text_align="center",
                                font_size="0.85rem"),
                        align="center",
                    ),
                    **card_style(),
                ),
                rx.card(
                    rx.vstack(
                        rx.icon("heart", size=30, color=GOLD),
                        rx.heading("Excellence", size="3", color=WHITE),
                        rx.text("Delivering nothing but the best", color=LIGHT_GRAY, text_align="center",
                                font_size="0.85rem"),
                        align="center",
                    ),
                    **card_style(),
                ),
                rx.card(
                    rx.vstack(
                        rx.icon("users", size=30, color=GOLD),
                        rx.heading("Collaboration", size="3", color=WHITE),
                        rx.text("Working together for success", color=LIGHT_GRAY, text_align="center",
                                font_size="0.85rem"),
                        align="center",
                    ),
                    **card_style(),
                ),
                rx.card(
                    rx.vstack(
                        rx.icon("shield", size=30, color=GOLD),
                        rx.heading("Integrity", size="3", color=WHITE),
                        rx.text("Honesty and transparency always", color=LIGHT_GRAY, text_align="center",
                                font_size="0.85rem"),
                        align="center",
                    ),
                    **card_style(),
                ),
                columns=rx.breakpoints(initial="1", sm="2", md="4"),
                spacing="4",
                width="100%",
                padding="0.5em 0",
            ),

            spacing="3",
            width="100%",
            padding="0.5em",
            align="center",
        )
    )