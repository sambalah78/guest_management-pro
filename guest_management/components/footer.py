import reflex as rx
from guest_management.styles.theme import BLACK, GOLD, WHITE


def footer() -> rx.Component:
    """Footer component"""
    return rx.box(
        rx.hstack(
            rx.text(
                "© 2025 EventLah. All rights reserved.",
                color="#888888",
                font_size="0.7rem",
            ),
            rx.spacer(),
            rx.hstack(
                rx.link("Privacy", href="#", color="#888888", font_size="0.7rem", _hover={"color": GOLD}),
                rx.link("Terms", href="#", color="#888888", font_size="0.7rem", _hover={"color": GOLD}),
                spacing="3",
            ),
            justify="between",
            align="center",
            width="100%",
        ),
        width="100%",
        padding="0.6em 1.5em",
        bg=BLACK,
        border_top=f"1px solid {GOLD}",
    )