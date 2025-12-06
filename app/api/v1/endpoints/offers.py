from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_db
from app.schemas.offer import EligibilityResponse
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
