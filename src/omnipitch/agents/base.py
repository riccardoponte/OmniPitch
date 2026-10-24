"""Base agent interfaces and schemas for OmniPitch multi-agent ecosystem."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class AgentThought(BaseModel):
    """Internal reasoning step for explainability and auditing."""
    agent_name: str
    rationale: str
    evidence_ids: List[str] = Field(default_factory=list)
    confidence_score: float = Field(default=1.0, ge=0.0, le=1.0)


class TacticalAnalysisReport(BaseModel):
    """Structured report produced by TacticalAnalystAgent."""
    summary: str
    dominant_team: str
    control_vs_chaos_assessment: str
    pressing_pattern: str
    key_event_ids: List[str]
    metrics_snapshot: Dict[str, Any] = Field(default_factory=dict)


class NarrativeDraft(BaseModel):
    """Draft narrative produced by NarratorAgent."""
    headline: str
    commentary: str
    persona: str  # 'analyst' or 'fan'
    language: str  # 'en', 'it', 'es', etc.
    cited_event_ids: List[str]
    insight_kind: str = "balanced-contest"
    is_color_moment: bool = False


class VerificationResult(BaseModel):
    """Verification verdict from GroundingVerifierAgent."""
    is_grounded: bool
    confidence: float
    verified_event_ids: List[str]
    notes: str
    claims_checked: int = 0
    rejected_claims: List[str] = Field(default_factory=list)


class BroadcastOverlayPayload(BaseModel):
    """Machine-readable JSON overlay ready for live broadcast graphics."""
    overlay_id: str
    match_id: str
    match_time: str
    headline: str
    narrative: str
    persona: str
    language: str
    is_verified: bool
    evidence_event_ids: List[str]
    metrics: Dict[str, Any] = Field(default_factory=dict)
    player_focus: Optional[Dict[str, Any]] = None
    trace: Optional[Dict[str, Any]] = None
    generated_by: str = "omnipitch-multiagent"

    # Live broadcast extras
    event_type: Optional[str] = None
    minute_label: Optional[str] = None
    insight_kind: Optional[str] = None
    display_priority: int = Field(1, ge=1, le=3, description="1 routine, 2 notable, 3 must-show")
    commentary: List[Dict[str, Any]] = Field(default_factory=list, description="Live commentary lines (lead + color)")
    agent_trace: List[Dict[str, Any]] = Field(default_factory=list, description="Per-agent handoff timing and status")
    verification: Optional[Dict[str, Any]] = None


class BaseAgent(ABC):
    """Abstract base class for all OmniPitch agents."""

    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    async def process(self, context: Dict[str, Any]) -> Any:
        """Execute agent task asynchronously."""
        pass
