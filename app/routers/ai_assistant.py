import uuid
from typing import List, Optional

from fastapi import APIRouter, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from core.database import get_db
from core.dependencies import get_current_user
from models.adversarial_case import AdversarialCase
from models.ai_interaction import AIInteraction, LLMProvider, ThreatCategory
from models.user import User
from schemas.ai import (
    AdversarialCaseCreate,
    AdversarialCaseResponse,
    AIInteractionResponse,
    ChatRequest,
    ChatResponse,
)
from services.ai_service import process_chat

router = APIRouter(prefix="/ai", tags=["Assistente IA (FinBot)"])


@router.post("/chat", response_model=ChatResponse)
async def chat(
    data: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Envia uma mensagem ao FinBot (assistente financeiro IA).
    Suporta: ollama, deepseek, gemini.
    
    Para pesquisa adversarial, utilize os campos `is_adversarial`, 
    `threat_category` e `researcher_notes`.
    """
    session_id = data.session_id or str(uuid.uuid4())

    interaction = await process_chat(
        db=db,
        user_id=current_user.id,
        user_message=data.message,
        session_id=session_id,
        provider=data.provider,
        custom_system_prompt=data.system_prompt,
        is_adversarial=data.is_adversarial,
        threat_category=data.threat_category,
        researcher_notes=data.researcher_notes,
    )

    return ChatResponse(
        interaction_id=interaction.id,
        session_id=interaction.session_id,
        provider=interaction.provider,
        model_name=interaction.model_name,
        response=interaction.assistant_response or "",
        safety_triggered=interaction.safety_triggered,
        tokens_used=interaction.tokens_used,
        latency_ms=interaction.latency_ms or 0.0,
    )


@router.get("/interactions", response_model=List[AIInteractionResponse])
async def list_interactions(
    session_id: Optional[str] = None,
    adversarial_only: bool = False,
    limit: int = 50,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista histórico de interações com o assistente IA."""
    query = select(AIInteraction).where(AIInteraction.user_id == current_user.id)
    if session_id:
        query = query.where(AIInteraction.session_id == session_id)
    if adversarial_only:
        query = query.where(AIInteraction.is_adversarial == True)
    query = query.order_by(AIInteraction.created_at.desc()).limit(limit)

    result = await db.execute(query)
    return list(result.scalars().all())


@router.get("/interactions/{interaction_id}", response_model=AIInteractionResponse)
async def get_interaction(
    interaction_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retorna detalhes de uma interação específica."""
    from fastapi import HTTPException
    result = await db.execute(
        select(AIInteraction).where(
            AIInteraction.id == interaction_id,
            AIInteraction.user_id == current_user.id,
        )
    )
    interaction = result.scalar_one_or_none()
    if not interaction:
        raise HTTPException(status_code=404, detail="Interação não encontrada.")
    return interaction


@router.post("/cases", response_model=AdversarialCaseResponse, status_code=status.HTTP_201_CREATED)
async def create_adversarial_case(
    data: AdversarialCaseCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Registra um caso de teste adversarial."""
    case = AdversarialCase(created_by=current_user.id, **data.model_dump())
    db.add(case)
    await db.flush()
    await db.refresh(case)
    return case


@router.get("/cases", response_model=List[AdversarialCaseResponse])
async def list_adversarial_cases(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos os casos adversariais registrados."""
    result = await db.execute(
        select(AdversarialCase).order_by(AdversarialCase.created_at.desc())
    )
    return list(result.scalars().all())
