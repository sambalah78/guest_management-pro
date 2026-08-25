# components/email_dialog.py
import reflex as rx
from guest_management.state import State, GOLD, BLACK, DARK_GRAY, LIGHT_GRAY, EmailState, UIState


def email_dialog():
    """Send email dialog."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.heading(
                    rx.cond(
                        EmailState.selected_guest_for_email,
                        f"Send Email to {UIState.selected_guest_for_email.get('Name', 'Guest')}",
                        "Send Email"
                    ),
                    size="5",
                    color=GOLD,
                ),
                rx.cond(
                    UIState.selected_guest_for_email,
                    rx.vstack(
                        rx.hstack(
                            rx.icon(tag="user", size=16, color=GOLD),
                            rx.text(UIState.selected_guest_for_email.get("Name", ""), color="white"),
                            spacing="1",
                        ),
                        rx.hstack(
                            rx.icon(tag="id-card", size=16, color=GOLD),
                            rx.text(f"ID: {UIState.selected_guest_for_email.get('ID', 'N/A')}", color=LIGHT_GRAY),
                            spacing="1",
                        ),
                        rx.hstack(
                            rx.icon(tag="mail", size=16, color=GOLD),
                            rx.text(UIState.selected_guest_for_email.get("Email", ""), color=LIGHT_GRAY),
                            spacing="1",
                        ),
                        rx.cond(
                            UIState.selected_guest_for_email.get("email_sent", False),
                            rx.badge("Previously sent", color_scheme="gold", size="1"),
                        ),
                        spacing="2",
                        align="start",
                    ),
                ),
                rx.vstack(
                    rx.button(
                        rx.hstack(
                            rx.cond(UIState.is_loading, rx.spinner(size="2")),
                            rx.text(
                                rx.cond(
                                    UIState.selected_guest_for_email,
                                    rx.cond(
                                        UIState.selected_guest_for_email.get("email_sent", False),
                                        "Resend",
                                        "Send"
                                    ),
                                    "Send"
                                )
                            ),
                        ),
                        on_click=EmailState.send_guest_email,
                        bg=GOLD,
                        color=BLACK,
                        width="100%",
                        is_loading=UIState.is_loading,
                    ),
                    rx.button(
                        "Cancel",
                        on_click=EmailState.close_email_dialog,
                        variant="outline",
                        border_color=GOLD,
                        color=GOLD,
                        width="100%",
                    ),
                    spacing="2",
                    width="100%",
                ),
                spacing="4",
                padding="2em",
                width="100%",
            ),
            bg=DARK_GRAY,
            border=f"2px solid {GOLD}",
        ),
        open=EmailState.email_dialog_open,
    )