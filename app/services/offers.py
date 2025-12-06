from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.bank_offer import BankOffer
from app.models.card import Card
from app.models.credit_score_history import CreditScoreHistory
from app.models.customer import Customer
from app.models.loan import Loan


class CustomerMetrics:
    def __init__(self, score: int | None, max_dpd: int):
        self.credit_score = score
        self.max_days_past_due = max_dpd


async def get_eligibility_metrics(db: AsyncSession, customer_id: str) -> CustomerMetrics | None:
    """Calculate eligibility metrics: Latest Score and Max Days Past Due."""
    
    # 1. Get Customer ID (internal)
    stmt_cust = select(Customer.id).where(Customer.external_id == customer_id)
    cust_id = (await db.execute(stmt_cust)).scalar_one_or_none()
    
    if not cust_id:
        return None
        
    # 2. Get metrics
    # Credit Score (Latest)
    stmt_score = (
        select(CreditScoreHistory.credit_score)
        .where(CreditScoreHistory.customer_id == cust_id)
        .order_by(CreditScoreHistory.score_date.desc())
        .limit(1)
    )
    score = (await db.execute(stmt_score)).scalar_one_or_none()
    
    # Max Days Past Due - Across Cards and Loans
    # Separate queries to handle polymorphism safely/simply
    stmt_dpd_card = select(func.max(Card.days_past_due)).where(Card.customer_id == cust_id)
    max_dpd_card = (await db.execute(stmt_dpd_card)).scalar_one_or_none() or 0
    
    stmt_dpd_loan = select(func.max(Loan.days_past_due)).where(Loan.customer_id == cust_id)
    max_dpd_loan = (await db.execute(stmt_dpd_loan)).scalar_one_or_none() or 0
    
    max_dpd = max(max_dpd_card, max_dpd_loan)
    
    return CustomerMetrics(score=score, max_dpd=max_dpd)


async def get_eligible_offers(db: AsyncSession, customer_id: str) -> tuple[CustomerMetrics | None, list[BankOffer]]:
    """Fetch metrics and matching offers."""
    
    metrics = await get_eligibility_metrics(db, customer_id)
    if not metrics:
        return None, []
        
    # Fetch all offers
    stmt_offers = select(BankOffer)
    all_offers = (await db.execute(stmt_offers)).scalars().all()
    
    eligible = []
    for offer in all_offers:
        # Check Score
        if offer.min_credit_score is not None:
            if metrics.credit_score is None or metrics.credit_score < offer.min_credit_score:
                continue
                
        # Check Past Due
        if offer.max_days_past_due is not None:
            if metrics.max_days_past_due > offer.max_days_past_due:
                continue
                
        eligible.append(offer)
        
    return metrics, eligible
