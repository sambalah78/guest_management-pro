"""Compatibility wrapper for the canonical Lucky Draw hall display.

The canonical presentation implementation lives in lucky_draw_hall.py.
Keeping one implementation prevents visual/behavioral drift.
"""

from .lucky_draw_hall import lucky_draw_hall_page


def lucky_draw_external_display_page():
    """Return the canonical hall display."""
    return lucky_draw_hall_page()