# guest_management/pages/dashboard.py
import reflex as rx

from guest_management.pages import page_layout_dashboard
from guest_management.state import State, ScannerState, LuckyDrawState, EventState, UIState, EmailState, AuthState, \
    VoucherState, GuestState

from guest_management.utils.constants import GOLD, BLACK, DARK_GRAY, LIGHT_GRAY
from guest_management.components.stat_card import stat_card
from guest_management.components import (
    upload_dialog,
    clear_table_dialog,
    event_qr_dialog,
    guest_qr_dialog,
    email_dialog,
    email_management,
    transaction_history,
)
from guest_management.styles.theme import button_style, outline_button_style


def render_cell(col: str, guest: dict):
    """Render a table cell with column-aware styling."""
    value = guest.get(col, "")

    # Use rx.cond for ALL conditional rendering - col is a Var in rx.foreach
    return rx.cond(
        col == "Status",
        rx.badge(
            value,
            color_scheme=rx.cond(value == "Present", "green", "red"),
            radius="full",
            variant="soft",
            style={"fontSize": "clamp(0.65rem, 2vw, 0.95rem)"},
        ),
        rx.cond(
            col == "Email Sent",
            rx.cond(
                guest.get("email_sent", False),
                rx.hstack(
                    rx.icon(tag="circle_check", color="green", size=16,
                            style={"width": "clamp(12px, 2vw, 20px)", "height": "clamp(12px, 2vw, 20px)"}),
                    rx.text("Sent", color="green",
                            style={"fontSize": "clamp(0.6rem, 1.8vw, 0.9rem)"}),
                    spacing="1",
                ),
                rx.hstack(
                    rx.icon(tag="circle_x", color="gray", size=16,
                            style={"width": "clamp(12px, 2vw, 20px)", "height": "clamp(12px, 2vw, 20px)"}),
                    rx.text("Not Sent", color="gray",
                            style={"fontSize": "clamp(0.6rem, 1.8vw, 0.9rem)"}),
                    spacing="1",
                ),
            ),
            rx.cond(
                col == "Amount",
                rx.cond(
                    value != "",
                    rx.text(
                        value,
                        color=GOLD,
                        weight="bold",
                        style={"fontSize": "clamp(0.65rem, 2vw, 0.95rem)"},
                    ),
                    rx.text(
                        f"RM {guest.get('amount_value', 0):.2f}",
                        color=GOLD,
                        weight="bold",
                        style={"fontSize": "clamp(0.65rem, 2vw, 0.95rem)"},
                    ),
                ),
                rx.cond(
                    col == "Prize",
                    rx.cond(
                        value != "",
                        rx.hstack(
                            rx.icon(tag="crown", color=GOLD, size=14,
                                    style={"width": "clamp(10px, 1.8vw, 16px)", "height": "clamp(10px, 1.8vw, 16px)"}),
                            rx.text(value, color=GOLD, weight="bold",
                                    style={"fontSize": "clamp(0.6rem, 1.8vw, 0.9rem)"}),
                            spacing="1",
                        ),
                        rx.text(
                            "",
                            color="gray",
                            style={"fontSize": "clamp(0.65rem, 2vw, 0.95rem)"},
                        ),
                    ),
                    rx.text(
                        value,
                        color="gray",
                        style={"fontSize": "clamp(0.65rem, 2vw, 0.95rem)"},
                    ),
                ),
            ),
        ),
    )


def _checkin_alert_banner() -> rx.Component:
    """Appears at the top whenever State.last_checkin_name is set."""
    return rx.cond(
        ScannerState.last_checkin_name != "",
        rx.hstack(
            rx.icon(tag="user-check", size=18, color=BLACK),
            rx.text("✅  Checked in: ", weight="bold", color=BLACK, size="2"),
            rx.text(ScannerState.last_checkin_name, color=BLACK, weight="bold", size="2"),
            rx.cond(
                ScannerState.last_checkin_table != "",
                rx.text(f" — Table {ScannerState.last_checkin_table}", color=BLACK, size="2"),
                rx.fragment(),
            ),
            rx.spacer(),
            rx.button(
                rx.icon(tag="x", size=14),
                on_click=ScannerState.dismiss_checkin_alert,
                variant="ghost",
                size="1",
                color=BLACK,
                _hover={"bg": "#00000020"},
            ),
            width="100%",
            bg=GOLD,
            padding="0.4em 1em",
            align="center",
            spacing="2",
            style={"animation": "slideDown 0.35s ease-out forwards"},
        ),
        rx.fragment(),
    )


def _guest_table() -> rx.Component:
    """Render the guest table with proper structure."""
    return rx.cond(
        State.guest_data.length() > 0,
        rx.box(
            rx.table.root(
                rx.table.header(
                    rx.table.row(
                        rx.foreach(
                            State.columns,
                            lambda col: rx.table.column_header_cell(
                                col,
                                color=BLACK,
                                weight="bold",
                                padding="0.3em 0.5em",
                                style={
                                    "position": "sticky",
                                    "top": "0",
                                    "background": GOLD,
                                    "zIndex": "10",
                                    "whiteSpace": "nowrap",
                                    "fontSize": "clamp(0.6rem, 1.5vw, 0.8rem)",
                                    "borderBottom": f"2px solid {DARK_GRAY}",
                                    "minWidth": "80px",
                                }
                            )
                        ),
                        rx.table.column_header_cell(
                            "Actions",
                            color=BLACK,
                            weight="bold",
                            padding="0.3em 0.5em",
                            style={
                                "position": "sticky",
                                "top": "0",
                                "background": GOLD,
                                "zIndex": "10",
                                "whiteSpace": "nowrap",
                                "fontSize": "clamp(0.6rem, 1.5vw, 0.8rem)",
                                "borderBottom": f"2px solid {GOLD}",
                                "minWidth": "120px",
                            }
                        ),
                    )
                ),
                rx.table.body(
                    rx.foreach(
                        State.paginated_guests,
                        lambda guest: rx.table.row(
                            rx.foreach(
                                State.columns,
                                lambda col: rx.table.cell(
                                    render_cell(col, guest),
                                    padding="0.2em 0.5em",
                                    style={
                                        "whiteSpace": "normal",
                                        "wordBreak": "break-word",
                                        "fontSize": "clamp(0.6rem, 1.5vw, 0.85rem)",
                                        "borderBottom": f"1px solid {DARK_GRAY}33",
                                    }
                                )
                            ),
                            rx.table.cell(
                                rx.hstack(
                                    # Individual guest email action.
                                    # Guest table rows use display-field names in some
                                    # dashboard paths ("Email"/"ID"), while other paths
                                    # use database names ("email"/"guest_id"). Do NOT
                                    # hide the button based on only one spelling.
                                    # Individual guest email action.
                                    rx.button(
                                        rx.hstack(
                                            rx.cond(
                                                EmailState.sending_email_guest_id
                                                == str(
                                                    guest.get(
                                                        "ID",
                                                        guest.get(
                                                            "Id",
                                                            guest.get(
                                                                "id",
                                                                guest.get(
                                                                    "guest_id",
                                                                    "",
                                                                ),
                                                            ),
                                                        ),
                                                    )
                                                ),
                                                rx.spinner(size="1"),
                                                rx.icon(
                                                    tag="mail",
                                                    size=13,
                                                ),
                                            ),
                                            rx.text(
                                                rx.cond(
                                                    EmailState.sending_email_guest_id
                                                    == str(
                                                        guest.get(
                                                            "ID",
                                                            guest.get(
                                                                "Id",
                                                                guest.get(
                                                                    "id",
                                                                    guest.get(
                                                                        "guest_id",
                                                                        "",
                                                                    ),
                                                                ),
                                                            ),
                                                        )
                                                    ),
                                                    "Sending…",
                                                    rx.cond(
                                                        guest.get("email_sent", False),
                                                        "Resend Email",
                                                        "Send Email",
                                                    ),
                                                ),
                                                size="1",
                                            ),
                                            spacing="1",
                                            align="center",
                                        ),
                                        on_click=lambda: EmailState.open_email_dialog(guest),
                                        size="1",
                                        variant="outline",
                                        border_color=rx.cond(
                                            guest.get("email_sent", False),
                                            "green",
                                            GOLD,
                                        ),
                                        color=rx.cond(
                                            guest.get("email_sent", False),
                                            "green",
                                            GOLD,
                                        ),
                                    ),
                                    rx.cond(
                                        EventState.show_food_vouchers,
                                        rx.tooltip(
                                            rx.button(
                                                rx.icon(
                                                    tag="history",
                                                    size=12,
                                                ),
                                                on_click=lambda: VoucherState.show_guest_history(
                                                    guest
                                                ),
                                                variant="ghost",
                                                _hover={
                                                    "bg": f"{GOLD}33"
                                                },
                                            ),
                                            content="View purchase history",
                                        ),
                                    ),
                                    # Voucher button - only for Sports Day events with amount > 0
                                    rx.cond(
                                        EventState.show_food_vouchers & (guest.get("amount_value", 0) != 0),
                                        rx.tooltip(
                                            rx.button(
                                                rx.icon(tag="store", size=14, color=GOLD),
                                                on_click=lambda: rx.redirect(
                                                    f"/voucher-manager?guest_id={guest.get('ID', guest.get('guest_id', ''))}"),
                                                size="1",
                                                variant="ghost",
                                                _hover={"bg": f"{GOLD}33"},
                                            ),
                                            content="View vouchers",
                                        ),
                                        rx.fragment(),
                                    ),
                                    rx.tooltip(
                                        rx.button(
                                            rx.icon(
                                                tag="user_check",
                                                size=14,
                                                color=rx.cond(guest.get("Status") == "Present", "green", "red"),
                                                style={"width": "clamp(12px, 1.5vw, 16px)",
                                                       "height": "clamp(12px, 1.5vw, 16px)"},
                                            ),
                                            on_click=lambda: ScannerState.handle_scan(
                                                str(guest.get("ID", guest.get("Id", guest.get("id", ""))))
                                            ),
                                            size="1",
                                            variant="ghost",
                                            is_disabled=guest.get("Status") == "Present",
                                            _hover=rx.cond(
                                                guest.get("Status") == "Present",
                                                {},
                                                {"bg": f"{GOLD}33"},
                                            ),
                                        ),
                                        content=rx.cond(
                                            guest.get("Status") == "Present",
                                            "Already checked in",
                                            "Check in",
                                        ),
                                    ),
                                    spacing="1",
                                    align="center",
                                    min_width="150px",
                                    wrap="wrap",
                                ),
                                padding="0.2em 0.5em",
                                style={
                                    "whiteSpace": "nowrap",
                                    "borderBottom": f"1px solid {DARK_GRAY}33",
                                }
                            ),
                            _hover={"bg": f"{GOLD}11"},
                            style={
                                "transition": "background-color 0.2s ease",
                            }
                        )
                    )
                ),
                variant="surface",
                size="1",
                width="100%",
                style={
                    "tableLayout": "auto",
                    "minWidth": "700px",
                    "borderCollapse": "collapse",
                    "width": "100%",
                },
            ),
            width="100%",
            style={
                "overflowX": "auto",
                "overflowY": "auto",
                "flex": "1",
                "minHeight": "200px",
                "maxHeight": "calc(100vh - 450px)",
                "borderRadius": "8px",
                "border": f"1px solid {GOLD}33",
            },
            padding="0",
        ),
        rx.center(
            rx.vstack(
                rx.icon(tag="table", size=50, color=GOLD),
                rx.heading("No Guest Data", size="4", color="white"),
                rx.text("Upload an Excel or CSV file to get started", color="gray", size="2"),
                spacing="2",
                padding="2em",
                bg=DARK_GRAY,
                border_radius="12px",
                border=f"1px solid {GOLD}33",
                width="100%",
                max_width="400px",
            ),
            width="100%",
            style={
                # "flex": "1",
                # "display": "flex",
                "alignItems": "center",
                "justifyContent": "center",
                # "minHeight": "300px",
            },
        ),
    )


def _no_event_selected() -> rx.Component:
    """Display when no event is selected."""
    return rx.center(
        rx.vstack(
            rx.icon(tag="calendar-x", size=60, color=GOLD),
            rx.heading("No Event Selected", size="5", color="white"),
            rx.text("Please select an event from the events page to continue.", color="gray", size="3"),
            rx.button(
                rx.hstack(
                    rx.icon(tag="calendar", size=14),
                    rx.text("Go to Events", size="2"),
                    spacing="2",
                ),
                on_click=rx.redirect("/events"),
                bg=GOLD,
                color=BLACK,
                _hover={"opacity": "0.8"},
                margin_top="1em",
            ),
            spacing="3",
            padding="3em",
            bg=DARK_GRAY,
            border_radius="12px",
            border=f"1px solid {GOLD}33",
            max_width="500px",
        ),
        width="100%",
        style={
            "flex": "1",
            "display": "flex",
            "alignItems": "center",
            "justifyContent": "center",
            "minHeight": "400px",
        },
    )


def _is_event_selected() -> rx.Component:
    """Check if event is selected and show appropriate content."""
    return rx.cond(
        State.current_event_id == "",
        _no_event_selected(),
        rx.cond(
            State.current_event_id == None,  # noqa: E711
            _no_event_selected(),
            _dashboard_content(),
        ),
    )


def _dashboard_content() -> rx.Component:
    """The main dashboard content when an event is selected."""
    return rx.vstack(
        # ── Header ────────────────────────────────────────────────────────
        rx.hstack(
            rx.vstack(
                rx.hstack(
                    rx.heading(
                        State.current_event.get("name", "Event"),
                        font_size=["0.8em", "0.9em", "1em", "1.2em"],
                        color=GOLD,
                        weight="bold",
                    ),
                    rx.badge(
                        rx.hstack(
                            rx.text(State.event_config_icon),
                            rx.text(State.event_config_name),
                            spacing="1",
                        ),
                        color_scheme="gold",
                        size="1",
                    ),
                    spacing="2",
                    align="center",
                ),
                rx.hstack(
                    rx.hstack(
                        rx.icon(tag="calendar", size=10, color=GOLD),
                        rx.text(State.current_event.get("date", ""), color=LIGHT_GRAY,
                                font_size=["0.35em", "0.45em", "0.55em", "0.7em"]),
                        spacing="1",
                    ),
                    rx.hstack(
                        rx.icon(tag="clock", size=10, color=GOLD),
                        rx.text(State.current_event.get("time", ""), color=LIGHT_GRAY,
                                font_size=["0.35em", "0.45em", "0.55em", "0.7em"]),
                        spacing="1",
                    ),
                    rx.hstack(
                        rx.icon(tag="map-pin", size=10, color=GOLD),
                        rx.text(State.current_event.get("venue", ""), color=LIGHT_GRAY,
                                font_size=["0.35em", "0.45em", "0.55em", "0.7em"]),
                        spacing="1",
                    ),
                    spacing="2",
                    wrap="wrap",
                ),
                align="start",
                spacing="1",
            ),
            rx.spacer(),
            rx.hstack(
                stat_card("Total", State.total_guests, LIGHT_GRAY, "  "),
                stat_card("Present", State.present_count, "green", percentage=State.present_percentage),
                stat_card("Absent", State.absent_count, "red", percentage=State.absent_percentage),
                spacing="2",
                width="40%",
                min_width="200px",
            ),
            rx.menu.root(
                rx.menu.trigger(
                    rx.button(
                        rx.hstack(
                            rx.icon(tag="settings", size=14),
                            rx.text("Actions", size="1"),
                            rx.icon(tag="chevron-down", size=10),
                            spacing="1",
                        ),
                        variant="outline",
                        border_color=GOLD,
                        color=GOLD,
                        size="1",
                        _hover={"bg": GOLD, "color": BLACK},
                    )
                ),
                rx.menu.content(
                    rx.menu.item(
                        rx.hstack(rx.icon(tag="upload", size=12), rx.text("Upload Guest List", size="1"), spacing="2"),
                        on_click=State.open_upload_dialog,
                    ),
                    rx.menu.separator(),
                    rx.cond(
                        EventState.show_lucky_draw,
                        rx.menu.item(
                            rx.hstack(rx.icon(tag="gift", size=12), rx.text("Lucky Draw", size="1"), spacing="2"),
                            on_click=rx.redirect("/lucky-draw"),
                        ),
                    ),
                    rx.cond(EventState.show_lucky_draw, rx.menu.separator()),
                    rx.menu.item(
                        rx.hstack(rx.icon(tag="download", size=12), rx.text("Export Excel", size="1"), spacing="2"),
                        on_click=State.download_guest_list,
                    ),
                    rx.menu.item(
                        rx.hstack(
                            rx.cond(EmailState.email_sending, rx.spinner(size="1"), rx.icon(tag="mail", size=12)),
                            rx.text(
                                rx.cond(EmailState.email_sending,
                                        f"Sending {EmailState.email_progress}/{EmailState.email_total}", "Bulk Email"),
                                size="1",
                            ),
                            spacing="2",
                        ),
                        on_click=EmailState.process_email_queue,
                        is_disabled=EmailState.email_sending,
                    ),
                    rx.menu.item(
                        rx.hstack(
                            rx.icon(
                                tag="mail-check",
                                size=12,
                            ),
                            rx.text(
                                "Email Management",
                                size="1",
                            ),
                            spacing="2",
                        ),
                        on_click=EmailState.open_email_management,
                    ),
                    rx.menu.separator(),
                    rx.menu.item(
                        rx.hstack(rx.icon(tag="calendar", size=12), rx.text("Events", size="1"), spacing="2"),
                        on_click=rx.redirect("/events"),
                    ),
                    rx.menu.separator(),
                    rx.menu.item(
                        rx.hstack(rx.icon(tag="camera", size=12), rx.text("Camera Scanner", size="1"), spacing="2"),
                        on_click=rx.redirect(f"/scanner/{State.current_event_id}"),
                    ),
                    rx.menu.item(
                        rx.hstack(
                            rx.icon(tag="usb", size=12),
                            rx.text("External Scanner", size="1"),
                            rx.badge("USB", color_scheme="blue", size="1"),
                            spacing="2",
                        ),
                        on_click=rx.call_script(f"""
                            console.log('Opening external scanner for event: {State.current_event_id}');
                            const scannerWindow = window.open(
                                '/scanner-guest/{State.current_event_id}',
                                '_blank',
                                'width=600,height=750,resizable=yes,scrollbars=yes,toolbar=no,menubar=no,status=no'
                            );
                            if (scannerWindow) {{
                                console.log('Scanner window opened successfully');
                            }} else {{
                                alert('Please allow popups for this site to open the scanner.');
                            }}
                        """),
                    ),
                    rx.menu.separator(),
                    rx.menu.item(
                        rx.hstack(rx.icon(tag="user-check", size=12), rx.text("Manual Check-In", size="1"),
                                  spacing="2"),
                        on_click=rx.redirect(f"/checkin/{State.current_event_id}"),
                    ),
                    rx.menu.item(
                        rx.hstack(rx.icon("log-out", size=14), rx.text("Logout", size="1", color="red"), spacing="2"),
                        on_click=AuthState.logout,
                        color="red",
                    ),
                ),
            ),
            # Voucher button in header - only for Sports Day events with any guest having amount
            rx.cond(
                EventState.show_food_vouchers & State.has_amounts,
                rx.button(
                    rx.hstack(rx.icon(tag="store", size=14), rx.text("Vouchers", size="1")),
                    on_click=rx.redirect("/voucher-manager"),
                    variant="outline",
                    border_color=GOLD,
                    color=GOLD,
                    size="1",
                    _hover={"bg": GOLD, "color": BLACK},
                ),
                rx.fragment(),
            ),
            width="100%",
            border_bottom=f"1px solid {GOLD}",
            align="center",
            padding_bottom="0.55em",
            wrap="wrap",
            spacing="2",
        ),

        # ── Search ────────────────────────────────────────────────────────
        rx.input(
            placeholder="🔎  Search guests…",
            on_change=State.search_guests,
            size="1",
            width="100%",
            bg=BLACK,
            border_color=GOLD,
            color="white",
            _placeholder={"color": "gray"},
            margin="0.5em 0",
        ),
        rx.cond(
            State.guest_data.length() > 0,
            rx.button(
                rx.hstack(
                    rx.icon(tag="file-spreadsheet", size=14),
                    rx.text("Export Excel", size="1"),
                    spacing="1",
                ),
                on_click=State.export_guest_data_to_excel,
                **outline_button_style(),
            ),
            rx.fragment(),
        ),

        # ── Guest table ───────────────────────────────────────────────────
        _guest_table(),

        # ── Pagination ────────────────────────────────────────────────────
        rx.cond(
            State.guest_data.length() > 0,
            rx.hstack(
                rx.hstack(
                    rx.text("Show:", color="gray", style={"fontSize": "clamp(0.6rem, 1.5vw, 0.8rem)"}),
                    rx.select(
                        ["10", "25", "50", "100"],
                        value=State.items_per_page.to_string(),
                        on_change=State.set_items_per_page,
                        size="1",
                        width="60px",
                        bg=BLACK,
                        border_color=GOLD,
                        color="white",
                    ),
                    rx.text("entries", color="gray", style={"fontSize": "clamp(0.6rem, 1.5vw, 0.8rem)"}),
                    spacing="1",
                    align="center",
                ),
                rx.spacer(),
                rx.hstack(
                    rx.button(
                        rx.icon(tag="chevron-left", size=10,
                                style={"width": "clamp(8px, 1.2vw, 12px)", "height": "clamp(8px, 1.2vw, 12px)"}),
                        on_click=State.prev_page,
                        is_disabled=State.current_page == 1,
                        size="1",
                        variant="outline",
                        border_color=GOLD,
                        color=GOLD,
                        _hover={"bg": GOLD, "color": BLACK},
                    ),
                    rx.text(
                        f"Page {State.current_page.to_string()} of {State.total_pages.to_string()}",
                        color="white",
                        style={"fontSize": "clamp(0.6rem, 1.5vw, 0.8rem)"},
                    ),
                    rx.button(
                        rx.icon(tag="chevron-right", size=10,
                                style={"width": "clamp(8px, 1.2vw, 12px)", "height": "clamp(8px, 1.2vw, 12px)"}),
                        on_click=State.next_page,
                        is_disabled=State.current_page == State.total_pages,
                        size="1",
                        variant="outline",
                        border_color=GOLD,
                        color=GOLD,
                        _hover={"bg": GOLD, "color": BLACK},
                    ),
                    spacing="1",
                    align="center",
                ),
                rx.spacer(),
                rx.text(
                    f"Showing {State.paginated_guests.length().to_string()} of {State.filtered_data.length().to_string()} guests",
                    color="gray",
                    style={"fontSize": "clamp(0.55rem, 1.4vw, 0.75rem)"},
                ),
                width="100%",
                padding="0.3em 0.8em",
                background=BLACK,
                border_top=f"1px solid {GOLD}33",
                wrap="wrap",
                spacing="2",
            ),
            rx.fragment(),
        ),

        # ── Dialogs ───────────────────────────────────────────────────────
        upload_dialog.upload_dialog(),
        clear_table_dialog.clear_table_dialog(),
        event_qr_dialog.event_qr_dialog(),
        guest_qr_dialog.guest_qr_dialog(),
        email_dialog.email_dialog(),
        transaction_history.transaction_history_modal(),

        width="100%",
        spacing="3",
    )


def dashboard() -> rx.Component:
    """Main dashboard page."""
    return page_layout_dashboard(
        rx.vstack(
            # ── Live alert banner ──────────────────────────────────────────────
            _checkin_alert_banner(),

            # ── Check if event is selected ──────────────────────────────────
            _is_event_selected(),
            email_management.email_management_panel(),
            width="100%",
            style={
                "height": "100%",
                "minHeight": "100vh",
                "padding": "0.5em",
            },
            # Load guests when page mounts
            on_mount=State.load_guests,
        ),
    )
