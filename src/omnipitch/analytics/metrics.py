"""Tactical metric algorithms and calculations for synthetic football analytics."""

import math
from typing import Dict, List, Tuple
from omnipitch.models import Coordinates, MatchEvent, TacticalContext


def calculate_euclidean_distance(c1: Coordinates, c2: Coordinates) -> float:
    """Calculates distance on a standard 105m x 68m pitch."""
    # Convert normalized 0-100 coordinates to pitch meters
    dx = (c2.x - c1.x) * 1.05
    dy = (c2.y - c1.y) * 0.68
    return round(math.sqrt(dx * dx + dy * dy), 2)


def calculate_pass_difficulty(
    start: Coordinates,
    end: Coordinates,
    defensive_pressure: float
) -> Tuple[float, float]:
    """
    Computes:
    - pass_distance_m: distance in meters
    - pass_difficulty: normalized rating between 0.05 and 0.98 based on distance, angle, and opposition pressure.
    """
    distance_m = calculate_euclidean_distance(start, end)

    # Base difficulty scaled by distance (short pass = low, 40m+ diagonal = high)
    distance_factor = min(distance_m / 50.0, 1.0) * 0.5

    # Forward progression factor (passes towards goal are harder than backpasses)
    forward_delta = (end.x - start.x) / 100.0
    forward_factor = max(0.0, forward_delta) * 0.25

    # Pressure factor
    pressure_factor = defensive_pressure * 0.25

    difficulty = min(max(distance_factor + forward_factor + pressure_factor, 0.05), 0.98)
    return distance_m, round(difficulty, 2)


def calculate_expected_goals(
    shot_location: Coordinates,
    defensive_pressure: float
) -> float:
    """
    Computes Expected Goals (xG) based on:
    - Distance to target goal (assumed at x=100 or x=0, y=50)
    - Central angle to goal mouth
    - Opposition defensive pressure factor
    """
    target = Coordinates(x=100.0, y=50.0)
    dist_m = calculate_euclidean_distance(shot_location, target)

    # Base probability decay with distance
    # 6-yard box (~5m) -> ~0.55+; penalty spot (11m) -> ~0.35; outside box (22m+) -> ~0.04
    base_xg = math.exp(-dist_m / 14.0) * 0.85

    # Centrality factor (punish sharp angles)
    y_deviation = abs(shot_location.y - 50.0) / 50.0
    angle_factor = max(0.2, 1.0 - (y_deviation * 0.7))

    # Defensive pressure reduction
    pressure_penalty = 1.0 - (defensive_pressure * 0.35)

    xg = base_xg * angle_factor * pressure_penalty
    return round(min(max(xg, 0.01), 0.92), 2)


def is_sprint_speed(speed_kmh: float) -> bool:
    """Premier League physical performance threshold: sprints exceed 27.0 km/h."""
    return speed_kmh >= 27.0


def evaluate_tactical_state(
    consecutive_passes: int,
    turnovers_last_5_min: int,
    pitch_zone_x: float
) -> TacticalContext:
    """
    Determines real-time tactical context:
    - Control vs Chaos: high consecutive passes & low turnovers = high control; fast turnovers = high chaos
    - Defensive Pressure: increases in attacking third
    - Game Rhythm Tempo: classification of the match phase
    """
    # Control vs Chaos: 1.0 is supreme control, 0.0 is utter chaos
    raw_control = (consecutive_passes * 0.12) - (turnovers_last_5_min * 0.15) + 0.5
    control_index = round(min(max(raw_control, 0.05), 0.95), 2)

    # Defensive pressure higher as ball approaches defending goal (x > 65)
    base_pressure = 0.3 + (pitch_zone_x / 100.0) * 0.45
    pressure_index = round(min(max(base_pressure, 0.1), 0.95), 2)

    # Tempo classification
    if control_index < 0.35:
        tempo = "frantic-transition"
    elif control_index > 0.70:
        tempo = "structured-possession"
    elif pitch_zone_x > 75.0:
        tempo = "high-block-siege"
    else:
        tempo = "balanced-contest"

    return TacticalContext(
        control_vs_chaos_index=control_index,
        defensive_pressure_index=pressure_index,
        game_rhythm_tempo=tempo
    )


def calculate_zonal_territory(events: List[MatchEvent]) -> Dict[str, float]:
    """Calculates percentage of possession across three pitch thirds."""
    if not events:
        return {"defensive_third": 33.3, "middle_third": 33.4, "attacking_third": 33.3}

    counts = {"defensive_third": 0, "middle_third": 0, "attacking_third": 0}
    for e in events:
        x = e.start_coordinates.x
        if x < 33.3:
            counts["defensive_third"] += 1
        elif x < 66.6:
            counts["middle_third"] += 1
        else:
            counts["attacking_third"] += 1

    total = len(events)
    return {
        k: round((v / total) * 100.0, 1) for k, v in counts.items()
    }
