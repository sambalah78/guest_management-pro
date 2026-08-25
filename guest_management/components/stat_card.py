# components/stat_card.py
import reflex as rx
from guest_management.state import DARK_GRAY, LIGHT_GRAY


def stat_card(label: str, value, color: str, percentage: float = None):
    """Stat card component with optional percentage display"""
    css_class = ""
    if label == "Present":
        css_class = "stat-present"
    elif label == "Total":
        css_class = "stat-total"
    elif label == "Absent":
        css_class = "stat-absent"

    return rx.card(
        rx.hstack(
            rx.text(label, color=DARK_GRAY, font_size=["0.4em", "0.6em", "0.8em", "1em"], weight="medium"),
            rx.heading(value, size="3", color="white", weight="bold"),
            rx.spacer(),
            rx.cond(
                percentage is not None,
                rx.hstack(
                    rx.cond(
                        label in ["Present", "present"],
                        rx.icon(tag="arrow-up", size=14, style={"width": "clamp(10px, 1.5vw, 14px)", "height": "clamp(10px, 1.5vw, 14px)"}, color="green"),
                        rx.cond(
                            label in ["Absent", "absent"],
                            rx.icon(tag="arrow-down", size=14, style={"width": "clamp(10px, 1.5vw, 14px)", "height": "clamp(10px, 1.5vw, 14px)"}, color="red"),
                            rx.fragment(),
                        ),
                    ),
                    rx.text(
                        percentage,
                        font_size=["0.55em", "0.65em", "0.75em", "0.85em"],
                        color=rx.cond(
                            label in ["Present", "present"], "green",
                            rx.cond(label in ["Absent", "absent"], "red", "gray")
                        ),
                        weight="bold",
                    ),
                    spacing="1",
                    bg=f"{color}20",
                    border_radius="full",
                ),
                rx.fragment(),
            ),
            align="start",
            width="100%",
        ),
        class_name=css_class,
        bg=LIGHT_GRAY,
        border=f"1px solid {color}",
        border_radius="8px",
        padding="0.5em 0.75em",
        width="100%",
        _hover={
            "border_color": color,
            "transform": "translateY(-1px)",
            "transition": "all 0.2s ease",
        },
    )