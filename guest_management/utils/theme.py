"""EventLah application UI theme."""

# Core palette
BG = "#F8F9FA"
SURFACE = "#FFFFFF"
SURFACE_MUTED = "#d9dadb"

NAVY = "#1F2937"
NAVY_DARK = "#111827"

GOLD = "#D9A514"
GOLD_LIGHT = "#FFF3C4"
GOLD_HOVER = "#C7940F"

TEXT = "#FFFFFF"
TEXT_MUTED = "#A8A8A8"
TEXT_LIGHT = "#9CA3AF"
TEXT_SECONDARY = "#D0D0D0"

BORDER = "#D1D5DB"
BORDER_LIGHT = "#E5E7EB"

SUCCESS = "#4CAF50"
SUCCESS_LIGHT = "#ECFDF5"

DANGER = "#FF4D4D"
DANGER_LIGHT = "#FEF2F2"

WARNING = "#D97706"
WARNING_LIGHT = "#FFFBEB"

# Dimensions
RADIUS_SM = "8px"
RADIUS_MD = "12px"
RADIUS_LG = "14px"

PAGE_MAX_WIDTH = "1200px"
PAGE_PADDING = ["12px", "16px", "20px"]
CARD_PADDING = ["16px", "18px"]
SECTION_GAP = "16px"

# Common component styles
CARD_STYLE = {
    "background": SURFACE,
    "border": f"1px solid {BORDER}",
    "border_radius": RADIUS_MD,
    "box_shadow": "0 1px 2px rgba(0, 0, 0, 0.04)",
}

HEADER_STYLE = {
    "background": NAVY,
    "color": SURFACE,
    "border_radius": RADIUS_MD,
}

PRIMARY_BUTTON_STYLE = {
    "background": GOLD,
    "color": NAVY_DARK,
    "border_radius": RADIUS_SM,
    "_hover": {
        "background": GOLD_HOVER,
    },
}

SECONDARY_BUTTON_STYLE = {
    "background": SURFACE,
    "color": NAVY,
    "border": f"1px solid {BORDER}",
    "border_radius": RADIUS_SM,
    "_hover": {
        "background": SURFACE_MUTED,
    },
}

INPUT_STYLE = {
    "background": SURFACE,
    "color": TEXT,
    "border": f"1px solid {BORDER}",
    "border_radius": RADIUS_SM,
    "_focus": {
        "border_color": GOLD,
    },
}
