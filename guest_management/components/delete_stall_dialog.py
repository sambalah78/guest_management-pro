import reflex as rx
from ..state import State, GOLD, DARK_GRAY, VoucherState, UIState


def delete_stall_dialog():
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.icon(tag="triangle_alert", size=3, color="red"),
                rx.heading("Delete Stall", size="5", color="red"),
                rx.cond(
                    VoucherState.stall_to_delete,
                    rx.text(
                        f"Are you sure you want to delete '{VoucherState.stall_to_delete.get('name', '')}'?",
                        color="white",
                        text_align="center",
                    ),
                    rx.text("Are you sure you want to delete this stall?", color="white",
                            text_align="center"),
                ),
                rx.text(
                    "This will also delete ALL menu items in this stall. This action cannot be undone.",
                    color="gray",
                    size="2",
                    text_align="center",
                ),
                rx.hstack(
                    rx.button(
                        "Cancel",
                        on_click=VoucherState.cancel_delete_stall,
                        variant="outline",
                        border_color=GOLD,
                        color=GOLD,
                        flex="1",
                    ),
                    rx.button(
                        rx.hstack(
                            rx.cond(
                                UIState.is_loading,
                                rx.spinner(size="2", color="white"),
                                rx.icon(tag="trash-2", size=16),
                            ),
                            rx.text("Delete Stall"),
                        ),
                        on_click=VoucherState.confirm_delete_stall,
                        bg="red.500",
                        color="white",
                        flex="1",
                        is_loading=UIState.is_loading,
                    ),
                    spacing="3",
                    width="100%",
                ),
                spacing="4",
                padding="2em",
                align="center",
            ),
            bg=DARK_GRAY,
            border="2px solid red",
            border_radius="15px",
            max_width="400px",
        ),
        open=VoucherState.show_delete_stall_confirm,
    )

def delete_all_stall_dialog():
    return  rx.dialog.root(
                    rx.dialog.content(
                        rx.vstack(
                            rx.icon(tag="triangle_alert", size=3, color="red"),
                            rx.heading("Delete All Stalls", size="5", color="red"),
                            rx.text(
                                "Are you sure you want to delete ALL stalls and menu items?",
                                color="white",
                                text_align="center",
                            ),
                            rx.text(
                                "This action cannot be undone. All stalls and their menu items will be permanently deleted.",
                                color="gray",
                                size="2",
                                text_align="center",
                            ),
                            rx.hstack(
                                rx.button(
                                    "Cancel",
                                    on_click=VoucherState.cancel_delete_all_stalls,
                                    variant="outline",
                                    border_color=GOLD,
                                    color=GOLD,
                                    flex="1",
                                ),
                                rx.button(
                                    rx.hstack(
                                        rx.cond(
                                            UIState.is_loading,
                                            rx.spinner(size="2", color="white"),
                                            rx.icon(tag="trash-2", size=16),
                                        ),
                                        rx.text("Delete All"),
                                    ),
                                    on_click=VoucherState.confirm_delete_all_stalls,
                                    bg="red.500",
                                    color="white",
                                    flex="1",
                                    is_loading=UIState.is_loading,
                                ),
                                spacing="3",
                                width="100%",
                            ),
                            spacing="4",
                            padding="2em",
                            align="center",
                        ),
                        bg=DARK_GRAY,
                        border="2px solid red",
                        border_radius="15px",
                        max_width="400px",
                    ),
                    open=VoucherState.show_delete_all_stalls_confirm,
                )