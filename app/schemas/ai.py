from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field

from models.ai_interaction import LLMProvider, ThreatCategory
from models.adversarial_case import CaseSeverity


# ─── Chat Schemas ──────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # "user" or "assistant"
    content: str


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    session_id: Optional[str] = None
    provider: Optional[LLMProvider] = None   # overrides default
    model_name: Optional[str] = None         # dynamically overrides LLM model (e.g. specific Ollama model)
    system_prompt: Optional[str] = None
    is_adversarial: bool = False             # flag for research tracking
    threat_category: ThreatCategory = ThreatCategory.NONE
    researcher_notes: Optional[str] = None


class ChatResponse(BaseModel):
    interaction_id: int
    session_id: str
    provider: LLMProvider
    model_name: str
    response: str
    safety_triggered: bool
    tokens_used: Optional[int]
    latency_ms: float


# ─── Interaction Schemas ───────────────────────────────────────────────────────

class AIInteractionResponse(BaseModel):
    id: int
    session_id: str
    provider: LLMProvider
    model_name: str
    user_prompt: str
    assistant_response: Optional[str]
    threat_category: ThreatCategory
    is_adversarial: bool
    safety_triggered: bool
    researcher_notes: Optional[str]
    tokens_used: Optional[int]
    latency_ms: Optional[float]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Adversarial Case Schemas ──────────────────────────────────────────────────

class AdversarialCaseCreate(BaseModel):
    title: str = Field(..., max_length=255)
    description: str
    attack_vector: str = Field(..., max_length=100)
    severity: CaseSeverity = CaseSeverity.MEDIUM
    expected_behavior: str
    observed_behavior: Optional[str] = None
    is_successful_attack: Optional[bool] = None
    mitigation_notes: Optional[str] = None
    interaction_id: Optional[int] = None


class AdversarialCaseResponse(BaseModel):
    id: int
    created_by: int
    title: str
    description: str
    attack_vector: str
    severity: CaseSeverity
    expected_behavior: str
    observed_behavior: Optional[str]
    is_successful_attack: Optional[bool]
    mitigation_notes: Optional[str]
    interaction_id: Optional[int]
    created_at: datetime

    model_config = {"from_attributes": True}


# ─── Research Metrics ──────────────────────────────────────────────────────────

class SecurityMetrics(BaseModel):
    total_interactions: int
    adversarial_interactions: int
    safety_triggered_count: int
    safety_trigger_rate: float
    interactions_by_provider: dict
    interactions_by_threat: dict
    successful_attacks: int
    failed_attacks: int
    attack_success_rate: float
    attack_success_probability: float
