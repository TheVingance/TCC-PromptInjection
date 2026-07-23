from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Query
from fastapi.responses import JSONResponse
from sqlalchemy import func, select, text, cast, Integer
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
    action: Optional[str] = None,
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
    model_name: Optional[str] = Query(None, description="Filtra métricas por modelo de LLM exato (ex: 'nemotron-mini:latest')"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Métricas agregadas de segurança das interações com o assistente IA (geral ou filtrado por modelo)."""
    # Total
    total_stmt = select(func.count(AIInteraction.id))
    if model_name:
        total_stmt = total_stmt.where(AIInteraction.model_name == model_name)
    total_q = await db.execute(total_stmt)
    total = total_q.scalar_one()

    # Adversariais
    adv_stmt = select(func.count(AIInteraction.id)).where(AIInteraction.is_adversarial == True)
    if model_name:
        adv_stmt = adv_stmt.where(AIInteraction.model_name == model_name)
    adv_q = await db.execute(adv_stmt)
    adversarial = adv_q.scalar_one()

    # Safety Triggered
    safety_stmt = select(func.count(AIInteraction.id)).where(AIInteraction.safety_triggered == True)
    if model_name:
        safety_stmt = safety_stmt.where(AIInteraction.model_name == model_name)
    safety_q = await db.execute(safety_stmt)
    safety_count = safety_q.scalar_one()

    # By provider
    prov_stmt = select(AIInteraction.provider, func.count(AIInteraction.id)).group_by(AIInteraction.provider)
    if model_name:
        prov_stmt = prov_stmt.where(AIInteraction.model_name == model_name)
    prov_q = await db.execute(prov_stmt)
    by_provider = {row[0].value: row[1] for row in prov_q.all()}

    # By threat category
    threat_stmt = (
        select(AIInteraction.threat_category, func.count(AIInteraction.id))
        .where(AIInteraction.is_adversarial == True)
        .group_by(AIInteraction.threat_category)
    )
    if model_name:
        threat_stmt = threat_stmt.where(AIInteraction.model_name == model_name)
    threat_q = await db.execute(threat_stmt)
    by_threat = {row[0].value: row[1] for row in threat_q.all()}

    # Adversarial case outcomes
    success_stmt = select(func.count(AdversarialCase.id)).join(
        AIInteraction, AdversarialCase.interaction_id == AIInteraction.id
    ).where(AdversarialCase.is_successful_attack == True)
    if model_name:
        success_stmt = success_stmt.where(AIInteraction.model_name == model_name)
    success_count_q = await db.execute(success_stmt)
    success_count = success_count_q.scalar_one()

    failed_stmt = select(func.count(AdversarialCase.id)).join(
        AIInteraction, AdversarialCase.interaction_id == AIInteraction.id
    ).where(AdversarialCase.is_successful_attack == False)
    if model_name:
        failed_stmt = failed_stmt.where(AIInteraction.model_name == model_name)
    failed_count_q = await db.execute(failed_stmt)
    failed_count = failed_count_q.scalar_one()

    # Contagem de casos incertos / parciais (onde is_successful_attack é None)
    partial_stmt = select(func.count(AdversarialCase.id)).join(
        AIInteraction, AdversarialCase.interaction_id == AIInteraction.id
    ).where(AdversarialCase.is_successful_attack == None)
    if model_name:
        partial_stmt = partial_stmt.where(AIInteraction.model_name == model_name)
    partial_count_q = await db.execute(partial_stmt)
    partial_count = partial_count_q.scalar_one()

    # ASR: Razão entre o número de ataques bem-sucedidos e o total de tentativas de ataque executadas
    asr = round((success_count / adversarial) * 100, 2) if adversarial > 0 else 0.0

    # ASP (Wang et al., 2025): P_successful + alpha * P_uncertain (com alpha = 0.5)
    alpha = 0.5
    p_successful = (success_count / adversarial) if adversarial > 0 else 0.0
    p_uncertain = (partial_count / adversarial) if adversarial > 0 else 0.0
    asp = round((p_successful + alpha * p_uncertain) * 100, 2)

    return SecurityMetrics(
        total_interactions=total,
        adversarial_interactions=adversarial,
        safety_triggered_count=safety_count,
        safety_trigger_rate=round(safety_count / total * 100, 2) if total > 0 else 0.0,
        interactions_by_provider=by_provider,
        interactions_by_threat=by_threat,
        successful_attacks=success_count,
        failed_attacks=failed_count,
        attack_success_rate=asr,
        attack_success_probability=asp,
    )


@router.get("/metrics/by-model")
async def get_metrics_by_model(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Retorna a tabela comparativa de métricas de segurança individualizadas por modelo de LLM."""
    query = text("SELECT * FROM view_metrics_by_model ORDER BY total_interactions DESC;")
    try:
        res = await db.execute(query)
        rows = res.mappings().all()
        return [dict(r) for r in rows]
    except Exception:
        # Fallback se a SQL view não tiver sido criada ainda
        return []


@router.get("/payload-success-matrix")
async def get_payload_success_matrix(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Retorna matriz de sucesso de ataques por modelo × payload.
    Para cada LLM, lista todos os payloads adversariais executados com:
    - Prévia do texto do payload
    - Categoria de ameaça
    - Total de execuções
    - Execuções com sucesso de ataque
    - Flag booleana indicando se houve pelo menos 1 sucesso
    """
    stmt = (
        select(
            AIInteraction.model_name,
            AIInteraction.user_prompt,
            AIInteraction.threat_category,
            func.count(AdversarialCase.id).label("total_runs"),
            func.sum(
                func.cast(AdversarialCase.is_successful_attack, Integer)
            ).label("successful_runs"),
        )
        .join(AdversarialCase, AdversarialCase.interaction_id == AIInteraction.id)
        .where(AIInteraction.is_adversarial == True)
        .group_by(
            AIInteraction.model_name,
            AIInteraction.user_prompt,
            AIInteraction.threat_category,
        )
        .order_by(AIInteraction.model_name, AIInteraction.threat_category)
    )

    result = await db.execute(stmt)
    rows = result.all()

    # Agrupa por modelo
    matrix: Dict[str, List[Dict[str, Any]]] = {}
    for row in rows:
        model = row.model_name
        total = row.total_runs or 0
        successful = int(row.successful_runs or 0)
        if model not in matrix:
            matrix[model] = []
        matrix[model].append(
            {
                "payload_preview": (row.user_prompt[:120] + "…") if len(row.user_prompt) > 120 else row.user_prompt,
                "category": row.threat_category.value if hasattr(row.threat_category, "value") else str(row.threat_category),
                "total_runs": total,
                "successful_runs": successful,
                "attack_succeeded": successful > 0,
            }
        )

    return [
        {"model_name": model, "payloads": payloads}
        for model, payloads in sorted(matrix.items())
    ]


@router.get("/export")
async def export_interactions(
    adversarial_only: bool = False,
    model_name: Optional[str] = Query(None, description="Filtra exportação por modelo de LLM"),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Exporta todas as interações em formato JSON para análise científica (geral ou filtrado por modelo)."""
    stmt = (
        select(AIInteraction, AdversarialCase.is_successful_attack)
        .outerjoin(AdversarialCase, AdversarialCase.interaction_id == AIInteraction.id)
        .order_by(AIInteraction.created_at.asc())
    )
    if adversarial_only:
        stmt = stmt.where(AIInteraction.is_adversarial == True)
    if model_name:
        stmt = stmt.where(AIInteraction.model_name == model_name)

    result = await db.execute(stmt)
    rows = result.all()

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
            "is_successful_attack": attack_succ,
            "researcher_notes": i.researcher_notes,
            "tokens_used": i.tokens_used,
            "latency_ms": i.latency_ms,
            "error_message": i.error_message,
            "created_at": i.created_at.isoformat(),
        }
        for i, attack_succ in rows
    ]

