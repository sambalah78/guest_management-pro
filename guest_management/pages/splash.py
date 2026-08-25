# guest_management/pages/splash.py
"""Splash screen with animated logo and text."""

import reflex as rx
from guest_management.state import GuestState


def splash_screen() -> rx.Component:
    """Splash screen with flying text animation."""
    return rx.center(
        rx.vstack(
            # Logo
            rx.image(
                src="/logonew.png",
                width=["200px", "220px", "250px", "270px"],
                height="auto",
                margin_bottom="0.1em",
                bg="transparent",
                style={
                    "animation": "scaleIn 0.8s ease-out forwards",
                    "opacity": "0",
                    "transform": "scale(0.5)",
                }
            ),

            # Animated Text Container
            rx.box(
                rx.image(
                    src="/event.PNG",
                    width=["200px", "220px", "250px", "270px"],
                    style={
                        "animation": "flyFromLeft 0.8s ease-out forwards",
                        "opacity": "0",
                        "transform": "translateX(-200px)",
                    }
                ),
                rx.image(
                    src="/lah.PNG",
                    width=["120px", "140px", "160px", "180px"],
                    margin_left="0.1em",
                    style={
                        "animation": "flyFromRight 0.8s ease-out 0.2s forwards",
                        "opacity": "0",
                        "transform": "translateX(200px)",
                    }
                ),
                display="flex",
                justify="center",
                align_items="center",
                wrap="wrap",
                spacing="1",
                margin_top="0.2em",
            ),

            # Tagline
            rx.image(
                src="/arrow.PNG",
                width=["200px", "220px", "250px", "270px"],
                style={
                    "animation": "flyFromBottom 0.8s ease-out forwards",
                    "opacity": "0",
                    "transform": "translateX(-200px)",
                }
            ),
            rx.text(
                "Smart Events",
                font_size=["0.8em", "1em", "1.2em", "1.5em"],
                color="gray",
                margin_top="0.1em",
                style={
                    "animation": "flyFromBottom 0.8s ease-out 0.5s forwards",
                    "opacity": "0",
                    "transform": "translateY(100px)",
                }
            ),

            # Loading dots animation
            rx.hstack(
                rx.text(".", color="#D4AF37", font_size="2em", style={"animation": "bounce 0.8s infinite 0s"}),
                rx.text(".", color="#D4AF37", font_size="2em", style={"animation": "bounce 0.8s infinite 0.2s"}),
                rx.text(".", color="#D4AF37", font_size="2em", style={"animation": "bounce 0.8s infinite 0.4s"}),
                spacing="1",
                margin_top="2em",
                style={"opacity": "0", "animation": "fadeIn 1.2s ease-out 1.8s forwards"},
            ),

            spacing="1",
            align="center",
        ),
        width="100%",
        height="100vh",
        bg="#111111",
        style={
            "div[data-radix-portal]": {
                "& footer": {
                    "display": "none !important",
                },
            },
            "div[class*='reflex-badge']": {
                "display": "none !important",
            },
            "div:has(> a[href*='reflex'])": {
                "display": "none !important",
            },
            "a[href*='reflex.dev']": {
                "display": "none !important",
            },
            "div[class*='PoweredBy']": {
                "display": "none !important",
            },
            "footer": {"display": "none !important"},
            "[class*='PoweredBy']": {"display": "none !important"},
            "a[href*='reflex']": {"display": "none !important"},
            "@keyframes flyFromLeft": {
                "0%": {"opacity": "0", "transform": "translateX(-200px)"},
                "100%": {"opacity": "1", "transform": "translateX(0)"}
            },
            "@keyframes flyFromRight": {
                "0%": {"opacity": "0", "transform": "translateX(200px)"},
                "100%": {"opacity": "1", "transform": "translateX(0)"}
            },
            "@keyframes flyFromBottom": {
                "0%": {"opacity": "0", "transform": "translateY(100px)"},
                "100%": {"opacity": "1", "transform": "translateY(0)"}
            },
            "@keyframes scaleIn": {
                "0%": {"opacity": "0", "transform": "scale(0.5)"},
                "100%": {"opacity": "1", "transform": "scale(1)"}
            },
            "@keyframes bounce": {
                "0%, 100%": {"transform": "translateY(0)"},
                "50%": {"transform": "translateY(-10px)"}
            },
            "@keyframes fadeIn": {
                "0%": {"opacity": "0"},
                "100%": {"opacity": "1"}
            }
        },
        # Redirect to home after 2.5 seconds
        on_mount=GuestState.redirect_after_delay,
    )