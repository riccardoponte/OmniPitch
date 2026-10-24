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
    defensive_pressure: float,
    attacking_right: bool = True,
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
    forward_delta = ((end.x - start.x) if attacking_right else (start.x - end.x)) / 100.0
    forward_factor = max(0.0, forward_delta) * 0.25

    # Pressure factor
    pressure_factor = defensive_pressure * 0.25

    difficulty = min(max(distance_factor + forward_factor + pressure_factor, 0.05), 0.98)
    return distance_m, round(difficulty, 2)


def calculate_expected_goals(
    shot_location: Coordinates,
    defensive_pressure: float,
    attacking_right: bool = True,
) -> float:
    """
    Computes Expected Goals (xG) based on:
    - Distance to target goal (assumed at x=100 or x=0, y=50)
    - Central angle to goal mouth
    - Opposition defensive pressure factor
    """
    target = Coordinates(x=100.0 if attacking_right else 0.0, y=50.0)
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
    """Common elite-football tracking threshold: sprints exceed 27.0 km/h."""
    return speed_kmh >= 27.0


def evaluate_tactical_state(
    consecutive_passes: int,
    turnovers_last_5_min: int,
    pitch_zone_x: float
) -> TacticalContext:
    # pitch_zone_x is the attacking team's progress up the pitch (0 = own goal, 100 = opponent goal)
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


def calculate_attack_momentum(events_window: List[MatchEvent], home_team_id: str) -> float:
    """
    Calculates minute-by-minute Attack Momentum for a time window (e.g. 1 minute).
    Positive values (+1.0 to +100.0) indicate Home dominance.
    Negative values (-1.0 to -100.0) indicate Away dominance.
    0.0 indicates neutral contest.
    """
    if not events_window:
        return 0.0

    home_points = 0.0
    away_points = 0.0

    for e in events_window:
        is_home = (e.team_id == home_team_id)
        pts = 0.0

        if e.event_type.value == "goal":
            pts += 80.0
        elif e.event_type.value == "shot":
            pts += 25.0 + ((e.expected_goals or 0.1) * 35.0)
        elif e.event_type.value == "pass":
            # Passes in attacking third carry heavier momentum
            if (is_home and e.start_coordinates.x > 66.0) or (not is_home and e.start_coordinates.x < 34.0):
                pts += 12.0
            else:
                pts += 4.0
        elif e.event_type.value in ("tackle", "interception"):
            pts += 10.0
        elif e.event_type.value == "pressure":
            pts += 6.0

        if is_home:
            home_points += pts
        else:
            away_points += pts

    total = home_points + away_points
    if total == 0:
        return 0.0

    raw_momentum = ((home_points - away_points) / max(total, 40.0)) * 100.0
    return round(min(max(raw_momentum, -100.0), 100.0), 1)


def calculate_player_match_rating(
    total_passes: int,
    completed_passes: int,
    average_pass_difficulty: float,
    total_shots: int,
    goals: int,
    tackles_won: int = 0,
    interceptions: int = 0,
    saves: int = 0,
    fouls: int = 0,
    sprint_bursts: int = 0,
    position: str = "MID"
) -> Tuple[float, str]:
    """
    Multi-factor Player Match Performance Rating algorithm.
    Returns (rating, rating_color_class):
    - rating: float between 3.0 and 10.0 (baseline 6.5)
    - rating_color: 'green' (>= 7.0), 'orange' (6.5 - 6.9), 'red' (< 6.5)
    """
    rating = 6.5

    # Passing contribution
    if total_passes > 0:
        completion_pct = completed_passes / total_passes
        # High volume and high accuracy reward
        rating += (completion_pct - 0.75) * 1.2
        rating += (average_pass_difficulty - 0.25) * 0.8

    # Goals and Shots
    rating += goals * 1.1
    rating += (total_shots - goals) * 0.15

    # Defensive & Goalkeeper contributions
    rating += tackles_won * 0.25
    rating += interceptions * 0.20
    rating += saves * 0.40

    # Physical intensity
    rating += min(sprint_bursts * 0.08, 0.6)

    # Penalties
    rating -= fouls * 0.25

    # Position adjustment: GK baseline stability
    if position == "GK" and goals == 0:
        rating += 0.3

    # Bound strictly between 3.0 and 10.0
    final_rating = round(min(max(rating, 3.0), 10.0), 1)

    if final_rating >= 7.0:
        color = "green"
    elif final_rating >= 6.5:
        color = "orange"
    else:
        color = "red"

    return final_rating, color

