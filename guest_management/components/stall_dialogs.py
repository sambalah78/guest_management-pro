import reflex as rx
from guest_management.state import State, GOLD, BLACK, DARK_GRAY, VoucherState


def add_stall_dialog():
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.hstack(
                    rx.icon(tag="store", size=24, color=GOLD),
                    rx.heading("Add New Stall", size="5", color=GOLD),
                    spacing="2",
                ),
                rx.divider(),
                rx.input(
                    placeholder="Stall Name",
                    value=VoucherState.stall_name,
                    on_change=VoucherState.set_stall_name,
                    width="100%",
                    bg=BLACK,
                    border_color=GOLD,
                    color="white",
                ),
                rx.hstack(
                    rx.button("Cancel", on_click=VoucherState.close_stall_dialog, variant="outline", border_color=GOLD, color=GOLD, flex="1"),
                    rx.button("Add Stall", on_click=VoucherState.add_stall, bg=GOLD, color=BLACK, flex="1"),
                    spacing="3",
                    width="100%",
                ),
                spacing="4",
                padding="2em",
            ),
            bg=DARK_GRAY,
            border=f"2px solid {GOLD}",
        ),
        open=VoucherState.show_stall_dialog,
    )

def add_menu_item_dialog():
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.hstack(
                    rx.icon(tag="utensils", size=24, color=GOLD),
                    rx.heading("Add Menu Item", size="5", color=GOLD),
                    spacing="2",
                ),
                rx.divider(),
                rx.input(
                    placeholder="Item Name",
                    value=VoucherState.menu_item_name,
                    on_change=VoucherState.set_menu_item_name,
                    width="100%",
                    bg=BLACK,
                    border_color=GOLD,
                    color="white",
                ),
                rx.input(
                    placeholder="Price (RM)",
                    type="number",
                    value=str(VoucherState.menu_item_price),
                    on_change=VoucherState.set_menu_item_price,
                    width="100%",
                    bg=BLACK,
                    border_color=GOLD,
                    color="white",
                ),
                rx.hstack(
                    rx.button("Cancel", on_click=VoucherState.close_menu_dialog, variant="outline", border_color=GOLD, color=GOLD, flex="1"),
                    rx.button("Add Item", on_click=VoucherState.add_menu_item, bg=GOLD, color=BLACK, flex="1"),
                    spacing="3",
                    width="100%",
                ),
                spacing="4",
                padding="2em",
            ),
            bg=DARK_GRAY,
            border=f"2px solid {GOLD}",
        ),
        open=VoucherState.show_menu_dialog,
    )