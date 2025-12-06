"""API v1 router aggregator."""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    health,
    offers,
    simulations,
    strategies,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(simulations.router, prefix="/simulations", tags=["simulations"])
api_router.include_router(strategies.router, prefix="/simulations/strategies", tags=["strategies"])
api_router.include_router(offers.router, prefix="/offers", tags=["offers"])
