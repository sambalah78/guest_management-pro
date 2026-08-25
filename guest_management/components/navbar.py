# guest_management/components/navbar.py
import reflex as rx
from guest_management.state import GuestState, AuthState
from guest_management.utils.constants import GOLD, BLACK, WHITE


def navbar() -> rx.Component:
    """Navigation bar component."""
    return rx.box(
        rx.hstack(
            rx.link(
                rx.hstack(
                    rx.image(src="/logonew.png", width="25px", color=GOLD),
                    rx.image(src="/word.png", width=["60px", "80px", "100px", "120px"], class_name="animate-fly-in"),
                    spacing="2",
                    align="center",
                ),
                href="/home",
            ),
            rx.hstack(
                rx.link("Home", href="/home", color=WHITE, font_size="0.9rem", _hover={"color": GOLD}),
                rx.link("About", href="/about", color=WHITE, font_size="0.9rem", _hover={"color": GOLD}),
                rx.link("Products", href="/products", color=WHITE, font_size="0.9rem", _hover={"color": GOLD}),
                rx.link("Contact", href="/contact", color=WHITE, font_size="0.9rem", _hover={"color": GOLD}),
                spacing="4",
            ),
            rx.cond(
                AuthState.is_authenticated,
                rx.hstack(
                    rx.text(AuthState.username, color=GOLD, font_size="0.9rem"),
                    rx.button("Logout", on_click=AuthState.logout, variant="outline", border_color="red", color="red", font_size="0.85rem", padding="0.4em 1em", _hover={"bg": "red", "color": "white"}),
                    spacing="3",
                ),
                rx.button("Admin Login", on_click=rx.redirect("/login"), variant="outline", border_color=GOLD, color=GOLD, font_size="0.85rem", padding="0.4em 1em", _hover={"bg": GOLD, "color": BLACK}),
            ),
            justify="between",
            align="center",
            width="100%",
        ),
        justify="between",
        align="center",
        padding="0.65em",
        width="100%",
        bg=BLACK,
        border_bottom=f"1px solid {GOLD}",
    )