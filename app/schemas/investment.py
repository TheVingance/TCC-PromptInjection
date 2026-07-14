from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from models.investment import InvestmentType


class InvestmentCreate(BaseModel):
    investment_type: InvestmentType
    ticker: str = Field(..., max_length=20)
    name: str = Field(..., max_length=150)
    quantity: float = Field(..., gt=0)
    average_price: float = Field(..., gt=0)
    current_price: float = Field(..., gt=0)
    purchase_date: datetime


class InvestmentUpdate(BaseModel):
    current_price: Optional[float] = Field(None, gt=0)
    quantity: Optional[float] = Field(None, gt=0)


class InvestmentResponse(BaseModel):
    id: int
    account_id: int
    investment_type: InvestmentType
    ticker: str
    name: str
    quantity: float
    average_price: float
    current_price: float
    total_value: float
    profit_loss: float
    profit_loss_pct: float
    purchase_date: datetime
    created_at: datetime

    model_config = {"from_attributes": True}


class LoanCreate(BaseModel):
    requested_amount: float = Field(..., gt=0)
    term_months: int = Field(..., ge=1, le=360)
    purpose: Optional[str] = None


class LoanResponse(BaseModel):
    id: int
    user_id: int
    requested_amount: float
    approved_amount: Optional[float]
    interest_rate: float
    term_months: int
    monthly_payment: Optional[float]
    outstanding_balance: Optional[float]
    status: str
    purpose: Optional[str]
    rejection_reason: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
