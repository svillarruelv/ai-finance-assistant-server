"""Simulation schemas for credit card payment simulations."""

from decimal import Decimal

from pydantic import BaseModel, Field


class MonthlyPaymentDetail(BaseModel):
    """Detail of a single month's payment in the simulation."""

    month: int = Field(..., ge=1, description="Month number (1-indexed)")
    starting_balance: Decimal = Field(..., description="Balance at start of month")
    payment: Decimal = Field(..., description="Payment made this month")
    interest_charged: Decimal = Field(..., description="Interest charged this month")
    ending_balance: Decimal = Field(..., description="Balance after payment and interest")
    total_paid: Decimal = Field(..., description="Cumulative total paid up to this month")
    total_interest: Decimal = Field(
        ..., description="Cumulative total interest up to this month"
    )


class CardSimulationResult(BaseModel):
    """Result of simulating minimum payments on a single credit card."""

    card_id: str = Field(..., description="External card ID")
    initial_balance: Decimal = Field(..., description="Starting card balance")
    annual_rate_pct: Decimal = Field(..., description="Annual interest rate (TEA)")
    monthly_rate_pct: Decimal = Field(..., description="Monthly interest rate (TEM)")
    min_payment_pct: Decimal = Field(..., description="Minimum payment percentage")
    days_past_due: int = Field(..., description="Days past due at simulation start")
    past_due_fee: Decimal = Field(..., description="Past due penalty on first payment")
    payment_used: Decimal = Field(
        ..., description="Monthly payment used (custom or minimum)"
    )
    total_months: int = Field(..., description="Total months to pay off debt")
    total_paid: Decimal = Field(..., description="Total amount paid")
    total_interest_paid: Decimal = Field(..., description="Total interest paid")
    monthly_schedule: list[MonthlyPaymentDetail] = Field(
        ..., description="Month-by-month payment schedule"
    )


class CustomerCardSimulationsResponse(BaseModel):
    """Response containing simulations for all customer cards."""

    customer_id: str = Field(..., description="Customer external ID")
    simulations: list[CardSimulationResult] = Field(
        ..., description="Simulation results for each card"
    )


class LoanSimulationResult(BaseModel):
    """Result of simulating payments on a single loan."""

    loan_id: str = Field(..., description="External loan ID")
    product_type: str = Field(..., description="Loan type (personal/micro)")
    principal: Decimal = Field(..., description="Current principal balance")
    annual_rate_pct: Decimal = Field(..., description="Annual interest rate (TEA)")
    monthly_rate_pct: Decimal = Field(..., description="Monthly interest rate (TEM)")
    remaining_term_months: int = Field(..., description="Remaining term in months")
    calculated_monthly_payment: Decimal = Field(
        ..., description="Minimum monthly payment required to pay off in term"
    )
    payment_used: Decimal = Field(
        ..., description="Monthly payment used (custom or calculated)"
    )
    start_days_past_due: int = Field(..., description="Days past due at start")
    past_due_fee: Decimal = Field(..., description="Penalty fee for past due")
    total_months: int = Field(..., description="Actual months to pay off")
    total_paid: Decimal = Field(..., description="Total amount paid")
    total_interest_paid: Decimal = Field(..., description="Total interest paid")
    monthly_schedule: list[MonthlyPaymentDetail] = Field(
        ..., description="Month-by-month amortization schedule"
    )


class CustomerLoanSimulationsResponse(BaseModel):
    """Response containing simulations for all customer loans."""

    customer_id: str = Field(..., description="Customer external ID")
    simulations: list[LoanSimulationResult] = Field(
        ..., description="Simulation results for each loan"
    )
