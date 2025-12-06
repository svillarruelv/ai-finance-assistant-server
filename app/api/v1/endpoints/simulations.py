"""Simulation endpoints for payment projections."""

from decimal import Decimal
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.simulation import (
    CardSimulationResult,
    CustomerCardSimulationsResponse,
    CustomerLoanSimulationsResponse,
    LoanSimulationResult,
)
from app.services.card_simulation import get_customer_cards, simulate_card_payments
from app.services.loan_simulation import get_customer_loans, simulate_loan_payments

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


@router.get(
    "/simulations/loans/{customer_id}",
    response_model=CustomerLoanSimulationsResponse,
    summary="Simulate loan amortization and extra payments",
    description="Simulates paying off all customer loans. Calculates the required "
    "monthly payment (PMT) based on current principal and remaining term. "
    "Allows providing a higher custom monthly payment to simulate prepayment effects "
    "(shorter term, less interest).",
)
async def simulate_customer_loans(
    customer_id: str,
    monthly_payment: Annotated[
        Decimal | None,
        Query(
            description="Optional custom monthly payment amount. "
            "If provided, this amount is used if higher than the required minimum.",
            ge=0,
        ),
    ] = None,
    db: AsyncSession = Depends(get_db),
) -> CustomerLoanSimulationsResponse:
    """Simulate amortization for all customer loans.
    
    Args:
        customer_id: Customer's external ID (e.g., 'CU-003')
        monthly_payment: Optional custom monthly payment
        db: Database session
    
    Returns:
        Simulation results for each loan
    
    Raises:
        404: Customer not found
    """
    customer, loans = await get_customer_loans(db, customer_id)
    
    if customer is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with external_id '{customer_id}' not found",
        )
    
    simulations: list[LoanSimulationResult] = []
    for loan in loans:
        result = simulate_loan_payments(loan, monthly_payment)
        simulations.append(result)
    
    return CustomerLoanSimulationsResponse(
        customer_id=customer_id,
        simulations=simulations,
    )
