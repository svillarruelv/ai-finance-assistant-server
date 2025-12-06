"""Credit score history model."""

from datetime import date

from sqlalchemy import Date, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, TimestampMixin, UUIDMixin


class CreditScoreHistory(Base, UUIDMixin, TimestampMixin):
    """Credit score history entry for a customer."""

    __tablename__ = "credit_score_history"

    customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    score_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    credit_score: Mapped[int] = mapped_column(Integer, nullable=False)

    # Relationships
    customer: Mapped["Customer"] = relationship(
        "Customer", back_populates="credit_score_history"
    )

    def __repr__(self) -> str:
        return f"CreditScoreHistory(customer_id={self.customer_id!r}, score={self.credit_score!r})"
