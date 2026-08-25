import reflex as rx
from guest_management.state import AuthState
from guest_management.styles.theme import GOLD, BLACK, DARK_GRAY

def login_page():
    return rx.center(
        rx.card(
            rx.vstack(
                rx.image(src="/logo.png", width="220px"),
                rx.heading("Welcome Back", color=GOLD, size="7"),
                rx.text("Sign in securely with your Google account.", color=DARK_GRAY),
                rx.button(
                    "Continue with Google",
                    on_click=AuthState.start_google_login,
                    width="100%", size="3", bg=GOLD, color=BLACK,
                    _hover={"opacity": "0.9"},
                ),
                rx.text("Your Google email is used as your EventLah account identity.", size="1", color="gray", text_align="center"),
                rx.link("Back to home", href="/", color=GOLD),
                spacing="4", width="100%", align="center",
            ),
            width=["92%", "80%", "460px"], padding="2.5em", bg=BLACK,
        ), width="100%", min_height="80vh", padding="2em"
    )
