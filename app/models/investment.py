import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class InvestmentType(str, enum.Enum):
    STOCKS = "stocks"           # Ações
    BONDS = "bonds"             # Renda fixa
    FUNDS = "funds"             # Fundos
    CRYPTO = "crypto"           # Criptomoedas
    REAL_ESTATE = "real_estate" # FIIs


class Investment(Base):
    __tablename__ = "investments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"), nullable=False)
    investment_type: Mapped[InvestmentType] = mapped_column(Enum(InvestmentType), nullable=False)
    ticker: Mapped[str] = mapped_column(String(20), nullable=False)
    name: Mapped[str] = mapped_column(String(150), nullable=False)
    quantity: Mapped[float] = mapped_column(Numeric(precision=15, scale=6), nullable=False)
    average_price: Mapped[float] = mapped_column(Numeric(precision=15, scale=2), nullable=False)
    current_price: Mapped[float] = mapped_column(Numeric(precision=15, scale=2), nullable=False)
    purchase_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    # Relationships
    account: Mapped["Account"] = relationship("Account", back_populates="investments")

    @property
    def total_value(self) -> float:
        return float(self.quantity) * float(self.current_price)

    @property
    def profit_loss(self) -> float:
        return (float(self.current_price) - float(self.average_price)) * float(self.quantity)

    @property
    def profit_loss_pct(self) -> float:
        if float(self.average_price) == 0:
            return 0
        return ((float(self.current_price) - float(self.average_price)) / float(self.average_price)) * 100
