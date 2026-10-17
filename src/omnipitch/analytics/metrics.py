"""Tactical metric algorithms and calculations for synthetic football analytics."""

import math
from typing import Tuple
from omnipitch.models import Coordinates, TacticalContext


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
