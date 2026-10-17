"""Core domain models for OmniPitch."""

from enum import Enum
from typing import List, Optional
from pydantic import BaseModel, Field


class EventType(str, Enum):
    MATCH_START = "match_start"
    PASS = "pass"
    SHOT = "shot"
    GOAL = "goal"
    SAVE = "save"
    TACKLE = "tackle"
    INTERCEPTION = "interception"
    TURNOVER = "turnover"
    PRESSURE = "pressure"
    FOUL = "foul"
    HALF_TIME = "half_time"
    MATCH_END = "match_end"


class PitchZone(str, Enum):
    DEFENSIVE_THIRD = "defensive_third"
    MIDDLE_THIRD = "middle_third"
    ATTACKING_THIRD = "attacking_third"
    PENALTY_BOX = "penalty_box"


class Coordinates(BaseModel):
    """Normalized pitch coordinates from 0.0 to 100.0 (x: length 0-100, y: width 0-100)."""
    x: float = Field(..., ge=0.0, le=100.0, description="Pitch length (0: defending goal, 100: attacking goal)")
    y: float = Field(..., ge=0.0, le=100.0, description="Pitch width (0: left touchline, 100: right touchline)")


class Player(BaseModel):
    """Fictitious player profile with real-time tracking metrics."""
    player_id: str
    name: str
    number: int
    position: str  # GK, DEF, MID, FWD
    team_id: str
    speed_kmh: float = 0.0
    distance_covered_km: float = 0.0


class Team(BaseModel):
    """Fictitious team model."""
    team_id: str
    name: str
    short_name: str
    primary_color: str
    secondary_color: str
    formation: str = "4-3-3"
    players: List[Player] = Field(default_factory=list)


class TacticalContext(BaseModel):
    """Real-time tactical indices explaining why moments matter."""
    control_vs_chaos_index: float = Field(
        ..., ge=0.0, le=1.0, description="0.0 = total chaos / frantic turnover; 1.0 = dominant possession control"
    )
    defensive_pressure_index: float = Field(
        ..., ge=0.0, le=1.0, description="Pressure applied by the defending side (0.0 = low, 1.0 = suffocating press)"
    )
    game_rhythm_tempo: str = Field(
        ..., description="Pace of match (e.g. 'high-tempo-transition', 'slow-buildup', 'broken-play')"
    )


class MatchEvent(BaseModel):
    """Synthetic football match event with physical metrics and evidence tracking."""
    event_id: str = Field(..., description="Unique event ID (e.g. EVT-0042) used as evidence for agent grounding")
    match_id: str
    minute: int
    second: int
    event_type: EventType
    team_id: str
    player: Optional[Player] = None
    target_player: Optional[Player] = None
    start_coordinates: Coordinates
    end_coordinates: Optional[Coordinates] = None

    # Physics & Quality metrics (Hero features from Official Rules)
    ball_speed_kmh: Optional[float] = None
    shot_speed_kmh: Optional[float] = None
    pass_distance_m: Optional[float] = None
    pass_difficulty_rating: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="0.0 = routine safe pass, 1.0 = high-risk line-breaking pass"
    )
    expected_goals: Optional[float] = Field(
        None, ge=0.0, le=1.0, description="Modeled probability of a shot resulting in a goal (0.01 - 0.99)"
    )
    is_sprint_burst: bool = Field(
        False, description="True if player speed exceeded high-intensity sprint threshold (>27.0 km/h)"
    )
    is_successful: bool = True

    # Tactical context attached to this moment
    tactical_context: TacticalContext


class MatchScore(BaseModel):
    home_score: int = 0
    away_score: int = 0


class MatchMetadata(BaseModel):
    match_id: str
    home_team: Team
    away_team: Team
    stadium: str
    weather: str
    score: MatchScore = Field(default_factory=MatchScore)
    current_minute: int = 0
    current_second: int = 0
