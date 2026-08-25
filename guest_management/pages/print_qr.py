# pages/print_qr.py
import reflex as rx
from guest_management.state import State, VoucherState
from guest_management.utils.constants import GOLD, BLACK, DARK_GRAY


def print_qr_page():
    """Page for printing all stall QR codes."""
    return rx.center(
        rx.vstack(
            rx.hstack(
                rx.button(
                    rx.hstack(rx.icon(tag="arrow-left", size=14), rx.text("Back")),
                    on_click=rx.redirect("/voucher-manager"),
                    variant="outline",
                    border_color=GOLD,
                    color=GOLD,
                ),
                rx.spacer(),
                rx.heading("Stall QR Codes", size="5", color=GOLD),
                rx.spacer(),
                rx.button(
                    rx.hstack(rx.icon(tag="printer", size=14), rx.text("Print All")),
                    on_click=rx.call_script("window.print()"),
                    bg=GOLD,
                    color=BLACK,
                ),
                width="100%",
            ),
            rx.divider(),
            rx.grid(
                rx.foreach(
                    VoucherState.stalls_list,
                    lambda stall: rx.card(
                        rx.vstack(
                            rx.heading(stall.get("stall_name", ""), size="3", color=GOLD),
                            rx.cond(
                                stall.get("qr_code", ""),
                                rx.image(src=stall.get("qr_code", ""), width="150px", height="150px"),
                                rx.text("QR not available", color="gray"),
                            ),
                            rx.text("Scan to order", color="gray", size="1"),
                            spacing="2",
                            align="center",
                        ),
                        bg=DARK_GRAY,
                        border=f"1px solid {GOLD}",
                        padding="1em",
                    ),
                ),
                columns=rx.breakpoints(initial="1", sm="2", md="3", lg="4"),
                spacing="3",
                width="100%",
            ),
            spacing="4",
            padding="2em",
            width="100%",
        ),
        width="100%",
        min_height="100vh",
        bg=BLACK,
    )