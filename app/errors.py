"""Custom exception hierarchy for consistent error handling."""


class AppError(Exception):
    """Base application error."""

    status_code = 500

    def __init__(self, message: str = "Internal server error", status_code: int | None = None):
        super().__init__(message)
        self.message = message
        if status_code is not None:
            self.status_code = status_code


class ValidationError(AppError):
    """Invalid input data."""

    status_code = 400


class AuthorizationError(AppError):
    """Insufficient permissions."""

    status_code = 403


class NotFoundError(AppError):
    """Requested resource does not exist."""

    status_code = 404
