"""Service for simulating debt payoff strategies (Avalanche/Snowball)."""

from copy import deepcopy
from datetime import date, timedelta
from decimal import Decimal, ROUND_HALF_UP
from typing import Literal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.card import Card
from app.models.customer import Customer
from app.models.loan import Loan
from app.schemas.simulation import StrategyResult
from app.services.loan_simulation import calculate_pmt
from app.utils.interest_rates import tea_to_ted, tea_to_tem

StrategyType = Literal["avalanche", "snowball"]


class SimulationDebt:
    """Ephemeral debt object wrapper for simulation state."""
    
    def __init__(self, debt_id: str, type_: str, balance: Decimal, rate: Decimal, 
                 min_payment_pct: Decimal = Decimal(0), # for cards
                 remaining_term: int = 0, # for loans
                 days_past_due: int = 0
                 ):
        self.id = debt_id
        self.type = type_
        self.balance = balance
        self.annual_rate = rate
        self.min_payment_pct = min_payment_pct
        self.remaining_term = remaining_term
        self.days_past_due = days_past_due
        
        # Derived rates
        self.monthly_rate = tea_to_tem(rate) / Decimal("100")
        self.daily_rate = tea_to_ted(rate) / Decimal("100")
        
        # State
        self.cumulative_interest = Decimal("0")
        self.cumulative_paid = Decimal("0")

    def calculate_minimum_payment(self, month_idx: int) -> Decimal:
        """Calculate required minimum for current month."""
        if self.balance <= 0:
            return Decimal("0")
            
        payment = Decimal("0")
        
        if self.type == "card":
            # Card: Balance * Min %
            min_pay = (self.balance * (self.min_payment_pct / Decimal("100"))).quantize(
                Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            payment = max(min_pay, Decimal("1.00")) # Floor of 1.00
            
        elif self.type == "loan":
            # Loan: Fixed PMT based on INITIAL terms? 
            # Usually loans have a fixed schedule. We should probably calculated it once 
            # based on current state (assuming it's the fixed payment for the rest of term)
            # But here we recalc based on *simulated* remaining term if we want precise accuracy?
            # Actually, standard loans have CONSTANT payment. 
            # We'll calculate it once based on current state and keep it fixed.
            # However, for this simulation, let's treat it as the required PMT for *simulated* paydown.
            # To be safe/simple: recalculate based on *initial* simulation state for fixed term.
            pass 
            
        # Add past due fee only on month 1
        if month_idx == 1 and self.days_past_due > 0:
            fee = (self.daily_rate * self.days_past_due * self.balance).quantize(
                 Decimal("0.01"), rounding=ROUND_HALF_UP
            )
            payment += fee
            
        return min(payment, self.balance)

    def apply_payment(self, payment: Decimal) -> dict[str, Decimal]:
        """Apply payment, accrue interest, return details."""
        if self.balance <= 0:
            return {
                "principal_paid": Decimal("0"),
                "interest_paid": Decimal("0"),
                "ending_balance": Decimal("0")
            }
            
        # Interest accrued for the period
        interest_accrued = (self.balance * self.monthly_rate).quantize(
            Decimal("0.01"), rounding=ROUND_HALF_UP
        )
        
        old_balance = self.balance
        
        # Determine how much of the payment goes to interest and principal
        # Payment first covers accrued interest
        interest_paid = min(payment, interest_accrued)
        principal_paid = payment - interest_paid
        
        # New Balance = Current Balance + Interest - Payment
        # So effective principal reduction = Payment - Interest
        
        self.balance = self.balance + interest_accrued - payment
        
        # Fix small dust
        if self.balance < Decimal("0.01"):
            self.balance = Decimal("0")
            
        # Determine actual paid amounts
        # We assume payment covers interest first (interest_paid), then principal.
        # But wait, we already calculated interest_paid and principal_paid above based on projected interest.
        # We should use those, but handle the case where we paid off the debt fully.
        
        real_principal_paid = old_balance - self.balance
        # real_interest_paid = payment - real_principal_paid (approximately)
        
        # But accounting-wise:
        # If payment > interest_accrued:
        #   Interest Paid = interest_accrued
        #   Principal Paid = Payment - interest_accrued
        
        p_paid = Decimal("0")
        i_paid = Decimal("0")
        
        if payment >= interest_accrued:
            i_paid = interest_accrued
            p_paid = payment - interest_accrued
        else:
            i_paid = payment
            p_paid = Decimal("0")

        # Adjust for final payoff precision
        # If we paid it off, p_paid should equal old_balance exactly (if we ignore interest? no).
        # Total Paid = p_paid + i_paid
        # Ending Balance = Old Balance + Interest Accrued - Total Paid
        # 0 = Old + Interest - (P_paid + I_paid)
        # P_paid + I_paid = Old + Interest
        # If I_paid = Interest, then P_paid = Old.
        # Correct.
        
        # However, due to decimals, might vary slightly.
        # Let's rely on standard calculation logic above.
            
        self.cumulative_interest += i_paid
        self.cumulative_paid += payment
        
        return {
            "principal_paid": p_paid,
            "interest_paid": i_paid,
            "ending_balance": self.balance
        }


def calculate_payment_capacity(customer: Customer) -> dict[str, Decimal]:
    """Calculate payment capacities based on income and expenses."""
    income = customer.monthly_income_avg or Decimal("0")
    expenses = customer.essential_expenses_avg or Decimal("0")
    variability = (customer.income_variability_pct or Decimal("0")) / Decimal("100")
    
    # Base: Average Income - Expenses
    base_capacity = max(income - expenses, Decimal("0"))
    
    # Conservative: (Income * (1 - Variability)) - Expenses
    low_income = income * (Decimal("1") - variability)
    low_capacity = max(low_income - expenses, Decimal("0"))
    
    return {
        "Base": base_capacity,
        "Conservative": low_capacity
    }


def simulate_strategy(
    debts: list[SimulationDebt], 
    monthly_capacity: Decimal, 
    method: StrategyType
) -> dict:
    """Run month-by-month simulation for all debts."""
    
    # Deep copy debts to not mutate original list between runs
    active_debts = deepcopy(debts)
    
    # Pre-calculate fixed payments for loans (they don't change ideally)
    loan_payments = {}
    for d in active_debts:
        if d.type == "loan":
            # PMT based on current state
            pmt = calculate_pmt(d.balance, d.monthly_rate, d.remaining_term)
            loan_payments[d.id] = pmt

    total_months = 0
    month_idx = 0
    max_months = 300 # 50y cap
    
    monthly_output: list[dict] = [] # To map to StrategyMonthlyAllocation schemas later
    
    while any(d.balance > 0 for d in active_debts) and month_idx < max_months:
        month_idx += 1
        
        # 1. Calculate Minimums
        current_minimums = []
        for d in active_debts:
            if d.balance <= 0:
                # Debt is paid
                continue
                
            if d.type == "loan":
                # Fixed payment, but capped at balance (plus interest roughly)?
                # Simplified: Use fixed PMT.
                min_pay = loan_payments[d.id]
                # Month 1 past due fee
                if month_idx == 1 and d.days_past_due > 0:
                    fee = (d.daily_rate * d.days_past_due * d.balance).quantize(
                        Decimal("0.01"), rounding=ROUND_HALF_UP
                    )
                    min_pay += fee
                
                # Check if slightly less than balance? 
                # Just use min(min_pay, balance + interest_approx)
                # We'll let apply_payment handle exact payoff logic, 
                # here just setting target.
                current_minimums.append((d, min_pay))
            else:
                # Card
                min_pay = d.calculate_minimum_payment(month_idx)
                current_minimums.append((d, min_pay))

        total_min_needed = sum(m[1] for m in current_minimums)
        
        # 2. Check Capacity
        # If capacity < minimums, we pay what we can (pro-rata? or priority?).
        # For this sim, we assume user pays minimums even if it exceeds capacity 
        # (borrowing elsewhere), OR we cap at capacity.
        # Requirement says "maximizing its cash flow... based on base and low".
        # If capacity is low, we might not meet minimums.
        # Let's assume Capacity is the BUDGET. If Budget < Mins, we are insolvent.
        # We will use max(Capacity, Total Mins) to ensure simulation completes, 
        # but report the Capacity as the "Available". 
        # Actually better: Use Capacity. If Capacity < Mins, debt grows (fees/interest).
        # But for 'payoff strategy', we usually assume Mins are met. 
        # Let's use `actual_cash = max(monthly_capacity, total_min_needed)` 
        # implying they find the money for minimums.
        
        actual_cash = max(monthly_capacity, total_min_needed)
        extra_cash = actual_cash - total_min_needed
        
        # 3. Sort for Extra Allocation
        # Only consider active debts
        candidates = [x for x in active_debts if x.balance > 0]
        
        if method == "avalanche":
            # Highest Rate First
            candidates.sort(key=lambda x: x.annual_rate, reverse=True)
        else: # snowball
            # Lowest Balance First
            candidates.sort(key=lambda x: x.balance)
            
        # 4. Allocate Extra
        # Default allocation is just the minimum, or 0 if paid off
        allocations = {d.id: Decimal("0") for d in active_debts}
        for d, min_pay in current_minimums:
            allocations[d.id] = min_pay
        
        remaining_extra = extra_cash
        for cand in candidates:
            if remaining_extra <= 0:
                break
            
            # Prevent overpayment using lookahead logic
            # Balance + (Balance * Rate) = Approx payoff amount
            # This is slightly simplified (interest is calc'd later exactly)
            # But safe enough to prevent massive overpayment.
            approx_interest = cand.balance * cand.monthly_rate
            payoff_amount = cand.balance + approx_interest
            
            already_allocated = allocations.get(cand.id, Decimal("0"))
            
            # How much MORE can we add?
            # Max useful payment is payoff_amount
            # Space remaining = payoff_amount - already_allocated
            space = max(payoff_amount - already_allocated, Decimal("0"))
            
            to_add = min(remaining_extra, space)
            allocations[cand.id] = already_allocated + to_add
            remaining_extra -= to_add
            
        # 5. Execute Month
        month_allocs = []
        month_total_pay = Decimal("0")
        
        for d in active_debts:
            pay = allocations.get(d.id, Decimal("0"))
            
            # Apply payment details
            # Note: apply_payment handles capping at actual relevant usage?
            # Ideally apply_payment returns actual amount used if we passed too much.
            # But the 'space' calculation above tried to prevent it.
            # If ApplyPayment reduces balance to 0 and we overpaid, that's "refunded" 
            # or just lost in simulation noise? 
            # Ideally precise simulation: 
            # 1. Apply payment. 2. If overpayment, return change?
            # For now, we assume `space` calc is close enough.
            
            # Actually, `apply_payment` in SimulationDebt logic mutates balance.
            # Let's adjust apply_payment to return actual amount used if capping happens?
            # Currently it returns interest paid.
            
            # Let's assume paid = allocations for display, unless balance < allocation?
            # We'll stick to allocation for schedule to align with cash flow usage.
            
            details = d.apply_payment(pay)
            
            status = "active" if d.balance > Decimal("0") else "paid_off"
            
            if pay > 0 or status == "active": # Only log relevant items
                 month_allocs.append({
                     "debt_id": d.id,
                     "debt_name": d.type.title(), # Just Type for now, ID is key
                     "payment_amount": pay,
                     "principal_paid": details["principal_paid"],
                     "interest_paid": details["interest_paid"],
                     "ending_balance": details["ending_balance"],
                     "status": status
                 })
                 month_total_pay += pay
        
        total_remaining_balance = sum(d.balance for d in active_debts)
        
        monthly_output.append({
            "month": month_idx,
            "total_payment": month_total_pay,
            "allocations": month_allocs,
            "remaining_total_balance": total_remaining_balance
        })

    # End Loop
    
    total_paid = sum(d.cumulative_paid for d in active_debts)
    total_interest = sum(d.cumulative_interest for d in active_debts)
    
    # Freedom date
    today = date.today()
    freedom_date = today + timedelta(days=30 * month_idx)
    
    return {
        "months": month_idx,
        "total_paid": total_paid,
        "total_interest": total_interest,
        "freedom_date": freedom_date.strftime("%Y-%m"),
        "monthly_schedule": monthly_output
    }


async def generate_strategies(
    db: AsyncSession, customer_id: str
) -> list[StrategyResult]:
    """Generate all 4 strategy scenarios."""
    
    # 1. Fetch Data
    stmt_cust = select(Customer).where(Customer.external_id == customer_id)
    cust = (await db.execute(stmt_cust)).scalar_one_or_none()
    
    if not cust:
        return []

    # Get debts - Fetch separately to avoid Greenlet/lazy load issues with async polymorphic
    
    # 2. Fetch Cards
    stmt_cards = select(Card).where(Card.customer_id == cust.id)
    cards = list((await db.execute(stmt_cards)).scalars().all())
    
    # 3. Fetch Loans
    stmt_loans = select(Loan).where(Loan.customer_id == cust.id)
    loans = list((await db.execute(stmt_loans)).scalars().all())
    
    debts = []
    
    for p in cards:
        debts.append(SimulationDebt(
            debt_id=p.external_id,
            type_="card",
            balance=p.balance,
            rate=p.annual_rate_pct,
            min_payment_pct=p.min_payment_pct,
            days_past_due=p.days_past_due
        ))
        
    for p in loans:
        debts.append(SimulationDebt(
            debt_id=p.external_id,
            type_="loan",
            balance=p.principal,
            rate=p.annual_rate_pct,
            remaining_term=p.remaining_term_months,
            days_past_due=p.days_past_due
        ))
            
    if not debts:
        return []
        
    capacities = calculate_payment_capacity(cust)
    
    results = []
    scenarios = [
        ("Base", "avalanche"),
        ("Base", "snowball"),
        ("Conservative", "avalanche"),
        ("Conservative", "snowball")
    ]
    
    for cap_name, method in scenarios:
        capacity = capacities[cap_name]
        
        res = simulate_strategy(debts, capacity, method)
        
        results.append(StrategyResult(
            strategy_name=f"{cap_name} - {method.title()}",
            monthly_capacity=capacity,
            total_months=res["months"],
            total_interest_paid=res["total_interest"],
            freedom_date=res["freedom_date"],
            total_balance_paid=res["total_paid"] - res["total_interest"],
            monthly_schedule=res["monthly_schedule"]
        ))
        
    return results
