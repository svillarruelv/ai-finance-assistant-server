from decimal import Decimal
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.models.customer import Customer
from app.models.bank_offer import BankOffer
from app.services.card_simulation import get_customer_cards, simulate_card_payments
from app.services.loan_simulation import get_customer_loans, simulate_loan_payments, simulate_simple_loan_data, calculate_pmt
from app.services.consolidation import simulate_offer_consolidation_strategies
from app.services.strategy_simulation import generate_strategies, SimulationDebt, simulate_strategy, calculate_payment_capacity
from app.utils.interest_rates import tea_to_tem


async def run_minimum_payment_simulation(customer_id: str) -> dict:
    """
    Run a simulation where the customer ONLY pays minimums on cards and standard monthly payments on loans.
    This serves as the 'Baseline' to compare savings against.
    Returns DETAILED per-product breakdown.
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
        
        # Detailed per-product info
        products = []
        for c in card_results:
            products.append({
                "id": c.card_id,
                "type": "card",
                "initial_balance": str(c.initial_balance),
                "annual_rate": str(c.annual_rate_pct),
                "total_interest": str(c.total_interest_paid),
                "total_months": c.total_months,
                "monthly_payment": str(c.payment_used)
            })
        for l in loan_results:
            products.append({
                "id": l.loan_id,
                "type": "loan",
                "initial_balance": str(l.principal),
                "annual_rate": str(l.annual_rate_pct),
                "total_interest": str(l.total_interest_paid),
                "total_months": l.total_months,
                "monthly_payment": str(l.payment_used)
            })
            
        return {
            "scenario": "Minimum Payment Baseline",
            "total_interest_paid": str(total_interest),
            "max_months_to_debt_free": max_months,
            "products": products
        }


async def fetch_customer_profile(customer_id: str) -> dict:
    """Fetch customer financial profile (income, expenses)."""
    async with SessionLocal() as db:
        stmt = select(Customer).where(Customer.external_id == customer_id)
        cust = (await db.execute(stmt)).scalar_one_or_none()
        if not cust:
            return {"error": "Customer not found"}
        
        # Calculate payment capacity
        capacities = calculate_payment_capacity(cust)
            
        return {
            "monthly_income": str(cust.monthly_income_avg),
            "essential_expenses": str(cust.essential_expenses_avg),
            "income_variability": str(cust.income_variability_pct),
            "base_payment_capacity": str(capacities["Base"]),
            "conservative_payment_capacity": str(capacities["Conservative"])
        }


async def fetch_debts(customer_id: str) -> dict:
    """Fetch all customer debts (cards and loans) with detailed info."""
    async with SessionLocal() as db:
        _, cards = await get_customer_cards(db, customer_id)
        _, loans = await get_customer_loans(db, customer_id)
        
        debts = []
        
        # Add cards with minimum payment simulation
        for c in cards:
            sim = simulate_card_payments(c)
            debts.append({
                "id": c.external_id,
                "type": "card",
                "days_past_due": c.days_past_due,
                "rate": str(c.annual_rate_pct),
                "balance": str(c.balance),
                "min_payment_pct": str(c.min_payment_pct),
                "monthly_min_payment": str(sim.payment_used),
                "months_to_payoff_min": sim.total_months,
                "total_interest_min": str(sim.total_interest_paid)
            })
        
        # Add loans with standard payment simulation
        for l in loans:
            sim = simulate_loan_payments(l)
            debts.append({
                "id": l.external_id,
                "type": "loan",
                "loan_subtype": l.loan_type,
                "days_past_due": l.days_past_due,
                "rate": str(l.annual_rate_pct),
                "principal": str(l.principal),
                "remaining_months": l.remaining_term_months,
                "monthly_payment": str(sim.payment_used),
                "months_to_payoff": sim.total_months,
                "total_interest": str(sim.total_interest_paid)
            })
            
        return {"debts": debts}


async def run_consolidation_simulation(customer_id: str) -> dict:
    """Run consolidation simulations for bank offers."""
    async with SessionLocal() as db:
        result = await simulate_offer_consolidation_strategies(db, customer_id)
        return result.model_dump(mode="json")


async def run_payoff_strategies(customer_id: str) -> list[dict]:
    """Run Avalanche and Snowball payoff strategies on ALL current debts."""
    async with SessionLocal() as db:
        results = await generate_strategies(db, customer_id)
        return [r.model_dump(mode="json") for r in results]


async def run_hybrid_strategy(customer_id: str, strategy: str = "avalanche") -> dict:
    """
    Simulate a HYBRID approach:
    1. Consolidate only eligible debts with the best offer
    2. Apply Avalanche/Snowball to the consolidated loan + remaining non-eligible debts
    
    This helps compare:
    - Pure strategy (pay all debts at original rates)
    - Hybrid (consolidate eligible → pay consolidated + remaining with strategy)
    """
    async with SessionLocal() as db:
        # 1. Get customer and all debts
        stmt_cust = select(Customer).where(Customer.external_id == customer_id)
        cust = (await db.execute(stmt_cust)).scalar_one_or_none()
        if not cust:
            return {"error": "Customer not found"}
        
        _, cards = await get_customer_cards(db, customer_id)
        _, loans = await get_customer_loans(db, customer_id)
        
        # 2. Get eligible offers
        from app.services.offers import get_eligible_offers
        metrics, offers = await get_eligible_offers(db, customer_id)
        
        if not offers:
            return {"scenario": "hybrid", "available": False, "reason": "No eligible offers"}
        
        # 3. Find best offer (lowest rate)
        best_offer = min(offers, key=lambda o: o.new_rate_pct)
        eligible_types = set(best_offer.product_types_eligible)
        
        # 4. Identify which debts get consolidated vs remain
        consolidated_debts = []
        remaining_debts = []
        consolidated_balance = Decimal("0")
        
        for c in cards:
            if "card" in eligible_types and consolidated_balance + c.balance <= best_offer.max_consolidated_balance:
                consolidated_debts.append({"id": c.external_id, "type": "card", "balance": c.balance, "rate": c.annual_rate_pct})
                consolidated_balance += c.balance
            else:
                remaining_debts.append(SimulationDebt(
                    debt_id=c.external_id, type_="card", balance=c.balance,
                    rate=c.annual_rate_pct, min_payment_pct=c.min_payment_pct
                ))
        
        for l in loans:
            if l.loan_type in eligible_types and consolidated_balance + l.principal <= best_offer.max_consolidated_balance:
                consolidated_debts.append({"id": l.external_id, "type": "loan", "balance": l.principal, "rate": l.annual_rate_pct})
                consolidated_balance += l.principal
            else:
                remaining_debts.append(SimulationDebt(
                    debt_id=l.external_id, type_="loan", balance=l.principal,
                    rate=l.annual_rate_pct, remaining_term=l.remaining_term_months
                ))
        
        if consolidated_balance <= 0:
            return {"scenario": "hybrid", "available": False, "reason": "No debts eligible for consolidation"}
        
        # 5. Create consolidated loan as a new SimulationDebt
        monthly_rate = tea_to_tem(best_offer.new_rate_pct) / Decimal("100")
        consolidated_loan = SimulationDebt(
            debt_id=f"consolidated_{best_offer.offer_id}",
            type_="loan",
            balance=consolidated_balance,
            rate=best_offer.new_rate_pct,
            remaining_term=best_offer.max_term_months
        )
        
        # 6. Combine consolidated loan + remaining debts
        all_debts_post_consolidation = [consolidated_loan] + remaining_debts
        
        # 7. Get payment capacity
        capacities = calculate_payment_capacity(cust)
        capacity = capacities["Base"]
        
        # 8. Run strategy simulation on post-consolidation portfolio
        method = "avalanche" if strategy.lower() == "avalanche" else "snowball"
        result = simulate_strategy(all_debts_post_consolidation, capacity, method)
        
        return {
            "scenario": f"hybrid_{method}",
            "offer_used": best_offer.offer_id,
            "offer_rate": str(best_offer.new_rate_pct),
            "consolidated_products": [d["id"] for d in consolidated_debts],
            "consolidated_balance": str(consolidated_balance),
            "remaining_products": [d.id for d in remaining_debts],
            "total_months": result["months"],
            "total_interest_paid": str(result["total_interest"]),
            "freedom_date": str(result["freedom_date"]) if result.get("freedom_date") else None,
            "monthly_payment": str(capacity)
        }
