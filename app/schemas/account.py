from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from models.account import AccountStatus, AccountType


class AccountCreate(BaseModel):
    account_type: AccountType
    initial_deposit: float = Field(default=0.0, ge=0)


class AccountResponse(BaseModel):
    id: int
    user_id: int
    account_number: str
    agency: str
    account_type: AccountType
    balance: float
    status: AccountStatus
    created_at: datetime

    model_config = {"from_attributes": True}


class DepositRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Valor do depósito (deve ser positivo)")
    description: Optional[str] = None


class WithdrawalRequest(BaseModel):
    amount: float = Field(..., gt=0, description="Valor do saque (deve ser positivo)")
    description: Optional[str] = None


class TransferRequest(BaseModel):
    to_account_number: str
    amount: float = Field(..., gt=0)
    description: Optional[str] = None


class PixRequest(BaseModel):
    pix_key: str = Field(..., description="Chave PIX do destinatário (CPF, email, telefone ou aleatória)")
    amount: float = Field(..., gt=0)
    description: Optional[str] = None
