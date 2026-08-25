# guest_management/pages/stall_landing.py
"""Stall landing page - COMPLETE FIXED VERSION."""

import reflex as rx
from guest_management.state import VoucherState, GOLD, BLACK, DARK_GRAY


def stall_landing():
    """Stall landing page - shows loading state until params are loaded."""
    return rx.center(
        rx.vstack(
            rx.cond(
                ~VoucherState.params_loaded,
                rx.vstack(
                    rx.spinner(size="3", color=GOLD),
                    rx.text("Loading stall information...", color=GOLD, size="3", margin_top="1em"),
                    rx.text(f"Stall ID: {VoucherState.url_stall_id}", color="gray", size="1"),
                    rx.text(f"Event ID: {VoucherState.url_event_id}", color="gray", size="1"),
                    spacing="3",
                    align="center",
                ),
                rx.cond(
                    VoucherState.stall_load_error | (VoucherState.current_stall == None),
                    rx.vstack(
                        rx.icon(tag="triangle_alert", size=60, color="red"),
                        rx.heading("Stall Not Found", size="5", color="white"),
                        rx.text(f"Stall ID: {VoucherState.url_stall_id}", color="gray"),
                        rx.text(f"Event ID: {VoucherState.url_event_id}", color="gray"),
                        rx.text("Please scan a valid stall QR code", color="gray", size="2"),
                        rx.cond(
                            VoucherState.current_event_id,
                            rx.button(
                                "Go to Dashboard",
                                on_click=rx.redirect(f"/dashboard/{VoucherState.current_event_id}"),
                                bg=GOLD,
                                color=BLACK,
                                margin_top="1em",
                            ),
                            rx.button(
                                "Go to Events",
                                on_click=rx.redirect("/events"),
                                bg=GOLD,
                                color=BLACK,
                                margin_top="1em",
                            ),
                        ),
                        spacing="4",
                        align="center",
                        padding="2em",
                    ),
                    rx.cond(
                        VoucherState.guest_authenticated & (VoucherState.authenticated_guest != None),
                        rx.vstack(
                            rx.hstack(
                                rx.icon(tag="store", size=50, color=GOLD),
                                rx.heading(VoucherState.current_stall.get("stall_name", "Stall"), size="5", color=GOLD),
                                spacing="1",
                                align="center",
                            ),
                            rx.text("Welcome to our stall!", color="gray"),
                            rx.divider(),
                            rx.card(
                                rx.vstack(
                                    rx.hstack(
                                        rx.icon(tag="user", size=20, color=GOLD),
                                        rx.text("Guest:", color="gray", weight="bold"),
                                        rx.text(VoucherState.authenticated_guest.get("name", ""), color="white", weight="bold"),
                                        spacing="2",
                                    ),
                                    rx.hstack(
                                        rx.icon(tag="id-card", size=20, color=GOLD),
                                        rx.text("ID:", color="gray", weight="bold"),
                                        rx.text(VoucherState.authenticated_guest.get("guest_id", ""), color="white"),
                                        spacing="2",
                                    ),
                                    rx.hstack(
                                        rx.icon(tag="wallet", size=20, color=GOLD),
                                        rx.text("Opening Balance:", color="gray", weight="bold"),
                                        rx.text(f"RM {VoucherState.authenticated_guest.get('initial_amount', 0):.2f}", color="white"),
                                        spacing="2",
                                    ),
                                    rx.hstack(
                                        rx.icon(tag="trending-down", size=20, color=GOLD),
                                        rx.text("Used:", color="gray", weight="bold"),
                                        rx.text(f"RM {VoucherState.used_amount:.2f}", color="orange"),
                                        spacing="2",
                                    ),
                                    rx.hstack(
                                        rx.icon(tag="wallet", size=20, color=GOLD),
                                        rx.text("Available:", color="gray", weight="bold"),
                                        rx.text(f"RM {VoucherState.authenticated_guest.get('amount', 0):.2f}", color=GOLD, weight="bold"),
                                        spacing="2",
                                    ),
                                    spacing="3",
                                    align="start",
                                ),
                                bg=DARK_GRAY,
                                border=f"1px solid {GOLD}",
                                width="100%",
                                padding="1.5em",
                            ),
                            rx.divider(),
                            rx.vstack(
                                rx.button(
                                    rx.hstack(rx.icon(tag="shopping-cart", size=20), rx.text("Continue at This Stall", size="3", weight="bold")),
                                    on_click=VoucherState.continue_to_menu,
                                    bg=GOLD,
                                    color=BLACK,
                                    width="100%",
                                    height="60px",
                                    _hover={"bg": DARK_GRAY, "color": GOLD, "border": f"1px solid {GOLD}"},
                                ),
                                rx.button(
                                    rx.hstack(rx.icon(tag="qr-code", size=20), rx.text("Scan New Stall", size="3", weight="bold")),
                                    on_click=VoucherState.scan_new_stall,
                                    variant="outline",
                                    border_color=GOLD,
                                    color=GOLD,
                                    width="100%",
                                    height="60px",
                                    _hover={"bg": GOLD, "color": BLACK},
                                ),
                                rx.button(
                                    "Clear saved ID",
                                    on_click=VoucherState.clear_stored_guest,
                                    variant="ghost",
                                    size="3",
                                    color="gray",
                                ),
                                spacing="3",
                                width="100%",
                            ),
                            spacing="1",
                            padding="2em",
                            width="100%",
                        ),
                        rx.vstack(
                            rx.vstack(
                                rx.icon(tag="store", size=40, color=GOLD),
                                rx.heading(VoucherState.current_stall.get("stall_name", "Stall"), size="6", color=GOLD),
                                rx.text("Enter your Guest ID to start ordering", color="white"),
                                spacing="3",
                                align="center",
                            ),
                            rx.divider(),
                            rx.vstack(
                                rx.text("Guest ID", color="gray", size="2", align_self="start"),
                                rx.input(
                                    placeholder="Enter your Guest ID",
                                    value=VoucherState.guest_id_input,
                                    on_change=VoucherState.set_guest_id_input,
                                    width="100%",
                                    bg=BLACK,
                                    border_color=GOLD,
                                    color="white",
                                    size="3",
                                ),
                                width="100%",
                                spacing="2",
                            ),
                            rx.button(
                                rx.hstack(rx.icon(tag="arrow-right", size=16), rx.text("Verify & Continue", size="3", weight="bold")),
                                on_click=VoucherState.start_order_from_landing,
                                width="100%",
                                bg=GOLD,
                                color=BLACK,
                                height="50px",
                                _hover={"bg": DARK_GRAY, "color": GOLD},
                            ),
                            rx.text("Your Guest ID was provided in your invitation email", color="gray", size="1", text_align="center"),
                            spacing="4",
                            padding="2em",
                            width="100%",
                        ),
                    ),
                ),
            ),
            width="100%",
            max_width="500px",
        ),
        width="100%",
        height="100vh",
        bg=BLACK,
    )