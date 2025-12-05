"""Health check endpoints."""

from fastapi import APIRouter

from app.api.deps import SettingsDep
from app.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(settings: SettingsDep) -> HealthResponse:
    """
    Health check endpoint for readiness/liveness probes.

    Returns the current status and version of the application.
    """
    return HealthResponse(
        status="healthy",
        version=settings.app_version,
    )
