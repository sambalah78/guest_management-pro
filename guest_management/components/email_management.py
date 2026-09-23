"""Dashboard email management UI with delivery details."""

from __future__ import annotations

import reflex as rx

from guest_management.state import EmailState
from guest_management.utils.constants import GOLD, DARK_GRAY, LIGHT_GRAY


def _summary_card(label, value, icon: str, icon_color: str):
    return rx.box(
        rx.hstack(
            rx.box(
                rx.icon(tag=icon, size=18, color=icon_color),
                padding="0.65em",
                border_radius="10px",
                background=f"{icon_color}18",
            ),
            rx.vstack(
                rx.text(label, color=LIGHT_GRAY, size="1"),
                rx.text(value, color="white", size="5", weight="bold"),
                spacing="0",
                align="start",
            ),
            spacing="3",
            align="center",
        ),
        background=DARK_GRAY,
        border=f"1px solid {GOLD}22",
        border_radius="12px",
        padding="1em",
        flex="1",
        min_width="190px",
    )


def _status_badge(status):
    return rx.cond(
        status == "sent",
        rx.badge("Sent", color_scheme="green", variant="soft"),
        rx.cond(
            status == "failed",
            rx.badge("Failed", color_scheme="red", variant="soft"),
            rx.cond(
                status == "cancelled",
                rx.badge("Cancelled", color_scheme="gray", variant="soft"),
                rx.cond(
                    status == "processing",
                    rx.badge("Processing", color_scheme="blue", variant="soft"),
                    rx.cond(
                        status == "queued",
                        rx.badge("Queued", color_scheme="orange", variant="soft"),
                        rx.badge(status, color_scheme="gray", variant="soft"),
                    ),
                ),
            ),
        ),
    )


def _job_actions(job):
    status = job["status"]
    job_id = job["id"]

    return rx.hstack(
        rx.button(
            rx.icon(tag="info", size=14),
            "Details",
            size="1",
            variant="outline",
            color_scheme="gray",
            on_click=EmailState.open_delivery_details(job_id),
        ),
        rx.cond(
            status == "sent",
            rx.button(
                rx.icon(tag="send", size=14),
                "Resend",
                size="1",
                variant="outline",
                color_scheme="blue",
                on_click=EmailState.resend_email_job(job_id),
            ),
            rx.cond(
                (status == "failed") | (status == "cancelled"),
                rx.button(
                    rx.icon(tag="refresh-cw", size=14),
                    "Retry",
                    size="1",
                    variant="soft",
                    color_scheme="orange",
                    on_click=EmailState.retry_email_job(job_id),
                ),
                rx.fragment(),
            ),
        ),
        spacing="2",
        align="center",
    )


def _job_row(job):
    return rx.table.row(
        rx.table.cell(rx.text(job["guest_id"], size="2")),
        rx.table.cell(rx.text(job["recipient"], size="2")),
        rx.table.cell(
            rx.text(
                job["subject"],
                size="2",
                max_width="240px",
                overflow="hidden",
                text_overflow="ellipsis",
                white_space="nowrap",
            )
        ),
        rx.table.cell(_status_badge(job["status"])),
        rx.table.cell(rx.text(job["attempts"], size="2")),
        rx.table.cell(
            rx.cond(
                job["provider_message_id"] != "",
                rx.text(
                    job["provider_message_id"],
                    size="1",
                    max_width="170px",
                    overflow="hidden",
                    text_overflow="ellipsis",
                    white_space="nowrap",
                ),
                rx.text("—", color=LIGHT_GRAY, size="1"),
            )
        ),
        rx.table.cell(
            rx.cond(
                job["provider_status"] != "",
                rx.text(job["provider_status"], size="1"),
                rx.text("—", color=LIGHT_GRAY, size="1"),
            )
        ),
        rx.table.cell(
            rx.cond(
                job["delivered_at"] != "",
                rx.text(job["delivered_at"], size="1"),
                rx.text("—", color=LIGHT_GRAY, size="1"),
            )
        ),
        rx.table.cell(_job_actions(job)),
    )


def _detail_row(label: str, value):
    return rx.hstack(
        rx.text(label, color=LIGHT_GRAY, size="2", min_width="145px"),
        rx.text(
            value,
            color="white",
            size="2",
            flex="1",
            overflow_wrap="anywhere",
        ),
        width="100%",
        align="start",
        spacing="3",
    )


def _delivery_details_dialog():
    job = EmailState.selected_delivery_job
    return rx.dialog.root(
        rx.dialog.content(
            rx.vstack(
                rx.hstack(
                    rx.vstack(
                        rx.heading("Delivery Details", size="6", color=GOLD),
                        rx.text(
                            "Complete delivery information for the selected email.",
                            color=LIGHT_GRAY,
                            size="2",
                        ),
                        spacing="1",
                        align="start",
                    ),
                    rx.spacer(),
                    rx.button(
                        rx.icon(tag="x", size=17),
                        variant="ghost",
                        color=LIGHT_GRAY,
                        on_click=EmailState.close_delivery_details,
                    ),
                    width="100%",
                    align="start",
                ),
                rx.box(
                    rx.vstack(
                        _detail_row("Job ID", job["id"]),
                        _detail_row("Guest ID", job["guest_id"]),
                        _detail_row("Recipient", job["recipient"]),
                        _detail_row("Email Type", job["email_type"]),
                        _detail_row("Subject", job["subject"]),
                        _detail_row("Status", _status_badge(job["status"])),
                        _detail_row("Attempts", job["attempts"]),
                        _detail_row("Provider Status", job["provider_status"]),
                        _detail_row("Provider Message ID", job["provider_message_id"]),
                        _detail_row("Queued / Available", job["available_at"]),
                        _detail_row("Locked At", job["locked_at"]),
                        _detail_row("Sent At", job["sent_at"]),
                        _detail_row("Delivered At", job["delivered_at"]),
                        _detail_row("Bounced At", job["bounced_at"]),
                        _detail_row("Opened At", job["opened_at"]),
                        _detail_row("Clicked At", job["clicked_at"]),
                        _detail_row("Created At", job["created_at"]),
                        _detail_row("Updated At", job["updated_at"]),
                        rx.cond(
                            job["last_error"] != "",
                            rx.box(
                                rx.text("Last Error", color="tomato", weight="bold", size="2"),
                                rx.text(
                                    job["last_error"],
                                    color="tomato",
                                    size="2",
                                    overflow_wrap="anywhere",
                                ),
                                width="100%",
                                padding="0.8em",
                                border_radius="8px",
                                background="#ff000010",
                                border="1px solid #ff000033",
                            ),
                            rx.fragment(),
                        ),
                        spacing="3",
                        width="100%",
                    ),
                    width="100%",
                    max_height="65vh",
                    overflow_y="auto",
                    padding="1em",
                    border=f"1px solid {GOLD}22",
                    border_radius="10px",
                    background=DARK_GRAY,
                ),
                rx.hstack(
                    rx.spacer(),
                    rx.button(
                        "Close",
                        variant="outline",
                        border_color=GOLD,
                        color=GOLD,
                        on_click=EmailState.close_delivery_details,
                    ),
                    width="100%",
                ),
                spacing="4",
                width="100%",
            ),
            background=DARK_GRAY,
            border=f"1px solid {GOLD}",
            border_radius="14px",
            padding="1.5em",
            max_width="900px",
            width="92vw",
        ),
        open=EmailState.delivery_details_open,
    )


def email_management_panel():
    """Render the complete email management dialog."""
    return rx.fragment(
        rx.dialog.root(
            rx.dialog.content(
                rx.vstack(
                    rx.hstack(
                        rx.vstack(
                            rx.heading("Email Management", size="6", color=GOLD),
                            rx.text(
                                "Monitor invitation delivery and safely retry or resend emails.",
                                color=LIGHT_GRAY,
                                size="2",
                            ),
                            spacing="1",
                            align="start",
                        ),
                        rx.spacer(),
                        rx.button(
                            rx.cond(
                                EmailState.email_management_loading,
                                rx.spinner(size="1"),
                                rx.icon(tag="refresh-cw", size=16),
                            ),
                            "Refresh",
                            on_click=EmailState.refresh_email_management,
                            variant="outline",
                            border_color=GOLD,
                            color=GOLD,
                            size="2",
                        ),
                        rx.button(
                            rx.icon(tag="x", size=16),
                            variant="ghost",
                            color=LIGHT_GRAY,
                            on_click=EmailState.close_email_management,
                        ),
                        width="100%",
                        align="start",
                    ),
                    rx.cond(
                        EmailState.email_message != "",
                        rx.callout(EmailState.email_message, icon="check", color_scheme="green", width="100%"),
                        rx.fragment(),
                    ),
                    rx.cond(
                        EmailState.email_error != "",
                        rx.callout(EmailState.email_error, icon="triangle-alert", color_scheme="red", width="100%"),
                        rx.fragment(),
                    ),
                    rx.flex(
                        _summary_card("Sent", EmailState.email_sent_count, "circle-check", "green"),
                        _summary_card("Queued", EmailState.email_queued_count, "clock", "orange"),
                        _summary_card("Processing", EmailState.email_processing_count, "loader", "blue"),
                        _summary_card("Failed", EmailState.email_failed_count, "circle-alert", "red"),
                        _summary_card("Cancelled", EmailState.email_cancelled_count, "circle-x", "gray"),
                        gap="0.75em",
                        width="100%",
                        wrap="wrap",
                    ),
                    rx.hstack(
                        rx.button(
                            rx.icon(tag="refresh-cw", size=14),
                            "Retry All Failed",
                            on_click=EmailState.retry_all_failed,
                            variant="soft",
                            color_scheme="orange",
                            size="2",
                            is_disabled=EmailState.email_failed_count == 0,
                        ),
                        rx.text(
                            "Retry = failed/cancelled only. Resend = intentional duplicate send.",
                            color=LIGHT_GRAY,
                            size="1",
                        ),
                        spacing="3",
                        width="100%",
                        align="center",
                    ),
                    rx.box(
                        rx.table.root(
                            rx.table.header(
                                rx.table.row(
                                    rx.table.column_header_cell("Guest ID"),
                                    rx.table.column_header_cell("Recipient"),
                                    rx.table.column_header_cell("Subject"),
                                    rx.table.column_header_cell("Status"),
                                    rx.table.column_header_cell("Attempts"),
                                    rx.table.column_header_cell("Provider ID"),
                                    rx.table.column_header_cell("Provider"),
                                    rx.table.column_header_cell("Delivered"),
                                    rx.table.column_header_cell("Action"),
                                )
                            ),
                            rx.table.body(rx.foreach(EmailState.email_jobs, _job_row)),
                            width="100%",
                            variant="surface",
                            size="1",
                        ),
                        width="100%",
                        overflow_x="auto",
                        max_height="55vh",
                        overflow_y="auto",
                        border=f"1px solid {GOLD}22",
                        border_radius="10px",
                    ),
                    rx.hstack(
                        rx.text("Showing the latest 100 email jobs.", color=LIGHT_GRAY, size="1"),
                        rx.spacer(),
                        rx.button(
                            "Close",
                            variant="outline",
                            border_color=GOLD,
                            color=GOLD,
                            on_click=EmailState.close_email_management,
                        ),
                        width="100%",
                    ),
                    spacing="4",
                    width="100%",
                ),
                background=DARK_GRAY,
                border=f"1px solid {GOLD}",
                border_radius="14px",
                padding="1.5em",
                max_width="1500px",
                width="96vw",
            ),
            open=EmailState.email_management_open,
        ),
        _delivery_details_dialog(),
    )