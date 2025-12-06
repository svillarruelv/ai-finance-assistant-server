"""Loan model extending Product."""

from decimal import Decimal

from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.models.product import Product


class Loan(Product):
    """Loan product entity.

    Inherits from Product using Joined Table Inheritance.
    loan_type can be 'personal' or 'micro'.
    """

    __tablename__ = "loans"

    id: Mapped[str] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), primary_key=True
    )
    loan_type: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="personal or micro"
    )
    principal: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)
    remaining_term_months: Mapped[int] = mapped_column(Integer, nullable=False)
    collateral: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    __mapper_args__ = {
        "polymorphic_identity": "loan",
    }

    def __repr__(self) -> str:
        return f"Loan(id={self.id!r}, loan_type={self.loan_type!r}, principal={self.principal!r})"
