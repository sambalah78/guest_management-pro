# guest_management/pages/lucky_draw.py
"""Lucky Draw dashboard page."""

import reflex as rx

from ..state import State, UIState, LuckyDrawState
from ..utils.constants import GOLD, BLACK, DARK_GRAY, LIGHT_GRAY
from ..components import upload_dialog
from ..components.lucky_draw_manager import lucky_draw_manager


# -----------------------------------------------------------------------------
# Small reusable UI helpers
# -----------------------------------------------------------------------------


def _stat_card(label, value, icon, *, background=BLACK):
    """Render one compact dashboard statistic card."""
    return rx.box(
        rx.hstack(
            rx.icon(tag=icon, size=20, color=GOLD),
            rx.vstack(
                rx.text(
                    label,
                    color=LIGHT_GRAY,
                    font_size="0.78rem",
                    weight="medium",
                ),
                rx.text(
                    value,
                    color=GOLD,
                    font_size=["1.45rem", "1.7rem"],
                    weight="bold",
                ),
                spacing="0",
                align="start",
            ),
            spacing="3",
            align="center",
        ),
        background=background,
        border="1px solid rgba(212, 175, 55, 0.25)",
        border_radius="12px",
        padding=["0.85em", "1em"],
        width="100%",
    )


def _section_header(icon, title, description):
    """Render a dashboard card header."""
    return rx.hstack(
        rx.box(
            rx.icon(tag=icon, size=20, color=BLACK),
            background=GOLD,
            border_radius="10px",
            padding="0.55em",
            display="flex",
            align_items="center",
            justify_content="center",
        ),
        rx.vstack(
            rx.heading(
                title,
                size="4",
                color="white",
                margin="0",
            ),
            rx.text(
                description,
                color=LIGHT_GRAY,
                font_size="0.78rem",
            ),
            spacing="0",
            align="start",
        ),
        spacing="3",
        align="center",
        width="100%",
    )


def _guest_list_card():
    """Guest list summary and entry point to the normal guest manager."""
    return rx.card(
        rx.vstack(
            _section_header(
                "users",
                "Guest List",
                "Manage the participants for this Lucky Draw event.",
            ),
            rx.divider(),
            rx.hstack(
                rx.vstack(
                    rx.text(
                        LuckyDrawState.lucky_draw_eligible_count,
                        color=GOLD,
                        font_size=["2rem", "2.4rem"],
                        weight="bold",
                    ),
                    rx.text(
                        "Eligible guests",
                        color=LIGHT_GRAY,
                        font_size="0.8rem",
                    ),
                    spacing="0",
                    align="start",
                ),
                rx.spacer(),
                rx.button(
                    rx.hstack(
                        rx.icon(tag="upload", size=16),
                        rx.text("Import Guests"),
                        spacing="2",
                    ),
                    on_click=rx.redirect(
                        f"/dashboard/{LuckyDrawState.current_event_id}"
                    ),
                    bg=GOLD,
                    color=BLACK,
                    size="2",
                    _hover={"transform": "translateY(-1px)"},
                ),
            ),
            rx.text(
                "Guest lists can be uploaded and managed from the event dashboard.",
                color="gray",
                font_size="0.72rem",
            ),
            spacing="4",
            width="100%",
        ),
        background=DARK_GRAY,
        border="1px solid rgba(212, 175, 55, 0.35)",
        border_radius="14px",
        padding=["1em", "1.25em"],
        width="100%",
    )


def _prize_count():
    """Return the count for the currently selected prize input mode."""
    return rx.cond(
        LuckyDrawState.prize_mode == "single",
        rx.cond(
            LuckyDrawState.single_prize_name != "",
            1,
            0,
        ),
        rx.cond(
            LuckyDrawState.prize_mode == "multiple",
            LuckyDrawState.multiple_prizes_list.length(),
            LuckyDrawState.excel_prizes_list.length(),
        ),
    )


def _prize_list_card():
    """Prize configuration summary with the existing Excel import path."""
    return rx.card(
        rx.vstack(
            _section_header(
                "gift",
                "Prize List",
                "Add the prizes that will be awarded during the draw.",
            ),
            rx.divider(),
            rx.hstack(
                rx.vstack(
                    rx.text(
                        _prize_count(),
                        color=GOLD,
                        font_size=["2rem", "2.4rem"],
                        weight="bold",
                    ),
                    rx.text(
                        "Prizes configured",
                        color=LIGHT_GRAY,
                        font_size="0.8rem",
                    ),
                    spacing="0",
                    align="start",
                ),
                rx.spacer(),
                rx.upload(
                    rx.button(
                        rx.hstack(
                            rx.icon(tag="file-spreadsheet", size=16),
                            rx.text("Upload Prize Excel"),
                            spacing="2",
                        ),
                        bg=GOLD,
                        color=BLACK,
                        size="2",
                    ),
                    id="lucky_draw_prize_excel_upload",
                    multiple=False,
                    accept={
                        ".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                        ".xls": "application/vnd.ms-excel",
                        ".csv": "text/csv",
                    },
                    max_files=1,
                    on_drop=LuckyDrawState.set_excel_prize_file,
                ),
            ),
            rx.cond(
                LuckyDrawState.prize_selected_file_name != "",
                rx.hstack(
                    rx.icon(tag="file-text", size=14, color=GOLD),
                    rx.text(
                        LuckyDrawState.prize_selected_file_name,
                        color=GOLD,
                        font_size="0.78rem",
                        flex="1",
                    ),
                    rx.button(
                        "Import Prizes",
                        on_click=LuckyDrawState.process_excel_prize_upload,
                        bg=GOLD,
                        color=BLACK,
                        size="1",
                        is_loading=LuckyDrawState.is_loading,
                    ),
                    width="100%",
                    align="center",
                    spacing="2",
                    background=f"{GOLD}15",
                    border_radius="8px",
                    padding="0.6em",
                ),
                rx.text(
                    "Excel columns: Name (required), Value (optional), Image URL (optional).",
                    color="gray",
                    font_size="0.72rem",
                ),
            ),
            rx.text(
                "For single or manually entered prizes, use the advanced prize configuration below.",
                color="gray",
                font_size="0.72rem",
            ),
            spacing="4",
            width="100%",
        ),
        background=DARK_GRAY,
        border="1px solid rgba(212, 175, 55, 0.35)",
        border_radius="14px",
        padding=["1em", "1.25em"],
        width="100%",
    )


def _winner_history():
    """Compact recent-winners section."""
    return rx.cond(
        LuckyDrawState.winners_list.length() > 0,
        rx.card(
            rx.vstack(
                rx.hstack(
                    rx.hstack(
                        rx.icon(tag="crown", size=17, color=GOLD),
                        rx.heading("Recent Winners", size="3", color="white"),
                        spacing="2",
                    ),
                    rx.spacer(),
                    rx.button(
                        rx.hstack(
                            rx.icon(tag="download", size=13),
                            rx.text("Export"),
                            spacing="1",
                        ),
                        on_click=LuckyDrawState.download_winner_list,
                        variant="outline",
                        border_color=GOLD,
                        color=GOLD,
                        size="1",
                    ),
                    rx.button(
                        rx.hstack(
                            rx.icon(tag="trash-2", size=13),
                            rx.text("Clear"),
                            spacing="1",
                        ),
                        on_click=LuckyDrawState.clear_winners_history,
                        variant="outline",
                        border_color="red.500",
                        color="red.500",
                        size="1",
                    ),
                    width="100%",
                    align="center",
                    wrap="wrap",
                ),
                rx.vstack(
                    rx.foreach(
                        LuckyDrawState.winners_list[:10],
                        lambda winner: rx.hstack(
                            rx.icon(tag="crown", size=13, color=GOLD),
                            rx.text(
                                winner.get("name", "Unknown"),
                                color="white",
                                weight="bold",
                                font_size="0.8rem",
                            ),
                            rx.spacer(),
                            rx.text(
                                winner.get("prize_name", ""),
                                color=GOLD,
                                font_size="0.75rem",
                            ),
                            width="100%",
                            padding="0.45em 0.6em",
                            background=BLACK,
                            border_radius="7px",
                        ),
                    ),
                    width="100%",
                    max_height="220px",
                    overflow="auto",
                    spacing="2",
                ),
                spacing="3",
                width="100%",
            ),
            background=DARK_GRAY,
            border="1px solid rgba(212, 175, 55, 0.25)",
            border_radius="14px",
            padding="1em",
            width="100%",
        ),
        rx.fragment(),
    )


def _prize_configuration_dialog():
    """Render the existing prize manager in a dedicated configuration dialog."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.hstack(
                    rx.icon(tag="gift", size=22, color=GOLD),
                    rx.heading("Prize Configuration", size="5", color=GOLD),
                    spacing="2",
                ),
                rx.divider(),
                lucky_draw_manager(),
                rx.hstack(
                    rx.button(
                        "Close",
                        on_click=LuckyDrawState.close_new_draw_dialog,
                        variant="outline",
                        border_color=GOLD,
                        color=GOLD,
                        flex="1",
                    ),
                    spacing="2",
                    width="100%",
                ),
                spacing="4",
                padding="1.2em",
                width="100%",
            ),
            background=DARK_GRAY,
            border=f"2px solid {GOLD}",
            border_radius="15px",
            max_width="760px",
            width="95%",
        ),
        open=LuckyDrawState.lucky_draw_show_new_draw_dialog,
    )


def _advanced_prize_setup():
    """Keep the existing prize manager available without making it the main UI."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon(tag="settings", size=17, color=GOLD),
                rx.heading("Advanced Prize Configuration", size="3", color="white"),
                spacing="2",
                width="100%",
            ),
            rx.text(
                "Use the existing prize manager for single prizes or manual multiple-prize entry.",
                color=LIGHT_GRAY,
                font_size="0.75rem",
            ),
            rx.button(
                rx.hstack(
                    rx.icon(tag="settings", size=14),
                    rx.text("Open Prize Configuration"),
                    spacing="2",
                ),
                on_click=LuckyDrawState.open_new_draw_dialog,
                variant="outline",
                border_color=GOLD,
                color=GOLD,
                width="100%",
            ),
            spacing="3",
            width="100%",
        ),
        background=DARK_GRAY,
        border="1px solid rgba(212, 175, 55, 0.2)",
        border_radius="14px",
        padding="1em",
        width="100%",
    )


def lucky_draw_page():
    """Lucky Draw administration dashboard."""
    return rx.box(
        rx.container(
            rx.vstack(
                # Header ------------------------------------------------------
                rx.hstack(
                    rx.vstack(
                        rx.hstack(
                            rx.icon(tag="gift", size=25, color=GOLD),
                            rx.heading(
                                "Lucky Draw Dashboard",
                                size="7",
                                color="white",
                                font_size=["1.55rem", "2rem", "2.35rem"],
                            ),
                            spacing="3",
                        ),
                        rx.hstack(
                            rx.text(
                                LuckyDrawState.lucky_draw_event_name,
                                color=LIGHT_GRAY,
                                font_size=["0.82rem", "0.9rem", "1rem"],
                            ),
                            rx.badge(
                                "LIVE",
                                color_scheme="green",
                                variant="soft",
                                size="1",
                            ),
                            spacing="2",
                        ),
                        spacing="1",
                        align="start",
                    ),
                    rx.spacer(),
                    rx.button(
                        rx.hstack(
                            rx.icon(tag="arrow-left", size=14),
                            rx.text("Back to Event"),
                            spacing="2",
                        ),
                        on_click=rx.redirect(
                            f"/dashboard/{LuckyDrawState.current_event_id}"
                        ),
                        variant="outline",
                        border_color=GOLD,
                        color=GOLD,
                        size="2",
                    ),
                    width="100%",
                    align="center",
                    wrap="wrap",
                ),

                # Setup cards -------------------------------------------------
                rx.grid(
                    _guest_list_card(),
                    _prize_list_card(),
                    columns=["1fr", "1fr"],
                    spacing="4",
                    width="100%",
                ),

                # Statistics --------------------------------------------------
                rx.grid(
                    _stat_card(
                        "Guests",
                        LuckyDrawState.lucky_draw_eligible_count,
                        "users",
                        background="#FFF8D9",
                    ),
                    _stat_card(
                        "Prizes",
                        _prize_count(),
                        "gift",
                        background="#F4F4F4",
                    ),
                    _stat_card(
                        "Winners",
                        LuckyDrawState.winners_list.length(),
                        "crown",
                        background="#E8F6EA",
                    ),
                    columns=["1fr", "1fr", "1fr"],
                    spacing="4",
                    width="100%",
                ),

                # Main action -------------------------------------------------
                rx.card(
                    rx.vstack(
                        rx.heading(
                            "Ready to Start?",
                            size="5",
                            color="white",
                        ),
                        rx.text(
                            "When setup is complete, open the dedicated display screen for the event audience.",
                            color=LIGHT_GRAY,
                            text_align="center",
                            font_size="0.82rem",
                        ),
                        rx.button(
                            rx.hstack(
                                rx.icon(tag="monitor", size=19),
                                rx.text("START DISPLAY SCREEN"),
                                spacing="2",
                            ),
                            on_click=LuckyDrawState.setup_complete_and_go_to_display,
                            bg=GOLD,
                            color=BLACK,
                            width="100%",
                            size="3",
                            padding="1em",
                            _hover={
                                "transform": "translateY(-1px)",
                            },
                        ),
                        spacing="3",
                        width="100%",
                        align="center",
                    ),
                    background=DARK_GRAY,
                    border=f"1px solid {GOLD}",
                    border_radius="14px",
                    padding=["1em", "1.4em"],
                    width="100%",
                ),

                _advanced_prize_setup(),
                _winner_history(),
                _prize_configuration_dialog(),

                # Existing guest upload dialog remains available through the
                # normal event dashboard and is rendered here so its state is
                # not lost if this page is later used as the upload entry point.
                upload_dialog.upload_dialog(),

                spacing="5",
                width="100%",
                max_width="1200px",
                padding=["1em", "1.5em", "2em"],
            ),
            width="100%",
            max_width="1200px",
        ),
        width="100%",
        min_height="100vh",
        background=BLACK,
        padding="12px",
    )
