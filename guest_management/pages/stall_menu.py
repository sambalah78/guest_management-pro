# guest_management/pages/stall_menu.py
"""Stall menu page – Full corrected version."""

import reflex as rx
from guest_management.state import VoucherState, GOLD, BLACK, DARK_GRAY
from guest_management.components.purchase_receipt import purchase_receipt_dialog


def stall_menu():
    """Stall menu page - uses state variables set by on_load."""
    return rx.cond(
        VoucherState.current_stall & VoucherState.current_guest,
        rx.cond(
            VoucherState.current_guest.get("status") != "Present",
            rx.center(
                rx.vstack(
                    rx.icon(tag="triangle_alert", size=50, color="red"),
                    rx.heading("Check-in Required", size="5", color="white"),
                    rx.text("You must check in at the event entrance before ordering food.", color="gray",
                            text_align="center"),
                    rx.button("Go to Check-in", on_click=rx.redirect(f"/checkin/{VoucherState.current_event_id}"), bg=GOLD,
                              color=BLACK),
                    spacing="4", padding="2em",
                ),
                bg=BLACK, height="100vh",
            ),
            rx.center(
                rx.vstack(
                    rx.hstack(
                        rx.spacer(),
                        rx.hstack(
                            rx.icon(tag="store", size=28, color=GOLD),
                            rx.heading(
                                VoucherState.current_stall.get("stall_name", ""),
                                font_size=["1.5em", "1.75em", "2em", "2.25em"],
                                color=GOLD
                            ),
                            width="100%"
                        ),
                        rx.spacer(),
                        rx.box(width="100px"),
                    ),
                    rx.card(
                        rx.vstack(
                            rx.hstack(
                                rx.icon(tag="user", size=18, color=GOLD),
                                rx.text("Name:", color=GOLD),
                                rx.text(VoucherState.current_guest.get("name", ""), color="white", weight="bold"),
                                spacing="2"
                            ),
                            rx.hstack(
                                rx.icon(tag="wallet", size=18, color=GOLD),
                                rx.text("Bal:", color=GOLD),
                                rx.text(
                                    f"RM {VoucherState.current_guest.get('amount', 0):.2f}",
                                    color="white",
                                    weight="bold",
                                    size="4"
                                ),
                                spacing="2"
                            ),
                            spacing="2",
                            align="start",
                        ),
                        bg=DARK_GRAY,
                        border=f"1px solid {GOLD}",
                        width="100%",
                        padding="1em"
                    ),
                    rx.divider(),
                    rx.vstack(
                        rx.foreach(
                            VoucherState.current_stall["menu_items"].to(list),
                            lambda item: rx.card(
                                rx.hstack(
                                    rx.checkbox(
                                        on_change=lambda checked: VoucherState.toggle_order_item(item.to(dict), checked)
                                    ),
                                    rx.vstack(
                                        rx.text(item.to(dict)["item_name"], color="white", weight="bold"),
                                        spacing="0",
                                        align="start"
                                    ),
                                    rx.spacer(),
                                    rx.text(f"RM {item.to(dict)['price']:.2f}", color=GOLD, weight="bold"),
                                    spacing="3",
                                    width="100%"
                                ),
                                bg=BLACK,
                                border=f"1px solid {GOLD}33",
                                padding="1em",
                                width="100%",
                                _hover={"border": f"1px solid {GOLD}"}
                            )
                        ),
                        width="100%",
                        spacing="2",
                        max_height="400px",
                        overflow_y="auto"
                    ),
                    rx.divider(),
                    rx.card(
                        rx.vstack(
                            rx.hstack(
                                rx.text("Items:", color="white", weight="bold"),
                                rx.spacer(),
                                rx.text(VoucherState.order_items.length().to_string() + " item(s)", color=GOLD)
                            ),
                            rx.hstack(
                                rx.text("Total:", color="white", weight="bold", size="4"),
                                rx.spacer(),
                                rx.text(f"RM {VoucherState.order_total:.2f}", color=GOLD, weight="bold", size="4")
                            ),
                            rx.button(
                                rx.hstack(
                                    rx.cond(
                                        VoucherState.is_loading,
                                        rx.spinner(size="3", color=BLACK),
                                        rx.icon(tag="credit-card", size=20)
                                    ),
                                    rx.text("Purchase", size="3", weight="bold")
                                ),
                                on_click=VoucherState.confirm_purchase,
                                width="100%",
                                bg=GOLD,
                                color=BLACK,
                                height="50px",
                                is_disabled=VoucherState.order_total == 0,
                                _hover={"bg": DARK_GRAY, "color": GOLD}
                            ),
                            rx.button(
                                rx.text("⬅️ Back", size="3", weight="bold", color=BLACK),
                                on_click=rx.redirect(
                                    f"/stall?stall_id={VoucherState.current_stall.get('id')}&event_id={VoucherState.current_event_id}"
                                ),
                                variant="outline",
                                border_color=GOLD,
                                bg=GOLD,
                                _hover={"bg": GOLD, "color": BLACK},
                                width="100%",
                            ),
                            rx.cond(
                                VoucherState.order_total > 0,
                                rx.cond(
                                    VoucherState.is_insufficient_balance,
                                    rx.text(
                                        f"Insufficient balance! Need RM {VoucherState.order_total:.2f}, have RM {VoucherState.current_guest.get('amount', 0):.2f}",
                                        color="red",
                                        size="1"
                                    ),
                                    rx.fragment()
                                ),
                                rx.fragment()
                            ),
                            spacing="3",
                            width="100%",
                        ),
                        bg=DARK_GRAY,
                        border=f"1px solid {GOLD}",
                        width="100%",
                        padding="1.5em"
                    ),
                    purchase_receipt_dialog(),
                    spacing="4",
                    padding="2em",
                    bg=DARK_GRAY,
                    border=f"1px solid {GOLD}",
                    border_radius="lg",
                    width="600px",
                    max_width="95%",
                ),
                width="100%",
                min_height="100vh",
                bg=BLACK,
                padding="0.5em",
            ),
        ),
        rx.center(rx.spinner(color=GOLD), height="100vh", bg=BLACK),
    )