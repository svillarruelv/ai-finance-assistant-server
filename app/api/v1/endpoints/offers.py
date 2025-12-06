from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.offer import EligibilityResponse
from app.schemas.simulation import CustomerLoanSimulationsResponse
from app.services.consolidation import simulate_offer_consolidation_strategies
from app.services.offers import get_eligible_offers

router = APIRouter()


@router.get("/eligibility/{customer_id}", response_model=EligibilityResponse)
async def check_eligibility(
    customer_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Check which bank offers a customer is eligible for based on:
    - Current Credit Score
    - Maximum Days Past Due (Mora)
    """
    metrics, offers = await get_eligible_offers(db, customer_id)
    
    if metrics is None:
        raise HTTPException(status_code=404, detail="Customer not found")
        
    return EligibilityResponse(
        customer_id=customer_id,
        current_credit_score=metrics.credit_score,
        max_days_past_due=metrics.max_days_past_due,
        eligible_offers=offers
    )


@router.get("/simulation/{customer_id}", response_model=CustomerLoanSimulationsResponse)
async def simulate_offers(
    customer_id: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Run simulations for all eligible bank offers.
    
    This simulation:
    1. Identifies eligible offers for the customer.
    2. Groups eligible existing debts (Cards/Loans).
    3. Simulates consolidating them into the Offer's terms.
    4. Optimizes the term by using the customer's maximum cash flow (Base Capacity)
       to pay down the debt faster than the offer's max term, if possible.
    """
    return await simulate_offer_consolidation_strategies(db, customer_id)
