"""Unit tests for tactical metric calculations."""

from omnipitch.analytics.metrics import (
    calculate_euclidean_distance,
    calculate_pass_difficulty,
    evaluate_tactical_state,
)
from omnipitch.generator.models import Coordinates


def test_distance_calculation():
    c1 = Coordinates(x=0.0, y=0.0)
    c2 = Coordinates(x=100.0, y=0.0)
    dist = calculate_euclidean_distance(c1, c2)
    # Pitch length is 105m
    assert abs(dist - 105.0) < 0.1


def test_pass_difficulty_scaling():
    start = Coordinates(x=30.0, y=50.0)
    short_end = Coordinates(x=35.0, y=50.0)
    long_end = Coordinates(x=85.0, y=85.0)

    _, easy_diff = calculate_pass_difficulty(start, short_end, defensive_pressure=0.1)
    _, hard_diff = calculate_pass_difficulty(start, long_end, defensive_pressure=0.9)

    assert hard_diff > easy_diff
    assert 0.0 <= easy_diff <= 1.0
    assert 0.0 <= hard_diff <= 1.0


def test_tactical_state_indices():
    # Many passes, zero turnovers = high control
    state_ctrl = evaluate_tactical_state(consecutive_passes=12, turnovers_last_5_min=0, pitch_zone_x=45.0)
    assert state_ctrl.control_vs_chaos_index > 0.65

    # Frantic turnovers = chaos
    state_chaos = evaluate_tactical_state(consecutive_passes=0, turnovers_last_5_min=4, pitch_zone_x=70.0)
    assert state_chaos.control_vs_chaos_index < 0.35
