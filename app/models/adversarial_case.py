from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
import enum

from core.database import Base


class CaseSeverity(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class AdversarialCase(Base):
    __tablename__ = "adversarial_cases"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    created_by: Mapped[int] = mapped_column(Integer, ForeignKey("users.id"), nullable=False)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    model_name: Mapped[str | None] = mapped_column(String(100), nullable=True, index=True)
    attack_vector: Mapped[str] = mapped_column(String(100), nullable=False)  # e.g. "prompt_injection"
    severity: Mapped[CaseSeverity] = mapped_column(
        Enum(CaseSeverity, values_callable=lambda obj: [e.value for e in obj]),
        default=CaseSeverity.MEDIUM
    )
    expected_behavior: Mapped[str] = mapped_column(Text, nullable=False)     # What the model SHOULD do
    observed_behavior: Mapped[str | None] = mapped_column(Text, nullable=True)  # What it actually did
    is_successful_attack: Mapped[bool | None] = mapped_column(default=None, nullable=True)
    mitigation_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    interaction_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("ai_interactions.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )
