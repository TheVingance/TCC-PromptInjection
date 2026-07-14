from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, Float, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from core.database import Base


class LLMProvider(str, enum.Enum):
    OLLAMA = "ollama"
    DEEPSEEK = "deepseek"
    GEMINI = "gemini"


class ThreatCategory(str, enum.Enum):
    NONE = "none"                           # Interação normal
    JAILBREAK = "jailbreak"                 # Tentativa de jailbreak
    SOCIAL_ENGINEERING = "social_eng"       # Engenharia social
    DATA_EXTRACTION = "data_extraction"     # Tentativa de extrair dados
    PRIVILEGE_ESCALATION = "priv_esc"       # Escalada de privilégios
    FINANCIAL_FRAUD = "financial_fraud"     # Fraude financeira simulada
    PROMPT_INJECTION = "prompt_injection"   # Injeção de prompt
    MISINFORMATION = "misinformation"       # Desinformação financeira
    OTHER = "other"


class AIInteraction(Base):
    __tablename__ = "ai_interactions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    session_id: Mapped[str] = mapped_column(String(50), nullable=False, index=True)
    provider: Mapped[LLMProvider] = mapped_column(
        Enum(LLMProvider, values_callable=lambda obj: [e.value for e in obj]), nullable=False
    )
    model_name: Mapped[str] = mapped_column(String(100), nullable=False)

    # Prompt & Response
    system_prompt: Mapped[str | None] = mapped_column(Text, nullable=True)
    user_prompt: Mapped[str] = mapped_column(Text, nullable=False)
    assistant_response: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Security Research Fields
    threat_category: Mapped[ThreatCategory] = mapped_column(
        Enum(ThreatCategory, values_callable=lambda obj: [e.value for e in obj]),
        default=ThreatCategory.NONE
    )
    is_adversarial: Mapped[bool] = mapped_column(Boolean, default=False)
    safety_triggered: Mapped[bool] = mapped_column(Boolean, default=False)  # Did the model refuse?
    researcher_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Metadata
    tokens_used: Mapped[int | None] = mapped_column(Integer, nullable=True)
    latency_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    error_message: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="ai_interactions")
