"""Loan simulation service for amortization simulations."""

from decimal import Decimal, ROUND_HALF_UP, ROUND_UP

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.customer import Customer
from app.models.loan import Loan
from app.schemas.simulation import (
    LoanSimulationResult,
    MonthlyPaymentDetail,
)
from app.utils.interest_rates import tea_to_ted, tea_to_tem


async def get_customer_loans(
    db: AsyncSession, customer_external_id: str
) -> tuple[Customer | None, list[Loan]]:
    """Get all loans for a customer by their external ID.
    
    Args:
        db: Database session
        customer_external_id: Customer's external ID (e.g., 'CU-003')
    
    Returns:
        Tuple of (customer, list of loans). Customer is None if not found.
    """
    # 1. Get Customer to ensure they exist
    stmt_customer = select(Customer).where(Customer.external_id == customer_external_id)
    result_customer = await db.execute(stmt_customer)
    customer = result_customer.scalar_one_or_none()
    
    if customer is None:
        return None, []
    
    # 2. Get Loans directly
    stmt_loans = select(Loan).where(Loan.customer_id == customer.id)
    result_loans = await db.execute(stmt_loans)
    loans = list(result_loans.scalars().all())
    
    return customer, loans


def calculate_pmt(principal: Decimal, monthly_rate: Decimal, months: int) -> Decimal:
    """Calculate fixed monthly payment (PMT) for a loan.
    
    Formula: PMT = P * (r * (1 + r)^n) / ((1 + r)^n - 1)
    
    Args:
        principal: Loan principal amount (P)
        monthly_rate: Monthly interest rate as decimal (r)
        months: Number of months (n)
        
    Returns:
        Fixed monthly payment amount
    """
    if monthly_rate == 0:
        return principal / Decimal(months) if months > 0 else principal
    
    if months <= 0:
        return principal
        
    factor = (Decimal("1") + monthly_rate) ** Decimal(months)
    pmt = principal * (monthly_rate * factor) / (factor - Decimal("1"))
    # Round UP to ensure we cover the full principal within the term
    # avoiding "0.15 remainder" pushing into month N+1
    return pmt.quantize(Decimal("0.5"), rounding=ROUND_UP)


def simulate_simple_loan_data(
    principal: Decimal,
    annual_rate_pct: Decimal,
    term_months: int,
    product_type: str,
    loan_id: str = "simulation",
    custom_payment: Decimal | None = None,
    start_days_past_due: int = 0,
    consolidated_product_ids: list[str] | None = None
) -> LoanSimulationResult:
    """Simulate paying off a loan with raw data parameters.
    
    Args:
        principal: Loan principal amount
        annual_rate_pct: Annual interest rate (TEA)
        term_months: Remaining term in months
        product_type: Type of loan (for reporting)
        loan_id: ID for the simulation result
        custom_payment: Optional custom monthly payment.
                        If None, uses calculated PMT based on term.
        start_days_past_due: Days past due at start
        consolidated_product_ids: Optional list of consolidated debt IDs
        
    Returns:
        LoanSimulationResult with amortization schedule
    """
    # Convert rates
    monthly_rate_pct = tea_to_tem(annual_rate_pct)
    daily_rate_pct = tea_to_ted(annual_rate_pct)
    
    monthly_rate = monthly_rate_pct / Decimal("100")
    daily_rate = daily_rate_pct / Decimal("100")
    
    # Calculate required base payment (PMT)
    base_payment = calculate_pmt(principal, monthly_rate, term_months)
    
    # Determine actual payment to use (max of base or custom)
    if custom_payment is not None:
        payment_used = max(custom_payment, base_payment)
    else:
        payment_used = base_payment

    # Calculate past due fee (only applied on first payment)
    past_due_fee = Decimal("0")
    if start_days_past_due > 0:
        past_due_fee = (daily_rate * start_days_past_due * principal).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    
    monthly_schedule: list[MonthlyPaymentDetail] = []
    cumulative_paid = Decimal("0")
    cumulative_interest = Decimal("0")
    month = 0
    balance = principal
    
    # Safety limit
    max_months = 1200 
    
    while balance > Decimal("0.01") and month < max_months:
        month += 1
        starting_balance = balance
        
        current_payment = payment_used
        
        # Add past due fee to first payment only
        if month == 1 and past_due_fee > 0:
            current_payment = current_payment + past_due_fee
        
        # Calculate interest for this month
        interest = (balance * monthly_rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        
        # Cap payment at total amount needed to clear debt this month
        amount_needed = balance + interest
        if month == 1:
            amount_needed += past_due_fee
            
        if current_payment >= amount_needed:
            current_payment = amount_needed
            
        # Allocation
        remaining_payment = current_payment
        fee_paid = Decimal("0")
        
        if month == 1 and past_due_fee > 0:
            fee_paid = min(remaining_payment, past_due_fee)
            remaining_payment -= fee_paid
        
        interest_paid = min(remaining_payment, interest)
        remaining_payment -= interest_paid
        
        principal_paid = remaining_payment
        
        # Update balance
        balance = balance - principal_paid
        
        # Update cumulative
        cumulative_paid += current_payment
        cumulative_interest += interest_paid
        
        monthly_schedule.append(
            MonthlyPaymentDetail(
                month=month,
                starting_balance=starting_balance,
                payment=current_payment,
                interest_charged=interest_paid,
                ending_balance=max(balance, Decimal("0")),
                total_paid=cumulative_paid,
                total_interest=cumulative_interest,
            )
        )
        
        if balance <= Decimal("0.01"):
            balance = Decimal("0")
            break
            
    return LoanSimulationResult(
        loan_id=loan_id,
        product_type=product_type,
        consolidated_product_ids=consolidated_product_ids,
        principal=principal,
        annual_rate_pct=annual_rate_pct,
        monthly_rate_pct=monthly_rate_pct,
        remaining_term_months=term_months,
        calculated_monthly_payment=base_payment,
        payment_used=payment_used,
        start_days_past_due=start_days_past_due,
        past_due_fee=past_due_fee,
        total_months=month,
        total_paid=cumulative_paid,
        total_interest_paid=cumulative_interest,
        monthly_schedule=monthly_schedule,
    )


def simulate_loan_payments(
    loan: Loan, 
    monthly_payment: Decimal | None = None
) -> LoanSimulationResult:
    """Simulate paying off a loan with fixed or custom payments.
    
    Args:
        loan: The loan to simulate
        monthly_payment: Optional custom monthly payment. 
                        If None, uses calculated PMT based on remaining term.
    
    Returns:
        LoanSimulationResult with amortization schedule
    """
    return simulate_simple_loan_data(
        principal=loan.principal,
        annual_rate_pct=loan.annual_rate_pct,
        term_months=loan.remaining_term_months,
        product_type=loan.loan_type,
        loan_id=loan.external_id,
        custom_payment=monthly_payment,
        start_days_past_due=loan.days_past_due
    )
