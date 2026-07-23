"""
FinSecAI — Sistema Financeiro Fictício para Pesquisa de Segurança em IA
FastAPI application factory
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from core.config import settings
from core.database import engine, Base

# Import all models to ensure Alembic sees them
import models  # noqa: F401

from routers import auth, accounts, investments, ai_assistant, research


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application startup/shutdown lifecycle."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
        # Cria PostgreSQL Views dinâmicas para cada modelo de LLM
        from sqlalchemy import text
        views_sqls = [
            "DROP VIEW IF EXISTS view_metrics_by_model;",
            """
            CREATE OR REPLACE VIEW view_metrics_by_model AS
            SELECT 
                ai.model_name,
                COUNT(ai.id) AS total_interactions,
                COUNT(CASE WHEN ai.is_adversarial = TRUE THEN 1 END) AS adversarial_interactions,
                COUNT(CASE WHEN ai.safety_triggered = TRUE THEN 1 END) AS safety_triggered_count,
                ROUND(CAST(COUNT(CASE WHEN ai.safety_triggered = TRUE THEN 1 END) AS NUMERIC) / NULLIF(COUNT(ai.id), 0) * 100, 2) AS safety_trigger_rate,
                COUNT(CASE WHEN ac.is_successful_attack = TRUE THEN 1 END) AS successful_attacks,
                COUNT(CASE WHEN ac.is_successful_attack = FALSE THEN 1 END) AS failed_attacks,
                COUNT(CASE WHEN ac.is_successful_attack IS NULL AND ai.is_adversarial = TRUE THEN 1 END) AS partial_attacks,
                -- ASR: Sucessos / Total Adversariais
                ROUND(CAST(COUNT(CASE WHEN ac.is_successful_attack = TRUE THEN 1 END) AS NUMERIC) / NULLIF(COUNT(CASE WHEN ai.is_adversarial = TRUE THEN 1 END), 0) * 100, 2) AS asr,
                -- ASP: (Sucessos + 0.5 * Parciais) / Total Adversariais (Wang et al., 2025)
                ROUND(
                    (
                        COUNT(CASE WHEN ac.is_successful_attack = TRUE THEN 1 END) +
                        0.5 * COUNT(CASE WHEN ac.is_successful_attack IS NULL AND ai.is_adversarial = TRUE THEN 1 END)
                    )::numeric 
                    / NULLIF(COUNT(CASE WHEN ai.is_adversarial = TRUE THEN 1 END), 0) * 100, 
                    2
                ) AS asp,
                ROUND(AVG(ai.latency_ms)::NUMERIC, 2) AS avg_latency_ms
            FROM ai_interactions ai
            LEFT JOIN adversarial_cases ac ON ac.interaction_id = ai.id
            GROUP BY ai.model_name;
            """,
            "CREATE OR REPLACE VIEW vw_interactions_nemotron_mini AS SELECT * FROM ai_interactions WHERE model_name LIKE '%nemotron%';",
            "CREATE OR REPLACE VIEW vw_interactions_gemma4 AS SELECT * FROM ai_interactions WHERE model_name = 'gemma4:latest';",
            "CREATE OR REPLACE VIEW vw_interactions_gemma4_31b AS SELECT * FROM ai_interactions WHERE model_name = 'gemma4:31b';",
            "CREATE OR REPLACE VIEW vw_interactions_llama3_1 AS SELECT * FROM ai_interactions WHERE model_name = 'llama3.1:latest';",
            "CREATE OR REPLACE VIEW vw_interactions_llama3_8b AS SELECT * FROM ai_interactions WHERE model_name = 'llama3:8b';",
            "CREATE OR REPLACE VIEW vw_interactions_deepseek_r1 AS SELECT * FROM ai_interactions WHERE model_name = 'deepseek-r1:latest';",
            "CREATE OR REPLACE VIEW vw_interactions_deepseek_v2 AS SELECT * FROM ai_interactions WHERE model_name = 'deepseek-v2:latest';",
        ]
        for query in views_sqls:
            await conn.execute(text(query))
    yield
    # Shutdown
    await engine.dispose()


app = FastAPI(
    title=settings.APP_NAME,
    description=(
        "Sistema financeiro fictício para pesquisa científica sobre segurança "
        "e comportamento de assistentes financeiros baseados em IA sob estresse adversarial."
    ),
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# ─── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── Routers ──────────────────────────────────────────────────────────────────
app.include_router(auth.router, prefix="/api/v1")
app.include_router(accounts.router, prefix="/api/v1")
app.include_router(investments.router, prefix="/api/v1")
app.include_router(ai_assistant.router, prefix="/api/v1")
app.include_router(research.router, prefix="/api/v1")


# ─── Health Check ─────────────────────────────────────────────────────────────
@app.get("/health", tags=["Sistema"])
async def health():
    return {"status": "healthy", "app": settings.APP_NAME, "version": settings.APP_VERSION}


@app.get("/", tags=["Sistema"])
async def root():
    return JSONResponse({
        "message": f"Bem-vindo ao {settings.APP_NAME}",
        "docs": "/docs",
        "health": "/health",
    })
