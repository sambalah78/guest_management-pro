# guest_management/utils/helpers.py
"""Helper utilities."""

import json
import time
from typing import Any, Dict, List, Optional
from datetime import datetime


def deep_merge(dict1: Dict[str, Any], dict2: Dict[str, Any]) -> Dict[str, Any]:
    """Deep merge two dictionaries."""
    result = dict1.copy()
    for key, value in dict2.items():
        if key in result and isinstance(result[key], dict) and isinstance(value, dict):
            result[key] = deep_merge(result[key], value)
        else:
            result[key] = value
    return result


def chunk_list(lst: List[Any], chunk_size: int) -> List[List[Any]]:
    """Split a list into chunks."""
    return [lst[i:i + chunk_size] for i in range(0, len(lst), chunk_size)]


def generate_id(prefix: str = "") -> str:
    """Generate a unique ID."""
    timestamp = int(time.time() * 1000)
    return f"{prefix}_{timestamp}" if prefix else str(timestamp)


def safe_json_loads(value: Any, default: Dict = None) -> Dict:
    """Safely parse JSON."""
    if default is None:
        default = {}
    if not value:
        return default
    try:
        if isinstance(value, dict):
            return value
        if isinstance(value, str):
            return json.loads(value)
        return default
    except Exception:
        return default


def safe_json_dumps(value: Any, default: str = "{}") -> str:
    """Safely dump to JSON."""
    if value is None:
        return default
    try:
        if isinstance(value, str):
            return value
        return json.dumps(value)
    except Exception:
        return default


def get_nested_value(data: Dict, path: str, default: Any = None) -> Any:
    """Get nested dictionary value using dot notation path."""
    keys = path.split(".")
    current = data
    for key in keys:
        if not isinstance(current, dict) or key not in current:
            return default
        current = current[key]
    return current


def now_iso() -> str:
    """Get current datetime in ISO format."""
    return datetime.now().isoformat()


def get_event_type_display(event_type: str) -> str:
    """Get display name for event type."""
    from .constants import EVENT_TYPES
    config = EVENT_TYPES.get(event_type, EVENT_TYPES["company_dinner"])
    return config["name"]


def get_event_type_icon(event_type: str) -> str:
    """Get icon for event type."""
    from .constants import EVENT_TYPES
    config = EVENT_TYPES.get(event_type, EVENT_TYPES["company_dinner"])
    return config["icon"]

def safe_str(value: Any, default: str = "") -> str:
    if value is None:
        return default
    return str(value).strip()


def safe_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
