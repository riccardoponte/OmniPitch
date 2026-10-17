"""Unit tests for synthetic match generator and models."""

import pytest
from omnipitch.generator.engine import MatchSimulationEngine
from omnipitch.generator.models import EventType
from omnipitch.generator.teams import create_fictitious_teams


def test_create_fictitious_teams():
    teams = create_fictitious_teams()
    assert len(teams) == 2
    home, away = teams[0], teams[1]

    assert home.team_id == "avalon_city"
    assert away.team_id == "solaria_rovers"
    assert len(home.players) == 11
    assert len(away.players) == 11

    # Check that positions are assigned
    positions = {p.position for p in home.players}
    assert "GK" in positions
    assert "DEF" in positions
    assert "MID" in positions
    assert "FWD" in positions


def test_engine_deterministic_seed():
    """Ensure identical seed produces identical event sequence."""
    engine_a = MatchSimulationEngine(seed=123)
    events_a = engine_a.generate_full_match(event_count=20)

    engine_b = MatchSimulationEngine(seed=123)
    events_b = engine_b.generate_full_match(event_count=20)

    assert len(events_a) == 20
    assert len(events_b) == 20

    for ea, eb in zip(events_a, events_b):
        assert ea.event_id == eb.event_id
        assert ea.event_type == eb.event_type
        assert ea.minute == eb.minute
        assert ea.second == eb.second
        if ea.player and eb.player:
            assert ea.player.player_id == eb.player.player_id


def test_event_evidence_and_metrics():
    """Verify hero metrics: pass difficulty, ball speed, tactical indices, evidence ID."""
    engine = MatchSimulationEngine(seed=42)
    events = engine.generate_full_match(event_count=35)

    for evt in events:
        assert evt.event_id.startswith("EVT-")
        assert 0.0 <= evt.start_coordinates.x <= 100.0
        assert 0.0 <= evt.start_coordinates.y <= 100.0

        # Tactical context must always be present
        ctx = evt.tactical_context
        assert 0.0 <= ctx.control_vs_chaos_index <= 1.0
        assert 0.0 <= ctx.defensive_pressure_index <= 1.0
        assert ctx.game_rhythm_tempo in {
            "frantic-transition",
            "structured-possession",
            "high-block-siege",
            "balanced-contest",
        }

        # Specific metric checks
        if evt.event_type == EventType.PASS:
            assert evt.pass_distance_m is not None
            assert evt.pass_difficulty_rating is not None
            assert 0.0 <= evt.pass_difficulty_rating <= 1.0
        elif evt.event_type in (EventType.SHOT, EventType.GOAL):
            assert evt.shot_speed_kmh is not None
            assert evt.shot_speed_kmh > 50.0
