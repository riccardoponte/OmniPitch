"""Central Multi-Agent Orchestrator coordinating analysis, commentary, narrative, verification and recaps."""

import logging
import time
from typing import Any, Dict, List, Optional

from omnipitch.agents.base import BroadcastOverlayPayload
from omnipitch.agents.commentary import CommentaryLine, CommentatorAgent, build_facts, intensity_for
from omnipitch.agents.fallback import FallbackNarrativeGenerator
from omnipitch.agents.foundry_client import MicrosoftFoundryClient
from omnipitch.agents.memory import MatchBlackboardMemory
from omnipitch.agents.narrator import NarratorAgent
from omnipitch.agents.player_focus import PlayerFocusAgent
from omnipitch.agents.recap import MatchRecap, RecapAgent
from omnipitch.agents.tactical_analyst import TacticalAnalystAgent
from omnipitch.agents.verifier import GroundingVerifierAgent
from omnipitch.analytics.metrics import calculate_zonal_territory
from omnipitch.generator.teams import create_fictitious_teams
from omnipitch.models import EventType, MatchEvent

logger = logging.getLogger("omnipitch.orchestrator")

AGENT_ORDER = ["ingest", "tactical_analyst", "lead_commentator", "narrator", "player_focus", "verifier", "broadcast"]


class MultiAgentOrchestrator:
    """
    Coordinates agent handoffs over a shared blackboard for every match event:

    1. Ingest            -> event recorded on the MatchBlackboardMemory (shared state)
    2. Tactical Analyst  -> control / pressure / tempo report over the recent window
    3. Lead Commentator  -> live play-by-play line (Foundry LLM on key moments, phrase bank otherwise)
    4. Narrator          -> on-screen headline + "why it matters", co-commentator line on big moments
    5. Player Focus      -> spotlight tracking for the viewer's chosen player
    6. Grounding Verifier-> every number and name checked against the event log and blackboard
    7. Broadcast         -> machine-readable overlay; deterministic fallback if verification fails
    At half-time and full time the Recap agent writes the match report from the same blackboard.
    """

    def __init__(self, match_id: str = "MATCH-2026-001", window_size: int = 5):
        self.match_id = match_id
        self.window_size = window_size
        self.events_history: List[MatchEvent] = []

        # Shared blackboard memory
        self.memory = MatchBlackboardMemory(match_id=match_id)

        # Multi-agent ecosystem
        self.foundry_client = MicrosoftFoundryClient()
        self.tactical_agent = TacticalAnalystAgent()
        self.commentator_agent = CommentatorAgent(foundry_client=self.foundry_client)
        self.narrator_agent = NarratorAgent()
        self.player_focus_agent = PlayerFocusAgent()
        self.verifier_agent = GroundingVerifierAgent()
        self.recap_agent = RecapAgent(foundry_client=self.foundry_client)

        self.teams = create_fictitious_teams()
        self.recaps: Dict[str, MatchRecap] = {}
        self.stats: Dict[str, Any] = {
            "events_processed": 0,
            "overlays_verified": 0,
            "fallbacks_used": 0,
            "claims_checked": 0,
            "claims_rejected": 0,
            "llm_attempts": 0,
            "llm_lines_accepted": 0,
            "llm_lines_rejected": 0,
            "commentary_lines": 0,
            "recaps_written": 0,
            "agent_latency_ms": {name: 0.0 for name in AGENT_ORDER},
        }
        self.recent_rejections: List[str] = []
        self.commentary_log: List[Dict[str, Any]] = []

    # ------------------------------------------------------------------ telemetry

    def _record_latency(self, agent: str, ms: float):
        n = max(self.stats["events_processed"], 1)
        avg = self.stats["agent_latency_ms"][agent]
        self.stats["agent_latency_ms"][agent] = round(avg + (ms - avg) / n, 3)

    def telemetry(self) -> Dict[str, Any]:
        s = self.stats
        checked = max(s["claims_checked"], 1)
        processed = max(s["events_processed"], 1)
        return {
            **s,
            "grounding_rate": round(1 - s["claims_rejected"] / checked, 4) if s["claims_checked"] else 1.0,
            "verified_overlay_rate": round(s["overlays_verified"] / processed, 4) if s["events_processed"] else 1.0,
            "pipeline_latency_ms": round(sum(s["agent_latency_ms"].values()), 2),
            "foundry_configured": self.foundry_client.is_configured,
            "model": self.foundry_client.model if self.foundry_client.is_configured else "local phrase bank",
            "recent_rejections": self.recent_rejections[-5:],
        }

    # ------------------------------------------------------------------ pipeline

    async def process_event(
        self,
        event: MatchEvent,
        persona: str = "analyst",
        language: str = "en",
        target_player: Optional[str] = None,
        favourite_club: Optional[str] = None,
    ) -> BroadcastOverlayPayload:
        """Processes an incoming match event and produces a verified broadcast overlay payload."""
        trace: List[Dict[str, Any]] = []

        def step(name: str, started: float, status: str = "ok", detail: str = ""):
            ms = (time.perf_counter() - started) * 1000.0
            trace.append({"agent": name, "ms": round(ms, 2), "status": status, "detail": detail})
            self._record_latency(name, ms)

        self.stats["events_processed"] += 1

        # 1. Ingest onto the shared blackboard
        t0 = time.perf_counter()
        self.events_history.append(event)
        self.memory.record_event(event)
        recent_window = self.events_history[-self.window_size:]
        state = self.memory.match_state()
        state_numbers = self.memory.state_numbers(state)
        scorer = self.memory.players_stats.get(event.player.player_id) if event.player else None
        facts = build_facts(
            event,
            player_goals=scorer.goals if scorer else 0,
            pass_streak=state["pass_streak"] if state["streak_team"] == event.team_id else 0,
        )
        step("ingest", t0, detail=event.event_id)

        spotlight_name = target_player or (event.player.name if event.player else None)

        try:
            # 2. Tactical Analyst
            t0 = time.perf_counter()
            tactical_report = await self.tactical_agent.process({"recent_events": recent_window})
            step("tactical_analyst", t0, detail=tactical_report.metrics_snapshot.get("game_rhythm_tempo", ""))

            # 3. Lead Commentator (may call Foundry; verified inside)
            t0 = time.perf_counter()
            ctx: Dict[str, Any] = {
                "latest_event": event, "facts": facts, "persona": persona, "language": language,
                "favourite_club": favourite_club, "verifier": self.verifier_agent,
            }
            lead_line: Optional[CommentaryLine] = await self.commentator_agent.process(ctx)
            llm_used = lead_line is not None and lead_line.source == "foundry-llm"
            if self.commentator_agent.foundry.is_configured and ctx.get("rejections") is not None:
                self.stats["llm_lines_rejected"] += len(ctx["rejections"])
                self.recent_rejections += ctx["rejections"]
            if ctx.get("llm_attempted"):
                self.stats["llm_attempts"] += 1
            if llm_used:
                self.stats["llm_lines_accepted"] += 1
            step("lead_commentator", t0, detail="foundry-llm" if llm_used else "phrase-bank")

            # 4. Narrator
            t0 = time.perf_counter()
            draft = await self.narrator_agent.process({
                "tactical_report": tactical_report,
                "latest_event": event,
                "match_state": state,
                "favourite_club": favourite_club,
                "persona": persona,
                "language": language,
            })
            step("narrator", t0, detail=draft.insight_kind)

            # 5. Player Focus
            t0 = time.perf_counter()
            player_focus_insight = None
            if spotlight_name:
                player_focus_insight = await self.player_focus_agent.process({
                    "target_player": spotlight_name,
                    "memory": self.memory,
                    "latest_event": event,
                    "language": language,
                })
            step("player_focus", t0, detail=spotlight_name or "")

            # 6. Grounding Verifier: narrative draft and the lead line
            t0 = time.perf_counter()
            verification = await self.verifier_agent.process({
                "narrative_draft": draft,
                "all_events": recent_window,
                "facts": facts,
                "state_numbers": state_numbers,
                "match_state": state,
            })
            line_check = self.verifier_agent.check_text(lead_line.text, facts) if lead_line else None
            checked = verification.claims_checked + (line_check.claims_checked if line_check else 0)
            rejected = verification.rejected_claims + (line_check.rejected_claims if line_check else [])
            self.stats["claims_checked"] += checked
            self.stats["claims_rejected"] += len(rejected)
            if rejected:
                self.recent_rejections += rejected
            step("verifier", t0, status="ok" if not rejected else "rejected", detail=f"{checked} claims")

            # 7. Broadcast payload
            t0 = time.perf_counter()
            zonal_pcts = calculate_zonal_territory(recent_window)
            combined_metrics = {**tactical_report.metrics_snapshot, "zonal_territory": zonal_pcts, "match_state": state}
            if event.expected_goals is not None:
                combined_metrics["expected_goals"] = event.expected_goals
            if event.is_sprint_burst:
                combined_metrics["is_sprint_burst"] = True

            headline, narrative = draft.headline, draft.commentary
            generated_by = "omnipitch-multiagent"
            if not verification.is_grounded:
                logger.warning("Narrative rejected (%s); using deterministic fallback.", verification.notes)
                fb = FallbackNarrativeGenerator.generate(event, persona=persona, language=language)
                headline, narrative = fb.headline, fb.narrative
                generated_by = "deterministic-fallback-engine"
                self.stats["fallbacks_used"] += 1
            else:
                self.stats["overlays_verified"] += 1

            commentary: List[Dict[str, Any]] = []
            if lead_line:
                commentary.append(lead_line.model_dump())
            if draft.is_color_moment and verification.is_grounded:
                commentary.append(CommentaryLine(
                    speaker="color", text=draft.commentary, intensity=min(intensity_for(event) + 0, 3),
                    language=draft.language, event_id=event.event_id, minute_label=event.match_minute_label,
                ).model_dump())
            self.stats["commentary_lines"] += len(commentary)
            self.commentary_log.extend(commentary)

            foundry_trace = self.foundry_client.last_trace if llm_used else None
            step("broadcast", t0, detail=generated_by)

            return BroadcastOverlayPayload(
                overlay_id=f"OVR-{event.event_id}",
                match_id=event.match_id,
                match_time=event.match_clock,
                headline=headline,
                narrative=narrative,
                persona=persona,
                language=draft.language,
                is_verified=True,
                evidence_event_ids=verification.verified_event_ids or [event.event_id],
                metrics=combined_metrics,
                player_focus=player_focus_insight.model_dump() if player_focus_insight else None,
                trace={
                    "model_name": foundry_trace.model_name if foundry_trace else (
                        self.foundry_client.model if self.foundry_client.is_configured else "local-agents"),
                    "latency_ms": round(sum(t["ms"] for t in trace), 2),
                    "status": foundry_trace.status if foundry_trace else (
                        "foundry_ready" if self.foundry_client.is_configured else "local"),
                },
                generated_by=generated_by,
                event_type=event.event_type.value,
                minute_label=event.match_minute_label,
                insight_kind=draft.insight_kind,
                display_priority=intensity_for(event) if draft.insight_kind not in ("streak", "press_win") else 2,
                commentary=commentary,
                agent_trace=trace,
                verification={
                    "claims_checked": checked,
                    "rejected": rejected,
                    "notes": verification.notes,
                },
            )

        except Exception as exc:
            logger.exception("Exception during multi-agent handoff: %s. Using fallback.", exc)
            self.stats["fallbacks_used"] += 1
            payload = FallbackNarrativeGenerator.generate(event, persona=persona, language=language)
            payload.event_type = event.event_type.value
            payload.minute_label = event.match_minute_label
            payload.agent_trace = trace
            return payload

    async def build_recap(self, kind: str = "full_time", language: str = "en", persona: str = "analyst") -> MatchRecap:
        """Half-time / full-time report from the shared blackboard (cached per kind, language, persona)."""
        key = f"{kind}:{language}:{persona}:{len(self.memory.events_log)}"
        if key in self.recaps:
            return self.recaps[key]
        overview = self.memory.get_match_center_overview(self.teams[0], self.teams[1])
        recap = await self.recap_agent.process({
            "overview": overview, "kind": kind, "language": language, "persona": persona,
            "verifier": self.verifier_agent,
        })
        self.recaps[key] = recap
        self.stats["recaps_written"] += 1
        return recap

    @property
    def last_phase(self) -> Optional[EventType]:
        for e in reversed(self.events_history):
            if e.event_type in (EventType.HALF_TIME, EventType.MATCH_END):
                return e.event_type
        return None
