"""Custom exceptions for the application. Mapped to HTTP status in main.py."""


class AppException(Exception):
    """Base for app exceptions. Subclasses set code and default status."""

    code: str = "ERROR"
    status_code: int = 500

    def __init__(self, message: str, details: dict | None = None):
        self.message = message
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppException):
    """Resource does not exist."""

    code = "NOT_FOUND"
    status_code = 404


class AlreadyExistsError(AppException):
    """Duplicate resource (e.g. email already registered)."""

    code = "ALREADY_EXISTS"
    status_code = 400


class AuthenticationError(AppException):
    """Bad credentials or invalid token."""

    code = "AUTHENTICATION_ERROR"
    status_code = 401


class AuthorizationError(AppException):
    """Not allowed to perform action."""

    code = "AUTHORIZATION_ERROR"
    status_code = 403


class ValidationError(AppException):
    """Invalid input."""

    code = "VALIDATION_ERROR"
    status_code = 422


class ExternalServiceError(AppException):
    """External service (LLM, Slack, etc.) failed."""

    code = "EXTERNAL_SERVICE_ERROR"
    status_code = 502
