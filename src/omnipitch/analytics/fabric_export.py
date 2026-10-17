"""Microsoft Fabric OneLake / Delta Lake Exporter for enterprise football data engineering."""

import json
from typing import Any, Dict, List
from omnipitch.agents.memory import MatchBlackboardMemory
from omnipitch.models import MatchEvent


class MicrosoftFabricLakehouseExporter:
    """
    Formats synthetic match events and multi-agent intelligence
    into standard schemas optimized for Microsoft Fabric OneLake Lakehouses,
    Synapse Data Engineering, and Power BI semantic models.
    """

    @staticmethod
    def format_event_for_lakehouse(event: MatchEvent) -> Dict[str, Any]:
        """Flattens a MatchEvent into a tabular record for Fabric Delta tables."""
        return {
            "event_id": event.event_id,
            "match_id": event.match_id,
            "minute": event.minute,
            "second": event.second,
            "event_type": event.event_type.value,
            "team_id": event.team_id,
            "player_id": event.player.player_id if event.player else None,
            "player_name": event.player.name if event.player else None,
            "player_position": event.player.position if event.player else None,
            "target_player_id": event.target_player.player_id if event.target_player else None,
            "start_x": event.start_coordinates.x,
            "start_y": event.start_coordinates.y,
            "end_x": event.end_coordinates.x if event.end_coordinates else None,
            "end_y": event.end_coordinates.y if event.end_coordinates else None,
            "ball_speed_kmh": event.ball_speed_kmh,
            "shot_speed_kmh": event.shot_speed_kmh,
            "pass_distance_m": event.pass_distance_m,
            "pass_difficulty_rating": event.pass_difficulty_rating,
            "expected_goals": event.expected_goals,
            "is_sprint_burst": event.is_sprint_burst,
            "control_vs_chaos_index": event.tactical_context.control_vs_chaos_index,
            "defensive_pressure_index": event.tactical_context.defensive_pressure_index,
            "game_rhythm_tempo": event.tactical_context.game_rhythm_tempo,
            "is_successful": event.is_successful,
        }

    @staticmethod
    def export_player_physical_summary(memory: MatchBlackboardMemory) -> List[Dict[str, Any]]:
        """Exports cumulative physical performance metrics for Fabric sports science analytics."""
        records = []
        for pid, stats in memory.players_stats.items():
            records.append({
                "match_id": memory.match_id,
                "player_id": stats.player_id,
                "player_name": stats.name,
                "team_id": stats.team_id,
                "distance_km": round(stats.distance_km, 3),
                "highest_speed_kmh": stats.highest_speed_kmh,
                "sprint_bursts_count": stats.sprint_bursts,
                "total_passes": stats.total_passes,
                "completed_passes": stats.completed_passes,
                "pass_accuracy_pct": round((stats.completed_passes / max(stats.total_passes, 1)) * 100.0, 1),
                "average_pass_difficulty": stats.average_pass_difficulty,
                "total_shots": stats.total_shots,
                "goals": stats.goals,
            })
        return records
