"""Debt strategy simulation endpoints."""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.simulation import CustomerStrategyResponse
from app.services.strategy_simulation import generate_strategies
from app.models.customer import Customer
from sqlalchemy import select

router = APIRouter()


@router.get(
    "/simulations/strategies/{customer_id}",
    response_model=CustomerStrategyResponse,
    summary="Generate debt payoff strategies (Avalanche/Snowball)",
    description="Simulates debt payoff using Avalanche (highest interest first) and "
    "Snowball (lowest balance first) methods. Calculates results for both "
    "'Base' (avg income) and 'Conservative' (low income) payment capacities.",
)
async def get_debt_strategies(
    customer_id: str,
    db: AsyncSession = Depends(get_db),
) -> CustomerStrategyResponse:
    """Generate debt strategies for a customer.
    
    Args:
        customer_id: Customer's external ID (e.g., 'CU-003')
        db: Database session
    
    Returns:
        Four strategy scenarios
    
    Raises:
        404: Customer not found
    """
    # Quick check if customer exists first (service does it too but good for explicit 404)
    stmt = select(Customer).where(Customer.external_id == customer_id)
    cust = (await db.execute(stmt)).scalar_one_or_none()
    
    if not cust:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Customer with external_id '{customer_id}' not found",
        )
        
    strategies = await generate_strategies(db, customer_id)
    
    recommended = None
    if strategies:
        # recommend strategy with lowest total interest
        best = min(strategies, key=lambda s: s.total_interest_paid)
        recommended = best.strategy_name

    return CustomerStrategyResponse(
        customer_id=customer_id,
        recommended_strategy=recommended,
        strategies=strategies,
    )
