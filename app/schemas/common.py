"""Common schemas used across the application."""

from typing import Any, Generic, TypeVar

from pydantic import BaseModel

DataT = TypeVar("DataT")


class HealthResponse(BaseModel):
    """Health check response schema."""

    status: str
    version: str
    database: str | None = None


class APIResponse(BaseModel, Generic[DataT]):
    """Standard API response wrapper."""

    success: bool = True
    message: str = "Operation completed successfully"
    data: DataT | None = None


class ErrorResponse(BaseModel):
    """Error response schema."""

    error: bool = True
    message: str
    details: dict[str, Any] = {}
