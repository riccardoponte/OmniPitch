"""Model Context Protocol (MCP) server for OmniPitch.

Exposes the live match and the multi-agent pipeline as MCP tools so external
agents (GitHub Copilot Agent Mode, a Microsoft Foundry agent, any MCP client)
can query the match, ask for an explanation of a moment, read the commentary or
pull the recap — on the same match the viewers are watching.

Transports:
- Streamable HTTP, mounted by the API at /mcp (shares the live match sessions)
- stdio, via the `omnipitch-mcp` console script (its own in-process match)
"""

from typing import Any, Dict, List, Optional

from omnipitch.agents.commentary import build_facts
from omnipitch.sessions import get_or_create_session

DEFAULT_MATCH = "MATCH-2026-001"


# ---------------------------------------------------------------------------
# Tool implementations (plain async functions, reused by every transport)
# ---------------------------------------------------------------------------

async def get_match_state(match_id: str = DEFAULT_MATCH) -> Dict[str, Any]:
    """Score, clock, phase and running team totals (xG, shots, possession) for the live match."""
    engine, orchestrator = get_or_create_session(match_id)
    overview = orchestrator.memory.get_match_center_overview(engine.home_team, engine.away_team)
    return {
        "match_id": match_id,
        "home": engine.home_team.name,
        "away": engine.away_team.name,
        "status": overview["status"],
        "stoppage_minutes_announced": {
            str(p): engine.stoppage_minutes[p] for p in (1, 2) if engine.stoppage_announced[p]
        },
        "running_totals": orchestrator.memory.match_state(),
        "comparison_stats": overview["comparison_stats"],
    }


async def get_match_tactical_state(match_id: str = DEFAULT_MATCH) -> Dict[str, Any]:
    """Control vs chaos, defensive pressure and game rhythm at the latest event."""
    engine, orchestrator = get_or_create_session(match_id)
    log = orchestrator.memory.events_log
    context = log[-1].tactical_context if log else engine._tactical_context()
    return {
        "match_id": match_id,
        "clock": log[-1].match_clock if log else "00:00",
        "score": f"{engine.home_team.name} {engine.score.home_score} - {engine.score.away_score} {engine.away_team.name}",
        "tactical_context": context.model_dump(),
    }


async def advance_match(match_id: str = DEFAULT_MATCH, persona: str = "analyst", language: str = "en",
                        favourite_club: Optional[str] = None) -> Dict[str, Any]:
    """Plays the next event of the live match through the full agent pipeline and returns the verified overlay."""
    engine, orchestrator = get_or_create_session(match_id)
    event = engine.next_event()
    if event is None:
        return {"match_id": match_id, "full_time": True, "message": "The match is over."}
    overlay = await orchestrator.process_event(event=event, persona=persona, language=language,
                                               favourite_club=favourite_club)
    return {"event": event.model_dump(), **overlay.model_dump()}


async def generate_broadcast_overlay(match_id: str = DEFAULT_MATCH, persona: str = "analyst",
                                     language: str = "en") -> Dict[str, Any]:
    """Runs the multi-agent pipeline on the next event and returns the broadcast overlay."""
    result = await advance_match(match_id, persona, language)
    result.pop("event", None)
    return result


async def simulate_next_event(match_id: str = DEFAULT_MATCH) -> Dict[str, Any]:
    """Advances the live match by one event and returns the raw event."""
    result = await advance_match(match_id)
    return result.get("event", result)


async def get_live_commentary(match_id: str = DEFAULT_MATCH, last_n: int = 10) -> List[Dict[str, Any]]:
    """The most recent live commentary lines (lead commentator and co-commentator), newest last."""
    _, orchestrator = get_or_create_session(match_id)
    return orchestrator.commentary_log[-max(1, min(last_n, 100)):]


async def explain_moment(event_id: str, match_id: str = DEFAULT_MATCH, persona: str = "analyst",
                         language: str = "en") -> Dict[str, Any]:
    """Explains why a past event mattered, with the evidence the explanation rests on."""
    _, orchestrator = get_or_create_session(match_id)
    history = orchestrator.events_history
    idx = next((i for i, e in enumerate(history) if e.event_id == event_id.upper()), None)
    if idx is None:
        return {"error": f"Event '{event_id}' has not been played yet in {match_id}."}
    event = history[idx]
    window = history[max(0, idx - orchestrator.window_size + 1): idx + 1]
    report = await orchestrator.tactical_agent.process({"recent_events": window})
    state = orchestrator.memory.match_state()
    draft = await orchestrator.narrator_agent.process({
        "tactical_report": report, "latest_event": event, "match_state": state,
        "persona": persona, "language": language,
    })
    verification = await orchestrator.verifier_agent.process({
        "narrative_draft": draft, "all_events": window, "facts": build_facts(event),
        "state_numbers": orchestrator.memory.state_numbers(state),
        "match_state": state,
    })
    return {
        "event": event.model_dump(),
        "headline": draft.headline,
        "explanation": draft.commentary,
        "insight_kind": draft.insight_kind,
        "evidence_event_ids": draft.cited_event_ids,
        "verification": verification.model_dump(),
        "tactical_report": report.model_dump(),
    }


async def get_match_recap(match_id: str = DEFAULT_MATCH, kind: str = "full_time", language: str = "en",
                          persona: str = "analyst") -> Dict[str, Any]:
    """Half-time or full-time report written by the Recap agent from the shared blackboard."""
    _, orchestrator = get_or_create_session(match_id)
    recap = await orchestrator.build_recap(kind=kind if kind in ("half_time", "full_time") else "full_time",
                                           language=language, persona=persona)
    return recap.model_dump()


async def get_player_live_stats(player: str, match_id: str = DEFAULT_MATCH) -> Dict[str, Any]:
    """Live match stats for a player (id like 'AVA-08' or name like 'Julian Drake')."""
    _, orchestrator = get_or_create_session(match_id)
    stats = orchestrator.memory.get_player_stats(player)
    if not stats:
        return {"error": f"No live data for '{player}' yet."}
    return stats.model_dump()


TOOL_FUNCTIONS = {
    "get_match_state": get_match_state,
    "get_match_tactical_state": get_match_tactical_state,
    "get_live_commentary": get_live_commentary,
    "explain_moment": explain_moment,
    "get_match_recap": get_match_recap,
    "get_player_live_stats": get_player_live_stats,
    "advance_match": advance_match,
    "generate_broadcast_overlay": generate_broadcast_overlay,
    "simulate_next_event": simulate_next_event,
}


# ---------------------------------------------------------------------------
# REST facade (used by /api/mcp/* and the dashboard's tool explorer)
# ---------------------------------------------------------------------------

class OmniPitchMCPServer:
    """Lists and dispatches the same tools over plain JSON for clients without an MCP SDK."""

    @classmethod
    def list_tools(cls) -> List[Dict[str, Any]]:
        import inspect

        tools = []
        for name, fn in TOOL_FUNCTIONS.items():
            params = {
                p.name: {"default": p.default} if p.default is not inspect.Parameter.empty else {"required": True}
                for p in inspect.signature(fn).parameters.values()
            }
            tools.append({"name": name, "description": (fn.__doc__ or "").strip(), "parameters": params})
        return tools

    @classmethod
    async def call_tool(cls, name: str, arguments: Dict[str, Any]) -> Any:
        fn = TOOL_FUNCTIONS.get(name)
        if fn is None:
            raise ValueError(f"Unknown MCP tool: '{name}'")
        return await fn(**arguments)


# ---------------------------------------------------------------------------
# Real MCP server (Model Context Protocol SDK)
# ---------------------------------------------------------------------------

def build_mcp_server():
    """Returns an MCPServer exposing the tools, or None when the `mcp` SDK is not installed."""
    try:
        from mcp.server.mcpserver import MCPServer
    except ImportError:  # pragma: no cover - optional dependency
        return None

    server = MCPServer(
        name="omnipitch",
        title="OmniPitch Match Intelligence",
        instructions=(
            "Live synthetic football match intelligence. Use get_match_state for the score and totals, "
            "get_live_commentary for what the commentators just said, explain_moment(event_id) to understand "
            "why an event mattered, and get_match_recap for the report. advance_match plays the next event."
        ),
    )
    for fn in TOOL_FUNCTIONS.values():
        server.tool()(fn)
    return server


def main():  # pragma: no cover - console entry point
    server = build_mcp_server()
    if server is None:
        raise SystemExit("Install the MCP SDK first: pip install 'omnipitch[mcp]'")
    server.run("stdio")


if __name__ == "__main__":  # pragma: no cover
    main()
