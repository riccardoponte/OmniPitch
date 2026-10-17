"""Central Multi-Agent Orchestrator coordinating tactical analysis, narrative, and grounding verification."""

import logging
from typing import List, Optional
from omnipitch.agents.base import BroadcastOverlayPayload
from omnipitch.agents.fallback import FallbackNarrativeGenerator
from omnipitch.agents.narrator import NarratorAgent
from omnipitch.agents.tactical_analyst import TacticalAnalystAgent
from omnipitch.agents.verifier import GroundingVerifierAgent
from omnipitch.models import MatchEvent

logger = logging.getLogger("omnipitch.orchestrator")


class MultiAgentOrchestrator:
    """
    Coordinates agent handoffs across the pipeline:
    1. Ingest event into rolling memory window
    2. Tactical Analyst Agent -> TacticalContext & Strategic Trends
    3. Narrator Agent -> Persona-tailored narrative draft
    4. Grounding Verifier Agent -> Multi-point evidence check
    5. Fallback Engine -> Guaranteed delivery if verification fails or timeout occurs
    """

    def __init__(self, window_size: int = 5):
        self.window_size = window_size
        self.events_history: List[MatchEvent] = []

        # Initialize agents
        self.tactical_agent = TacticalAnalystAgent()
        self.narrator_agent = NarratorAgent()
        self.verifier_agent = GroundingVerifierAgent()

    async def process_event(
        self,
        event: MatchEvent,
        persona: str = "analyst",
        language: str = "en"
    ) -> BroadcastOverlayPayload:
        """Processes an incoming match event and produces a verified broadcast overlay payload."""
        self.events_history.append(event)
        recent_window = self.events_history[-self.window_size:]

        try:
            # Step 1: Tactical Analyst Agent
            tactical_report = await self.tactical_agent.process({
                "recent_events": recent_window,
            })

            # Step 2: Narrator Agent
            narrative_draft = await self.narrator_agent.process({
                "tactical_report": tactical_report,
                "latest_event": event,
                "persona": persona,
                "language": language,
            })

            # Step 3: Grounding Verifier Agent
            verification = await self.verifier_agent.process({
                "narrative_draft": narrative_draft,
                "all_events": recent_window,
            })

            if verification.is_grounded:
                match_time = f"{event.minute:02d}:{event.second:02d}"
                return BroadcastOverlayPayload(
                    overlay_id=f"OVR-{event.event_id}",
                    match_id=event.match_id,
                    match_time=match_time,
                    headline=narrative_draft.headline,
                    narrative=narrative_draft.commentary,
                    persona=persona,
                    language=language,
                    is_verified=True,
                    evidence_event_ids=verification.verified_event_ids,
                    metrics=tactical_report.metrics_snapshot,
                    generated_by="omnipitch-multiagent-foundry",
                )
            else:
                logger.warning(
                    "Verification failed: %s. Falling back to deterministic narrative.",
                    verification.notes,
                )
                return FallbackNarrativeGenerator.generate(event, persona=persona, language=language)

        except Exception as exc:
            logger.error("Exception during multi-agent handoff: %s. Using fallback.", exc)
            return FallbackNarrativeGenerator.generate(event, persona=persona, language=language)
