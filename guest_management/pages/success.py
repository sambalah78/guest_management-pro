# guest_management/pages/success.py
import reflex as rx
from guest_management.state import GuestState, SuccessState, EventState, ScannerState
from guest_management.utils.constants import GOLD, BLACK


def success_page():
    """Success page - uses pre-set SuccessState values."""
    return rx.center(
        rx.cond(
            SuccessState.is_fetching,
            rx.vstack(
                rx.spinner(color=GOLD, size="3"),
                rx.text("Loading...", color="white", size="2"),
                spacing="2",
                align="center"
            ),
            rx.vstack(
                # Checkmark Animation
                rx.box(
                    rx.icon(tag="circle_check", size=80, color=GOLD),
                    animation="bounce 0.5s ease-in-out",
                ),
                rx.heading("Check-In Successful!", size="5", color=GOLD, weight="bold"),
                rx.text(f"Welcome, {SuccessState.guest_name}!", size="3", color="white", weight="medium"),

                # Table Number
                rx.card(
                    rx.vstack(
                        rx.text("Your Table Number", size="1", color="gray", weight="medium"),
                        rx.text(SuccessState.table_number, size="9", color=GOLD, weight="bold"),
                        spacing="1",
                        align="center",
                    ),
                    style={
                        "background": "#111111",
                        "border": f"1px solid {GOLD}",
                        "padding": "1.5em",
                        "borderRadius": "15px",
                        "width": "100%",
                    }
                ),

                # Team Name
                rx.card(
                    rx.vstack(
                        rx.text("Team / Company", size="1", color="gray", weight="medium"),
                        rx.cond(
                            SuccessState.team_name != "Individual",
                            rx.text(SuccessState.team_name, size="4", color="white", weight="bold"),
                            rx.text("Individual Entry", size="4", color="gray", weight="bold"),
                        ),
                        spacing="1",
                        align="center",
                    ),
                    style={
                        "background": "#111111",
                        "border": "1px solid #333333",
                        "padding": "1em",
                        "borderRadius": "12px",
                        "width": "100%",
                    }
                ),

                # Action Buttons
                rx.hstack(
                    rx.button(
                        rx.hstack(rx.icon(tag="refresh_cw", size=18), rx.text("Scan Next", size="2", weight="bold")),
                        on_click=rx.redirect(f"/scanner-guest/{EventState.current_event_id}"),
                        bg=GOLD, color=BLACK,
                        width="50%", height="50px", border_radius="30px",
                    ),
                    rx.button(
                        rx.hstack(rx.icon(tag="layout_dashboard", size=18), rx.text("Dashboard", size="2", weight="bold")),
                        on_click=ScannerState.close_scanner_and_go_to_dashboard,
                        bg="#333333", color="white",
                        width="50%", height="50px", border_radius="30px",
                    ),
                    spacing="3", width="100%",
                ),

                rx.button(
                    rx.hstack(rx.icon(tag="x", size=16), rx.text("Close Window", size="2")),
                    on_click=rx.call_script("if (window.opener) { window.close(); }"),
                    bg="#222222", color="white", width="100%", height="40px",
                ),
                spacing="4", padding="1.5em", width="100%", max_width="450px",
            )
        ),
        width="100%", height="100vh", bg=BLACK,
    )