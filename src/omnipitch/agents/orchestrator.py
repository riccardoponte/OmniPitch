"""Central Multi-Agent Orchestrator coordinating tactical analysis, narrative, and grounding verification."""

import logging
from typing import Any, Dict, List, Optional
from omnipitch.agents.base import BroadcastOverlayPayload
from omnipitch.agents.fallback import FallbackNarrativeGenerator
from omnipitch.agents.foundry_client import MicrosoftFoundryClient
from omnipitch.agents.memory import MatchBlackboardMemory
from omnipitch.agents.narrator import NarratorAgent
from omnipitch.agents.player_focus import PlayerFocusAgent
from omnipitch.agents.tactical_analyst import TacticalAnalystAgent
from omnipitch.agents.verifier import GroundingVerifierAgent
from omnipitch.analytics.metrics import calculate_zonal_territory
from omnipitch.models import MatchEvent

logger = logging.getLogger("omnipitch.orchestrator")


class MultiAgentOrchestrator:
    """
    Coordinates agent handoffs across the pipeline:
    1. Ingest event into rolling memory window & longitudinal MatchBlackboardMemory
    2. Tactical Analyst Agent -> TacticalContext & Strategic Trends
    3. Narrator Agent -> Persona-tailored narrative draft
    4. Player Focus Agent -> Dedicated single-player spotlight tracking
    5. Grounding Verifier Agent -> Multi-point evidence check
    6. Microsoft Foundry Execution -> Latency and token telemetry tracing
    7. Fallback Engine -> Guaranteed delivery if verification fails or timeout occurs
    """

    def __init__(self, match_id: str = "MATCH-2026-001", window_size: int = 5):
        self.match_id = match_id
        self.window_size = window_size
        self.events_history: List[MatchEvent] = []

        # Shared blackboard memory
        self.memory = MatchBlackboardMemory(match_id=match_id)

        # Multi-Agent ecosystem
        self.tactical_agent = TacticalAnalystAgent()
        self.narrator_agent = NarratorAgent()
        self.player_focus_agent = PlayerFocusAgent()
        self.verifier_agent = GroundingVerifierAgent()
        self.foundry_client = MicrosoftFoundryClient()

    async def process_event(
        self,
        event: MatchEvent,
        persona: str = "analyst",
        language: str = "en",
        target_player: Optional[str] = None,
    ) -> BroadcastOverlayPayload:
        """Processes an incoming match event and produces a verified broadcast overlay payload."""
        self.events_history.append(event)
        self.memory.record_event(event)
        recent_window = self.events_history[-self.window_size:]

        # Choose player to spotlight (explicit target or current event player)
        spotlight_name = target_player or (event.player.name if event.player else None)

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

            # Step 3: Player Focus Agent (if player spotlight requested)
            player_focus_insight = None
            if spotlight_name:
                player_focus_insight = await self.player_focus_agent.process({
                    "target_player": spotlight_name,
                    "memory": self.memory,
                    "latest_event": event,
                })

            # Step 4: Grounding Verifier Agent
            verification = await self.verifier_agent.process({
                "narrative_draft": narrative_draft,
                "all_events": recent_window,
            })

            # Step 5: Microsoft Foundry Tracing telemetry
            _, trace = await self.foundry_client.generate_tactical_text(
                system_prompt="Tactical narrator",
                user_prompt=narrative_draft.headline,
            )

            # Compute tactical zonal territory
            zonal_pcts = calculate_zonal_territory(recent_window)
            combined_metrics = {
                **tactical_report.metrics_snapshot,
                "zonal_territory": zonal_pcts,
            }
            if event.expected_goals is not None:
                combined_metrics["expected_goals"] = event.expected_goals
            if event.is_sprint_burst:
                combined_metrics["is_sprint_burst"] = True

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
                    metrics=combined_metrics,
                    player_focus=player_focus_insight.model_dump() if player_focus_insight else None,
                    trace=trace.model_dump() if trace else None,
                    generated_by="omnipitch-multiagent-foundry",
                )
            else:
                logger.warning(
                    "Verification failed: %s. Falling back to deterministic narrative.",
                    verification.notes,
                )
                fb = FallbackNarrativeGenerator.generate(event, persona=persona, language=language)
                fb.player_focus = player_focus_insight.model_dump() if player_focus_insight else None
                fb.trace = trace.model_dump() if trace else None
                return fb

        except Exception as exc:
            logger.error("Exception during multi-agent handoff: %s. Using fallback.", exc)
            return FallbackNarrativeGenerator.generate(event, persona=persona, language=language)
