# eventlah/__init__.py
import reflex as rx
from guest_management.components import navbar, footer



def page_layout(content: rx.Component) -> rx.Component:
    """Wraps pages to perfectly fit any screen without scrolling."""
    return rx.box(
        navbar.navbar(),
        rx.box(
            content,
            width="100%",
            flex="1",
            padding="1.5rem",
            overflow_y="auto",  # Allow scrolling within content area
        ),
        footer.footer(),
        background="radial-gradient(circle, #1a1a1a 0%, #0a0a0a 100%)",
        width="100vw",
        height="100vh",
        display="flex",
        flex_direction="column",
        overflow="hidden",
    )
def page_layout_dashboard(content: rx.Component) -> rx.Component:
    """Wraps pages to perfectly fit any screen without scrolling."""
    return rx.box(

        rx.box(
            content,
            width="100%",
            flex="1",
            padding="1.5rem",
            overflow_y="auto",  # Allow scrolling within content area
        ),
        footer.footer(),
        background="radial-gradient(circle, #1a1a1a 0%, #0a0a0a 100%)",
        width="100vw",
        height="100vh",
        display="flex",
        flex_direction="column",
        overflow="hidden",
    )