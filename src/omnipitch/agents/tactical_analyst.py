"""Tactical Analyst Agent for decoding game state and strategic shifts."""

from typing import Any, Dict, List
from omnipitch.agents.base import BaseAgent, TacticalAnalysisReport
from omnipitch.models import EventType, MatchEvent


class TacticalAnalystAgent(BaseAgent):
    """
    Analyzes sequences of synthetic match events to deduce tactical dynamics:
    - Control vs Chaos shifts
    - High pressing impact
    - Pass completion under pressure
    - Counter-attack vulnerability
    """

    def __init__(self, name: str = "TacticalAnalyst"):
        super().__init__(name=name)

    async def process(self, context: Dict[str, Any]) -> TacticalAnalysisReport:
        events: List[MatchEvent] = context.get("recent_events", [])
        if not events:
            return TacticalAnalysisReport(
                summary="Insufficient event data for tactical analysis.",
                dominant_team="neutral",
                control_vs_chaos_assessment="stable",
                pressing_pattern="passive",
                key_event_ids=[],
                metrics_snapshot={},
            )

        # Aggregate metrics from the recent window
        event_ids = [e.event_id for e in events]
        passes = [e for e in events if e.event_type == EventType.PASS]
        shots = [e for e in events if e.event_type in (EventType.SHOT, EventType.GOAL)]
        turnovers = [e for e in events if e.event_type in (EventType.TACKLE, EventType.TURNOVER)]

        latest = events[-1]
        tactical_ctx = latest.tactical_context

        # Determine dominant team by volume of attacking actions
        home_actions = sum(1 for e in events if e.team_id == "avalon_city")
        away_actions = len(events) - home_actions
        dominant_team = "avalon_city" if home_actions >= away_actions else "solaria_rovers"

        # Determine pressing and control assessment
        if tactical_ctx.control_vs_chaos_index > 0.65:
            control_str = "Dominant positional possession; sustained rhythm."
        elif tactical_ctx.control_vs_chaos_index < 0.35:
            control_str = "Frantic transition state with high turnover frequency."
        else:
            control_str = "Even contest in mid-block with calculated buildup."

        if tactical_ctx.defensive_pressure_index > 0.60:
            press_str = "Aggressive defensive high-press applied in attacking third."
        else:
            press_str = "Compact mid-block defending."

        # Pass metrics
        avg_pass_diff = 0.0
        if passes:
            diff_sum = sum(p.pass_difficulty_rating or 0.0 for p in passes)
            avg_pass_diff = round(diff_sum / len(passes), 2)

        summary = (
            f"Over the last {len(events)} events, {dominant_team.replace('_', ' ').title()} dictates "
            f"the tempo with a {tactical_ctx.game_rhythm_tempo} pattern. "
            f"{control_str} {press_str}"
        )

        return TacticalAnalysisReport(
            summary=summary,
            dominant_team=dominant_team,
            control_vs_chaos_assessment=control_str,
            pressing_pattern=press_str,
            key_event_ids=event_ids,
            metrics_snapshot={
                "passes_count": len(passes),
                "shots_count": len(shots),
                "turnovers_count": len(turnovers),
                "avg_pass_difficulty": avg_pass_diff,
                "control_vs_chaos_index": tactical_ctx.control_vs_chaos_index,
                "defensive_pressure_index": tactical_ctx.defensive_pressure_index,
                "game_rhythm_tempo": tactical_ctx.game_rhythm_tempo,
            },
        )
