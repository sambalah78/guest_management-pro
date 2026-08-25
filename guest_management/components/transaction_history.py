# components/transaction_history.py
import reflex as rx
from guest_management.state import VoucherState
from guest_management.utils.constants import GOLD, DARK_GRAY


def transaction_history_modal():
    """Modal to display guest purchase history."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.heading(
                    f"Purchase History - {VoucherState.history_guest.get('name', '')}",
                    size="5",
                    color=GOLD,
                ),
                rx.divider(),
                rx.vstack(
                    rx.foreach(
                        VoucherState.transactions_list,
                        lambda t: _render_transaction_item(t),
                    ),
                    width="100%",
                    max_height="400px",
                    overflow="auto",
                ),
                rx.button("Close", on_click=VoucherState.close_history_modal),
                spacing="4",
                padding="2em",
            ),
            bg=DARK_GRAY,
            border=f"1px solid {GOLD}",
        ),
        open=VoucherState.show_history_modal,
    )


def _render_transaction_item(transaction: dict) -> rx.Component:
    """
    Render a single transaction item.
    transaction is a Var (dict), so we use .get() to access fields.
    """
    return rx.hstack(
        rx.vstack(
            rx.text(transaction.get("item_name", ""), weight="bold"),
            rx.text(f"RM {transaction.get('amount', 0):.2f}", color=GOLD),
            spacing="0",
        ),
        rx.spacer(),
        rx.text(transaction.get("formatted_date", ""), size="1"),
        width="100%",
        padding="0.5em",
        border_bottom="1px solid rgba(212, 175, 55, 0.2)",
    )