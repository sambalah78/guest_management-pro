# guest_management/core/handlers.py
"""Error handlers and decorators."""

import functools
import logging
from typing import Callable, TypeVar, Any, Optional

import reflex as rx

from .exceptions import EventLahError, AuthenticationError

logger = logging.getLogger(__name__)
T = TypeVar("T")


def handle_errors(state: Any, fallback_message: str = "An error occurred") -> Callable:
    """Decorator to handle errors in state methods."""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                await func(*args, **kwargs)
            except AuthenticationError as e:
                logger.warning(f"Authentication error: {e.message}")
                yield rx.toast.error(e.message)
                yield rx.redirect("/login")
            except EventLahError as e:
                logger.warning(f"Application error: {e.message}")
                yield rx.toast.error(e.message)
            except Exception as e:
                logger.exception(f"Unexpected error in {func.__name__}: {e}")
                yield rx.toast.error(fallback_message)
            finally:
                if hasattr(state, "is_loading"):
                    state.is_loading = False
                yield
        return wrapper
    return decorator


def safe_async(func: Callable) -> Callable:
    """Safely execute async function with error handling."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        try:
            return await func(*args, **kwargs)
        except Exception as e:
            logger.exception(f"Error in {func.__name__}: {e}")
            return None
    return wrapper


def log_call(func: Callable) -> Callable:
    """Log function calls."""
    @functools.wraps(func)
    async def wrapper(*args, **kwargs):
        logger.debug(f"Calling {func.__name__}")
        try:
            result = await func(*args, **kwargs)
            logger.debug(f"{func.__name__} completed successfully")
            return result
        except Exception as e:
            logger.error(f"{func.__name__} failed: {e}")
            raise
    return wrapper