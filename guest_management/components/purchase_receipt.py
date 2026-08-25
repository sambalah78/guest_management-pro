# components/purchase_receipt.py
import reflex as rx
from guest_management.state import State, GOLD, BLACK, DARK_GRAY, VoucherState


def purchase_receipt_dialog():
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.icon(tag="circle_check", size=3, color="green"),
                rx.heading("Purchase Successful!", size="5", color=GOLD),
                rx.text("Thank you for your order!", color="white"),
                rx.divider(),
                rx.vstack(
                    rx.text("Items Purchased:", color=GOLD, weight="bold"),
                    rx.text(VoucherState.order_receipt.get("items_summary", "No items"), color="white"),
                    width="100%",
                ),
                rx.divider(),
                rx.hstack(
                    rx.text("Total:", color="white", weight="bold"),
                    rx.spacer(),
                    rx.text(f"RM {VoucherState.order_receipt.get('total', 0):.2f}", color=GOLD, weight="bold"),
                    width="100%",
                ),
                rx.hstack(
                    rx.text("Remaining Balance:", color="white"),
                    rx.spacer(),
                    rx.text(f"RM {VoucherState.order_receipt.get('balance', 0):.2f}", color=GOLD, weight="bold"),
                    width="100%",
                ),
                rx.divider(),
                rx.hstack(
                    rx.button(
                        "Shop More",
                        on_click=VoucherState.reset_order,
                        bg=GOLD,
                        color=BLACK,
                        flex="1",
                    ),
                    rx.button(
                        "Exit",
                        on_click=VoucherState.exit_to_lobby,
                        variant="outline",
                        border_color=GOLD,
                        color=GOLD,
                        flex="1",
                    ),
                    spacing="3",
                    width="100%",
                ),
                spacing="4",
                padding="2em",
                width="100%",
            ),
            bg=DARK_GRAY,
            border=f"2px solid {GOLD}",
            border_radius="15px",
            max_width="400px",
        ),
        open=VoucherState.show_purchase_receipt,
    )