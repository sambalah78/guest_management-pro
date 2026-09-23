# guest_management/pages/lucky_draw.py
"""Lucky Draw dashboard page."""

import reflex as rx

from ..state import LuckyDrawState
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
    """Show the participant source used by this event's Lucky Draw."""
    return rx.card(
        rx.vstack(
            _section_header(
                "users",
                rx.cond(
                    LuckyDrawState.lucky_draw_uses_attendance,
                    "Event Guest List",
                    "Participant List",
                ),
                LuckyDrawState.lucky_draw_source_label,
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
                        rx.cond(
                            LuckyDrawState.lucky_draw_uses_attendance,
                            "Checked-in guests eligible",
                            "Participants eligible",
                        ),
                        color=LIGHT_GRAY,
                        font_size="0.8rem",
                    ),
                    spacing="0",
                    align="start",
                ),
                rx.spacer(),
                rx.button(
                    rx.hstack(
                        rx.icon(tag="refresh-cw", size=16),
                        rx.text("Refresh"),
                        spacing="2",
                    ),
                    on_click=LuckyDrawState.load_lucky_draw_eligible_guests,
                    variant="outline",
                    border_color=GOLD,
                    color=GOLD,
                    size="2",
                ),
            ),
            rx.cond(
                LuckyDrawState.lucky_draw_uses_attendance,
                rx.vstack(
                    rx.hstack(
                        rx.switch(
                            checked=LuckyDrawState.lucky_draw_only_present,
                            on_change=LuckyDrawState.set_lucky_draw_only_present,
                            color_scheme="amber",
                        ),
                        rx.vstack(
                            rx.text(
                                rx.cond(
                                    LuckyDrawState.lucky_draw_only_present,
                                    "Only include checked-in guests",
                                    "Include all guests (including absent)",
                                ),
                                color="white",
                                font_weight="700",
                                font_size="0.78rem",
                            ),
                            rx.text(
                                "Uses the guest list uploaded on the Dashboard.",
                                color=LIGHT_GRAY,
                                font_size="0.68rem",
                            ),
                            spacing="0",
                        ),
                        spacing="2",
                        width="100%",
                        align="center",
                    ),
                    rx.text(
                        "The Lucky Draw uses the same guest records imported from the Dashboard Excel upload. Turn the switch off to include guests who did not check in.",
                        color=LIGHT_GRAY,
                        font_size="0.72rem",
                    ),
                    rx.button(
                        rx.hstack(
                            rx.icon(tag="upload", size=15),
                            rx.text("Manage Guest List"),
                            spacing="2",
                        ),
                        on_click=rx.redirect(
                            f"/dashboard/{LuckyDrawState.current_event_id}"
                        ),
                        bg=GOLD,
                        color=BLACK,
                        size="2",
                        width="100%",
                    ),
                    spacing="2",
                    width="100%",
                ),
                rx.vstack(
                    rx.text(
                        "Upload the participant file supplied by the client. No check-in is required for a standalone Lucky Draw.",
                        color=LIGHT_GRAY,
                        font_size="0.72rem",
                    ),
                    rx.button(
                        rx.hstack(
                            rx.icon(tag="upload", size=15),
                            rx.text("Import Participant File"),
                            spacing="2",
                        ),
                        on_click=LuckyDrawState.open_participant_import,
                        bg=GOLD,
                        color=BLACK,
                        size="2",
                        width="100%",
                    ),
                    spacing="2",
                    width="100%",
                ),
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

def _pre_draw_winner_upload_dialog():
    """Render the pre-draw winner upload dialog."""
    return rx.dialog.root(
        rx.dialog.trigger(
            rx.button(
                rx.hstack(
                    rx.icon(tag="upload", size=15),
                    rx.text("Upload / Manage"),
                    spacing="2",
                ),
                bg=GOLD,
                color=BLACK,
                size="2",
            ),
        ),
        rx.button(
            rx.hstack(
                rx.icon(tag="trash_2", size=16),
                rx.text("CLEAR LIST"),
                spacing="2",
            ),
            on_click=LuckyDrawState.clear_pre_draw_winners,
            variant="outline",
            border_color="red.500",
            color="red.400",
            size="2",
        ),
        rx.dialog.content(
            rx.vstack(
                rx.hstack(
                    rx.icon(
                        tag="trophy",
                        size=22,
                        color=GOLD,
                    ),
                    rx.heading(
                        "Upload Predetermined Winners",
                        size="5",
                        color=GOLD,
                    ),
                    spacing="2",
                    align="center",
                ),

                rx.text(
                    "Upload the Excel file containing guests who have "
                    "already won preliminary prizes.",
                    color=LIGHT_GRAY,
                    font_size="0.82rem",
                ),

                rx.divider(),

                rx.upload(
                    rx.vstack(
                        rx.icon(
                            tag="file-spreadsheet",
                            size=30,
                            color=GOLD,
                        ),
                        rx.text(
                            "Select Excel File",
                            color="white",
                            font_weight="700",
                        ),
                        rx.text(
                            "Drag and drop or click to browse",
                            color=LIGHT_GRAY,
                            font_size="0.72rem",
                        ),
                        spacing="2",
                        align="center",
                        justify="center",
                        width="100%",
                        padding="2em",
                    ),
                    id="pre_draw_winner_excel_upload",
                    multiple=False,
                    accept={
                        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": [".xlsx"],
                        "application/vnd.ms-excel": [".xls"],
                        "application/vnd.ms-excel.sheet.macroEnabled.12": [".xlsm"],
                    },
                    max_files=1,
                    on_drop=LuckyDrawState.set_pre_draw_winner_file,
                    border=f"1px dashed {GOLD}",
                    border_radius="10px",
                    width="100%",
                ),

                rx.cond(
                    LuckyDrawState.pre_draw_winner_selected_file_name != "",
                    rx.hstack(
                        rx.icon(
                            tag="file-text",
                            size=16,
                            color=GOLD,
                        ),
                        rx.text(
                            LuckyDrawState.pre_draw_winner_selected_file_name,
                            color=GOLD,
                            font_size="0.82rem",
                            flex="1",
                        ),
                        rx.button(
                            rx.icon(
                                tag="x",
                                size=14,
                            ),
                            on_click=(
                                LuckyDrawState.clear_pre_draw_winner_file
                            ),
                            variant="outline",
                            border_color=GOLD,
                            color=GOLD,
                            size="1",
                        ),
                        width="100%",
                        align="center",
                        spacing="2",
                        background=f"{GOLD}15",
                        border_radius="8px",
                        padding="0.7em",
                    ),
                    rx.text(
                        "No file selected.",
                        color="gray",
                        font_size="0.72rem",
                    ),
                ),

                rx.vstack(
                    rx.text(
                        "Required: Name, Guest ID",
                        color="white",
                        font_size="0.75rem",
                        font_weight="600",
                    ),
                    rx.text(
                        "Optional: Prize, Value, Image URL",
                        color=LIGHT_GRAY,
                        font_size="0.72rem",
                    ),
                    rx.text(
                        "Uploading a new file replaces the existing "
                        "pre-draw winner list.",
                        color="gray",
                        font_size="0.7rem",
                    ),
                    spacing="1",
                    align="start",
                    width="100%",
                ),

                rx.hstack(
                    rx.button(
                        "Cancel",
                        on_click=LuckyDrawState.close_pre_draw_upload_dialog,
                        variant="outline",
                        border_color=GOLD,
                        color=GOLD,
                        size="2",
                    ),
                    rx.button(
                        rx.hstack(
                            rx.icon(
                                tag="upload",
                                size=15,
                            ),
                            rx.text("Import Winners"),
                            spacing="2",
                        ),
                        on_click=(
                            LuckyDrawState.process_pre_draw_winner_upload
                        ),
                        bg=GOLD,
                        color=BLACK,
                        size="2",
                    ),
                    justify="end",
                    width="100%",
                    spacing="2",
                ),

                spacing="4",
                width="100%",
            ),
            background=DARK_GRAY,
            border=f"1px solid {GOLD}",
            border_radius="14px",
            padding="1.5em",
            max_width="600px",
            width="95%",
        ),
        open=LuckyDrawState.pre_draw_upload_dialog_open,
        on_open_change=LuckyDrawState.set_pre_draw_upload_dialog_open,
    )


def _pre_draw_winner_card():
    """Pre-draw winner management card."""
    return rx.card(
        rx.vstack(
            _section_header(
                "trophy",
                "Pre-Draw Winners",
                "Manage guests who have already won preliminary prizes.",
            ),

            rx.divider(),

            rx.hstack(
                rx.vstack(
                    rx.text(
                        LuckyDrawState.pre_draw_winner_count,
                        color=GOLD,
                        font_size=["2rem", "2.4rem"],
                        weight="bold",
                    ),
                    rx.text(
                        "Pre-draw winners",
                        color=LIGHT_GRAY,
                        font_size="0.8rem",
                    ),
                    spacing="0",
                    align="start",
                ),
                rx.spacer(),
_pre_draw_winner_upload_dialog(),
                width="100%",
                align="center",
            ),

            rx.cond(
                LuckyDrawState.pre_draw_winner_filename != "",
                rx.hstack(
                    rx.icon(
                        tag="file-text",
                        size=15,
                        color=GOLD,
                    ),
                    rx.vstack(
                        rx.text(
                            "Imported file",
                            color=LIGHT_GRAY,
                            font_size="0.68rem",
                        ),
                        rx.text(
                            LuckyDrawState.pre_draw_winner_filename,
                            color=GOLD,
                            font_size="0.8rem",
                            font_weight="600",
                        ),
                        spacing="0",
                        align="start",
                        flex="1",
                    ),
                    width="100%",
                    align="center",
                    spacing="2",
                    background=f"{GOLD}15",
                    border_radius="8px",
                    padding="0.7em",
                ),
                rx.text(
                    "No pre-draw winner file imported yet.",
                    color="gray",
                    font_size="0.72rem",
                ),
            ),

            rx.button(
                rx.hstack(
                    rx.icon(
                        tag="monitor",
                        size=16,
                    ),
                    rx.text("Open Pre-Draw Display"),
                    spacing="2",
                ),
                on_click=rx.redirect(
                    f"/lucky-draw/pre-draw-display?event_id={LuckyDrawState.current_event_id}"
                ),
                variant="outline",
                border_color=GOLD,
                color=GOLD,
                size="2",
                width="100%",
            ),

            rx.text(
                "The public display shows the event information and "
                "pre-draw winner table.",
                color="gray",
                font_size="0.7rem",
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
                rx.button(
                    rx.hstack(
                        rx.icon(tag="trash_2", size=16),
                        rx.text("CLEAR LIST"),
                        spacing="2",
                    ),
                    on_click=LuckyDrawState.clear_excel_prizes,
                    variant="outline",
                    border_color="red.500",
                    color="red.400",
                    size="2",
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


def _clear_history_dialog():
    """Confirmation dialog for clearing persisted winner history."""
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.icon(tag="triangle-alert", size=40, color="red.400"),
                rx.heading("Clear Winner History", size="5", color="red.400"),
                rx.text("Remove all confirmed winners for this event?", color="white", text_align="center"),
                rx.text("This cannot be undone.", color=LIGHT_GRAY, size="2"),
                rx.hstack(
                    rx.button("Cancel", on_click=LuckyDrawState.cancel_clear_winners, variant="outline", border_color=GOLD, color=GOLD, flex="1"),
                    rx.button("Clear All", on_click=LuckyDrawState.confirm_clear_winners, background="red.500", color="white", flex="1", disabled=LuckyDrawState.is_loading),
                    spacing="3", width="100%",
                ),
                spacing="4", padding="1.5em", align="center",
            ),
            background=DARK_GRAY, border="2px solid red", border_radius="15px", max_width="400px", width="90%",
        ),
        open=LuckyDrawState.show_clear_confirm,
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


def _pre_draw_prize_card():
    """Configure prizes for system-generated random Pre-Draw."""
    return rx.card(
        rx.vstack(
            rx.hstack(
                rx.icon(
                    tag="sparkles",
                    size=18,
                    color=GOLD,
                ),
                rx.vstack(
                    rx.heading(
                        "Random Pre-Draw",
                        size="3",
                        color="white",
                    ),
                    rx.text(
                        "Configure prizes and generate winners before the event.",
                        color=LIGHT_GRAY,
                        font_size="0.72rem",
                    ),
                    spacing="0",
                    align="start",
                ),
                width="100%",
                spacing="2",
            ),

            rx.divider(),

            rx.input(
                placeholder="Prize name",
                value=LuckyDrawState.pre_draw_prize_name,
                on_change=LuckyDrawState.set_pre_draw_prize_name,
                width="100%",
            ),

            rx.hstack(
                rx.input(
                    placeholder="Value",
                    value=LuckyDrawState.pre_draw_prize_value,
                    on_change=LuckyDrawState.set_pre_draw_prize_value,
                    width="100%",
                ),
                rx.input(
                    placeholder="Winner count",
                    type="number",
                    min="1",
                    value=LuckyDrawState.pre_draw_prize_winner_count,
                    on_change=LuckyDrawState.set_pre_draw_prize_winner_count,
                    width="100%",
                ),
                width="100%",
                spacing="2",
            ),

            rx.input(
                placeholder="Image URL (optional)",
                value=LuckyDrawState.pre_draw_prize_image_url,
                on_change=LuckyDrawState.set_pre_draw_prize_image_url,
                width="100%",
            ),

            rx.button(
                rx.hstack(
                    rx.icon(tag="plus", size=14),
                    rx.text("Add Pre-Draw Prize"),
                    spacing="2",
                ),
                on_click=LuckyDrawState.add_pre_draw_prize,
                bg=GOLD,
                color=BLACK,
                width="100%",
            ),

            rx.vstack(
                rx.foreach(
                    LuckyDrawState.pre_draw_prizes,
                    lambda prize: rx.hstack(
                        rx.vstack(
                            rx.text(
                                prize["name"],
                                color="white",
                                font_weight="700",
                            ),
                            rx.text(
                                prize["winner_count"].to_string()
                                + " winner(s)",
                                color=LIGHT_GRAY,
                                font_size="0.68rem",
                            ),
                            rx.badge(
                                prize["status"],
                                color_scheme="amber",
                                size="1",
                            ),
                            spacing="1",
                            align="start",
                        ),
                        rx.spacer(),
                        rx.button(
                            "Archive",
                            on_click=LuckyDrawState.archive_pre_draw_prize(
                                prize["id"]
                            ),
                            variant="outline",
                            border_color=GOLD,
                            color=GOLD,
                            size="1",
                        ),
                        width="100%",
                        align="center",
                        padding="0.65em",
                        background=f"{GOLD}10",
                        border_radius="8px",
                    ),
                ),
                spacing="2",
                width="100%",
            ),

            rx.text(
                rx.cond(
                    LuckyDrawState.pre_draw_winner_count > 0,
                    "Winners already exist. Use CLEAR LIST before running a new random Pre-Draw.",
                    "Random selection uses the uploaded guest list and does not require check-in.",
                ),
                color="gray",
                font_size="0.68rem",
            ),

            rx.button(
                rx.hstack(
                    rx.icon(tag="shuffle", size=15),
                    rx.text("Generate Random Winners"),
                    spacing="2",
                ),
                on_click=LuckyDrawState.generate_random_pre_draw,
                bg=GOLD,
                color=BLACK,
                width="100%",
                disabled=(
                    (LuckyDrawState.pre_draw_prize_count == 0)
                    | (LuckyDrawState.pre_draw_winner_count > 0)
                    | LuckyDrawState.pre_draw_generating
                ),
            ),

            spacing="3",
            width="100%",
        ),
        background=DARK_GRAY,
        border="1px solid rgba(212, 175, 55, 0.35)",
        border_radius="14px",
        padding=["1em", "1.25em"],
        width="100%",
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
                                rx.cond(
                                    LuckyDrawState.lucky_draw_uses_attendance,
                                    "ATTENDANCE LINKED",
                                    "NO CHECK-IN",
                                ),
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
                    rx.cond(
                        LuckyDrawState.pre_draw_enabled,
                        _pre_draw_winner_card(),
                        rx.fragment(),
                    ),
                    rx.cond(
                        LuckyDrawState.pre_draw_enabled,
                        _pre_draw_prize_card(),
                        rx.fragment(),
                    ),
                    _prize_list_card(),
                    columns=rx.breakpoints(
                        initial="1fr",
                        lg="repeat(2, minmax(0, 1fr))",
                    ),
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
                    columns="repeat(3, minmax(0, 1fr))",
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
                        rx.cond(
                            LuckyDrawState.lucky_draw_uses_attendance,
                            rx.text(
                                "The display will use the latest checked-in attendance from this event. The invitation guest list remains the source of participant records.",
                                color=LIGHT_GRAY,
                                text_align="center",
                                font_size="0.82rem",
                            ),
                            rx.text(
                                "The display will use the complete client-supplied participant list. No event-day check-in is required.",
                                color=LIGHT_GRAY,
                                text_align="center",
                                font_size="0.82rem",
                            ),
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
                        rx.button(
                            rx.hstack(
                                rx.icon(tag="monitor", size=18),
                                rx.text("OPEN HALL SCREEN"),
                                spacing="2",
                            ),
                            on_click=LuckyDrawState.open_hall_screen,
                            variant="outline",
                            border_color=GOLD,
                            color=GOLD,
                            width="100%",
                            size="3",
                            padding="1em",
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
                _clear_history_dialog(),
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
        min_height="100vh",
        background=BLACK,
        padding="12px",
    )
