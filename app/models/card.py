"""Card model extending Product."""

from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric
from sqlalchemy.orm import Mapped, mapped_column

from app.models.product import Product


class Card(Product):
    """Credit card product entity.

    Inherits from Product using Joined Table Inheritance.
    """

    __tablename__ = "cards"

    id: Mapped[str] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), primary_key=True
    )
    balance: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    min_payment_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    payment_due_day: Mapped[int] = mapped_column(Integer, nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": "card",
    }

    def __repr__(self) -> str:
        return f"Card(id={self.id!r}, balance={self.balance!r})"
