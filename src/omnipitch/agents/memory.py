"""Match Blackboard & Episodic Memory for Multi-Agent coordination."""

from typing import Dict, List, Optional
from pydantic import BaseModel, Field
from omnipitch.models import EventType, MatchEvent, Player


class PlayerCumulativeStats(BaseModel):
    player_id: str
    name: str
    team_id: str
    total_passes: int = 0
    completed_passes: int = 0
    total_shots: int = 0
    goals: int = 0
    sprint_bursts: int = 0
    distance_km: float = 0.0
    highest_speed_kmh: float = 0.0
    average_pass_difficulty: float = 0.0


class MatchStoryMilestone(BaseModel):
    minute: int
    second: int
    event_id: str
    headline: str
    description: str


class MatchBlackboardMemory:
    """
    Shared episodic blackboard memory for all OmniPitch agents.
    Maintains longitudinal state across the 90 minutes of the match.
    """

    def __init__(self, match_id: str = "MATCH-2026-001"):
        self.match_id = match_id
        self.players_stats: Dict[str, PlayerCumulativeStats] = {}
        self.milestones: List[MatchStoryMilestone] = []
        self.events_log: List[MatchEvent] = []

    def record_event(self, event: MatchEvent):
        """Updates cumulative statistics and longitudinal narrative state."""
        self.events_log.append(event)

        if event.player:
            pid = event.player.player_id
            if pid not in self.players_stats:
                self.players_stats[pid] = PlayerCumulativeStats(
                    player_id=pid,
                    name=event.player.name,
                    team_id=event.team_id,
                )

            stats = self.players_stats[pid]
            stats.distance_km = event.player.distance_covered_km
            if event.player.speed_kmh > stats.highest_speed_kmh:
                stats.highest_speed_kmh = event.player.speed_kmh

            if event.is_sprint_burst:
                stats.sprint_bursts += 1

            if event.event_type == EventType.PASS:
                stats.total_passes += 1
                if event.is_successful:
                    stats.completed_passes += 1
                # Update running average difficulty
                diff = event.pass_difficulty_rating or 0.2
                stats.average_pass_difficulty = round(
                    ((stats.average_pass_difficulty * (stats.total_passes - 1)) + diff) / stats.total_passes, 2
                )

            elif event.event_type == EventType.SHOT:
                stats.total_shots += 1

            elif event.event_type == EventType.GOAL:
                stats.total_shots += 1
                stats.goals += 1
                self.milestones.append(
                    MatchStoryMilestone(
                        minute=event.minute,
                        second=event.second,
                        event_id=event.event_id,
                        headline=f"Goal scored by {event.player.name}",
                        description=f"Clinical finish with {event.shot_speed_kmh or 0} km/h shot velocity.",
                    )
                )

    def get_player_stats(self, player_id_or_name: str) -> Optional[PlayerCumulativeStats]:
        """Looks up player stats by ID or exact/partial name."""
        query = player_id_or_name.lower()
        for pid, stats in self.players_stats.items():
            if pid.lower() == query or query in stats.name.lower():
                return stats
        return None

    def get_top_sprinters(self, top_n: int = 3) -> List[PlayerCumulativeStats]:
        """Returns the top players ranked by sprint bursts and top speed."""
        return sorted(self.players_stats.values(), key=lambda p: (p.sprint_bursts, p.highest_speed_kmh), reverse=True)[:top_n]
