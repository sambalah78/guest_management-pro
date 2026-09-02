from guest_management.state import (
    GOLD,
    BLACK,
    DARK_GRAY,
    LIGHT_GRAY,
    EmailState,
)
import reflex as rx


def email_dialog():
    """Individual guest invitation email confirmation dialog."""

    guest = EmailState.selected_guest_for_email

    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(

                # ============================================================
                # HEADER
                # ============================================================

                rx.vstack(
                    rx.text(
                        "EVENT INVITATION",
                        size="1",
                        weight="bold",
                        color=GOLD,
                        letter_spacing="0.16em",
                    ),

                    rx.heading(
                        rx.cond(
                            EmailState.selected_guest_for_email,
                            "Send Invitation",
                            "Send Email",
                        ),
                        size="5",
                        color="white",
                    ),

                    rx.text(
                        "Review the guest details before sending.",
                        size="2",
                        color=LIGHT_GRAY,
                    ),

                    spacing="1",
                    align="center",
                    width="100%",
                ),

                # ============================================================
                # GUEST INFORMATION
                # ============================================================

                rx.cond(
                    EmailState.selected_guest_for_email,

                    rx.box(
                        rx.vstack(

                            rx.hstack(
                                rx.icon(
                                    tag="user",
                                    size=17,
                                    color=GOLD,
                                ),
                                rx.vstack(
                                    rx.text(
                                        "Guest",
                                        size="1",
                                        color=LIGHT_GRAY,
                                    ),
                                    rx.text(
                                        EmailState.selected_guest_for_email.get(
                                            "name",
                                            EmailState.selected_guest_for_email.get(
                                                "Name",
                                                "Guest",
                                            ),
                                        ),
                                        size="3",
                                        weight="bold",
                                        color="white",
                                    ),
                                    spacing="0",
                                ),
                                spacing="3",
                                align="center",
                                width="100%",
                            ),

                            rx.divider(
                                color=f"{GOLD}33",
                            ),

                            rx.hstack(
                                rx.icon(
                                    tag="id-card",
                                    size=16,
                                    color=GOLD,
                                ),
                                rx.vstack(
                                    rx.text(
                                        "Guest ID",
                                        size="1",
                                        color=LIGHT_GRAY,
                                    ),
                                    rx.text(
                                        EmailState.selected_guest_for_email.get(
                                            "guest_id",
                                            EmailState.selected_guest_for_email.get(
                                                "ID",
                                                "N/A",
                                            ),
                                        ),
                                        size="2",
                                        color="white",
                                    ),
                                    spacing="0",
                                ),
                                spacing="3",
                                width="100%",
                            ),

                            rx.hstack(
                                rx.icon(
                                    tag="mail",
                                    size=16,
                                    color=GOLD,
                                ),
                                rx.vstack(
                                    rx.text(
                                        "Email",
                                        size="1",
                                        color=LIGHT_GRAY,
                                    ),
                                    rx.text(
                                        EmailState.selected_guest_for_email.get(
                                            "email",
                                            EmailState.selected_guest_for_email.get(
                                                "Email",
                                                "",
                                            ),
                                        ),
                                        size="2",
                                        color="white",
                                    ),
                                    spacing="0",
                                ),
                                spacing="3",
                                width="100%",
                            ),

                            rx.hstack(
                                rx.icon(
                                    tag="armchair",
                                    size=16,
                                    color=GOLD,
                                ),
                                rx.vstack(
                                    rx.text(
                                        "Table",
                                        size="1",
                                        color=LIGHT_GRAY,
                                    ),
                                    rx.text(
                                        EmailState.selected_guest_for_email.get(
                                            "table_number",
                                            EmailState.selected_guest_for_email.get(
                                                "Table",
                                                "TBD",
                                            ),
                                        ),
                                        size="2",
                                        color="white",
                                    ),
                                    spacing="0",
                                ),
                                spacing="3",
                                width="100%",
                            ),

                            rx.cond(
                                EmailState.selected_guest_for_email.get(
                                    "email_sent",
                                    False,
                                ),
                                rx.badge(
                                    "Previously sent",
                                    color_scheme="gold",
                                    size="1",
                                ),
                            ),

                            spacing="3",
                            width="100%",
                        ),

                        background=f"{BLACK}",
                        border=f"1px solid {GOLD}44",
                        border_radius="14px",
                        padding="18px",
                        width="100%",
                    ),
                ),

                # ============================================================
                # WHAT WILL BE SENT
                # ============================================================

                rx.box(
                    rx.vstack(

                        rx.text(
                            "EMAIL CONTENT",
                            size="1",
                            weight="bold",
                            color=GOLD,
                            letter_spacing="0.12em",
                        ),

                        rx.hstack(
                            rx.icon(
                                tag="image",
                                size=15,
                                color=GOLD,
                            ),
                            rx.text(
                                "Event logo, if uploaded",
                                size="2",
                                color=LIGHT_GRAY,
                            ),
                            spacing="2",
                        ),

                        rx.hstack(
                            rx.icon(
                                tag="image",
                                size=15,
                                color=GOLD,
                            ),
                            rx.text(
                                "Wedding invitation, if uploaded",
                                size="2",
                                color=LIGHT_GRAY,
                            ),
                            spacing="2",
                        ),

                        rx.hstack(
                            rx.icon(
                                tag="qr-code",
                                size=15,
                                color=GOLD,
                            ),
                            rx.text(
                                "Personal guest QR code",
                                size="2",
                                color=LIGHT_GRAY,
                            ),
                            spacing="2",
                        ),

                        spacing="2",
                        align="start",
                        width="100%",
                    ),

                    background=f"{GOLD}0D",
                    border=f"1px solid {GOLD}33",
                    border_radius="12px",
                    padding="15px",
                    width="100%",
                ),

                # ============================================================
                # ACTIONS
                # ============================================================

                rx.vstack(

                    rx.button(
                        rx.hstack(
                            rx.cond(
                                EmailState.is_loading,
                                rx.spinner(size="2"),
                                rx.icon(
                                    tag="send",
                                    size=15,
                                ),
                            ),

                            rx.text(
                                rx.cond(
                                    EmailState.selected_guest_for_email,
                                    rx.cond(
                                        EmailState.selected_guest_for_email.get(
                                            "email_sent",
                                            False,
                                        ),
                                        "Resend Invitation",
                                        "Send Invitation",
                                    ),
                                    "Send",
                                ),
                            ),

                            spacing="2",
                        ),

                        on_click=EmailState.send_guest_email,

                        bg=GOLD,
                        color=BLACK,

                        width="100%",
                        size="3",

                        is_loading=EmailState.is_loading,
                    ),

                    rx.button(
                        "Cancel",

                        on_click=EmailState.close_email_dialog,

                        variant="outline",
                        border_color=GOLD,
                        color=GOLD,

                        width="100%",
                        size="2",
                    ),

                    spacing="2",
                    width="100%",
                ),

                spacing="5",
                padding="28px",
                width="100%",
            ),

            background=DARK_GRAY,
            border=f"1px solid {GOLD}88",
            border_radius="18px",
            max_width="460px",
            width="95vw",
        ),

        open=EmailState.email_dialog_open,
    )
