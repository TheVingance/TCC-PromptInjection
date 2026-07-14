from typing import List

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.database import get_db
from core.dependencies import get_current_user
from crud.account import create_account, get_user_accounts
from models.account import Account
from models.transaction import Transaction
from models.user import User
from schemas.account import (
    AccountCreate,
    AccountResponse,
    DepositRequest,
    PixRequest,
    TransferRequest,
    WithdrawalRequest,
)
from schemas.transaction import TransactionResponse
from services.banking_service import deposit, pix, transfer, withdraw

router = APIRouter(prefix="/accounts", tags=["Contas Bancárias"])


@router.get("", response_model=List[AccountResponse])
async def list_accounts(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista todas as contas do usuário autenticado."""
    return await get_user_accounts(db, current_user.id)


@router.post("", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_new_account(
    data: AccountCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Cria uma nova conta (corrente, poupança ou investimento)."""
    return await create_account(db, current_user.id, data)


@router.get("/{account_id}/transactions", response_model=List[TransactionResponse])
async def get_transactions(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retorna histórico de transações de uma conta."""
    result = await db.execute(
        select(Transaction).where(
            (Transaction.from_account_id == account_id) |
            (Transaction.to_account_id == account_id)
        ).order_by(Transaction.created_at.desc()).limit(100)
    )
    return list(result.scalars().all())


@router.post("/{account_id}/deposit", response_model=TransactionResponse)
async def make_deposit(
    account_id: int,
    data: DepositRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Realiza um depósito na conta."""
    return await deposit(db, account_id, current_user.id, data, request.client.host)


@router.post("/{account_id}/withdraw", response_model=TransactionResponse)
async def make_withdrawal(
    account_id: int,
    data: WithdrawalRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Realiza um saque da conta."""
    return await withdraw(db, account_id, current_user.id, data, request.client.host)


@router.post("/{account_id}/transfer", response_model=TransactionResponse)
async def make_transfer(
    account_id: int,
    data: TransferRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Transfere valor para outra conta."""
    return await transfer(db, account_id, current_user.id, data, request.client.host)


@router.post("/{account_id}/pix", response_model=TransactionResponse)
async def make_pix(
    account_id: int,
    data: PixRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Envia um PIX."""
    return await pix(db, account_id, current_user.id, data, request.client.host)
