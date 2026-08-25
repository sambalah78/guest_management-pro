"""Base repository with fail-fast database error handling."""

from __future__ import annotations

import logging
from typing import Any, Optional

from guest_management.core.exceptions import DatabaseError
from guest_management.database_client import get_db

logger = logging.getLogger(__name__)


class BaseRepository:
    """Base repository for trusted server-side database operations."""

    def __init__(self, db=None):
        self._db = db

    @property
    def db(self):
        if self._db is None:
            self._db = get_db()
        return self._db

    @staticmethod
    def _safe_int(value: Any) -> Optional[int]:
        if value is None:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None

    @staticmethod
    def _safe_str(value: Any) -> str:
        return "" if value is None else str(value)

    @staticmethod
    def _extract_event_id(event_id: Any) -> Optional[int]:
        return BaseRepository._safe_int(event_id)

    @staticmethod
    def _raise_db(operation: str, exc: Exception) -> None:
        logger.exception("Database operation failed: %s", operation)
        raise DatabaseError(f"Database operation failed: {operation}") from exc
