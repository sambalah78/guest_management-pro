import reflex as rx

from guest_management.state import AuthState
from guest_management.styles.theme import GOLD, BLACK, DARK_GRAY


def login_page():
    return rx.center(
        rx.card(
            rx.vstack(
                rx.image(
                    src="/logo.png",
                    width=["210px","2400px","270px","300px"],
                ),

                rx.heading(
                    "Welcome Back",
                    color=GOLD,
                    size="7",
                ),

                rx.text(
                    "Sign in to your EventLah account.",
                    color=DARK_GRAY,
                ),

                # --------------------------------------------------
                # Email
                # --------------------------------------------------

                rx.vstack(
                    rx.text(
                        "Email",
                        color="white",
                        size="2",
                    ),

                    rx.input(
                        placeholder="Enter your email",
                        type="email",
                        value=AuthState.username,
                        on_change=AuthState.set_username,
                        width="100%",
                        size="3",
                    ),

                    width="100%",
                    align="stretch",
                    spacing="1",
                ),

                # --------------------------------------------------
                # Password
                # --------------------------------------------------

                rx.vstack(
                    rx.text(
                        "Password",
                        color="white",
                        size="2",
                    ),

                    rx.input(
                        placeholder="Enter your password",
                        type="password",
                        value=AuthState.password,
                        on_change=AuthState.set_password,
                        width="100%",
                        size="3",
                    ),

                    width="100%",
                    align="stretch",
                    spacing="1",
                ),

                # --------------------------------------------------
                # Authentication error
                # --------------------------------------------------

                rx.cond(
                    AuthState.auth_error != "",
                    rx.text(
                        AuthState.auth_error,
                        color="red",
                        size="2",
                        text_align="center",
                    ),
                ),

                # --------------------------------------------------
                # Sign in
                # --------------------------------------------------

                rx.button(
                    rx.cond(
                        AuthState.is_loading,
                        "Signing in...",
                        "Sign In",
                    ),
                    on_click=AuthState.login,
                    width="100%",
                    size="3",
                    bg=GOLD,
                    color=BLACK,
                    disabled=AuthState.is_loading,
                    _hover={
                        "opacity": "0.9",
                    },
                ),

                rx.text(
                    "Sign in with your EventLah account.",
                    size="1",
                    color="gray",
                    text_align="center",
                ),

                rx.link(
                    "Back to home",
                    href="/",
                    color=GOLD,
                ),

                spacing="4",
                width="100%",
                align="center",
            ),

            width=["92%", "80%", "460px"],
            padding="2.5em",
            bg=BLACK,
        ),

        width="100%",
        min_height="80vh",
        padding="2em",
    )