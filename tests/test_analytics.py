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


def test_expected_goals_calculation():
    from omnipitch.analytics.metrics import calculate_expected_goals
    # Penalty box central shot (close to goal)
    close_shot = Coordinates(x=92.0, y=50.0)
    xg_high = calculate_expected_goals(close_shot, defensive_pressure=0.2)

    # Halfway line shot (far from goal)
    far_shot = Coordinates(x=55.0, y=10.0)
    xg_low = calculate_expected_goals(far_shot, defensive_pressure=0.8)

    assert xg_high > xg_low
    assert 0.01 <= xg_high <= 0.99
    assert 0.01 <= xg_low <= 0.20


def test_sprint_detection_threshold():
    from omnipitch.analytics.metrics import is_sprint_speed
    assert is_sprint_speed(28.4) is True
    assert is_sprint_speed(27.0) is True
    assert is_sprint_speed(24.5) is False


def test_fabric_lakehouse_export():
    from omnipitch.analytics.fabric_export import MicrosoftFabricLakehouseExporter
    from omnipitch.generator.engine import MatchSimulationEngine
    from omnipitch.agents.memory import MatchBlackboardMemory

    engine = MatchSimulationEngine(seed=42)
    events = engine.generate_full_match(event_count=10)

    memory = MatchBlackboardMemory()
    for e in events:
        memory.record_event(e)

    record = MicrosoftFabricLakehouseExporter.format_event_for_lakehouse(events[0])
    assert "event_id" in record
    assert "match_id" in record
    assert "control_vs_chaos_index" in record

    summary = MicrosoftFabricLakehouseExporter.export_player_physical_summary(memory)
    assert len(summary) > 0
    assert "distance_km" in summary[0]


def test_calculate_attack_momentum():
    from omnipitch.analytics.metrics import calculate_attack_momentum
    from omnipitch.generator.engine import MatchSimulationEngine

    engine = MatchSimulationEngine(seed=42)
    events = engine.generate_full_match(event_count=8)

    # Empty window should be 0.0
    assert calculate_attack_momentum([], "TEAM-AVALON") == 0.0

    momentum = calculate_attack_momentum(events, "TEAM-AVALON")
    assert -100.0 <= momentum <= 100.0


def test_calculate_player_match_rating():
    from omnipitch.analytics.metrics import calculate_player_match_rating

    # Baseline player with average performance
    rating, color = calculate_player_match_rating(
        total_passes=20, completed_passes=16, average_pass_difficulty=0.3,
        total_shots=1, goals=0
    )
    assert 6.0 <= rating <= 7.5
    assert color in ("green", "orange", "red")

    # Star performance player (goals + assists + tackles)
    star_rating, star_color = calculate_player_match_rating(
        total_passes=45, completed_passes=42, average_pass_difficulty=0.5,
        total_shots=4, goals=2, tackles_won=3, sprint_bursts=4
    )
    assert star_rating >= 8.0
    assert star_color == "green"


