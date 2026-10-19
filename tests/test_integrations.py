"""
Tests for Microsoft AI Foundry Agent Service and Power Automate / Logic Apps Adaptive Card integrations.
"""

import pytest
from fastapi.testclient import TestClient
from omnipitch.api.app import app
from omnipitch.integrations.power_automate import (
    build_goal_adaptive_card,
    build_tactical_shift_adaptive_card,
    build_incident_adaptive_card,
    PowerAutomateDispatcher,
)


@pytest.fixture
def client():
    return TestClient(app)


def test_foundry_agents_endpoint(client):
    """Verifies that /api/foundry/agents returns the 5 Microsoft AI Foundry agents and benchmarks."""
    response = client.get("/api/foundry/agents")
    assert response.status_code == 200
    data = response.json()
    assert data["total_active_agents"] == 5
    assert data["primary_model"] == "gpt-4o"
    assert "evaluations_summary" in data
    assert "groundedness" in data["evaluations_summary"]
    
    agent_ids = [a["id"] for a in data["agents"]]
    assert "ingest_agent" in agent_ids
    assert "tactical_analyst_agent" in agent_ids
    assert "narrator_agent" in agent_ids
    assert "verifier_agent" in agent_ids
    assert "broadcast_director_agent" in agent_ids


def test_power_automate_preview_endpoint(client):
    """Verifies that /api/integrations/power-automate/preview returns valid Adaptive Cards."""
    response = client.get("/api/integrations/power-automate/preview")
    assert response.status_code == 200
    data = response.json()
    assert "goal_card" in data
    assert "tactical_shift_card" in data
    assert "incident_card" in data

    for key in ["goal_card", "tactical_shift_card", "incident_card"]:
        card = data[key]
        assert card["type"] == "AdaptiveCard"
        assert card["version"] == "1.5"
        assert len(card["body"]) > 0
        assert len(card["actions"]) > 0


def test_power_automate_dispatch_goal(client):
    """Verifies dispatching a Goal Adaptive Card to Power Automate."""
    payload = {"event_type": "goal", "match_id": "TEST-MATCH-001"}
    response = client.post("/api/integrations/power-automate/dispatch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["status"] in ("simulated_success", "delivered")
    assert data["event_type"] == "goal"
    assert data["adaptive_card"]["type"] == "AdaptiveCard"


def test_power_automate_dispatch_tactical_shift(client):
    """Verifies dispatching a Tactical Shift Adaptive Card."""
    payload = {"event_type": "tactical_shift", "match_id": "TEST-MATCH-001"}
    response = client.post("/api/integrations/power-automate/dispatch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["event_type"] == "tactical_shift"
    assert data["adaptive_card"]["type"] == "AdaptiveCard"


def test_power_automate_dispatch_incident(client):
    """Verifies dispatching a Match Incident Adaptive Card."""
    payload = {"event_type": "incident", "match_id": "TEST-MATCH-001"}
    response = client.post("/api/integrations/power-automate/dispatch", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["event_type"] == "incident"
    assert data["adaptive_card"]["type"] == "AdaptiveCard"


def test_adaptive_card_builders():
    """Unit tests for card builder utility functions."""
    goal_card = build_goal_adaptive_card(
        match_id="M-1",
        minute=10, second=20,
        scorer_name="Julian Drake", scorer_number=8,
        team_name="Avalon City FC", team_color="#00A3E0",
        home_score=1, away_score=0,
        expected_goals=0.45, shot_speed_kmh=98.0,
        narrative="Superb curling effort into top right corner.",
        evidence_ids=["E-1", "E-2"]
    )
    assert goal_card["type"] == "AdaptiveCard"
    assert any("Julian Drake" in str(item) for item in goal_card["body"])

    tactical_card = build_tactical_shift_adaptive_card(
        match_id="M-1",
        minute=25, dominant_team="Avalon City FC",
        momentum_delta=24.5, ppda_index=7.8,
        tactical_insight="Avalon is pinning opponent.",
        recommendation="Exploit half space."
    )
    assert tactical_card["type"] == "AdaptiveCard"

    incident_card = build_incident_adaptive_card(
        match_id="M-1",
        minute=44, incident_type="Red Card",
        player_name="Silas Brandt", team_name="Solaria Rovers",
        detail="Dangerous tackle."
    )
    assert incident_card["type"] == "AdaptiveCard"


def test_power_automate_dispatcher_simulated():
    """Verifies dispatcher behavior when no URL is supplied."""
    dispatcher = PowerAutomateDispatcher(webhook_url="")
    card = {"type": "AdaptiveCard", "version": "1.5", "body": []}
    result = dispatcher.dispatch("goal", card)
    assert result["status"] == "simulated_success"
    assert result["adaptive_card"] == card
