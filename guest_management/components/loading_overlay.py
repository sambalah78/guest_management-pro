# guest_management/components/loading_overlay.py
"""Reusable non-flickering page/action loading overlay."""

from __future__ import annotations

import reflex as rx

from guest_management.utils.constants import GOLD, BLACK


def loading_overlay(
    visible,
    message: str = "Loading...",
) -> rx.Component:
    """Show a blocking loading indicator at a page/UI boundary."""
    return rx.cond(
        visible,
        rx.box(
            rx.vstack(
                rx.spinner(size="3", color=GOLD),
                rx.text(
                    message,
                    color="white",
                    font_size="0.9rem",
                    font_weight="700",
                    text_align="center",
                ),
                spacing="3",
                align="center",
            ),
            position="fixed",
            inset="0",
            z_index="9999",
            display="flex",
            align_items="center",
            justify_content="center",
            background="rgba(0, 0, 0, 0.78)",
            backdrop_filter="blur(3px)",
            pointer_events="auto",
        ),
        rx.fragment(),
    )


def eventlah_viewport_page(
    content: rx.Component,
    loading=False,
    message: str = "Loading...",
) -> rx.Component:
    return rx.box(
        rx.box(
            rx.fragment(
                content,
                loading_overlay(loading, message),
            ),
            width="100%",
            min_width="0",
            min_height="0",
            flex="1 1 auto",
            overflow_x="hidden",
            overflow_y="auto",
            class_name="eventlah-page-scroll",
        ),
        width="100%",
        height="100dvh",
        min_width="0",
        min_height="0",
        max_height="100dvh",
        display="flex",
        flex_direction="column",
        overflow="hidden",
        class_name="eventlah-viewport-page",
    )
