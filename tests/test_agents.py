"""Tests for OmniPitch multi-agent system and MCP tools."""

import pytest
from omnipitch.agents.fallback import FallbackNarrativeGenerator
from omnipitch.agents.mcp_server import OmniPitchMCPServer
from omnipitch.agents.orchestrator import MultiAgentOrchestrator
from omnipitch.generator.engine import MatchSimulationEngine
from omnipitch.models import EventType


@pytest.mark.asyncio
async def test_multi_agent_orchestrator_pipeline():
    engine = MatchSimulationEngine(seed=42)
    events = engine.generate_full_match(event_count=5)

    orchestrator = MultiAgentOrchestrator(window_size=3)

    for evt in events:
        overlay = await orchestrator.process_event(evt, persona="analyst", language="en")
        assert overlay.overlay_id.startswith("OVR-")
        assert overlay.match_id == evt.match_id
        assert overlay.is_verified is True
        assert len(overlay.evidence_event_ids) > 0
        assert overlay.headline != ""
        assert overlay.narrative != ""
        assert "control_vs_chaos_index" in overlay.metrics


@pytest.mark.asyncio
async def test_orchestrator_persona_and_localization():
    engine = MatchSimulationEngine(seed=99)
    event = engine.generate_event(minute=14, second=22)

    orchestrator = MultiAgentOrchestrator()

    # Italian Fan persona
    overlay_it_fan = await orchestrator.process_event(event, persona="fan", language="it")
    assert overlay_it_fan.persona == "fan"
    assert overlay_it_fan.language == "it"
    assert overlay_it_fan.is_verified is True

    # English Analyst persona
    overlay_en_analyst = await orchestrator.process_event(event, persona="analyst", language="en")
    assert overlay_en_analyst.persona == "analyst"
    assert overlay_en_analyst.language == "en"
    assert "difficulty" in overlay_en_analyst.narrative.lower() or "difficulty" in str(overlay_en_analyst.metrics)


def test_deterministic_fallback_generator():
    engine = MatchSimulationEngine(seed=77)
    event = engine.generate_event(minute=33, second=10)

    fallback_payload = FallbackNarrativeGenerator.generate(event, persona="analyst", language="en")
    assert fallback_payload.generated_by == "deterministic-fallback-engine"
    assert fallback_payload.is_verified is True
    assert fallback_payload.evidence_event_ids == [event.event_id]


@pytest.mark.asyncio
async def test_mcp_server_tools():
    tools = OmniPitchMCPServer.list_tools()
    assert len(tools) >= 3
    tool_names = [t["name"] for t in tools]
    assert "get_match_tactical_state" in tool_names
    assert "generate_broadcast_overlay" in tool_names

    # Test invoking MCP tool
    res = await OmniPitchMCPServer.call_tool("get_match_tactical_state", {"match_id": "MATCH-2026-001"})
    assert "tactical_context" in res
    assert "control_vs_chaos_index" in res["tactical_context"]

    # Test generating overlay via MCP
    overlay_res = await OmniPitchMCPServer.call_tool(
        "generate_broadcast_overlay",
        {"match_id": "MATCH-2026-001", "persona": "fan", "language": "en"}
    )
    assert overlay_res["persona"] == "fan"
    assert overlay_res["is_verified"] is True
