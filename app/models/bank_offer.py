"""Bank offer model."""

from decimal import Decimal

from sqlalchemy import Integer, Numeric, String
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, TimestampMixin, UUIDMixin


class BankOffer(Base, UUIDMixin, TimestampMixin):
    """Bank consolidation offer entity."""

    __tablename__ = "bank_offers"

    offer_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    product_types_eligible: Mapped[list[str]] = mapped_column(
        ARRAY(String(20)), nullable=False
    )
    max_consolidated_balance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2), nullable=False
    )
    new_rate_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    max_term_months: Mapped[int] = mapped_column(Integer, nullable=False)

    # Structured condition fields for filtering
    min_credit_score: Mapped[int | None] = mapped_column(Integer, nullable=True)
    max_days_past_due: Mapped[int | None] = mapped_column(Integer, nullable=True)
    conditions_description: Mapped[str | None] = mapped_column(
        String(500), nullable=True
    )

    def __repr__(self) -> str:
        return f"BankOffer(offer_id={self.offer_id!r}, rate={self.new_rate_pct!r})"
