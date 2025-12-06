"""Models module - imports all models for Alembic to detect."""

from app.models.bank_offer import BankOffer
from app.models.card import Card
from app.models.credit_score_history import CreditScoreHistory
from app.models.customer import Customer
from app.models.loan import Loan
from app.models.payment import Payment
from app.models.product import Product

__all__ = [
    "BankOffer",
    "Card",
    "CreditScoreHistory",
    "Customer",
    "Loan",
    "Payment",
    "Product",
]
