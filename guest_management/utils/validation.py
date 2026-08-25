# guest_management/utils/validation.py
"""Validation utilities."""

import re
from typing import Any, Optional


def is_valid_email(email: str) -> bool:
    """Check if email is valid."""
    if not email:
        return False
    pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    return bool(re.match(pattern, email))


def is_valid_guest_id(guest_id: str) -> bool:
    """Check if guest ID is valid."""
    return bool(guest_id and len(guest_id) >= 2)


def is_valid_url(url: str) -> bool:
    """Check if URL is valid."""
    if not url:
        return False
    pattern = r"^https?://[^\s/$.?#].[^\s]*$"
    return bool(re.match(pattern, url))


def safe_int(value: Any, default: int = 0) -> int:
    """Safely convert to int."""
    try:
        return int(value)
    except (ValueError, TypeError):
        return default


def safe_float(value: Any, default: float = 0.0) -> float:
    """Safely convert to float."""
    try:
        return float(value)
    except (ValueError, TypeError):
        return default


def safe_str(value: Any, default: str = "") -> str:
    """Safely convert to string."""
    if value is None:
        return default
    return str(value)


def extract_team_name(guest: dict) -> str:
    """Extract team name from guest data."""
    # Check direct fields
    for field in ["team_name", "Team", "team", "TeamName", "group", "Group", "squad", "Squad"]:
        if guest.get(field):
            return safe_str(guest[field])

    # Check full_data
    full_data = guest.get("full_data")
    if full_data:
        import json
        try:
            row = json.loads(full_data) if isinstance(full_data, str) else full_data
            for key in ["team", "Team", "team_name", "TeamName", "group", "Group", "squad", "Squad"]:
                if key in row and row[key]:
                    return safe_str(row[key])
        except Exception:
            pass

    return ""


def extract_table_number(guest: dict) -> str:
    """Extract table number from guest data."""
    table = guest.get("table_number", "")
    if table:
        return format_table_number(table)

    full_data = guest.get("full_data")
    if full_data:
        import json
        try:
            row = json.loads(full_data) if isinstance(full_data, str) else full_data
            for key in ["table", "Table", "table_number", "tableNumber"]:
                if key in row and row[key]:
                    return format_table_number(row[key])
        except Exception:
            pass

    return "TBD"
