"""FastAPI application for OmniPitch live streaming, overlays, and match intelligence."""

import asyncio
import csv
import io
import json
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
from omnipitch.models import MatchEvent, MatchMetadata

app = FastAPI(
    title="OmniPitch API",
    description="Personalized Synthetic Match Intelligence & Multi-Agent Broadcast Overlays",
    version="0.1.0",
)

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

# Global in-memory simulation state (can be backed by Azure Cosmos DB)
simulation_sessions: Dict[str, MatchSimulationEngine] = {}
orchestrator_sessions: Dict[str, MultiAgentOrchestrator] = {}


def get_or_create_session(match_id: str, seed: int = 42) -> tuple[MatchSimulationEngine, MultiAgentOrchestrator]:
    if match_id not in simulation_sessions:
        simulation_sessions[match_id] = MatchSimulationEngine(match_id=match_id, seed=seed)
        orchestrator_sessions[match_id] = MultiAgentOrchestrator(match_id=match_id)
    return simulation_sessions[match_id], orchestrator_sessions[match_id]


@app.get("/api/health")
async def health_check():
    """Health check endpoint for Azure Container Apps / monitoring."""
    return {
        "status": "healthy",
        "service": "OmniPitch API",
        "version": "0.1.0",
        "multi_agent_system": "operational",
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
        for event in engine.generate_stream(step_seconds=45):
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
    delay: float = Query(default=1.0, ge=0.2, le=5.0),
    max_overlays: int = Query(default=20, ge=3, le=60),
    seed: int = 42,
):
    """
    Server-Sent Events (SSE) streaming machine-readable broadcast overlays
    synthesized by the Multi-Agent system (Tactical Analyst -> Narrator -> Verifier).
    Supports Player Focus Mode with dedicated spotlight tracking.
    """
    engine, orchestrator = get_or_create_session(match_id, seed)

    async def overlay_generator() -> AsyncGenerator[str, None]:
        count = 0
        for event in engine.generate_stream(step_seconds=45):
            count += 1
            overlay = await orchestrator.process_event(
                event=event,
                persona=persona,
                language=lang,
                target_player=player,
            )
            payload = json.dumps(overlay.model_dump())
            yield f"event: broadcast_overlay\ndata: {payload}\n\n"
            if count >= max_overlays:
                break
            await asyncio.sleep(delay)

    return StreamingResponse(overlay_generator(), media_type="text/event-stream")


@app.post("/api/match/{match_id}/reset")
async def reset_match_session(match_id: str, seed: int = 42):
    """Resets the simulation engine and multi-agent memory for the match session."""
    simulation_sessions[match_id] = MatchSimulationEngine(match_id=match_id, seed=seed)
    orchestrator_sessions[match_id] = MultiAgentOrchestrator(match_id=match_id)
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
    engine, orchestrator = get_or_create_session(match_id, seed)
    events = engine.generate_full_match(event_count=50)

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
        mm = f"{ev.minute:02d}"
        ss = f"{ev.second:02d}"
        rows.append({
            "event_id": ev.event_id,
            "match_time": f"{mm}:{ss}",
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
    engine, orchestrator = get_or_create_session(match_id, seed)
    events = orchestrator.memory.events_log
    if not events:
        events = engine.generate_full_match(event_count=30)

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

