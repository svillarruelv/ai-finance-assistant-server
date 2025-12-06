from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.card import Card
from app.models.customer import Customer
from app.models.loan import Loan
from app.schemas.simulation import (
    CustomerLoanSimulationsResponse,
    LoanSimulationResult,
)
from app.services.loan_simulation import (
    calculate_pmt,
    simulate_simple_loan_data
)
from app.services.offers import get_eligible_offers
from app.services.strategy_simulation import (
    calculate_payment_capacity,
    SimulationDebt
)
from app.utils.interest_rates import tea_to_tem


async def simulate_offer_consolidation_strategies(
    db: AsyncSession, customer_id: str
) -> CustomerLoanSimulationsResponse:
    """Generate consolidation simulations for eligible offers.
    
    For each eligible offer:
    1. Filter existing debts by eligible product types.
    2. Sum balances up to max_consolidated_balance.
    3. Simulate a new loan with offer terms (rate, max term).
    4. Optimize: If customer MAX cash flow > required payment, 
       reduce term by paying more (up to max cash flow).
    """
    
    # 1. Get Customer (verify existence)
    stmt_cust = select(Customer).where(Customer.external_id == customer_id)
    cust = (await db.execute(stmt_cust)).scalar_one_or_none()
    
    if not cust:
        # Return empty structure or raise 404
        # Schema requires customer_id, so we return empty list if cust not found 
        # (though usually this would be handled by endpoint validation)
        return CustomerLoanSimulationsResponse(
            customer_id=customer_id,
            simulations=[]
        )

    # 2. Get Eligible Offers
    metrics, offers = await get_eligible_offers(db, customer_id)
    if not offers:
        return CustomerLoanSimulationsResponse(
            customer_id=customer_id,
            simulations=[]
        )
        
    # 3. Get All Debts to Consolidate
    stmt_cards = select(Card).where(Card.customer_id == cust.id)
    cards = list((await db.execute(stmt_cards)).scalars().all())
    
    stmt_loans = select(Loan).where(Loan.customer_id == cust.id)
    loans = list((await db.execute(stmt_loans)).scalars().all())
    
    # 4. Get Payment Capacity
    capacities = calculate_payment_capacity(cust)
    base_capacity = capacities["Base"] # Max cash flow available
    
    simulations = []
    
    for offer in offers:
        eligible_types = set(offer.product_types_eligible) # e.g. ["card", "loan"] or ["personal", "micro"]? 
        # Note: product_types_eligible is a list of strings.
        # We need to match debt types to these.
        # Cards are "card". Loans are "personal" or "micro".
        
        candidates = []
        
        # We need more info for excluded debt calculation (rate/min_payment_pct)
        if "card" in eligible_types:
            for c in cards:
                candidates.append({
                    "id": c.external_id,
                    "balance": c.balance,
                    "type": "card",
                    "rate": c.annual_rate_pct,
                    "min_payment_pct": c.min_payment_pct,
                    "remaining_term": 0
                })
                
        for l in loans:
            if l.loan_type in eligible_types:
                candidates.append({
                    "id": l.external_id,
                    "balance": l.principal,
                    "type": l.loan_type,
                    "rate": l.annual_rate_pct,
                    "min_payment_pct": Decimal("0"),
                    "remaining_term": l.remaining_term_months
                })
        
        # Sort candidates to prioritize consolidation? 
        # Typically highest interest rate first (Avalanche prioritization for consolidation)
        candidates.sort(key=lambda x: x["rate"], reverse=True)
        
        consolidated_balance = Decimal("0")
        included_debts = []
        excluded_debts = []
        
        for debt in candidates:
            if consolidated_balance + debt["balance"] <= offer.max_consolidated_balance:
                consolidated_balance += debt["balance"]
                included_debts.append(debt)
            else:
                excluded_debts.append(debt)
        
        if consolidated_balance <= 0:
            continue

        included_ids = set(d["id"] for d in included_debts)

        # Calculate Minimum Payment for NON-ELIGIBLE Debts Only
        # Per user request: "instead of excluded candidates you should calculate the max offering based on the non eligible types of debts"
        # We subtract the obligations of debts that CANNOT be consolidated (wrong type).
        # We DO NOT subtract the obligations of eligible debts that simply didn't fit (excluded candidates).
        other_obligations = Decimal("0")
        
        # Helper to calc min payment
        def get_min_pmt(d_obj, d_type):
            sim_d = SimulationDebt(
                debt_id=d_obj.external_id,
                type_=d_type,
                balance=d_obj.balance if d_type == "card" else d_obj.principal,
                rate=d_obj.annual_rate_pct,
                min_payment_pct=d_obj.min_payment_pct if d_type == "card" else Decimal("0"),
                remaining_term=0 if d_type == "card" else d_obj.remaining_term_months
            )
            return sim_d.calculate_minimum_payment(month_idx=2)

        # Check all cards
        for c in cards:
            if c.external_id not in included_ids:
                other_obligations += get_min_pmt(c, "card")
                
        # Check all loans
        for l in loans:
            if l.external_id not in included_ids:
                monthly_rate = tea_to_tem(l.annual_rate_pct) / Decimal("100")
                other_obligations += calculate_pmt(l.principal, monthly_rate, l.remaining_term_months)

        remaining_capacity_for_offer = max(base_capacity - other_obligations, Decimal("0"))

        # Simulation Parameters
        new_rate = offer.new_rate_pct
        max_term = offer.max_term_months
        
        # 1. Standard Simulation (Min PMT)
        monthly_rate = tea_to_tem(new_rate) / Decimal("100")
        min_pmt = calculate_pmt(consolidated_balance, monthly_rate, max_term)
        
        sim_standard = simulate_simple_loan_data(
            principal=consolidated_balance,
            annual_rate_pct=new_rate,
            term_months=max_term,
            product_type="consolidation_offer_standard",
            loan_id=f"offer_{offer.offer_id}_std",
            custom_payment=None,
            start_days_past_due=0,
            consolidated_product_ids=list(included_ids)
        )
        simulations.append(sim_standard)

        # 2. Optimized (Max Cash Flow adjusted for non-eligible debts)
        # Only if remaining capacity > minimum required for the offer
        if remaining_capacity_for_offer > min_pmt:
            sim_optimized = simulate_simple_loan_data(
                principal=consolidated_balance,
                annual_rate_pct=new_rate,
                term_months=max_term,
                product_type="consolidation_offer_optimized",
                loan_id=f"offer_{offer.offer_id}_opt",
                custom_payment=remaining_capacity_for_offer,
                start_days_past_due=0,
                consolidated_product_ids=list(included_ids)
            )
            simulations.append(sim_optimized)
        
    return CustomerLoanSimulationsResponse(
        customer_id=customer_id,
        simulations=simulations
    )
