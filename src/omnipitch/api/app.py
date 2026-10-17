"""FastAPI application for OmniPitch live streaming, overlays, and match intelligence."""

import asyncio
import json
from pathlib import Path
from typing import AsyncGenerator, Dict, List, Optional
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from omnipitch.agents.orchestrator import MultiAgentOrchestrator
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
        orchestrator_sessions[match_id] = MultiAgentOrchestrator()
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
    delay: float = Query(default=1.0, ge=0.2, le=5.0),
    max_overlays: int = Query(default=20, ge=3, le=60),
    seed: int = 42,
):
    """
    Server-Sent Events (SSE) streaming machine-readable broadcast overlays
    synthesized by the Multi-Agent system (Tactical Analyst -> Narrator -> Verifier).
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
            )
            payload = json.dumps(overlay.model_dump())
            yield f"event: broadcast_overlay\ndata: {payload}\n\n"
            if count >= max_overlays:
                break
            await asyncio.sleep(delay)

    return StreamingResponse(overlay_generator(), media_type="text/event-stream")


class IngestEventRequest(BaseModel):
    match_id: str
    event: MatchEvent
    persona: Optional[str] = "analyst"
    language: Optional[str] = "en"


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

