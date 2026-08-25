"""Minimal liveness endpoint for deployment/load balancers."""

import reflex as rx


def health_page() -> rx.Component:
    return rx.text("ok")
