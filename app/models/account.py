import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class AccountType(str, enum.Enum):
    CHECKING = "checking"       # Conta corrente
    SAVINGS = "savings"         # Conta poupança
    INVESTMENT = "investment"   # Conta investimento


class AccountStatus(str, enum.Enum):
    ACTIVE = "active"
    FROZEN = "frozen"
    CLOSED = "closed"


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    account_number: Mapped[str] = mapped_column(String(20), unique=True, index=True, nullable=False)
    agency: Mapped[str] = mapped_column(String(10), nullable=False, default="0001")
    account_type: Mapped[AccountType] = mapped_column(
        Enum(AccountType, values_callable=lambda obj: [e.value for e in obj]), nullable=False
    )
    balance: Mapped[float] = mapped_column(Numeric(precision=15, scale=2), default=0.00)
    status: Mapped[AccountStatus] = mapped_column(
        Enum(AccountStatus, values_callable=lambda obj: [e.value for e in obj]),
        default=AccountStatus.ACTIVE
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    owner: Mapped["User"] = relationship("User", back_populates="accounts")
    transactions_from: Mapped[list["Transaction"]] = relationship(
        "Transaction", foreign_keys="Transaction.from_account_id", back_populates="from_account", lazy="selectin"
    )
    transactions_to: Mapped[list["Transaction"]] = relationship(
        "Transaction", foreign_keys="Transaction.to_account_id", back_populates="to_account", lazy="selectin"
    )
    investments: Mapped[list["Investment"]] = relationship("Investment", back_populates="account", lazy="selectin")
