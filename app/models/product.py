"""Product base model with Joined Table Inheritance."""

from decimal import Decimal

from sqlalchemy import ForeignKey, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.base import Base, TimestampMixin, UUIDMixin


class Product(Base, UUIDMixin, TimestampMixin):
    """Base product entity using Joined Table Inheritance.

    Loans and Cards inherit from this class.
    """

    __tablename__ = "products"

    external_id: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    customer_id: Mapped[str] = mapped_column(
        ForeignKey("customers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    product_type: Mapped[str] = mapped_column(String(20), nullable=False)
    annual_rate_pct: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False)
    days_past_due: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="products")
    payments: Mapped[list["Payment"]] = relationship(
        "Payment", back_populates="product", cascade="all, delete-orphan"
    )

    __mapper_args__ = {
        "polymorphic_identity": "product",
        "polymorphic_on": "product_type",
    }

    def __repr__(self) -> str:
        return f"Product(id={self.id!r}, type={self.product_type!r})"
