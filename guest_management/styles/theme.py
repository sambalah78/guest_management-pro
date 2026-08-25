# styles/theme.py
import reflex as rx

# Colors
BLACK = "#000000"
GOLD = "#D4AF37"
DARK_GOLD = "#B8960C"
LIGHT_GOLD = "#E6C84A"
DARK_GRAY = "#696969"
LIGHT_GRAY = "#D3D3D3"

# Font colors
WHITE = "#FFFFFF"
GOLD_TEXT = GOLD

# Fonts
FONT_FAMILY = "Inter, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif"

def base_style():
    """Base style for full-screen layout without scrolling"""
    return {
        "font_family": FONT_FAMILY,
        "background_color": BLACK,
        "color": WHITE,
        "height": "100vh",
        "width": "100vw",
        "overflow": "hidden",
        "margin": "0",
        "padding": "0",
    }

def card_style():
    """Card style with gold border - no padding to allow component control"""
    return {
        "background": BLACK,
        "border_radius": "12px",
        "border": f"1px solid {GOLD}",
        "box_shadow": "0 4px 16px rgba(212, 175, 55, 0.1)",
        # Removed padding from here
    }

def card_style_with_padding(padding="1.5em"):
    """Card style with gold border and custom padding"""
    base = card_style()
    base["padding"] = padding
    return base

def button_style():
    """Button style with gold background"""
    return {
        "background": GOLD,
        "color": BLACK,
        "border_radius": "8px",
        "font_weight": "bold",
        "_hover": {
            "background": DARK_GOLD,
            "transform": "translateY(-1px)",
            "transition": "all 0.2s ease",
        },
    }

def outline_button_style():
    """Outline button style"""
    return {
        "background": "transparent",
        "color": GOLD,
        "border_radius": "8px",
        "padding": "0.6em 1.2em",
        "font_weight": "bold",
        "font_size": "0.9rem",
        "border": f"1px solid {GOLD}",
        "_hover": {
            "background": GOLD,
            "color": BLACK,
            "transition": "all 0.2s ease",
        },
    }