"""Application error types. Services raise these; routes translate them to responses."""


class AppError(Exception):
    """Base class for all expected application errors."""

    status_code = 500

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class NotFoundError(AppError):
    """Raised when a requested resource does not exist."""

    status_code = 404


class ValidationError(AppError):
    """Raised when input fails validation."""

    status_code = 400
