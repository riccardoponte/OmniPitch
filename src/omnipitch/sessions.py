"""In-process match sessions shared by the REST API, the SSE streams and the MCP server."""

from typing import Dict, Tuple

from omnipitch.agents.orchestrator import MultiAgentOrchestrator
from omnipitch.generator.engine import MatchSimulationEngine

# Global in-memory simulation state (can be backed by Azure Cosmos DB)
simulation_sessions: Dict[str, MatchSimulationEngine] = {}
orchestrator_sessions: Dict[str, MultiAgentOrchestrator] = {}


def get_or_create_session(match_id: str, seed: int = 42) -> Tuple[MatchSimulationEngine, MultiAgentOrchestrator]:
    if match_id not in simulation_sessions:
        simulation_sessions[match_id] = MatchSimulationEngine(match_id=match_id, seed=seed)
        orchestrator_sessions[match_id] = MultiAgentOrchestrator(match_id=match_id)
    return simulation_sessions[match_id], orchestrator_sessions[match_id]


def reset_session(match_id: str, seed: int = 42) -> None:
    simulation_sessions[match_id] = MatchSimulationEngine(match_id=match_id, seed=seed)
    orchestrator_sessions[match_id] = MultiAgentOrchestrator(match_id=match_id)
