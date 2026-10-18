"""Tests for OmniPitch FastAPI endpoints."""

from fastapi.testclient import TestClient
from omnipitch.api.app import app
from omnipitch.generator.engine import MatchSimulationEngine

client = TestClient(app)


def test_health_endpoint():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "OmniPitch API"


def test_dashboard_root_endpoint():
    response = client.get("/")
    assert response.status_code == 200
    assert "OmniPitch" in response.text
    assert "pitch-canvas" in response.text


def test_match_info_endpoint():
    response = client.get("/api/match/MATCH-2026-TEST/info?seed=42")
    assert response.status_code == 200
    data = response.json()
    assert data["match_id"] == "MATCH-2026-TEST"
    assert data["home_team"]["name"] == "Avalon City FC"
    assert data["away_team"]["name"] == "Solaria Rovers"


def test_match_events_batch_endpoint():
    response = client.get("/api/match/MATCH-2026-TEST/events?count=5&seed=42")
    assert response.status_code == 200
    events = response.json()
    assert len(events) == 5
    first = events[0]
    assert first["event_id"] == "EVT-0001"
    assert "tactical_context" in first


def test_ingest_event_webhook():
    engine = MatchSimulationEngine(seed=12)
    sample_event = engine.generate_event(minute=10, second=15)

    payload = {
        "match_id": "MATCH-TEST-INGEST",
        "event": sample_event.model_dump(),
        "persona": "analyst",
        "language": "en",
    }

    response = client.post("/api/events/ingest", json=payload)
    assert response.status_code == 200
    overlay = response.json()
    assert overlay["match_id"] == "MATCH-TEST-INGEST"
    assert overlay["is_verified"] is True
    assert len(overlay["evidence_event_ids"]) > 0


def test_fabric_export_endpoint():
    response = client.get("/api/match/MATCH-2026-TEST/fabric/export?seed=42")
    assert response.status_code == 200
    data = response.json()
    assert data["lakehouse_workspace"] == "OmniPitch-Fabric-Analytics"
    assert "delta_tables" in data
    assert "fact_match_events" in data["delta_tables"]
    assert "dim_player_physical_summary" in data["delta_tables"]


def test_match_center_overview_endpoint():
    response = client.get("/api/match/MATCH-PRO-TEST/matchcenter/overview?seed=42")
    assert response.status_code == 200
    data = response.json()
    assert data["match_id"] == "MATCH-PRO-TEST"
    assert "attack_momentum" in data
    assert len(data["attack_momentum"]) > 0
    assert "comparison_stats" in data
    assert "expected_goals" in data["comparison_stats"]
    assert "possession" in data["comparison_stats"]
    assert "total_shots" in data["comparison_stats"]
    assert "lineups" in data
    assert len(data["lineups"]["home"]) == 11
    assert len(data["lineups"]["away"]) == 11
    # Check that at least one player is designated MVP
    all_players = data["lineups"]["home"] + data["lineups"]["away"]
    mvp_players = [p for p in all_players if p["is_mvp"]]
    assert len(mvp_players) == 1
    assert "shot_map" in data
    assert "timeline" in data


def test_match_center_prematch_overview():
    """Verify that a new unstarted match begins with clean 0 statistics and no premature MVP."""
    response = client.get("/api/match/MATCH-PREMATCH-CLEAN/matchcenter/overview?seed=42")
    assert response.status_code == 200
    data = response.json()
    assert data["match_id"] == "MATCH-PREMATCH-CLEAN"
    assert data["attack_momentum"] == []
    assert data["shot_map"] == []
    assert data["timeline"] == []
    stats = data["comparison_stats"]
    assert stats["expected_goals"]["home"] == 0.0
    assert stats["expected_goals"]["away"] == 0.0
    assert stats["possession"]["home"] == 50.0
    assert stats["possession"]["away"] == 50.0
    assert stats["total_shots"]["home"] == 0
    assert stats["total_shots"]["away"] == 0
    all_players = data["lineups"]["home"] + data["lineups"]["away"]
    mvp_players = [p for p in all_players if p["is_mvp"]]
    assert len(mvp_players) == 0


def test_reset_match_session():
    """Verify that resetting a match session clears blackboard memory."""
    # Seed events
    client.get("/api/match/MATCH-TO-RESET-TEST/matchcenter/overview")
    # Reset
    reset_resp = client.post("/api/match/MATCH-TO-RESET-TEST/reset")
    assert reset_resp.status_code == 200
    assert reset_resp.json()["status"] == "reset"


def test_league_standings_endpoint():
    response = client.get("/api/league/standings")
    assert response.status_code == 200
    data = response.json()
    assert "standings" in data
    assert len(data["standings"]) == 10
    assert data["standings"][0]["team_id"] == "avalon_city"
    assert data["standings"][1]["team_id"] == "solaria_rovers"


def test_team_profile_endpoint():
    response = client.get("/api/teams/avalon_city")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Avalon City FC"
    assert "stadium" in data
    assert "tactical_system" in data
    assert "season_stats" in data


def test_player_dossier_endpoint():
    response = client.get("/api/players/AVA-08")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Julian Drake"
    assert data["number"] == 8
    assert "cv_highlights" in data
    assert "season_2025_stats" in data
    assert "live_match_stats" in data


def test_events_table_endpoint():
    response = client.get("/api/match/MATCH-TABLE-TEST/events/table")
    assert response.status_code == 200
    data = response.json()
    assert "rows" in data
    assert "columns" in data
    assert len(data["rows"]) > 0


def test_events_csv_endpoint():
    response = client.get("/api/match/MATCH-CSV-TEST/events/csv")
    assert response.status_code == 200
    assert "text/csv" in response.headers["content-type"]
    assert "EventID,MatchID" in response.text




