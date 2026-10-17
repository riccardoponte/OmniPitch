"""Player Focus Mode Agent for dedicated single-player real-time spotlight."""

from typing import Any, Dict, Optional
from pydantic import BaseModel, Field
from omnipitch.agents.base import BaseAgent
from omnipitch.agents.memory import MatchBlackboardMemory, PlayerCumulativeStats
from omnipitch.models import MatchEvent


class PlayerFocusInsight(BaseModel):
    """Insight payload tailored for the dedicated Player Focus viewing mode."""
    player_id: str
    player_name: str
    team_id: str
    current_speed_kmh: float
    distance_covered_km: float
    sprint_bursts_count: int
    pass_completion_rate: float
    average_pass_difficulty: float
    spotlight_narrative: str
    is_actively_involved: bool
    evidence_event_ids: list[str] = Field(default_factory=list)


class PlayerFocusAgent(BaseAgent):
    """
    Dedicated agent for 'Player Focused Mode'.
    Tracks a specific chosen player (e.g. key playmaker or striker)
    and produces high-frequency, tailored performance intelligence.
    """

    def __init__(self, name: str = "PlayerFocusAgent"):
        super().__init__(name=name)

    async def process(self, context: Dict[str, Any]) -> Optional[PlayerFocusInsight]:
        target_player_name: str = context.get("target_player", "")
        memory: MatchBlackboardMemory = context.get("memory")
        latest_event: MatchEvent = context.get("latest_event")

        if not target_player_name or not memory:
            return None

        stats: Optional[PlayerCumulativeStats] = memory.get_player_stats(target_player_name)
        if not stats:
            return None

        # Check if the player was directly involved in the latest event
        is_involved = False
        evidence_ids = []
        if latest_event.player and latest_event.player.player_id == stats.player_id:
            is_involved = True
            evidence_ids.append(latest_event.event_id)
        elif latest_event.target_player and latest_event.target_player.player_id == stats.player_id:
            is_involved = True
            evidence_ids.append(latest_event.event_id)

        # Pass completion rate
        completion_pct = 100.0
        if stats.total_passes > 0:
            completion_pct = round((stats.completed_passes / stats.total_passes) * 100.0, 1)

        # Generate spotlight commentary
        if is_involved:
            action_type = latest_event.event_type.value.upper()
            speed_txt = f"sprinting at {latest_event.player.speed_kmh} km/h" if latest_event.is_sprint_burst else "on the ball"
            spotlight_narrative = (
                f"Active engagement: {stats.name} executed a {action_type} action, {speed_txt}. "
                f"Total distance covered: {stats.distance_km:.2f} km."
            )
        else:
            spotlight_narrative = (
                f"Positional tracking: {stats.name} maintaining spatial balance. "
                f"Sprints logged: {stats.sprint_bursts} | Pass accuracy: {completion_pct}%."
            )

        return PlayerFocusInsight(
            player_id=stats.player_id,
            player_name=stats.name,
            team_id=stats.team_id,
            current_speed_kmh=latest_event.player.speed_kmh if (latest_event.player and latest_event.player.player_id == stats.player_id) else 0.0,
            distance_covered_km=stats.distance_km,
            sprint_bursts_count=stats.sprint_bursts,
            pass_completion_rate=completion_pct,
            average_pass_difficulty=stats.average_pass_difficulty,
            spotlight_narrative=spotlight_narrative,
            is_actively_involved=is_involved,
            evidence_event_ids=evidence_ids or [latest_event.event_id],
        )
