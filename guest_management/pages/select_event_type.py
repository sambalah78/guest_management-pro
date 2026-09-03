# pages/select_event_type.py

import reflex as rx

from ..state import EventState
from ..utils.constants import EVENT_TYPES
from ..utils.theme import (
    BG,
    NAVY,
    GOLD,
    GOLD_HOVER,
    SURFACE,
    TEXT,
    TEXT_MUTED,
    BORDER,
    SUCCESS,
    SURFACE_MUTED,
)


def _event_card(
    icon: str,
    title: str,
    description: str,
    features: list[str],
    event_type: str,
):
    return rx.card(
        rx.vstack(
            rx.text(
                icon,
                font_size="2.8em",
                line_height="1",
            ),
            rx.heading(
                title,
                size="4",
                color=NAVY,
                text_align="center",
            ),
            rx.text(
                description,
                color=TEXT_MUTED,
                size="2",
                text_align="center",
                min_height="42px",
            ),
            rx.hstack(
                *[
                    rx.badge(
                        feature,
                        color=GOLD,
                        size="1",
                    )
                    for feature in features
                ],
                wrap="wrap",
                spacing="1",
                justify="center",
            ),
            rx.spacer(),
            rx.button(
                "Select",
                on_click=EventState.select_event_type(event_type),
                background=GOLD,
                color=NAVY,
                width="100%",
                _hover={
                    "background": GOLD_HOVER,
                    "color": NAVY,
                },
            ),
            spacing="3",
            align="center",
            height="100%",
            width="100%",
        ),
        background=SURFACE_MUTED,
        border=f"1px solid {BORDER}",
        border_radius="14px",
        padding="1.5em",
        width="100%",
        min_height="250px",
        _hover={
            "transform": "translateY(-4px)",
            "box_shadow": "0 8px 24px rgba(0, 0, 0, 0.08)",
            "transition": "0.2s",
        },
    )


def select_event_type_page():
    """Event type selection page."""

    event_cards = [
        _event_card(
            config["icon"],
            config["name"],
            config["description"],
            config["display_features"],
            event_type,
        )
        for event_type, config in EVENT_TYPES.items()
    ]

    return rx.box(
        rx.vstack(
            # Header
            rx.hstack(
                rx.button(
                    rx.hstack(
                        rx.icon(
                            tag="arrow-left",
                            size=16,
                        ),
                        rx.text("Back to Events"),
                    ),
                    on_click=rx.redirect("/events"),
                    variant="outline",
                    border_color=GOLD,
                    color=GOLD,
                    size="1",
                    _hover={
                        "background": GOLD,
                        "color": NAVY,
                    },
                ),
                rx.spacer(),
                rx.heading(
                    "Select Event Type",
                    size="5",
                    color=SURFACE,
                ),
                rx.spacer(),
                rx.box(width="120px"),
                width="100%",
                padding="0.75em 1em",
                background=NAVY,
                border_radius="12px",
            ),
            rx.vstack(
                rx.text(
                    "Choose the type of event you want to organize",
                    color=TEXT_MUTED,
                    size="2",
                    text_align="center",
                ),
                rx.grid(
                    *event_cards,
                    columns=rx.breakpoints(
                        initial="1",
                        sm="1",
                        md="2",
                        lg="4",
                    ),
                    spacing="4",
                    width="100%",
                ),
                width="100%",
                max_width="1200px",
                spacing="4",
            ),
            width="100%",
            max_width="1200px",
            padding="1.5em",
            spacing="5",
        ),
        width="100%",
        min_height="100vh",
        background=BG,
        padding="12px",
    )
