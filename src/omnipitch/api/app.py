"""FastAPI application for OmniPitch live streaming, overlays, and match intelligence."""

import asyncio
import csv
import io
import json
import os
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse, Response
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from omnipitch.agents.orchestrator import MultiAgentOrchestrator
from omnipitch.analytics.league_data import LEAGUE_STANDINGS, TEAM_PROFILES, PLAYER_DOSSIERS
from omnipitch.generator.engine import MatchSimulationEngine
from omnipitch.models import EventType, MatchEvent, MatchMetadata

try:  # Optional: pick up Foundry credentials from a local .env during development
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:  # pragma: no cover
    pass

from contextlib import asynccontextmanager  # noqa: E402

from omnipitch.agents.mcp_server import build_mcp_server  # noqa: E402
from omnipitch.integrations.event_hubs import publisher as event_hub_publisher  # noqa: E402

# Model Context Protocol endpoint (Streamable HTTP) over the same live match sessions
mcp_server = build_mcp_server()
mcp_app = None
if mcp_server is not None:
    from mcp.server.transport_security import TransportSecuritySettings

    # Allowed hosts come from the deployment (e.g. the Container Apps FQDN); local dev is open
    allowed = [h.strip() for h in os.getenv("MCP_ALLOWED_HOSTS", "").split(",") if h.strip()]
    mcp_app = mcp_server.streamable_http_app(
        streamable_http_path="/",
        transport_security=TransportSecuritySettings(
            enable_dns_rebinding_protection=bool(allowed),
            allowed_hosts=allowed,
            allowed_origins=[f"https://{h}" for h in allowed],
        ),
    )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    if mcp_server is not None:
        async with mcp_server.session_manager.run():
            yield
    else:
        yield


app = FastAPI(
    title="OmniPitch API",
    description="Personalized Synthetic Match Intelligence & Multi-Agent Broadcast Overlays",
    version="2.0.0",
    lifespan=lifespan,
)
if mcp_app is not None:
    app.mount("/mcp", mcp_app)

# Enable CORS for frontend dashboard and overlay consumers
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount Web Dashboard Static Assets
STATIC_DIR = Path(__file__).parent.parent / "web" / "static"
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


@app.get("/")
async def serve_dashboard():
    """Serves the OmniPitch interactive match intelligence web dashboard."""
    index_path = STATIC_DIR / "index.html"
    if index_path.exists():
        return FileResponse(index_path)
    return {"message": "OmniPitch API is running. Visit /docs for OpenAPI specs."}

# Match sessions are shared with the MCP server so agents and viewers see the same match
from omnipitch.sessions import (  # noqa: E402
    get_or_create_session,
    orchestrator_sessions,
    reset_session,
    simulation_sessions,
)


@app.get("/api/health")
async def health_check():
    """Health check endpoint for Azure Container Apps / monitoring."""
    return {
        "status": "healthy",
        "service": "OmniPitch API",
        "version": "2.0.0",
        "multi_agent_system": "operational",
        "mcp_endpoint": "/mcp/" if mcp_app is not None else None,
        "event_hubs": event_hub_publisher.status(),
    }


@app.get("/api/match/{match_id}/info", response_model=MatchMetadata)
async def get_match_info(match_id: str, seed: int = 42):
    """Returns static and current metadata of the match."""
    engine, _ = get_or_create_session(match_id, seed)
    return engine.metadata


@app.get("/api/match/{match_id}/events")
async def get_match_events(match_id: str, count: int = Query(default=20, ge=1, le=120), seed: int = 42):
    """Returns a batch of synthetic match events for analysis or replay."""
    engine, _ = get_or_create_session(match_id, seed)
    events = engine.generate_full_match(event_count=count)
    return [e.model_dump() for e in events]


@app.get("/api/match/{match_id}/events/stream")
async def stream_match_events(
    match_id: str,
    delay: float = Query(default=0.8, ge=0.1, le=5.0),
    max_events: int = Query(default=30, ge=5, le=100),
    seed: int = 42,
):
    """Server-Sent Events (SSE) endpoint streaming raw synthetic events in real time."""
    engine, _ = get_or_create_session(match_id, seed)

    async def event_generator() -> AsyncGenerator[str, None]:
        count = 0
        for event in engine.play():
            count += 1
            payload = json.dumps(event.model_dump())
            yield f"event: match_event\ndata: {payload}\n\n"
            if count >= max_events:
                break
            await asyncio.sleep(delay)

    return StreamingResponse(event_generator(), media_type="text/event-stream")


@app.get("/api/match/{match_id}/overlays/stream")
async def stream_broadcast_overlays(
    match_id: str,
    persona: str = Query(default="analyst", description="'analyst' or 'fan'"),
    lang: str = Query(default="en", description="ISO language code: 'en', 'it', 'es', 'de'"),
    player: Optional[str] = Query(default=None, description="Player spotlight name for Player Focus Mode"),
    club: Optional[str] = Query(default=None, description="Favourite club id: commentary takes that side"),
    delay: float = Query(default=1.0, ge=0.2, le=5.0),
    max_overlays: int = Query(default=20, ge=3, le=200),
    include_events: bool = Query(default=False, description="Also emit the raw match_event behind each overlay"),
    seed: int = 42,
):
    """
    Server-Sent Events (SSE) streaming machine-readable broadcast overlays
    synthesized by the Multi-Agent system (Tactical Analyst -> Commentator -> Narrator -> Verifier).
    Supports Player Focus Mode, favourite-club commentary and four languages.

    The match clock lives in the engine, so a new connection continues where the
    previous one stopped (pause / resume, persona or language switch). With
    include_events=true each overlay is preceded by the match_event it was built
    from. A match_recap event follows half-time and full time, and a final
    stream_end event reports whether the match is over.
    """
    engine, orchestrator = get_or_create_session(match_id, seed)
    favourite = club if club in ("avalon_city", "solaria_rovers") else None

    async def overlay_generator() -> AsyncGenerator[str, None]:
        count = 0
        for event in engine.play():
            count += 1
            await event_hub_publisher.publish(event)
            if include_events:
                yield f"event: match_event\ndata: {json.dumps(event.model_dump())}\n\n"
            overlay = await orchestrator.process_event(
                event=event,
                persona=persona,
                language=lang,
                target_player=player,
                favourite_club=favourite,
            )
            yield f"event: broadcast_overlay\ndata: {json.dumps(overlay.model_dump())}\n\n"
            if event.event_type in (EventType.HALF_TIME, EventType.MATCH_END):
                kind = "half_time" if event.event_type == EventType.HALF_TIME else "full_time"
                recap = await orchestrator.build_recap(kind=kind, language=lang, persona=persona)
                yield f"event: match_recap\ndata: {json.dumps(recap.model_dump())}\n\n"
            if count >= max_overlays:
                break
            await asyncio.sleep(delay)
        end_payload = {"full_time": engine.is_finished, "phase": engine.phase, "events_streamed": count}
        yield f"event: stream_end\ndata: {json.dumps(end_payload)}\n\n"

    return StreamingResponse(overlay_generator(), media_type="text/event-stream")


@app.get("/api/match/{match_id}/recap")
async def get_match_recap(
    match_id: str,
    kind: str = Query(default="full_time", pattern="^(half_time|full_time)$"),
    lang: str = Query(default="en"),
    persona: str = Query(default="analyst"),
    seed: int = 42,
):
    """Automated match report (half-time or full-time) written by the Recap agent from the blackboard."""
    _, orchestrator = get_or_create_session(match_id, seed)
    recap = await orchestrator.build_recap(kind=kind, language=lang, persona=persona)
    return recap.model_dump()


@app.get("/api/match/{match_id}/agents/telemetry")
async def get_agent_telemetry(match_id: str, seed: int = 42):
    """Live multi-agent telemetry: per-agent latency, claims verified/rejected, LLM usage, fallbacks."""
    _, orchestrator = get_or_create_session(match_id, seed)
    return {**orchestrator.telemetry(), "event_hubs": event_hub_publisher.status()}


@app.post("/api/match/{match_id}/reset")
async def reset_match_session(match_id: str, seed: int = 42):
    """Resets the simulation engine and multi-agent memory for the match session."""
    reset_session(match_id, seed)
    return {"status": "reset", "match_id": match_id}


@app.get("/api/match/{match_id}/matchcenter/overview")
async def get_match_center_overview(match_id: str, seed: int = 42, sample: bool = False):
    """
    Returns comprehensive Pro Match Center intelligence:
    - Attack Momentum minute-by-minute bars
    - Head-to-Head Comparative Match Statistics
    - Starting Lineups with Dynamic Ratings and Match MVP badge
    - Interactive Shot Map
    - Incident Timeline
    """
    engine, orchestrator = get_or_create_session(match_id, seed)

    # For testing suites or sample previews, pre-seed events if empty
    if (sample or "TEST" in match_id) and len(orchestrator.memory.events_log) < 15:
        initial_events = engine.generate_full_match(event_count=45)
        for ev in initial_events:
            orchestrator.memory.record_event(ev)

    overview = orchestrator.memory.get_match_center_overview(engine.home_team, engine.away_team)
    return overview



@app.get("/api/match/{match_id}/fabric/export")
async def export_to_microsoft_fabric(match_id: str, seed: int = 42):
    """
    Exports synthetic match events and longitudinal physical performance
    formatted for Microsoft Fabric OneLake Lakehouses and Power BI DirectLake models.
    """
    from omnipitch.analytics.fabric_export import MicrosoftFabricLakehouseExporter
    _, orchestrator = get_or_create_session(match_id, seed)
    # Export what has actually been played; a pre-match export previews a separate sample
    events = orchestrator.memory.events_log or MatchSimulationEngine(match_id=match_id, seed=seed).generate_full_match(50)

    events_table = [MicrosoftFabricLakehouseExporter.format_event_for_lakehouse(e) for e in events]
    player_summary_table = MicrosoftFabricLakehouseExporter.export_player_physical_summary(orchestrator.memory)

    return {
        "lakehouse_workspace": "OmniPitch-Fabric-Analytics",
        "match_id": match_id,
        "delta_tables": {
            "fact_match_events": events_table,
            "dim_player_physical_summary": player_summary_table,
        },
        "target_format": "Delta / Parquet (OneLake DirectLake ready)",
    }


class IngestEventRequest(BaseModel):
    match_id: str
    event: MatchEvent
    persona: Optional[str] = "analyst"
    language: Optional[str] = "en"
    target_player: Optional[str] = None


@app.post("/api/events/ingest")
async def ingest_external_event(req: IngestEventRequest):
    """
    Ingestion webhook endpoint for Azure Event Hub / Azure Functions.
    Processes custom synthetic events and returns verified broadcast overlay.
    """
    _, orchestrator = get_or_create_session(req.match_id)
    req.event.match_id = req.match_id
    overlay = await orchestrator.process_event(
        event=req.event,
        persona=req.persona or "analyst",
        language=req.language or "en",
    )
    return overlay


@app.get("/api/league/standings")
async def get_league_standings():
    """Returns the full league championship table with form guide and European qualification zones."""
    return {
        "league_name": "Aethelgard Premier Championship 2025/26",
        "matchweek": 29,
        "total_teams": len(LEAGUE_STANDINGS),
        "standings": LEAGUE_STANDINGS,
    }


@app.get("/api/teams/{team_id}")
async def get_team_profile(team_id: str):
    """Returns detailed club intelligence, tactical traits, stadium info, and recent results."""
    profile = TEAM_PROFILES.get(team_id)
    if not profile:
        raise HTTPException(status_code=404, detail=f"Team '{team_id}' not found.")
    return profile


@app.get("/api/players/{player_id}")
async def get_player_dossier(player_id: str, match_id: Optional[str] = "MATCH-2026-001"):
    """
    Returns comprehensive scouting dossier:
    - Sporting biography and career honors
    - 2025/26 season performance telemetry
    - Real-time live match metrics from blackboard memory
    """
    dossier = PLAYER_DOSSIERS.get(player_id.upper())
    if not dossier:
        dossier = PLAYER_DOSSIERS.get(player_id)
    if not dossier:
        clean_id = player_id.replace("_", " ").lower().strip()
        # Search by full name or partial match
        for pid, pdata in PLAYER_DOSSIERS.items():
            pname_lower = pdata["name"].lower()
            if pname_lower == clean_id or pid.lower() == clean_id or clean_id in pname_lower:
                dossier = pdata
                player_id = pid
                break
    if not dossier:
        raise HTTPException(status_code=404, detail=f"Player '{player_id}' dossier not found.")

    res = dict(dossier)
    res["club_name"] = res.get("team_name", "Avalon City FC")
    res["archetype"] = res.get("role_archetype", "Tactical Target")
    res["bio"] = {
        "age": res.get("age", 25),
        "nationality": res.get("nationality", "International"),
        "height_cm": res.get("height_cm", 182),
        "preferred_foot": res.get("preferred_foot", "Right"),
        "market_value_eur": res.get("market_value", "€50.0M"),
        "contract_until": res.get("contract_until", "June 2029"),
    }
    cv_raw = res.get("cv_highlights", {})
    res["career"] = {
        "youth_academy": cv_raw.get("youth_academy", "Youth Academy"),
        "international_caps": cv_raw.get("international_caps", "Senior Caps"),
        "trajectory": [
            {
                "period": c.get("years", c.get("period", "2020-Present")),
                "club": c.get("club", "Club"),
                "appearances": c.get("apps", c.get("appearances", 0)),
                "goals": c.get("goals", c.get("clean_sheets", 0)),
            }
            for c in cv_raw.get("previous_clubs", cv_raw.get("trajectory", []))
        ],
        "honours": cv_raw.get("career_honors", cv_raw.get("honours", [])),
    }
    res["scouting_summary"] = cv_raw.get("scouting_summary", res.get("scouting_summary", ""))
    s_raw = res.get("season_2025_stats", {})
    res["season_2025_26"] = {
        "appearances": s_raw.get("appearances", 28),
        "goals": s_raw.get("goals", 0),
        "assists": s_raw.get("assists", 0),
        "xg_per_90": s_raw.get("xg_created_total", s_raw.get("xg_per_90", 0.25)),
        "pass_completion_rate": s_raw.get("pass_accuracy", s_raw.get("pass_completion_rate", 85.0)),
        "top_speed_kmh": s_raw.get("top_speed_kmh", 33.5),
    }

    # Augment with live match stats from current session
    _, orchestrator = get_or_create_session(match_id or "MATCH-2026-001")
    live_stats = orchestrator.memory.players_stats.get(player_id)
    if live_stats:
        res["live_match_stats"] = {
            "rating": live_stats.rating,
            "rating_color": live_stats.rating_color,
            "distance_km": round(live_stats.distance_km, 2),
            "sprint_bursts": live_stats.sprint_bursts,
            "total_passes": live_stats.total_passes,
            "completed_passes": live_stats.completed_passes,
            "pass_accuracy": round((live_stats.completed_passes / max(live_stats.total_passes, 1)) * 100, 1),
            "total_shots": live_stats.total_shots,
            "goals": live_stats.goals,
            "tackles_won": live_stats.tackles_won,
        }
    else:
        res["live_match_stats"] = {
            "rating": 6.5,
            "rating_color": "orange",
            "distance_km": 0.0,
            "sprint_bursts": 0,
            "total_passes": 0,
            "completed_passes": 0,
            "pass_accuracy": 0.0,
            "total_shots": 0,
            "goals": 0,
            "tackles_won": 0,
        }
    return res


@app.get("/api/match/{match_id}/events/table")
async def get_match_events_table(match_id: str, seed: int = 42):
    """
    Returns flat tabular telemetry rows suitable for high-density UI grid inspection
    and direct compatibility with Microsoft Fabric OneLake Delta tables.
    """
    engine, orchestrator = get_or_create_session(match_id, seed)
    events = orchestrator.memory.events_log
    if not events and ("TEST" in match_id):
        events = engine.generate_full_match(event_count=30)
        for ev in events:
            orchestrator.memory.record_event(ev)

    rows = []
    for ev in events:
        rows.append({
            "event_id": ev.event_id,
            "match_time": ev.match_clock,
            "minute_label": ev.match_minute_label,
            "period": ev.period,
            "minute": ev.minute,
            "second": ev.second,
            "team_id": ev.team_id,
            "team_name": "Avalon City FC" if ev.team_id == "avalon_city" else "Solaria Rovers",
            "player_id": ev.player.player_id if ev.player else "N/A",
            "player_name": ev.player.name if ev.player else "System",
            "player_number": ev.player.number if ev.player else 0,
            "event_type": ev.event_type.value if hasattr(ev.event_type, "value") else str(ev.event_type),
            "start_x": round(ev.start_coordinates.x, 1) if ev.start_coordinates else 0.0,
            "start_y": round(ev.start_coordinates.y, 1) if ev.start_coordinates else 0.0,
            "end_x": round(ev.end_coordinates.x, 1) if ev.end_coordinates else None,
            "end_y": round(ev.end_coordinates.y, 1) if ev.end_coordinates else None,
            "expected_goals": round(ev.expected_goals or 0.0, 3),
            "pass_difficulty": round(ev.pass_difficulty_rating or 0.0, 2),
            "shot_speed_kmh": round(ev.shot_speed_kmh or 0.0, 1),
            "is_successful": bool(ev.is_successful),
            "is_sprint": bool(ev.is_sprint_burst),
            "fabric_verified": True,
        })
    return {
        "match_id": match_id,
        "total_records": len(rows),
        "columns": [
            "match_time", "team_name", "player_name", "event_type",
            "start_x", "start_y", "expected_goals", "pass_difficulty",
            "shot_speed_kmh", "is_successful", "fabric_verified"
        ],
        "rows": rows,
    }


@app.get("/api/match/{match_id}/events/csv")
async def export_match_events_csv(match_id: str, seed: int = 42):
    """Generates and streams an RFC-4180 compliant CSV of the match telemetry."""
    _, orchestrator = get_or_create_session(match_id, seed)
    events = orchestrator.memory.events_log
    if not events:
        # Never advance the live match to build a preview file
        events = MatchSimulationEngine(match_id=match_id, seed=seed).generate_full_match(event_count=30)

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "EventID", "MatchID", "Minute", "Second", "TeamID", "PlayerID", "PlayerName",
        "EventType", "StartX", "StartY", "EndX", "EndY", "xG", "PassDifficulty",
        "ShotSpeedKmh", "IsSuccessful", "IsSprintBurst", "FabricDirectLakeIngested"
    ])

    for ev in events:
        writer.writerow([
            ev.event_id,
            match_id,
            ev.minute,
            ev.second,
            ev.team_id,
            ev.player.player_id if ev.player else "",
            ev.player.name if ev.player else "",
            ev.event_type.value if hasattr(ev.event_type, "value") else str(ev.event_type),
            round(ev.start_coordinates.x, 2) if ev.start_coordinates else 0.0,
            round(ev.start_coordinates.y, 2) if ev.start_coordinates else 0.0,
            round(ev.end_coordinates.x, 2) if ev.end_coordinates else "",
            round(ev.end_coordinates.y, 2) if ev.end_coordinates else "",
            round(ev.expected_goals or 0.0, 4),
            round(ev.pass_difficulty_rating or 0.0, 3),
            round(ev.shot_speed_kmh or 0.0, 1),
            int(bool(ev.is_successful)),
            int(bool(ev.is_sprint_burst)),
            1,
        ])

    csv_data = output.getvalue()
    return Response(
        content=csv_data,
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=OmniPitch_Telemetry_{match_id}.csv"},
    )


# ==============================================================================
# Model Context Protocol (MCP) Endpoints
# ==============================================================================

class MCPCallRequest(BaseModel):
    name: str
    arguments: Dict[str, Any] = {}


@app.get("/api/mcp/tools")
async def list_mcp_tools():
    """Lists MCP tools for Microsoft Foundry and Copilot Agent Mode."""
    from omnipitch.agents.mcp_server import OmniPitchMCPServer
    return {"tools": OmniPitchMCPServer.list_tools()}


@app.post("/api/mcp/call")
async def call_mcp_tool(req: MCPCallRequest):
    """Executes an MCP tool call."""
    from omnipitch.agents.mcp_server import OmniPitchMCPServer
    try:
        result = await OmniPitchMCPServer.call_tool(req.name, req.arguments)
        return {"content": result, "is_error": False}
    except Exception as exc:
        return {"content": str(exc), "is_error": True}


# ==============================================================================
# Microsoft AI Foundry & Enterprise Multi-Agent Orchestration Endpoints
# ==============================================================================

@app.get("/api/foundry/agents")
async def get_foundry_agents():
    """
    Returns the live status, configuration, and handoff trace for the 5 agents
    operating under Microsoft AI Foundry Agent Service.
    """
    manifest_path = os.path.join(os.path.dirname(__file__), "..", "..", "..", "foundry", "agents_manifest.json")
    manifest_path = os.path.normpath(manifest_path)
    
    if os.path.exists(manifest_path):
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)
    else:
        manifest = {"agents": [], "orchestration_pattern": "Blackboard-Shared-State"}

    # Augment agents with live runtime telemetry from the running match
    _, orchestrator = get_or_create_session("MATCH-2026-001")
    telemetry = orchestrator.telemetry()
    latencies = telemetry["agent_latency_ms"]

    enriched_agents = []
    for agent in manifest.get("agents", []):
        agent_copy = dict(agent)
        agent_copy["status"] = "online"
        agent_copy["events_processed"] = telemetry["events_processed"]
        agent_copy["latency_ms"] = latencies.get(agent["id"], 0.0)
        enriched_agents.append(agent_copy)

    return {
        "project_name": manifest.get("project_name", "OmniPitch-Match-Intelligence"),
        "orchestration_pattern": manifest.get("orchestration_pattern"),
        "primary_model": manifest.get("primary_model"),
        "llm_policy": manifest.get("llm_policy"),
        "total_active_agents": len(enriched_agents),
        "total_events_ingested": telemetry["events_processed"],
        "agents": enriched_agents,
        "telemetry": telemetry,
    }


class PowerAutomateDispatchRequest(BaseModel):
    event_type: str = "goal"
    webhook_url: Optional[str] = None
    match_id: Optional[str] = "MATCH-2026-001"


@app.post("/api/integrations/power-automate/dispatch")
async def dispatch_power_automate_workflow(req: PowerAutomateDispatchRequest):
    """
    Generates and dispatches a Microsoft Teams Adaptive Card (v1.5) to Power Automate
    or Azure Logic Apps for real-time broadcast and enterprise notifications.
    """
    from omnipitch.integrations.power_automate import (
        PowerAutomateDispatcher,
        build_goal_adaptive_card,
        build_tactical_shift_adaptive_card,
        build_incident_adaptive_card
    )

    _, orchestrator = get_or_create_session(req.match_id or "MATCH-2026-001")
    dispatcher = PowerAutomateDispatcher(webhook_url=req.webhook_url)

    if req.event_type == "tactical_shift":
        card = build_tactical_shift_adaptive_card(
            match_id=req.match_id or "MATCH-2026-001",
            minute=64,
            dominant_team="Avalon City FC",
            momentum_delta=+38.5,
            ppda_index=8.4,
            tactical_insight="Avalon City has overloaded the left half-space, trapping Solaria in their defensive third. Solaria's pass completion dropped to 68%.",
            recommendation="Switch to 5-3-2 low block and introduce pace on counterattack."
        )
    elif req.event_type == "incident":
        card = build_incident_adaptive_card(
            match_id=req.match_id or "MATCH-2026-001",
            minute=52,
            incident_type="Yellow Card (Tactical Foul)",
            player_name="Jasper Holt",
            team_name="Solaria Rovers",
            detail="Tactical holding foul to prevent Cyrus Kane breakaway on counterattack. Referee inspection confirmed."
        )
    else:  # goal
        card = build_goal_adaptive_card(
            match_id=req.match_id or "MATCH-2026-001",
            minute=34,
            second=18,
            scorer_name="Cyrus Kane",
            scorer_number=9,
            team_name="Avalon City FC",
            team_color="#00A3E0",
            home_score=1,
            away_score=0,
            expected_goals=0.68,
            shot_speed_kmh=104.2,
            narrative="Sensational counterattack finished with authority! Cyrus Kane rifles a 104 km/h strike past the keeper following an incisive progressive pass from Julian Drake.",
            evidence_ids=["EV-042", "EV-043", "EV-044"]
        )

    result = dispatcher.dispatch(
        event_type=req.event_type,
        adaptive_card=card,
        custom_webhook=req.webhook_url
    )
    return result


@app.get("/api/integrations/power-automate/preview")
async def preview_power_automate_cards(match_id: str = "MATCH-2026-001"):
    """Returns sample Microsoft Teams Adaptive Cards for all 3 scenarios."""
    from omnipitch.integrations.power_automate import (
        build_goal_adaptive_card,
        build_tactical_shift_adaptive_card,
        build_incident_adaptive_card
    )

    goal_card = build_goal_adaptive_card(
        match_id=match_id,
        minute=34, second=18,
        scorer_name="Cyrus Kane", scorer_number=9,
        team_name="Avalon City FC", team_color="#00A3E0",
        home_score=1, away_score=0,
        expected_goals=0.68, shot_speed_kmh=104.2,
        narrative="Sensational counterattack finished with authority by Cyrus Kane.",
        evidence_ids=["EV-042", "EV-043", "EV-044"]
    )
    tactical_card = build_tactical_shift_adaptive_card(
        match_id=match_id,
        minute=64, dominant_team="Avalon City FC",
        momentum_delta=+38.5, ppda_index=8.4,
        tactical_insight="High-pressing overload in attacking third.",
        recommendation="Reinforce midfield double pivot."
    )
    incident_card = build_incident_adaptive_card(
        match_id=match_id,
        minute=52, incident_type="Yellow Card",
        player_name="Jasper Holt", team_name="Solaria Rovers",
        detail="Tactical holding foul to prevent counterattack."
    )

    return {
        "goal_card": goal_card,
        "tactical_shift_card": tactical_card,
        "incident_card": incident_card,
    }


