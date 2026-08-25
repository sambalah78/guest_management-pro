"""Application exception hierarchy.

The UI can safely map these exceptions to user-facing messages while the
repository layer keeps the original provider error in logs.
"""


class EventLahError(Exception):
    """Base exception for the application."""

    status_code = 400

    def __init__(self, message: str, status_code: int | None = None):
        self.message = message
        if status_code is not None:
            self.status_code = status_code
        super().__init__(message)


class AuthenticationError(EventLahError):
    status_code = 401


class AuthorizationError(EventLahError):
    status_code = 403


# Backward-compatible alias for older modules.
PermissionDeniedError = AuthorizationError


class NotFoundError(EventLahError):
    status_code = 404


class EventNotFoundError(NotFoundError):
    pass


class GuestNotFoundError(NotFoundError):
    pass


class GuestAlreadyCheckedInError(EventLahError):
    status_code = 409


class StallNotFoundError(NotFoundError):
    pass


class ValidationError(EventLahError):
    status_code = 422


class DatabaseError(EventLahError):
    status_code = 500


class ConfigurationError(EventLahError):
    status_code = 500


class EmailError(EventLahError):
    status_code = 502


class ScannerError(EventLahError):
    status_code = 500


class RateLimitError(EventLahError):
    status_code = 429
