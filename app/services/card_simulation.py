"""Card simulation service for minimum payment simulations."""

from decimal import Decimal, ROUND_HALF_UP

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.card import Card
from app.models.customer import Customer
from app.schemas.simulation import (
    CardSimulationResult,
    MonthlyPaymentDetail,
)
from app.utils.interest_rates import tea_to_ted, tea_to_tem


async def get_customer_cards(
    db: AsyncSession, customer_external_id: str
) -> tuple[Customer | None, list[Card]]:
    """Get all credit cards for a customer by their external ID.
    
    Args:
        db: Database session
        customer_external_id: Customer's external ID (e.g., 'CU-003')
    
    Returns:
        Tuple of (customer, list of cards). Customer is None if not found.
    """
    # 1. Get Customer to ensure they exist
    stmt_customer = select(Customer).where(Customer.external_id == customer_external_id)
    result_customer = await db.execute(stmt_customer)
    customer = result_customer.scalar_one_or_none()
    
    if customer is None:
        return None, []
    
    # 2. Get Cards directly
    # Fetching Card directly ensures SQLAlchemy loads all subclass attributes (joined load)
    # instead of potentially deferring them when accessing via customer.products (polymorphic)
    stmt_cards = select(Card).where(Card.customer_id == customer.id)
    result_cards = await db.execute(stmt_cards)
    cards = list(result_cards.scalars().all())
    
    return customer, cards


def simulate_card_payments(
    card: Card, 
    monthly_payment: Decimal | None = None
) -> CardSimulationResult:
    """Simulate paying off a credit card with minimum or custom payments.
    
    Args:
        card: The credit card to simulate
        monthly_payment: Optional custom monthly payment. If None, uses minimum.
    
    Returns:
        CardSimulationResult with full payment schedule
    """
    # Convert rates
    annual_rate = card.annual_rate_pct
    monthly_rate_pct = tea_to_tem(annual_rate)
    daily_rate_pct = tea_to_ted(annual_rate)
    
    monthly_rate = monthly_rate_pct / Decimal("100")
    daily_rate = daily_rate_pct / Decimal("100")
    min_payment_rate = card.min_payment_pct / Decimal("100")
    
    balance = card.balance
    initial_balance = balance
    days_past_due = card.days_past_due
    
    # Calculate past due fee (only applied on first payment)
    past_due_fee = Decimal("0")
    if days_past_due > 0:
        past_due_fee = (daily_rate * days_past_due * balance).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
    
    monthly_schedule: list[MonthlyPaymentDetail] = []
    cumulative_paid = Decimal("0")
    cumulative_interest = Decimal("0")
    month = 0
    
    # Safety limit to prevent infinite loops
    max_months = 300  # 25 years
    
    while balance > Decimal("0.01") and month < max_months:
        month += 1
        starting_balance = balance
        
        # Calculate payment for this month
        if monthly_payment is not None:
            payment = monthly_payment
        else:
            payment = max((balance * min_payment_rate).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            ), 1)
        
        # Add past due fee to first payment only
        if month == 1 and past_due_fee > 0:
            payment = payment + past_due_fee
        
        # Ensure we don't pay more than the balance
        payment = min(payment, balance)
        
        # Apply payment
        balance = balance - payment
        
        # Calculate and apply interest on remaining balance
        interest = (balance * monthly_rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        balance = balance + interest
        
        # Update cumulative totals
        cumulative_paid += payment
        cumulative_interest += interest
        
        monthly_schedule.append(
            MonthlyPaymentDetail(
                month=month,
                starting_balance=starting_balance,
                payment=payment,
                interest_charged=interest,
                ending_balance=max(balance, Decimal("0")),
                total_paid=cumulative_paid,
                total_interest=cumulative_interest,
            )
        )
        
        # If balance is effectively zero, stop
        if balance <= Decimal("0.01"):
            balance = Decimal("0")
            break
    
    # Determine actual payment used for display
    payment_used = monthly_payment if monthly_payment is not None else (
        initial_balance * min_payment_rate
    ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    
    return CardSimulationResult(
        card_id=card.external_id,
        initial_balance=initial_balance,
        annual_rate_pct=annual_rate,
        monthly_rate_pct=monthly_rate_pct,
        min_payment_pct=card.min_payment_pct,
        days_past_due=days_past_due,
        past_due_fee=past_due_fee,
        payment_used=payment_used,
        total_months=month,
        total_paid=cumulative_paid,
        total_interest_paid=cumulative_interest,
        monthly_schedule=monthly_schedule,
    )
