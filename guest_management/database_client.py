"""Database client compatibility layer. Uses SQLAlchemy only."""
from .database import get_db

__all__ = ["get_db"]
