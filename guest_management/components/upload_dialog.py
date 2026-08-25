# components/upload_dialog.py
import reflex as rx
from guest_management.state import State, GOLD, BLACK, DARK_GRAY, EventState, VoucherState, UIState


def upload_dialog():
    """Upload guest list dialog."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.hstack(
                    rx.icon(tag="upload", size=24, color=GOLD),
                    rx.heading("Upload Guest List", size="5", color=GOLD),
                    spacing="2",
                ),
                rx.divider(),
                rx.vstack(
                    # Event Type Info
                    rx.hstack(
                        rx.text("Event Type:", color=GOLD, weight="bold"),
                        rx.text(EventState.event_config_name, color="white"),
                        spacing="2",
                    ),
                    # Required Columns Info
                    rx.vstack(
                        rx.text("Required Columns:", color=GOLD, weight="bold"),
                        rx.text("Name, Email, ID, Table", color="gray", size="1"),
                        rx.cond(
                            EventState.show_food_vouchers,
                            rx.text("Amount/Voucher (optional)", color="gray", size="1"),
                        ),
                        rx.cond(
                            EventState.show_dietary_restrictions,
                            rx.text("Dietary Restrictions (optional)", color="gray", size="1"),
                        ),
                        rx.cond(
                            EventState.show_plus_one,
                            rx.text("Plus One Name (optional)", color="gray", size="1"),
                        ),
                        rx.cond(
                            EventState.show_parent_guardian,
                            rx.text("Parent Name, Parent Phone (optional)", color="gray", size="1"),
                        ),
                        spacing="1",
                        align="start",
                    ),
                    rx.divider(),
                    # Selected File Display
                    rx.hstack(
                        rx.cond(
                            State.selected_file_name,
                            rx.hstack(
                                rx.icon(tag="file-text", size=16, color=GOLD),
                                rx.text(State.selected_file_name, color="white", size="2"),
                                spacing="2",
                                bg=BLACK,
                                padding="0.5em 1em",
                                border_radius="8px",
                                border=f"1px solid {GOLD}",
                                width="100%",
                            ),
                            rx.text("No file selected", color="gray", size="2", padding="0.5em"),
                        ),
                        width="100%",
                    ),
                    # File Upload Button
                    rx.upload(
                        rx.button(
                            rx.hstack(
                                rx.icon(tag="file", size=16),
                                rx.text("Select File"),
                            ),
                            border="none",
                            bg=GOLD,
                            color=BLACK,
                            width="100%",
                            _hover={"bg": DARK_GRAY, "color": "gray"},
                        ),
                        id="upload_guests",
                        multiple=False,
                        accept={
                            ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            ".xls": "application/vnd.ms-excel",
                            ".csv": "text/csv",
                        },
                        max_files=1,
                        border=GOLD,
                        padding="0.5em",
                        border_radius="1px",
                        on_drop=State.set_selected_file,
                    ),
                    rx.divider(),
                    # Action Buttons
                    rx.hstack(
                        rx.button(
                            rx.hstack(
                                rx.cond(
                                    UIState.is_loading,
                                    rx.spinner(size="2", color=BLACK),
                                    rx.icon(tag="upload", size=16),
                                ),
                                rx.text("Upload"),
                            ),
                            on_click=State.handle_upload,
                            bg=GOLD,
                            color=BLACK,
                            is_loading=UIState.is_loading,
                            _hover={"bg": DARK_GRAY, "color": "gray"},
                            flex="1",
                        ),
                        rx.button(
                            rx.hstack(
                                rx.icon(tag="trash-2", size=16),
                                rx.text("Clear Table"),
                            ),
                            on_click=State.clear_table_dialog,
                            variant="outline",
                            border_color="red",
                            color="red",
                            _hover={"bg": "red", "color": "white"},
                        ),
                        rx.button(
                            "Cancel",
                            on_click=State.close_upload_dialog,
                            variant="outline",
                            border_color=GOLD,
                            color=GOLD,
                            flex="1",
                        ),
                        spacing="2",
                        width="100%",
                    ),
                    # Upload Status
                    rx.cond(
                        State.uploaded_filename,
                        rx.hstack(
                            rx.icon(tag="check", color="green", size=16),
                            rx.text(f"Uploaded: {State.uploaded_filename}", color="green", size="2"),
                            bg=BLACK,
                            padding="0.5em",
                            border_radius="4px",
                            width="100%",
                        ),
                        rx.fragment(),
                    ),
                    rx.text("Supported formats: .xlsx, .xls, .csv", color="gray", size="1"),
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
            max_width="500px",
        ),
        open=State.show_upload_dialog,
    )