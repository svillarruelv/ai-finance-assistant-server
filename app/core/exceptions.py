"""Custom exception classes and handlers."""

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse


class AppException(Exception):
    """Base application exception."""

    def __init__(
        self,
        message: str,
        status_code: int = status.HTTP_500_INTERNAL_SERVER_ERROR,
        details: dict | None = None,
    ):
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)


class NotFoundError(AppException):
    """Resource not found exception."""

    def __init__(self, message: str = "Resource not found", details: dict | None = None):
        super().__init__(message, status.HTTP_404_NOT_FOUND, details)


class ValidationError(AppException):
    """Validation error exception."""

    def __init__(self, message: str = "Validation error", details: dict | None = None):
        super().__init__(message, status.HTTP_422_UNPROCESSABLE_ENTITY, details)


class BadRequestError(AppException):
    """Bad request exception."""

    def __init__(self, message: str = "Bad request", details: dict | None = None):
        super().__init__(message, status.HTTP_400_BAD_REQUEST, details)


async def app_exception_handler(request: Request, exc: AppException) -> JSONResponse:
    """Handle application exceptions."""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": True,
            "message": exc.message,
            "details": exc.details,
        },
    )


async def generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Handle unexpected exceptions."""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": True,
            "message": "An unexpected error occurred",
            "details": {},
        },
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers with the FastAPI app."""
    app.add_exception_handler(AppException, app_exception_handler)
