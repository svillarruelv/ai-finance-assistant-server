"""Customer model."""

from decimal import Decimal

from sqlalchemy import Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, TimestampMixin, UUIDMixin


class Customer(Base, UUIDMixin, TimestampMixin):
    """Customer entity with cashflow information."""

    __tablename__ = "customers"

    external_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    monthly_income_avg: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    income_variability_pct: Mapped[Decimal] = mapped_column(
        Numeric(5, 2), nullable=True
    )
    essential_expenses_avg: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=True
    )

    # Relationships
    products: Mapped[list["Product"]] = relationship(
        "Product", back_populates="customer", cascade="all, delete-orphan"
    )
    payments: Mapped[list["Payment"]] = relationship(
        "Payment", back_populates="customer", cascade="all, delete-orphan"
    )
    credit_score_history: Mapped[list["CreditScoreHistory"]] = relationship(
        "CreditScoreHistory", back_populates="customer", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"Customer(id={self.id!r}, external_id={self.external_id!r})"
