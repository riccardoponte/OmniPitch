"""Generator package for synthetic match events."""

from omnipitch.generator.engine import MatchSimulationEngine
from omnipitch.generator.models import EventType, MatchEvent, Player, Team
from omnipitch.generator.teams import create_fictitious_teams

__all__ = [
    "MatchSimulationEngine",
    "MatchEvent",
    "EventType",
    "Player",
    "Team",
    "create_fictitious_teams",
]
