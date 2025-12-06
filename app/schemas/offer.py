from decimal import Decimal
from typing import Optional

from pydantic import BaseModel, Field


class BankOfferResponse(BaseModel):
    """Schema for returning a bank offer."""
    
    offer_id: str = Field(..., description="Unique ID of the offer")
    product_types_eligible: list[str] = Field(..., description="Eligible product types (e.g. card, loan)")
    max_consolidated_balance: Decimal = Field(..., description="Max balance available to consolidate")
    new_rate_pct: Decimal = Field(..., description="New annual interest rate")
    max_term_months: int = Field(..., description="Maximum term in months")
    
    # Conditions
    min_credit_score: Optional[int] = Field(None, description="Minimum credit score required")
    max_days_past_due: Optional[int] = Field(None, description="Maximum days past due allowed")
    conditions_description: Optional[str] = Field(None, description="Human readable conditions")
    
    class Config:
        from_attributes = True


class EligibilityResponse(BaseModel):
    """Response checking eligibility for a customer."""
    
    customer_id: str = Field(..., description="Customer external ID")
    current_credit_score: Optional[int] = Field(None, description="Customer's latest credit score")
    max_days_past_due: int = Field(..., description="Customer's maximum current days past due")
    eligible_offers: list[BankOfferResponse] = Field(..., description="List of offers the customer qualifies for")
