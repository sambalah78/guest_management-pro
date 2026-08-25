import reflex as rx
from ..state import State, DARK_GRAY, GOLD, BLACK, VoucherState, UIState


def edit_menu_dialog():
    return rx.dialog.root(
                    rx.dialog.content(
                        rx.vstack(
                            rx.hstack(
                                rx.icon(tag="pencil", size=24, color=GOLD),
                                rx.heading("Edit Menu Item", size="5", color=GOLD),
                                spacing="2",
                            ),
                            rx.divider(),
                            rx.vstack(
                                rx.text("Item Name", color="white", size="2"),
                                rx.input(
                                    placeholder="Enter item name",
                                    value=VoucherState.edit_item_name,
                                    on_change=VoucherState.set_edit_item_name,
                                    width="100%",
                                    bg=BLACK,
                                    border_color=GOLD,
                                    color="white",
                                ),
                                rx.text("Price (RM)", color="white", size="2", margin_top="1em"),
                                rx.input(
                                    placeholder="0.00",
                                    value=VoucherState.edit_item_price.to_string(),
                                    on_change=VoucherState.set_edit_item_price,
                                    width="100%",
                                    bg=BLACK,
                                    border_color=GOLD,
                                    color="white",
                                    type="number",
                                    step="0.01",
                                ),
                                spacing="2",
                                width="100%",
                            ),
                            rx.hstack(
                                rx.button(
                                    "Cancel",
                                    on_click=VoucherState.cancel_edit_item,
                                    variant="outline",
                                    border_color=GOLD,
                                    color=GOLD,
                                    flex="1",
                                ),
                                rx.button(
                                    rx.hstack(
                                        rx.cond(
                                            UIState.is_loading,
                                            rx.spinner(size="2", color=BLACK),
                                            rx.icon(tag="save", size=16),
                                        ),
                                        rx.text("Save Changes"),
                                    ),
                                    on_click=VoucherState.update_menu_item,
                                    bg=GOLD,
                                    color=BLACK,
                                    flex="1",
                                    is_loading=UIState.is_loading,
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
                    open=VoucherState.show_edit_item_dialog,
                ),