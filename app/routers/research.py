from typing import Any, Dict, List

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from core.database import get_db
from core.dependencies import get_current_user
from models.adversarial_case import AdversarialCase
from models.ai_interaction import AIInteraction, ThreatCategory
from models.audit_log import AuditLog
from models.user import User
from schemas.ai import SecurityMetrics

router = APIRouter(prefix="/research", tags=["Pesquisa & Segurança"])


@router.get("/audit-logs")
async def get_audit_logs(
    limit: int = 100,
    action: str = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retorna logs de auditoria completos (crítico para análise de segurança)."""
    query = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    if action:
        query = query.where(AuditLog.action == action.upper())
    result = await db.execute(query)
    logs = result.scalars().all()
    return [
        {
            "id": l.id,
            "user_id": l.user_id,
            "action": l.action,
            "resource": l.resource,
            "resource_id": l.resource_id,
            "details": l.details,
            "ip_address": l.ip_address,
            "created_at": l.created_at.isoformat(),
        }
        for l in logs
    ]


@router.get("/metrics", response_model=SecurityMetrics)
async def get_security_metrics(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Métricas agregadas de segurança das interações com o assistente IA."""
    total_q = await db.execute(select(func.count(AIInteraction.id)))
    total = total_q.scalar_one()

    adv_q = await db.execute(
        select(func.count(AIInteraction.id)).where(AIInteraction.is_adversarial == True)
    )
    adversarial = adv_q.scalar_one()

    safety_q = await db.execute(
        select(func.count(AIInteraction.id)).where(AIInteraction.safety_triggered == True)
    )
    safety_count = safety_q.scalar_one()

    # By provider
    prov_q = await db.execute(
        select(AIInteraction.provider, func.count(AIInteraction.id)).group_by(AIInteraction.provider)
    )
    by_provider = {row[0].value: row[1] for row in prov_q.all()}

    # By threat category
    threat_q = await db.execute(
        select(AIInteraction.threat_category, func.count(AIInteraction.id))
        .where(AIInteraction.is_adversarial == True)
        .group_by(AIInteraction.threat_category)
    )
    by_threat = {row[0].value: row[1] for row in threat_q.all()}

    # Adversarial case outcomes
    success_q = await db.execute(
        select(func.count(AdversarialCase.id)).where(AdversarialCase.is_successful_attack == True)
    )
    failed_q = await db.execute(
        select(func.count(AdversarialCase.id)).where(AdversarialCase.is_successful_attack == False)
    )

    return SecurityMetrics(
        total_interactions=total,
        adversarial_interactions=adversarial,
        safety_triggered_count=safety_count,
        safety_trigger_rate=round(safety_count / total * 100, 2) if total > 0 else 0.0,
        interactions_by_provider=by_provider,
        interactions_by_threat=by_threat,
        successful_attacks=success_q.scalar_one(),
        failed_attacks=failed_q.scalar_one(),
    )


@router.get("/export")
async def export_interactions(
    adversarial_only: bool = False,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Exporta todas as interações em formato JSON para análise científica."""
    query = select(AIInteraction).order_by(AIInteraction.created_at.asc())
    if adversarial_only:
        query = query.where(AIInteraction.is_adversarial == True)
    result = await db.execute(query)
    interactions = result.scalars().all()

    return [
        {
            "id": i.id,
            "session_id": i.session_id,
            "provider": i.provider.value,
            "model_name": i.model_name,
            "user_prompt": i.user_prompt,
            "assistant_response": i.assistant_response,
            "threat_category": i.threat_category.value,
            "is_adversarial": i.is_adversarial,
            "safety_triggered": i.safety_triggered,
            "researcher_notes": i.researcher_notes,
            "tokens_used": i.tokens_used,
            "latency_ms": i.latency_ms,
            "error_message": i.error_message,
            "created_at": i.created_at.isoformat(),
        }
        for i in interactions
    ]
