# guest_management/utils/formatting.py
"""Formatting utilities."""

from datetime import datetime
from typing import Any, Optional


def format_date(date_str: str, input_format: str = "%Y-%m-%d", output_format: str = "%d %b %Y") -> str:
    """Format a date string."""
    if not date_str:
        return ""
    try:
        dt = datetime.fromisoformat(date_str.replace("Z", "+00:00"))
        return dt.strftime(output_format)
    except Exception:
        return date_str


def format_datetime(dt_str: str, output_format: str = "%Y-%m-%d %H:%M") -> str:
    """Format a datetime string."""
    if not dt_str:
        return ""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
        return dt.strftime(output_format)
    except Exception:
        return dt_str


def format_currency(amount: float, currency: str = "RM") -> str:
    """Format currency amount."""
    try:
        return f"{currency} {amount:.2f}"
    except (ValueError, TypeError):
        return f"{currency} 0.00"


def format_table_number(table: Any) -> str:
    """Format table number (handle float values)."""
    if not table or table == "":
        return "TBD"

    try:
        if isinstance(table, float):
            return str(int(table))
        if isinstance(table, str) and table.endswith(".0"):
            return table[:-2]
        return str(table)
    except (ValueError, TypeError):
        return str(table)


def truncate_string(value: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate a string to max length."""
    if not value or len(value) <= max_length:
        return value
    return value[:max_length - len(suffix)] + suffix


def to_bool(value: Any) -> bool:
    """Convert various values to boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        return value.lower() in ("true", "1", "yes", "on")
    return False
