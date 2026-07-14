from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field

from models.transaction import TransactionStatus, TransactionType


class TransactionResponse(BaseModel):
    id: int
    from_account_id: Optional[int]
    to_account_id: Optional[int]
    transaction_type: TransactionType
    amount: float
    status: TransactionStatus
    description: Optional[str]
    reference_id: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
