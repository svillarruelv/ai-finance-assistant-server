"""Health check endpoints."""

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import SettingsDep
from app.core.db import get_db
from app.schemas.common import HealthResponse

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check(
    settings: SettingsDep,
    db: AsyncSession = Depends(get_db),
) -> HealthResponse:
    """
    Health check endpoint for readiness/liveness probes.

    Returns the current status, version, and database connectivity.
    """
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception as e:
        db_status = f"error: {e}"

    return HealthResponse(
        status="healthy" if db_status == "connected" else "unhealthy",
        version=settings.app_version,
        database=db_status,
    )
