"""API v1 router aggregator."""

from fastapi import APIRouter

from app.api.v1.endpoints import health, simulations, strategies

api_router = APIRouter()

# Include endpoint routers
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(simulations.router, tags=["Simulations"])
api_router.include_router(strategies.router, tags=["Strategies"])

