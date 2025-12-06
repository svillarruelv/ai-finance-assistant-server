from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.core.db import SessionLocal
from app.models.customer import Customer
from app.services.card_simulation import get_customer_cards, simulate_card_payments
from app.services.loan_simulation import get_customer_loans, simulate_loan_payments
from app.services.consolidation import simulate_offer_consolidation_strategies
from app.services.strategy_simulation import generate_strategies

async def run_minimum_payment_simulation(customer_id: str) -> dict:
    """
    Run a simulation where the customer ONLY pays minimums on cards and standard monthly payments on loans.
    This serves as the 'Baseline' to compare savings against.
    """
    async with SessionLocal() as db:
        # Fetch Cards
        _, cards = await get_customer_cards(db, customer_id)
        card_results = [simulate_card_payments(c) for c in cards]
        
        # Fetch Loans
        _, loans = await get_customer_loans(db, customer_id)
        loan_results = [simulate_loan_payments(l) for l in loans]
        
        total_interest = sum(r.total_interest_paid for r in card_results) + sum(r.total_interest_paid for r in loan_results)
        max_months = 0
        if card_results:
            max_months = max(max_months, max(r.total_months for r in card_results))
        if loan_results:
            max_months = max(max_months, max(r.total_months for r in loan_results))
            
        return {
            "scenario": "Minimum Payment Baseline",
            "total_interest_paid": str(total_interest),
            "max_months_to_debt_free": max_months,
            "details": {
                "cards": [c.model_dump(mode="json", exclude={"monthly_schedule"}) for c in card_results],
                "loans": [l.model_dump(mode="json", exclude={"monthly_schedule"}) for l in loan_results]
            }
        }

async def fetch_customer_profile(customer_id: str) -> dict:
    """Fetch customer financial profile (income, expenses)."""
    async with SessionLocal() as db:
        stmt = select(Customer).where(Customer.external_id == customer_id)
        cust = (await db.execute(stmt)).scalar_one_or_none()
        if not cust:
            return {"error": "Customer not found"}
            
        return {
            "monthly_income": str(cust.monthly_income_avg),
            "essential_expenses": str(cust.essential_expenses_avg),
            "income_variability": str(cust.income_variability_pct),
        }

async def fetch_debts(customer_id: str) -> dict:
    """Fetch all customer debts (cards and loans)."""
    async with SessionLocal() as db:
        # Use the proper async-safe functions to avoid polymorphic lazy-loading issues
        _, cards = await get_customer_cards(db, customer_id)
        _, loans = await get_customer_loans(db, customer_id)
        
        debts = []
        
        # Add cards
        for c in cards:
            debts.append({
                "id": c.external_id,
                "type": "card",
                "days_past_due": c.days_past_due,
                "rate": str(c.annual_rate_pct),
                "balance": str(c.balance),
                "min_payment_pct": str(c.min_payment_pct)
            })
        
        # Add loans
        for l in loans:
            debts.append({
                "id": l.external_id,
                "type": "loan",
                "days_past_due": l.days_past_due,
                "rate": str(l.annual_rate_pct),
                "principal": str(l.principal),
                "loan_type": l.loan_type,
                "remaining_months": l.remaining_term_months
            })
            
        return {"debts": debts}

async def run_consolidation_simulation(customer_id: str) -> dict:
    """Run consolidation simulations for bank offers."""
    async with SessionLocal() as db:
        # This service returns a Pydantic model response
        result = await simulate_offer_consolidation_strategies(db, customer_id)
        # Convert to dict for agent
        return result.model_dump(mode="json")

async def run_payoff_strategies(customer_id: str) -> list[dict]:
    """Run Avalanche and Snowball payoff strategies."""
    async with SessionLocal() as db:
         # generate_strategies returns list[StrategyResult]
         results = await generate_strategies(db, customer_id)
         return [r.model_dump(mode="json") for r in results]
