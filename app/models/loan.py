import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class LoanStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    ACTIVE = "active"
    PAID = "paid"
    DEFAULTED = "defaulted"


class Loan(Base):
    __tablename__ = "loans"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    requested_amount: Mapped[float] = mapped_column(Numeric(precision=15, scale=2), nullable=False)
    approved_amount: Mapped[float | None] = mapped_column(Numeric(precision=15, scale=2), nullable=True)
    interest_rate: Mapped[float] = mapped_column(Numeric(precision=5, scale=2), nullable=False)  # % per month
    term_months: Mapped[int] = mapped_column(Integer, nullable=False)
    monthly_payment: Mapped[float | None] = mapped_column(Numeric(precision=15, scale=2), nullable=True)
    outstanding_balance: Mapped[float | None] = mapped_column(Numeric(precision=15, scale=2), nullable=True)
    status: Mapped[LoanStatus] = mapped_column(Enum(LoanStatus), default=LoanStatus.PENDING)
    purpose: Mapped[str | None] = mapped_column(Text, nullable=True)
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="loans")
