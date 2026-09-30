"""Minimal liveness endpoint for deployment/load balancers."""
from guest_management.components.loading_overlay import eventlah_viewport_page

import reflex as rx


def health_page() -> rx.Component:
    return eventlah_viewport_page(rx.text("ok"),
        loading=False,
        message="",
    )
