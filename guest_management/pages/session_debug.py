# pages/session_debug.py
import reflex as rx
from guest_management.state import State
from guest_management.database_client import get_db

GOLD = "#D4AF37"
BLACK = "#111111"
DARK_GRAY = "#1A1A1A"


def session_debug_page():
    """Debug page to check authentication status"""
    return rx.center(
        rx.card(
            rx.vstack(
                rx.heading("Session Debug", size="6", color=GOLD),

                rx.divider(),

                rx.vstack(
                    rx.hstack(
                        rx.text("Authenticated:", weight="bold", color="white"),
                        rx.cond(
                            State.is_authenticated,
                            rx.badge("Yes", color_scheme="green"),
                            rx.badge("No", color_scheme="red"),
                        ),
                        width="100%",
                    ),

                    rx.hstack(
                        rx.text("User ID:", weight="bold", color="white"),
                        rx.text(State.user_id or "None", color="white"),
                        width="100%",
                    ),

                    rx.hstack(
                        rx.text("User Email:", weight="bold", color="white"),
                        rx.text(State.user.get("email", "None"), color="white"),
                        width="100%",
                    ),

                    rx.hstack(
                        rx.text("User ID in State:", weight="bold", color="white"),
                        rx.text(str(State.user_id), color="white"),
                        width="100%",
                    ),

                    spacing="3",
                    align="start",
                    width="100%",
                ),

                rx.divider(),

                rx.hstack(
                    rx.button(
                        "Check Session",
                        on_click=State.check_auth_status,
                        bg=GOLD,
                        color=BLACK,
                    ),
                    rx.button(
                        "Back to Events",
                        on_click=rx.redirect("/events"),
                        variant="outline",
                        border_color=GOLD,
                        color=GOLD,
                    ),
                    spacing="2",
                    width="100%",
                ),

                spacing="4",
                width="100%",
            ),
            bg=DARK_GRAY,
            border=f"2px solid {GOLD}",
            padding="2em",
            width="500px",
        ),
        bg=BLACK,
        height="100vh",
    )