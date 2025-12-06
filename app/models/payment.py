"""Payment model."""

from datetime import date
from decimal import Decimal

from sqlalchemy import Date, ForeignKey, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, TimestampMixin, UUIDMixin


class Payment(Base, UUIDMixin, TimestampMixin):
    """Payment transaction entity."""

    __tablename__ = "payments"

    product_id: Mapped[str] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True
    )
    customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    payment_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(12, 2), nullable=False)

    # Relationships
    product: Mapped["Product"] = relationship("Product", back_populates="payments")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="payments")

    def __repr__(self) -> str:
        return f"Payment(id={self.id!r}, amount={self.amount!r}, date={self.payment_date!r})"
