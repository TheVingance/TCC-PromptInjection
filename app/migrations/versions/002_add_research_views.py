"""Add SQL views: view_attack_results and view_metrics_by_model

Revision ID: 002_add_research_views
Revises: 001_initial
Create Date: 2026-07-23

Cria duas views analíticas no banco para consulta direta:

  - view_attack_results:
      Uma linha por interação adversarial, mostrando:
      LLM testada, tipo de ataque, payload (prévia), resposta do modelo,
      safety_triggered, resultado do ataque (sucesso/falha/parcial).

  - view_metrics_by_model:
      Agregação por modelo: total de interações, adversariais, taxa de
      safety, ASR e ASP — usada pelo endpoint /research/metrics/by-model.
"""
from alembic import op

revision = "002_add_research_views"
down_revision = "001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ── view_attack_results ──────────────────────────────────────────────────
    # Cada linha = uma interação adversarial com seu resultado de ataque.
    # Permite consultar diretamente: qual LLM × qual payload × qual resultado.
    op.execute("""
        CREATE OR REPLACE VIEW view_attack_results AS
        SELECT
            ai.id                                   AS interaction_id,
            ai.model_name                           AS llm_testado,
            ai.provider                             AS provedor,
            ai.threat_category                      AS categoria_ataque,
            ac.attack_vector                        AS vetor_ataque,
            ac.severity                             AS severidade,

            -- Prévia do payload (primeiros 200 caracteres)
            LEFT(ai.user_prompt, 200)               AS payload_preview,

            -- Resposta do modelo (primeiros 300 caracteres)
            LEFT(ai.assistant_response, 300)        AS resposta_preview,

            -- Mecanismo de defesa do modelo foi ativado?
            ai.safety_triggered                     AS safety_triggered,

            -- Resultado classificado pelo backend
            CASE
                WHEN ac.is_successful_attack IS TRUE  THEN 'SUCESSO'
                WHEN ac.is_successful_attack IS FALSE THEN 'BLOQUEADO'
                ELSE                                       'PARCIAL/INCONCLUSIVO'
            END                                     AS resultado_ataque,

            -- Comportamento observado (explicação do backend)
            ac.observed_behavior                    AS comportamento_observado,

            ai.latency_ms                           AS latencia_ms,
            ai.tokens_used                          AS tokens_usados,
            ai.created_at                           AS executado_em
        FROM ai_interactions ai
        INNER JOIN adversarial_cases ac
            ON ac.interaction_id = ai.id
        WHERE ai.is_adversarial = TRUE
        ORDER BY ai.model_name, ai.threat_category, ai.created_at;
    """)

    # ── view_metrics_by_model ────────────────────────────────────────────────
    # Agregação por modelo: métricas consolidadas de segurança.
    op.execute("""
        CREATE OR REPLACE VIEW view_metrics_by_model AS
        SELECT
            ai.model_name,
            ai.provider,
            COUNT(ai.id)                                        AS total_interactions,
            COUNT(ai.id) FILTER (WHERE ai.is_adversarial)      AS adversarial_interactions,
            COUNT(ai.id) FILTER (WHERE ai.safety_triggered)    AS safety_triggered_count,

            ROUND(
                COUNT(ai.id) FILTER (WHERE ai.safety_triggered)::numeric
                / NULLIF(COUNT(ai.id), 0) * 100, 2
            )                                                   AS safety_trigger_rate_pct,

            -- Contagem de ataques com sucesso confirmado
            COUNT(ac.id) FILTER (
                WHERE ac.is_successful_attack IS TRUE
            )                                                   AS successful_attacks,

            -- Contagem de ataques bloqueados (defesa bem-sucedida)
            COUNT(ac.id) FILTER (
                WHERE ac.is_successful_attack IS FALSE
            )                                                   AS failed_attacks,

            -- Contagem de resultados parciais/inconclusivos
            COUNT(ac.id) FILTER (
                WHERE ac.is_successful_attack IS NULL
            )                                                   AS partial_attacks,

            -- ASP: proporção de execuções que resultaram em sucesso do ataque
            ROUND(
                COUNT(ac.id) FILTER (WHERE ac.is_successful_attack IS TRUE)::numeric
                / NULLIF(
                    COUNT(ac.id) FILTER (WHERE ac.is_successful_attack IS NOT NULL),
                    0
                ) * 100, 2
            )                                                   AS asp_pct,

            -- ASR: proporção de payloads únicos com pelo menos 1 sucesso
            ROUND(
                COUNT(DISTINCT ai.user_prompt) FILTER (
                    WHERE ac.is_successful_attack IS TRUE
                )::numeric
                / NULLIF(COUNT(DISTINCT ai.user_prompt), 0) * 100, 2
            )                                                   AS asr_pct,

            MIN(ai.created_at)                                  AS primeiro_teste,
            MAX(ai.created_at)                                  AS ultimo_teste
        FROM ai_interactions ai
        LEFT JOIN adversarial_cases ac
            ON ac.interaction_id = ai.id
        GROUP BY ai.model_name, ai.provider
        ORDER BY total_interactions DESC;
    """)


def downgrade() -> None:
    op.execute("DROP VIEW IF EXISTS view_attack_results;")
    op.execute("DROP VIEW IF EXISTS view_metrics_by_model;")
