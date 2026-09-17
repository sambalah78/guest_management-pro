# guest_management/utils/formatting.py
"""Formatting utilities."""
from __future__ import annotations

from datetime import date as date_type
from datetime import datetime as datetime_type
from datetime import time as time_type
from typing import Any, Optional


DISPLAY_DATE_FORMAT = "%d-%b-%Y"
DISPLAY_TIME_FORMAT = "%H:%M"
DISPLAY_DATETIME_FORMAT = "%d-%b-%Y %H:%M"

def _parse_datetime(value: Any) -> datetime_type | None:
    """Parse common PostgreSQL/ISO datetime representations."""
    if value is None or value == "":
        return None

    if isinstance(value, datetime_type):
        return value

    if isinstance(value, date_type):
        return datetime_type.combine(value, time_type.min)

    text = str(value).strip()

    if not text:
        return None

    # ISO timestamps such as:
    # 2026-09-16T17:30:00+00:00
    # 2026-09-16T17:30:00Z
    try:
        return datetime_type.fromisoformat(
            text.replace("Z", "+00:00")
        )
    except ValueError:
        pass

    # Date only.
    try:
        parsed_date = date_type.fromisoformat(text)
        return datetime_type.combine(parsed_date, time_type.min)
    except ValueError:
        pass

    # Common fallback formats.
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
    ):
        try:
            return datetime_type.strptime(text, fmt)
        except ValueError:
            continue

    return None

def format_date(value: Any) -> str:
    """Format a date as dd/mmm/yyyy."""
    if value is None or value == "":
        return ""

    parsed = _parse_datetime(value)

    if parsed is None:
        return str(value)

    return parsed.strftime(DISPLAY_DATE_FORMAT)


def format_time(value: Any) -> str:
    """Format a time as HH:MM."""
    if value is None or value == "":
        return ""

    if isinstance(value, time_type):
        return value.strftime(DISPLAY_TIME_FORMAT)

    text = str(value).strip()

    if not text:
        return ""

    # Time values such as 19:55:00.
    try:
        parsed = time_type.fromisoformat(text)
        return parsed.strftime(DISPLAY_TIME_FORMAT)
    except ValueError:
        pass

    # Datetime accidentally supplied to the function.
    parsed = _parse_datetime(value)

    if parsed is not None:
        return parsed.strftime(DISPLAY_TIME_FORMAT)

    return str(value)


def format_datetime(value: Any) -> str:
    """Format a datetime as dd/mmm/yyyy HH:MM."""
    if value is None or value == "":
        return ""

    parsed = _parse_datetime(value)

    if parsed is None:
        return str(value)

    return parsed.strftime(DISPLAY_DATETIME_FORMAT)


def format_event_datetime(
    event_date: Any,
    event_time: Any,
) -> str:
    """Format an event's separate date/time fields as dd/mmm/yyyy HH:MM."""
    formatted_date = format_date(event_date)
    formatted_time = format_time(event_time)

    if formatted_date and formatted_time:
        return f"{formatted_date} {formatted_time}"

    return formatted_date or formatted_time

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
