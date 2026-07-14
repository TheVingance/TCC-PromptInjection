from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.security import create_access_token
from crud.user import authenticate_user, create_user, get_user_by_cpf, get_user_by_email
from schemas.user import LoginRequest, Token, UserCreate, UserResponse
from services.audit_service import log_action

router = APIRouter(prefix="/auth", tags=["Autenticação"])


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Cadastra um novo usuário no sistema financeiro fictício."""
    if await get_user_by_email(db, data.email):
        raise HTTPException(status_code=409, detail="E-mail já cadastrado.")
    if await get_user_by_cpf(db, data.cpf):
        raise HTTPException(status_code=409, detail="CPF já cadastrado.")

    user = await create_user(db, data)
    await log_action(db, user.id, "REGISTER", "user", str(user.id), {}, request.client.host)
    return user


@router.post("/login", response_model=Token)
async def login(
    data: LoginRequest,
    request: Request,
    db: AsyncSession = Depends(get_db),
):
    """Autentica o usuário e retorna um JWT Bearer token."""
    user = await authenticate_user(db, data.email, data.password)
    if not user:
        await log_action(db, None, "LOGIN_FAILED", "user", None, {"email": data.email}, request.client.host)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Credenciais inválidas.",
        )
    token = create_access_token({"sub": str(user.id)})
    await log_action(db, user.id, "LOGIN", "user", str(user.id), {}, request.client.host)
    return Token(access_token=token, user=user)
