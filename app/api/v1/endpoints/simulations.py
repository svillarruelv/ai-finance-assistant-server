"""Simulation endpoints for payment projections."""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.simulation import (
    CardSimulationResult,
    CustomerCardSimulationsResponse,
)
from app.services.card_simulation import get_customer_cards, simulate_card_payments

router = APIRouter()


@router.get(
    "/simulations/cards/{customer_id}",
    response_model=CustomerCardSimulationsResponse,
    summary="Simulate credit card minimum payment payoff",
    description="Simulates paying off all credit cards for a customer using minimum "
    "payments (or a custom monthly payment). Returns a month-by-month schedule "
    "until debt is fully paid.",
)
async def simulate_customer_cards(
    customer_id: str,
    monthly_payment: Annotated[
        Decimal | None,
        Query(
            description="Optional custom monthly payment amount. "
            "If not provided, uses each card's minimum payment percentage.",
            ge=0,
        ),
    ] = None,
    db: AsyncSession = Depends(get_db),
) -> CustomerCardSimulationsResponse:
    """Simulate minimum payment payoff for all customer credit cards.
    
    Args:
        customer_id: Customer's external ID (e.g., 'CU-003')
        monthly_payment: Optional custom payment amount per month
        db: Database session
    
    Returns:
        Simulation results for each credit card
    
    Raises:
        404: Customer not found
    """
    customer, cards = await get_customer_cards(db, customer_id)
    
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with external_id '{customer_id}' not found",
        )
    
    simulations: list[CardSimulationResult] = []
    for card in cards:
        result = simulate_card_payments(card, monthly_payment)
        simulations.append(result)
    
    return CustomerCardSimulationsResponse(
        customer_id=customer_id,
        simulations=simulations,
    )
