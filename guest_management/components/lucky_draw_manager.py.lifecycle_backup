# components/lucky_draw_manager.py
import reflex as rx
from guest_management.state import State, GOLD, BLACK, DARK_GRAY, LuckyDrawState


def single_prize_section():
    """Single Prize Mode - Independent"""
    return rx.vstack(
        rx.vstack(
            rx.hstack(rx.icon(tag="link", size=14, color=GOLD),
                      rx.text("Prize Image URL", color="white", weight="bold"), spacing="2"),
            rx.input(
                placeholder="https://example.com/prize-image.jpg",
                value=LuckyDrawState.single_prize_picture,
                on_change=LuckyDrawState.set_single_prize_picture,
                width="100%", bg=BLACK, border_color=GOLD, color="white",
            ),
            rx.cond(LuckyDrawState.single_prize_picture,
                    rx.image(src=LuckyDrawState.single_prize_picture, width="80px", height="80px", object_fit="cover",
                             border_radius="8px", border=f"1px solid {GOLD}"),
                    rx.fragment()
                    ),
            width="100%",
        ),
        rx.input(
            placeholder="Prize Name (e.g., iPhone 15)",
            value=LuckyDrawState.single_prize_name,
            on_change=LuckyDrawState.set_single_prize_name,
            width="100%", bg=BLACK, border_color=GOLD, color="white",
        ),
        rx.input(
            placeholder="Prize Value (optional)",
            value=LuckyDrawState.single_prize_value,
            on_change=LuckyDrawState.set_single_prize_value,
            width="100%", bg=BLACK, border_color=GOLD, color="white",
        ),
        rx.button(
            rx.hstack(rx.icon(tag="refresh_ccw", size=14), rx.text("Clear Prize")),
            on_click=LuckyDrawState.clear_single_prize,
            variant="outline", border_color=GOLD, color=GOLD, width="100%",
        ),
        width="100%", spacing="3",
    )


def multiple_prizes_section():
    """Multiple Prizes Mode - Manual Entry"""
    return rx.vstack(
        rx.hstack(
            rx.heading(f"Prizes ({LuckyDrawState.multiple_prizes_list.length()})", size="3", color=GOLD),
            rx.spacer(),
            rx.button(rx.hstack(rx.icon(tag="plus", size=14), rx.text("Add Prize")), on_click=LuckyDrawState.add_multiple_prize,
                      bg=GOLD, color=BLACK),
            rx.button(rx.hstack(rx.icon(tag="trash-2", size=14), rx.text("Clear All")),
                      on_click=LuckyDrawState.clear_multiple_prizes, variant="outline", border_color="red", color="red"),
            width="100%",
        ),
        rx.cond(
            LuckyDrawState.multiple_prizes_list.length() > 0,
            rx.box(
                rx.vstack(
                    rx.foreach(
                        LuckyDrawState.multiple_prizes_list,
                        lambda prize, idx: rx.card(
                            rx.vstack(
                                rx.hstack(
                                    rx.badge(rx.cond(idx < 9, f"0{idx + 1}", f"{idx + 1}"), color_scheme="gold"),
                                    rx.text(prize.get("name", f"Prize {idx + 1}"), color=GOLD, weight="bold", flex="1"),
                                    rx.button(rx.icon(tag="x", size=14),
                                              on_click=lambda: LuckyDrawState.remove_multiple_prize(idx), variant="ghost",
                                              color="red"),
                                    width="100%",
                                ),
                                rx.divider(),
                                rx.vstack(
                                    rx.hstack(rx.icon(tag="image", size=12, color=GOLD),
                                              rx.text("Image URL", color="gray"), spacing="1"),
                                    rx.input(value=prize.get("image_url", ""),
                                             on_change=lambda v: LuckyDrawState.update_multiple_prize_field(idx, "image_url", v),
                                             width="100%", bg=BLACK, border_color=GOLD),
                                    rx.cond(prize.get("image_url"),
                                            rx.image(src=prize["image_url"], width="60px", height="60px",
                                                     object_fit="cover", border_radius="6px"), rx.fragment()),
                                    width="100%", spacing="1",
                                ),
                                rx.input(placeholder="Prize Name", value=prize.get("name", ""),
                                         on_change=lambda v: LuckyDrawState.update_multiple_prize_field(idx, "name", v),
                                         width="100%", bg=BLACK, border_color=GOLD),
                                rx.input(placeholder="Prize Value", value=prize.get("value", ""),
                                         on_change=lambda v: LuckyDrawState.update_multiple_prize_field(idx, "value", v),
                                         width="100%", bg=BLACK, border_color=GOLD),
                                spacing="3", width="100%",
                            ),
                            bg=DARK_GRAY, padding="1.2em", width="100%", margin_bottom="0.5em",
                        ),
                    ),
                    width="100%", spacing="3",
                ),
                width="100%", max_height="500px", overflow_y="auto",
            ),
            rx.center(rx.text("Click 'Add Prize' to add prizes", color="gray"), padding="2em"),
        ),
        width="100%", spacing="3",
    )


def excel_prize_section():
    """Excel Prizes Mode - Upload Only with image preview"""
    return rx.vstack(
        rx.vstack(
            rx.hstack(
                rx.upload(
                    rx.button(
                        rx.hstack(rx.icon(tag="file-spreadsheet", size=14), rx.text("Select Excel File")),
                        bg=GOLD, color=BLACK
                    ),
                    id="prize_excel_upload", multiple=False,
                    accept={".xlsx": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            ".xls": "application/vnd.ms-excel",
                            ".csv": "text/csv"},
                    max_files=1, border="1px dashed #D4AF37", padding="1em",
                    on_drop=LuckyDrawState.set_excel_prize_file,
                ),
                rx.button(
                    rx.hstack(rx.icon(tag="upload", size=14), rx.text("Process")),
                    on_click=LuckyDrawState.process_excel_prize_upload,
                    bg=GOLD, color=BLACK,
                    is_disabled=~LuckyDrawState.prize_selected_file_name
                ),
                spacing="2",
            ),
            rx.cond(
                LuckyDrawState.prize_selected_file_name,
                rx.hstack(
                    rx.icon(tag="file-text", size=14, color=GOLD),
                    rx.text(LuckyDrawState.prize_selected_file_name, color=GOLD),
                    rx.button(rx.icon(tag="x", size=12), on_click=LuckyDrawState.clear_excel_prize_file, variant="ghost", color="gray"),
                    spacing="2", bg=f"{GOLD}22", padding="0.5em 1em", border_radius="8px", width="100%",
                ),
                rx.text("No file selected. Choose an Excel file with 'Name' column.", color="gray", font_size="0.8rem"),
            ),
            width="100%",
        ),

        rx.button(
            rx.hstack(rx.icon(tag="trash-2", size=14), rx.text("Clear All Excel Prizes")),
            on_click=LuckyDrawState.clear_excel_prizes,
            variant="outline", border_color="red", color="red",
        ),

        # Show loaded prizes with images
        rx.cond(
            LuckyDrawState.excel_prizes_list.length() > 0,
            rx.vstack(
                rx.hstack(
                    rx.icon(tag="check", color="green"),
                    rx.text(f"Loaded: {LuckyDrawState.excel_filename} ({LuckyDrawState.excel_prizes_list.length()} prizes)", color="green"),
                    spacing="2",
                ),
                rx.text("Prizes loaded (first 5 shown):", color=GOLD, weight="bold", font_size="0.8rem"),
                rx.vstack(
                    rx.foreach(
                        LuckyDrawState.excel_prizes_list[:5],
                        lambda prize: rx.hstack(
                            # Prize Image
                            rx.cond(
                                prize.get("image_url") & prize.get("image_url") != "",
                                rx.image(
                                    src=prize["image_url"],
                                    width="50px", height="50px",
                                    object_fit="cover", border_radius="8px",
                                    border=f"1px solid {GOLD}",
                                ),
                                rx.box(
                                    rx.icon(tag="image", size=20, color="gray"),
                                    width="50px", height="50px",
                                    display="flex", align_items="center", justify_content="center",
                                    bg=BLACK, border_radius="8px", border="1px dashed gray"
                                )
                            ),
                            # Prize Info
                            rx.vstack(
                                rx.text(prize.get("name", "Unnamed"), color="white", weight="bold"),
                                rx.cond(prize.get("value"), rx.text(prize["value"], color=GOLD, font_size="0.7rem"), rx.fragment()),
                                spacing="0", align="start",
                            ),
                            spacing="2", width="100%", padding="0.5em",
                            border_bottom="1px solid rgba(212, 175, 55, 0.2)",
                        ),
                    ),
                    spacing="1",
                ),
                width="100%", max_height="250px", overflow="auto",
            ),
            rx.fragment(),
        ),

        rx.text("Excel columns: 'Name' (required), 'Value' (optional), 'Image URL' (optional)",
                color="gray", size="1"),
        width="100%", spacing="3",
    )


def lucky_draw_manager():
    """Complete lucky draw manager - Independent modes"""
    return rx.vstack(
        # Mode Selection - Using Buttons
        rx.hstack(
            rx.text("Prize Mode:", color="white", weight="bold"),
            rx.hstack(
                rx.button(
                    "Single Prize",
                    on_click=LuckyDrawState.set_prize_mode("single"),
                    bg=rx.cond(LuckyDrawState.prize_mode == "single", GOLD, DARK_GRAY),
                    color=rx.cond(LuckyDrawState.prize_mode == "single", BLACK, GOLD),
                    border=f"1px solid {GOLD}",
                    _hover={"bg": GOLD, "color": BLACK},
                ),
                rx.button(
                    "Multiple Prizes",
                    on_click=LuckyDrawState.set_prize_mode("multiple"),
                    bg=rx.cond(LuckyDrawState.prize_mode == "multiple", GOLD, DARK_GRAY),
                    color=rx.cond(LuckyDrawState.prize_mode == "multiple", BLACK, GOLD),
                    border=f"1px solid {GOLD}",
                    _hover={"bg": GOLD, "color": BLACK},
                ),
                rx.button(
                    "Excel Upload",
                    on_click=LuckyDrawState.set_prize_mode("excel"),
                    bg=rx.cond(LuckyDrawState.prize_mode == "excel", GOLD, DARK_GRAY),
                    color=rx.cond(LuckyDrawState.prize_mode == "excel", BLACK, GOLD),
                    border=f"1px solid {GOLD}",
                    _hover={"bg": GOLD, "color": BLACK},
                ),
                spacing="2",
            ),
            spacing="3", width="100%",
        ),

        rx.divider(),

        # Single Prize Mode - Independent
        rx.cond(LuckyDrawState.prize_mode == "single", single_prize_section()),

        # Multiple Prizes Mode - Independent
        rx.cond(LuckyDrawState.prize_mode == "multiple", multiple_prizes_section()),

        # Excel Upload Mode - Independent
        rx.cond(LuckyDrawState.prize_mode == "excel", excel_prize_section()),

        spacing="4", width="100%",
    )