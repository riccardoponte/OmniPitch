"""Model Context Protocol (MCP) tool server for OmniPitch.

Exposes OmniPitch match intelligence and multi-agent reasoning tools
to GitHub Copilot Agent Mode and Microsoft Foundry AI agents.
"""

from typing import Any, Dict, List, Optional
from omnipitch.agents.fallback import FallbackNarrativeGenerator
from omnipitch.agents.orchestrator import MultiAgentOrchestrator
from omnipitch.generator.engine import MatchSimulationEngine

# Global instances for MCP sessions
_mcp_engines: Dict[str, MatchSimulationEngine] = {}
_mcp_orchestrators: Dict[str, MultiAgentOrchestrator] = {}


def _get_session(match_id: str = "MATCH-2026-001"):
    if match_id not in _mcp_engines:
        _mcp_engines[match_id] = MatchSimulationEngine(match_id=match_id, seed=42)
        _mcp_orchestrators[match_id] = MultiAgentOrchestrator()
    return _mcp_engines[match_id], _mcp_orchestrators[match_id]


class OmniPitchMCPServer:
    """
    Standard Model Context Protocol (MCP) Interface.
    Enables external LLM orchestrators and Copilot Agent Mode to query live match intelligence.
    """

    TOOLS = [
        {
            "name": "get_match_tactical_state",
            "description": "Fetches current tactical indices: Control vs Chaos index, Defensive Pressure, and Game Rhythm Tempo.",
            "parameters": {
                "type": "object",
                "properties": {
                    "match_id": {"type": "string", "default": "MATCH-2026-001"}
                },
            },
        },
        {
            "name": "generate_broadcast_overlay",
            "description": "Runs the multi-agent reasoning pipeline to generate verified broadcast commentary for a specific persona and language.",
            "parameters": {
                "type": "object",
                "properties": {
                    "match_id": {"type": "string", "default": "MATCH-2026-001"},
                    "persona": {"type": "string", "enum": ["analyst", "fan"], "default": "analyst"},
                    "language": {"type": "string", "enum": ["en", "it", "es", "de"], "default": "en"},
                },
            },
        },
        {
            "name": "simulate_next_event",
            "description": "Simulates the next chronological synthetic football match event with physics telemetry.",
            "parameters": {
                "type": "object",
                "properties": {
                    "match_id": {"type": "string", "default": "MATCH-2026-001"}
                },
            },
        },
    ]

    @classmethod
    def list_tools(cls) -> List[Dict[str, Any]]:
        """Returns the list of available MCP tools."""
        return cls.TOOLS

    @classmethod
    async def call_tool(cls, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatches an MCP tool call to the appropriate internal agent or simulation engine."""
        match_id = arguments.get("match_id", "MATCH-2026-001")
        engine, orchestrator = _get_session(match_id)

        if name == "get_match_tactical_state":
            latest = engine.generate_event(minute=engine.metadata.current_minute, second=engine.metadata.current_second)
            return {
                "match_id": match_id,
                "score": f"{engine.metadata.home_team.name} {engine.score.home_score} - {engine.score.away_score} {engine.metadata.away_team.name}",
                "tactical_context": latest.tactical_context.model_dump(),
            }

        elif name == "generate_broadcast_overlay":
            persona = arguments.get("persona", "analyst")
            language = arguments.get("language", "en")
            event = engine.generate_event(minute=15, second=30)
            overlay = await orchestrator.process_event(event=event, persona=persona, language=language)
            return overlay.model_dump()

        elif name == "simulate_next_event":
            event = engine.generate_event(minute=engine.metadata.current_minute + 1, second=15)
            return event.model_dump()

        else:
            raise ValueError(f"Unknown MCP tool: '{name}'")
