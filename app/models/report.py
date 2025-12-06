from sqlalchemy import Column, ForeignKey, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column

from app.core.base import Base, TimestampMixin, UUIDMixin

class FinancialReport(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "financial_reports"

    customer_id: Mapped[str] = mapped_column(ForeignKey("customers.id"), nullable=False)
    content: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_info: Mapped[dict | None] = mapped_column("metadata", JSON, nullable=True)
    
    def __repr__(self):
        return f"<FinancialReport(id={self.id}, customer_id={self.customer_id})>"
