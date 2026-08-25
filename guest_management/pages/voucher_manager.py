# guest_management/pages/voucher_manager.py
from typing import Any

import reflex as rx

from guest_management.components.delete_stall_dialog import delete_stall_dialog, delete_all_stall_dialog
from guest_management.components.edit_menu_dialog import edit_menu_dialog
from guest_management.state import VoucherState, EventState, UIState
from guest_management.utils.constants import GOLD, BLACK, DARK_GRAY, LIGHT_GRAY
from guest_management.components.stall_dialogs import add_stall_dialog, add_menu_item_dialog


def stall_card(stall: Any) -> rx.Component:
    """Render a single stall card with edit and delete functionality."""

    # Cast stall to a dict
    stall_dict = stall.to(dict)

    # Cast menu_items to a list
    menu_items = stall_dict.get("menu_items", [])
    if hasattr(menu_items, 'to'):
        menu_items = menu_items.to(list)

    return rx.card(
        rx.vstack(
            # Stall header with edit and delete buttons
            rx.hstack(
                rx.heading(stall_dict["stall_name"], size="4", color=GOLD),
                rx.spacer(),
                rx.hstack(
                    rx.button("+ Item", on_click=lambda: VoucherState.open_menu_dialog(stall_dict["id"]),
                              variant="outline", border_color=GOLD, color=LIGHT_GRAY, size="1"),
                    rx.button("QR", on_click=lambda: VoucherState.show_stall_qr(stall_dict),
                              variant="outline", border_color=GOLD, color=LIGHT_GRAY, size="1"),
                    rx.button("Edit", on_click=lambda: VoucherState.edit_stall(stall_dict["id"], stall_dict["stall_name"]),
                              variant="outline", border_color="blue", color="blue", size="1"),
                    rx.button("Delete", on_click=lambda: VoucherState.delete_stall(stall_dict["id"], stall_dict["stall_name"]),
                              variant="outline", border_color="red", color="red", size="1"),
                    spacing="2",
                ),
                width="100%",
            ),
            rx.divider(),

            # Menu items list with edit and delete buttons
            rx.vstack(
                rx.foreach(
                    menu_items,
                    lambda item: rx.hstack(
                        # Item name
                        rx.text(item.to(dict)["item_name"], color="white", flex="1"),
                        # Item price
                        rx.text(f"RM {item.to(dict)['price']:.2f}", color=GOLD, weight="bold"),
                        # Edit button
                        rx.button(
                            rx.icon(tag="pencil", size=12),
                            on_click=lambda: VoucherState.edit_menu_item(
                                stall_dict["id"],
                                item.to(dict)["id"],
                                item.to(dict)["item_name"],
                                item.to(dict)["price"]
                            ),
                            variant="ghost",
                            color="blue",
                            size="1",
                            _hover={"color": "white", "bg": "blue"},
                        ),
                        # Delete button
                        rx.button(
                            rx.icon(tag="x", size=12),
                            on_click=lambda: VoucherState.delete_menu_item(
                                stall_dict["id"],
                                item.to(dict)["id"],
                                item.to(dict)["item_name"]
                            ),
                            variant="ghost",
                            color="red",
                            size="1",
                            _hover={"color": "white", "bg": "red"},
                        ),
                        spacing="3",
                        width="100%",
                        padding="0.5em",
                        border_bottom="1px solid #333",
                        _hover={"bg": f"{GOLD}11"},
                    )
                ),
                width="100%",
                spacing="0",
            ),

            spacing="2",
            width="100%",
        ),
        bg=BLACK,
        border=f"1px solid {GOLD}",
        padding="1em",
        width="100%",
    )


def show_stall_qr_dialog() -> rx.Component:
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.heading(VoucherState.current_stall.get("stall_name", ""), size="5", color=GOLD),
                rx.cond(
                    VoucherState.current_stall.get("qr_code_data", ""),
                    rx.image(
                        src=VoucherState.current_stall.get("qr_code_data", ""),
                        width="250px", height="250px",
                        border=f"2px solid {GOLD}", border_radius="10px",
                    ),
                    rx.text("Generating QR...", color="gray"),
                ),
                rx.text(f"URL: {VoucherState.current_stall.get('qr_url', '')}", color="gray", size="2"),
                rx.button("Close", on_click=VoucherState.close_qr_dialog, bg=GOLD, color=BLACK),
                spacing="4", padding="2em",
            ),
            bg=DARK_GRAY, border=f"2px solid {GOLD}",
        ),
        open=VoucherState.show_qr_dialog,
    )


def voucher_manager_page() -> rx.Component:
    """Voucher manager page with conditional display."""
    return rx.cond(
        VoucherState.has_amounts,
        rx.center(
            rx.vstack(
                # Header with back button
                rx.hstack(
                    rx.button(
                        rx.hstack(rx.icon(tag="arrow-left", size=16), rx.text("Back to Dashboard")),
                        on_click=rx.redirect(f"/dashboard/{EventState.current_event_id}"),
                        variant="outline",
                        border_color=GOLD,
                        color=GOLD,
                        _hover={"bg": GOLD, "color": BLACK},
                    ),
                    rx.spacer(),
                    rx.hstack(
                        rx.icon(tag="store", size=30, color=GOLD),
                        rx.heading("Voucher & Stall Manager", size="6", color=GOLD),
                        spacing="3",
                    ),
                    rx.spacer(),
                    rx.box(width="100px"),
                    width="100%",
                ),

                # Bulk upload section
                rx.card(
                    rx.vstack(
                        rx.hstack(
                            rx.icon(tag="upload", size=20, color=GOLD),
                            rx.heading("Bulk Upload Stalls & Items", size="4", color=GOLD),
                        ),

                        rx.cond(
                            UIState.is_loading,
                            rx.hstack(
                                rx.spinner(size="2", color=GOLD),
                                rx.text("Processing file...", color=GOLD, size="3"),
                                spacing="3",
                                justify="center",
                                width="100%",
                                padding="1em",
                            ),
                        ),

                        rx.cond(
                            ~UIState.is_loading,
                            rx.vstack(
                                rx.hstack(
                                    rx.upload(
                                        rx.button(
                                            rx.hstack(
                                                rx.icon(tag="file-spreadsheet", size=14),
                                                rx.text("Select Excel File"),
                                            ),
                                            bg=GOLD,
                                            color=BLACK,
                                        ),
                                        id="stall_excel_upload",
                                        multiple=False,
                                        accept={
                                            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                                            ".xls": "application/vnd.ms-excel",
                                        },
                                        max_files=1,
                                        border="none",
                                        padding="none",
                                    ),
                                    rx.button(
                                        rx.hstack(
                                            rx.icon(tag="upload", size=14),
                                            rx.text("Upload Stalls"),
                                        ),
                                        on_click=lambda: VoucherState.handle_stall_excel_upload(
                                            rx.upload_files(upload_id="stall_excel_upload")
                                        ),
                                        bg=GOLD,
                                        color=BLACK,
                                    ),
                                    spacing="3",
                                ),
                                rx.text("Excel format: Stall | Item | Price", color="gray", size="1"),
                                rx.text("Example: Burger Stall | Cheeseburger | 10", color="gray", size="1"),
                                spacing="3",
                                width="100%",
                            ),
                        ),
                        spacing="3",
                    ),
                    bg=DARK_GRAY,
                    padding="1em",
                    width="100%",
                ),

                rx.divider(),

                # Action buttons
                rx.hstack(
                    rx.button(
                        "+ Add Stall",
                        on_click=VoucherState.open_stall_dialog,
                        bg=GOLD,
                        color=BLACK,
                        is_disabled=UIState.is_loading,
                    ),
                    rx.button(
                        rx.hstack(rx.icon(tag="printer", size=14), rx.text("Print All QR Codes")),
                        on_click=rx.redirect("/print-qr"),
                        variant="outline",
                        border_color=GOLD,
                        color=GOLD,
                        is_disabled=UIState.is_loading,
                        _hover={"bg": GOLD, "color": BLACK},
                    ),
                    rx.button(
                        rx.hstack(rx.icon(tag="trash-2", size=14), rx.text("Delete All Stalls")),
                        on_click=VoucherState.delete_all_stalls,
                        variant="outline",
                        border_color="red",
                        color="red",
                        is_disabled=UIState.is_loading,
                        _hover={"bg": "red", "color": "white"},
                    ),
                    spacing="3",
                ),

                # Stalls list
                rx.cond(
                    UIState.is_loading,
                    rx.center(
                        rx.spinner(size="2", color=GOLD),
                        width="100%",
                        padding="2em",
                    ),
                    rx.cond(
                        VoucherState.stalls_list.length() > 0,
                        rx.vstack(
                            rx.foreach(
                                VoucherState.stalls_list.to(list),
                                stall_card
                            ),
                            width="100%",
                            spacing="4",
                        ),
                        rx.center(
                            rx.vstack(
                                rx.icon(tag="store", size=50, color=GOLD),
                                rx.heading("No Stalls Yet", size="4", color="white"),
                                rx.text("Add stalls manually or upload an Excel file", color="gray"),
                                spacing="3",
                                padding="2em",
                            ),
                            width="100%",
                        ),
                    ),
                ),

                # All Dialogs
                add_stall_dialog(),
                add_menu_item_dialog(),
                show_stall_qr_dialog(),

                # Edit Dialogs
                rx.dialog.root(
                    rx.dialog.content(
                        rx.vstack(
                            rx.hstack(
                                rx.icon(tag="pencil", size=24, color=GOLD),
                                rx.heading("Edit Stall Name", size="5", color=GOLD),
                                spacing="2",
                            ),
                            rx.divider(),
                            rx.vstack(
                                rx.text("Stall Name", color="white", size="2"),
                                rx.input(
                                    placeholder="Enter stall name",
                                    value=VoucherState.edit_stall_name,
                                    on_change=VoucherState.set_edit_stall_name,
                                    width="100%",
                                    bg=BLACK,
                                    border_color=GOLD,
                                    color="white",
                                ),
                                spacing="2",
                                width="100%",
                            ),
                            rx.hstack(
                                rx.button(
                                    "Cancel",
                                    on_click=VoucherState.cancel_edit_stall,
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
                                    on_click=VoucherState.update_stall_name,
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
                    open=VoucherState.show_edit_stall_dialog,
                ),

                # Delete Stall Confirmation Dialog
                delete_stall_dialog(),

                # Delete All Stalls Confirmation Dialog
                delete_all_stall_dialog(),

                # Edit Menu Item Dialog
                edit_menu_dialog(),

                spacing="5",
                width="100%",
                padding="2em",
            ),
            width="100%",
            min_height="100vh",
            bg=BLACK,
        ),
        # No voucher balances
        rx.center(
            rx.vstack(
                rx.icon(tag="triangle_alert", size=50, color="red"),
                rx.heading("No Voucher Balances", size="5", color="white"),
                rx.text("Please upload guest list with 'Amount' column first.", color="gray"),
                rx.button(
                    "Back to Dashboard",
                    on_click=rx.redirect(f"/dashboard/{EventState.current_event_id}"),
                    bg=GOLD,
                    color=BLACK,
                ),
                spacing="4",
            ),
            height="100vh",
            bg=BLACK,
        ),
    )