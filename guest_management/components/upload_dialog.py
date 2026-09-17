# components/upload_dialog.py
import reflex as rx

from guest_management.state import (
    State,
    


    EventState,
    VoucherState,
    UIState, 
)
from guest_management.utils.theme import TEXT_SECONDARY, TEXT_MUTED , GOLD, NAVY_DARK, NAVY


def upload_dialog():
    """Upload guest list dialog with guest-list clear confirmation."""

    return rx.fragment(
        # ================================================================
        # MAIN UPLOAD DIALOG
        # ================================================================
        rx.dialog.root(
            rx.dialog.content(
                rx.vstack(
                    # ------------------------------------------------------------
                    # HEADER
                    # ------------------------------------------------------------
                    rx.hstack(
                        rx.icon(
                            tag="upload",
                            size=24,
                            color=GOLD,
                        ),
                        rx.vstack(
                            rx.heading(
                                "Upload Guest List",
                                size="5",
                                color=GOLD,
                            ),
                            rx.text(
                                EventState.event_config_name,
                                color=TEXT_SECONDARY,
                                size="2",
                            ),
                            spacing="0",
                            align="start",
                        ),
                        spacing="2",
                        align="center",
                        width="100%",
                    ),

                    rx.divider(),

                    # ------------------------------------------------------------
                    # FILE REQUIREMENTS
                    # ------------------------------------------------------------
                    rx.vstack(
                        rx.text(
                            "Guest List Requirements",
                            color=GOLD,
                            weight="bold",
                            size="3",
                        ),

                        rx.hstack(
                            rx.vstack(
                                rx.text(
                                    "Required",
                                    color="white",
                                    weight="bold",
                                    size="2",
                                ),
                                rx.text(
                                    "Name",
                                    color=TEXT_SECONDARY,
                                    size="1",
                                ),
                                rx.text(
                                    "Email",
                                    color=TEXT_SECONDARY,
                                    size="1",
                                ),
                                rx.text(
                                    "ID",
                                    color=TEXT_SECONDARY,
                                    size="1",
                                ),
                                rx.text(
                                    "Table",
                                    color=TEXT_SECONDARY,
                                    size="1",
                                ),
                                spacing="1",
                                align="start",
                                flex="1",
                            ),

                            rx.vstack(
                                rx.text(
                                    "Optional",
                                    color="white",
                                    weight="bold",
                                    size="2",
                                ),

                                rx.cond(
                                    EventState.show_food_vouchers,
                                    rx.text(
                                        "Amount / Voucher",
                                        color=TEXT_SECONDARY,
                                        size="1",
                                    ),
                                    rx.fragment(),
                                ),

                                rx.cond(
                                    EventState.show_dietary_restrictions,
                                    rx.text(
                                        "Dietary Restrictions",
                                        color=TEXT_SECONDARY,
                                        size="1",
                                    ),
                                    rx.fragment(),
                                ),

                                rx.cond(
                                    EventState.show_plus_one,
                                    rx.text(
                                        "Plus One Name",
                                        color=TEXT_SECONDARY,
                                        size="1",
                                    ),
                                    rx.fragment(),
                                ),

                                rx.cond(
                                    EventState.show_parent_guardian,
                                    rx.text(
                                        "Parent Name / Phone",
                                        color=TEXT_SECONDARY,
                                        size="1",
                                    ),
                                    rx.fragment(),
                                ),

                                spacing="1",
                                align="start",
                                flex="1",
                            ),

                            spacing="6",
                            width="100%",
                        ),

                        rx.text(
                            "Supported formats: .xlsx, .xls, .csv",
                            color=TEXT_SECONDARY,
                            size="1",
                        ),

                        spacing="2",
                        width="100%",
                        align="start",
                    ),

                    rx.divider(),

                    # ------------------------------------------------------------
                    # DROP ZONE
                    # ------------------------------------------------------------
                    rx.upload(
                        rx.vstack(
                            rx.icon(
                                tag="file-spreadsheet",
                                size=36,
                                color=GOLD,
                            ),

                            rx.cond(
                                State.selected_file_name,
                                rx.vstack(
                                    rx.text(
                                        State.selected_file_name,
                                        color="white",
                                        weight="bold",
                                        size="2",
                                        text_align="center",
                                    ),
                                    rx.text(
                                        "File selected",
                                        color="green",
                                        size="1",
                                    ),
                                    spacing="1",
                                    align="center",
                                ),

                                rx.vstack(
                                    rx.text(
                                        "Drag & drop your guest list here",
                                        color="white",
                                        weight="bold",
                                        size="3",
                                        text_align="center",
                                    ),
                                    rx.text(
                                        "or",
                                        color=TEXT_SECONDARY,
                                        size="2",
                                    ),

                                    rx.button(
                                        rx.hstack(
                                            rx.icon(
                                                tag="file",
                                                size=16,
                                            ),
                                            rx.text("Select File"),
                                            spacing="2",
                                        ),
                                        bg=GOLD,
                                        color=NAVY_DARK,
                                        _hover={
                                            "bg": NAVY,
                                            "color": "white",
                                        },
                                    ),

                                    rx.text(
                                        "Excel or CSV file",
                                        color=TEXT_SECONDARY,
                                        size="1",
                                    ),

                                    spacing="2",
                                    align="center",
                                ),
                            ),

                            spacing="2",
                            align="center",
                            justify="center",
                            width="100%",
                            min_height="180px",
                            padding="1.5em",
                        ),

                        id="upload_guests",
                        multiple=False,
                        accept={
                            ".xlsx": (
                                "application/"
                                "vnd.openxmlformats-officedocument."
                                "spreadsheetml.sheet"
                            ),
                            ".xls": "application/vnd.ms-excel",
                            ".csv": "text/csv",
                        },
                        max_files=1,
                        border=f"2px dashed {GOLD}",
                        border_radius="12px",
                        width="100%",
                        padding="0.25em",
                        on_drop=State.set_selected_file,
                    ),

                    # ------------------------------------------------------------
                    # SELECTED FILE STATUS
                    # ------------------------------------------------------------
                    rx.cond(
                        State.selected_file_name,
                        rx.hstack(
                            rx.icon(
                                tag="circle-check",
                                color="green",
                                size=18,
                            ),
                            rx.vstack(
                                rx.text(
                                    "Ready to import",
                                    color="green",
                                    weight="bold",
                                    size="2",
                                ),
                                rx.text(
                                    State.selected_file_name,
                                    color=TEXT_SECONDARY,
                                    size="1",
                                ),
                                spacing="0",
                                align="start",
                            ),
                            spacing="2",
                            bg=NAVY_DARK,
                            padding="0.75em 1em",
                            border_radius="8px",
                            width="100%",
                        ),
                        rx.fragment(),
                    ),

                    # ------------------------------------------------------------
                    # ACTIONS
                    # ------------------------------------------------------------
                    rx.vstack(
                        rx.hstack(
                            rx.button(
                                "Cancel",
                                on_click=State.close_upload_dialog,
                                variant="outline",
                                border_color=GOLD,
                                color=GOLD,
                                flex="1",
                                _hover={
                                    "bg": GOLD,
                                    "color": NAVY_DARK,
                                },
                            ),

                            rx.button(
                                rx.hstack(
                                    rx.cond(
                                        UIState.is_loading,
                                        rx.spinner(
                                            size="2",
                                            color=NAVY_DARK,
                                        ),
                                        rx.icon(
                                            tag="upload",
                                            size=16,
                                        ),
                                    ),
                                    rx.text("Import Guest List"),
                                    spacing="2",
                                ),
                                on_click=State.handle_upload,
                                bg=GOLD,
                                color=NAVY_DARK,
                                flex="1",
                                is_loading=UIState.is_loading,
                                disabled=(
                                        (State.selected_file_name == "")
                                        | UIState.is_loading
                                ),
                                _hover={
                                    "bg": NAVY,
                                    "color": "white",
                                },
                            ),
                            spacing="2",
                            width="100%",
                        ),

                        rx.divider(),

                        # --------------------------------------------------------
                        # DANGER ZONE
                        # --------------------------------------------------------
                        rx.hstack(
                            rx.icon(
                                tag="triangle-alert",
                                size=15,
                                color="red",
                            ),
                            rx.text(
                                "Already have guests? Use Clear Guest List only "
                                "if you intend to remove the existing list.",
                                color=TEXT_SECONDARY,
                                size="1",
                            ),
                            spacing="2",
                            width="100%",
                        ),

                        rx.button(
                            rx.hstack(
                                rx.icon(
                                    tag="trash-2",
                                    size=15,
                                ),
                                rx.text("Clear Existing Guest List"),
                                spacing="2",
                            ),
                            on_click=State.clear_table_dialog,
                            variant="outline",
                            border_color="red",
                            color="red",
                            width="100%",
                            _hover={
                                "bg": "red",
                                "color": "white",
                            },
                        ),

                        spacing="3",
                        width="100%",
                    ),

                    spacing="4",
                    padding="2em",
                    width="100%",
                ),

                bg=NAVY,
                border=f"2px solid {GOLD}",
                border_radius="15px",
                width="100%",
                max_width="550px",
            ),

            open=State.show_upload_dialog,
        ),

        # ================================================================
        # CLEAR TABLE CONFIRMATION DIALOG
        # ================================================================
        rx.dialog.root(
            rx.dialog.content(
                rx.vstack(
                    rx.icon(
                        tag="triangle-alert",
                        size=40,
                        color="red",
                    ),

                    rx.heading(
                        "Clear Guest List?",
                        size="5",
                        color="white",
                    ),

                    rx.text(
                        "This will permanently remove all participants "
                        "from this event.",
                        color=TEXT_SECONDARY,
                        text_align="center",
                    ),

                    rx.text(
                        "This action cannot be undone.",
                        color="red",
                        weight="bold",
                        text_align="center",
                    ),

                    rx.hstack(
                        rx.button(
                            "Cancel",
                            on_click=State.cancel_clear_table,
                            variant="outline",
                            border_color=GOLD,
                            color=GOLD,
                            flex="1",
                        ),

                        rx.button(
                            rx.hstack(
                                rx.icon(
                                    tag="trash-2",
                                    size=16,
                                ),
                                rx.text("Clear Guest List"),
                                spacing="2",
                            ),
                            on_click=State.confirm_clear_table,
                            bg="red",
                            color="white",
                            flex="1",
                            _hover={
                                "bg": "darkred",
                            },
                        ),

                        spacing="2",
                        width="100%",
                    ),

                    spacing="4",
                    padding="2em",
                    width="100%",
                    align="center",
                ),

                bg=NAVY,
                border="2px solid red",
                border_radius="15px",
                max_width="450px",
            ),

            open=State.show_clear_table_confirm,
        ),
    )