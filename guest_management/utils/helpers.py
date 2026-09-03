# guest_management/utils/helpers.py
"""Helper utilities."""

from typing import Any


def safe_str(value: Any, default: str = "") -> str:
    """Safely convert a value to a stripped string."""
    if value is None:
        return default
    return str(value).strip()


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert a value to a float."""
    try:
        return float(value)
    except (TypeError, ValueError):
        return default