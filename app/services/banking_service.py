"""
Banking Service — Core financial business logic
Handles deposits, withdrawals, transfers, PIX, investments, and loans.
"""
import uuid
from decimal import Decimal
from typing import Optional

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from crud.account import get_account_by_id, get_account_by_number
from models.account import Account, AccountStatus
from models.investment import Investment
from models.loan import Loan, LoanStatus
from models.transaction import Transaction, TransactionStatus, TransactionType
from schemas.account import DepositRequest, PixRequest, TransferRequest, WithdrawalRequest
from schemas.investment import InvestmentCreate, LoanCreate
from services.audit_service import log_action


def _assert_active(account: Account) -> None:
    if account.status != AccountStatus.ACTIVE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Conta {account.account_number} não está ativa (status: {account.status}).",
        )


async def deposit(
    db: AsyncSession,
    account_id: int,
    user_id: int,
    data: DepositRequest,
    ip: str = "unknown",
) -> Transaction:
    account = await get_account_by_id(db, account_id)
    if not account or account.user_id != user_id:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")
    _assert_active(account)

    account.balance = float(account.balance) + data.amount
    tx = Transaction(
        to_account_id=account.id,
        transaction_type=TransactionType.DEPOSIT,
        amount=data.amount,
        description=data.description or "Depósito",
        status=TransactionStatus.COMPLETED,
    )
    db.add(tx)
    await db.flush()
    await log_action(db, user_id, "DEPOSIT", "transaction", str(tx.id), {"amount": data.amount}, ip)
    return tx


async def withdraw(
    db: AsyncSession,
    account_id: int,
    user_id: int,
    data: WithdrawalRequest,
    ip: str = "unknown",
) -> Transaction:
    account = await get_account_by_id(db, account_id)
    if not account or account.user_id != user_id:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")
    _assert_active(account)

    if float(account.balance) < data.amount:
        raise HTTPException(status_code=400, detail="Saldo insuficiente.")

    account.balance = float(account.balance) - data.amount
    tx = Transaction(
        from_account_id=account.id,
        transaction_type=TransactionType.WITHDRAWAL,
        amount=data.amount,
        description=data.description or "Saque",
        status=TransactionStatus.COMPLETED,
    )
    db.add(tx)
    await db.flush()
    await log_action(db, user_id, "WITHDRAWAL", "transaction", str(tx.id), {"amount": data.amount}, ip)
    return tx


async def transfer(
    db: AsyncSession,
    from_account_id: int,
    user_id: int,
    data: TransferRequest,
    ip: str = "unknown",
) -> Transaction:
    from_acc = await get_account_by_id(db, from_account_id)
    if not from_acc or from_acc.user_id != user_id:
        raise HTTPException(status_code=404, detail="Conta de origem não encontrada.")
    _assert_active(from_acc)

    to_acc = await get_account_by_number(db, data.to_account_number)
    if not to_acc:
        raise HTTPException(status_code=404, detail="Conta de destino não encontrada.")
    _assert_active(to_acc)

    if float(from_acc.balance) < data.amount:
        raise HTTPException(status_code=400, detail="Saldo insuficiente para transferência.")

    from_acc.balance = float(from_acc.balance) - data.amount
    to_acc.balance = float(to_acc.balance) + data.amount

    tx = Transaction(
        from_account_id=from_acc.id,
        to_account_id=to_acc.id,
        transaction_type=TransactionType.TRANSFER,
        amount=data.amount,
        description=data.description or f"Transferência para {data.to_account_number}",
        status=TransactionStatus.COMPLETED,
    )
    db.add(tx)
    await db.flush()
    await log_action(db, user_id, "TRANSFER", "transaction", str(tx.id), {
        "amount": data.amount,
        "to": data.to_account_number,
    }, ip)
    return tx


async def pix(
    db: AsyncSession,
    from_account_id: int,
    user_id: int,
    data: PixRequest,
    ip: str = "unknown",
) -> Transaction:
    from_acc = await get_account_by_id(db, from_account_id)
    if not from_acc or from_acc.user_id != user_id:
        raise HTTPException(status_code=404, detail="Conta de origem não encontrada.")
    _assert_active(from_acc)

    if float(from_acc.balance) < data.amount:
        raise HTTPException(status_code=400, detail="Saldo insuficiente para PIX.")

    from_acc.balance = float(from_acc.balance) - data.amount

    tx = Transaction(
        from_account_id=from_acc.id,
        transaction_type=TransactionType.PIX,
        amount=data.amount,
        description=data.description or f"PIX para {data.pix_key}",
        reference_id=data.pix_key,
        status=TransactionStatus.COMPLETED,
    )
    db.add(tx)
    await db.flush()
    await log_action(db, user_id, "PIX", "transaction", str(tx.id), {
        "amount": data.amount,
        "pix_key": data.pix_key,
    }, ip)
    return tx


async def add_investment(
    db: AsyncSession,
    account_id: int,
    user_id: int,
    data: InvestmentCreate,
    ip: str = "unknown",
) -> Investment:
    account = await get_account_by_id(db, account_id)
    if not account or account.user_id != user_id:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")

    total_cost = data.quantity * data.average_price
    if float(account.balance) < total_cost:
        raise HTTPException(status_code=400, detail="Saldo insuficiente para o investimento.")

    account.balance = float(account.balance) - total_cost

    investment = Investment(
        account_id=account.id,
        investment_type=data.investment_type,
        ticker=data.ticker.upper(),
        name=data.name,
        quantity=data.quantity,
        average_price=data.average_price,
        current_price=data.current_price,
        purchase_date=data.purchase_date,
    )
    db.add(investment)
    await db.flush()
    await log_action(db, user_id, "INVESTMENT_BUY", "investment", str(investment.id), {
        "ticker": data.ticker,
        "quantity": data.quantity,
        "total_cost": total_cost,
    }, ip)
    return investment


async def request_loan(
    db: AsyncSession,
    user_id: int,
    data: LoanCreate,
    ip: str = "unknown",
) -> Loan:
    # Simple credit scoring: auto-approve if amount <= 50000
    INTEREST_RATE = 2.5  # % per month (fictitious)
    approved = data.requested_amount <= 50_000.0
    monthly = None
    if approved:
        r = INTEREST_RATE / 100
        n = data.term_months
        monthly = data.requested_amount * (r * (1 + r) ** n) / ((1 + r) ** n - 1)

    loan = Loan(
        user_id=user_id,
        requested_amount=data.requested_amount,
        approved_amount=data.requested_amount if approved else None,
        interest_rate=INTEREST_RATE,
        term_months=data.term_months,
        monthly_payment=monthly,
        outstanding_balance=data.requested_amount if approved else None,
        status=LoanStatus.APPROVED if approved else LoanStatus.REJECTED,
        purpose=data.purpose,
        rejection_reason=None if approved else "Valor solicitado acima do limite aprovado automaticamente.",
    )
    db.add(loan)
    await db.flush()
    await log_action(db, user_id, "LOAN_REQUEST", "loan", str(loan.id), {
        "amount": data.requested_amount,
        "status": loan.status,
    }, ip)
    return loan
