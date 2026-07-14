from typing import List

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.database import get_db
from core.dependencies import get_current_user
from crud.account import get_account_by_id
from models.investment import Investment
from models.user import User
from schemas.investment import InvestmentCreate, InvestmentResponse, LoanCreate, LoanResponse
from services.banking_service import add_investment, request_loan

router = APIRouter(tags=["Investimentos & Empréstimos"])


# ─── Investments ───────────────────────────────────────────────────────────────

inv_router = APIRouter(prefix="/accounts/{account_id}/investments")


@inv_router.get("", response_model=List[InvestmentResponse])
async def list_investments(
    account_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista investimentos de uma conta."""
    account = await get_account_by_id(db, account_id)
    if not account or account.user_id != current_user.id:
        raise HTTPException(status_code=404, detail="Conta não encontrada.")
    result = await db.execute(select(Investment).where(Investment.account_id == account_id))
    return list(result.scalars().all())


@inv_router.post("", response_model=InvestmentResponse, status_code=status.HTTP_201_CREATED)
async def buy_investment(
    account_id: int,
    data: InvestmentCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Compra um ativo para a carteira de investimentos."""
    return await add_investment(db, account_id, current_user.id, data, request.client.host)


# ─── Loans ─────────────────────────────────────────────────────────────────────

loan_router = APIRouter(prefix="/loans")


@loan_router.get("", response_model=List[LoanResponse])
async def list_loans(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos os empréstimos do usuário."""
    from models.loan import Loan
    result = await db.execute(select(Loan).where(Loan.user_id == current_user.id))
    return list(result.scalars().all())


@loan_router.post("", response_model=LoanResponse, status_code=status.HTTP_201_CREATED)
async def apply_for_loan(
    data: LoanCreate,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Solicita um empréstimo (aprovação automática até R$ 50.000)."""
    return await request_loan(db, current_user.id, data, request.client.host)


router.include_router(inv_router)
router.include_router(loan_router)
