"""Match Blackboard & Episodic Memory for Multi-Agent coordination."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from omnipitch.analytics.metrics import calculate_attack_momentum, calculate_player_match_rating
from omnipitch.models import EventType, MatchEvent, Player, Team


class PlayerCumulativeStats(BaseModel):
    player_id: str
    name: str
    team_id: str
    total_passes: int = 0
    completed_passes: int = 0
    total_shots: int = 0
    goals: int = 0
    tackles_won: int = 0
    interceptions: int = 0
    saves: int = 0
    fouls: int = 0
    xg_total: float = 0.0
    sprint_bursts: int = 0
    distance_km: float = 0.0
    highest_speed_kmh: float = 0.0
    average_pass_difficulty: float = 0.0
    rating: float = 6.5
    rating_color: str = "orange"
    is_mvp: bool = False


class MatchStoryMilestone(BaseModel):
    minute: int
    second: int
    event_id: str
    headline: str
    description: str


class MatchBlackboardMemory:
    """
    Shared episodic blackboard memory for all OmniPitch agents.
    Maintains longitudinal state across the 90 minutes of the match and
    generates advanced pro match intelligence.
    """

    def __init__(self, match_id: str = "MATCH-2026-001"):
        self.match_id = match_id
        self.players_stats: Dict[str, PlayerCumulativeStats] = {}
        self.milestones: List[MatchStoryMilestone] = []
        self.events_log: List[MatchEvent] = []

    def record_event(self, event: MatchEvent):
        """Updates cumulative statistics and longitudinal narrative state."""
        self.events_log.append(event)

        if event.player:
            pid = event.player.player_id
            if pid not in self.players_stats:
                self.players_stats[pid] = PlayerCumulativeStats(
                    player_id=pid,
                    name=event.player.name,
                    team_id=event.team_id,
                )

            stats = self.players_stats[pid]
            stats.distance_km = event.player.distance_covered_km
            if event.player.speed_kmh > stats.highest_speed_kmh:
                stats.highest_speed_kmh = event.player.speed_kmh

            if event.is_sprint_burst:
                stats.sprint_bursts += 1

            if event.event_type == EventType.PASS:
                stats.total_passes += 1
                if event.is_successful:
                    stats.completed_passes += 1
                diff = event.pass_difficulty_rating or 0.2
                stats.average_pass_difficulty = round(
                    ((stats.average_pass_difficulty * (stats.total_passes - 1)) + diff) / stats.total_passes, 2
                )

            elif event.event_type == EventType.SHOT:
                stats.total_shots += 1
                if event.expected_goals:
                    stats.xg_total = round(stats.xg_total + event.expected_goals, 2)

            elif event.event_type == EventType.GOAL:
                stats.total_shots += 1
                stats.goals += 1
                if event.expected_goals:
                    stats.xg_total = round(stats.xg_total + event.expected_goals, 2)
                self.milestones.append(
                    MatchStoryMilestone(
                        minute=event.minute,
                        second=event.second,
                        event_id=event.event_id,
                        headline=f"Goal scored by {event.player.name}",
                        description=f"Clinical finish with {event.shot_speed_kmh or 0} km/h shot velocity.",
                    )
                )

            elif event.event_type == EventType.TACKLE and event.is_successful:
                stats.tackles_won += 1

            elif event.event_type == EventType.INTERCEPTION:
                stats.interceptions += 1

            elif event.event_type == EventType.FOUL:
                stats.fouls += 1

            # Update rating
            rating, color = calculate_player_match_rating(
                total_passes=stats.total_passes,
                completed_passes=stats.completed_passes,
                average_pass_difficulty=stats.average_pass_difficulty,
                total_shots=stats.total_shots,
                goals=stats.goals,
                tackles_won=stats.tackles_won,
                interceptions=stats.interceptions,
                saves=stats.saves,
                fouls=stats.fouls,
                sprint_bursts=stats.sprint_bursts,
                position=event.player.position,
            )
            stats.rating = rating
            stats.rating_color = color

        # If a save occurred, credit the goalkeeper
        if event.target_player and event.event_type == EventType.SHOT:
            gk_id = event.target_player.player_id
            if gk_id not in self.players_stats:
                self.players_stats[gk_id] = PlayerCumulativeStats(
                    player_id=gk_id,
                    name=event.target_player.name,
                    team_id=event.target_player.team_id,
                )
            gk_stats = self.players_stats[gk_id]
            gk_stats.saves += 1
            rating, color = calculate_player_match_rating(
                total_passes=gk_stats.total_passes,
                completed_passes=gk_stats.completed_passes,
                average_pass_difficulty=gk_stats.average_pass_difficulty,
                total_shots=gk_stats.total_shots,
                goals=gk_stats.goals,
                tackles_won=gk_stats.tackles_won,
                interceptions=gk_stats.interceptions,
                saves=gk_stats.saves,
                fouls=gk_stats.fouls,
                sprint_bursts=gk_stats.sprint_bursts,
                position="GK",
            )
            gk_stats.rating = rating
            gk_stats.rating_color = color

    def get_player_stats(self, player_id_or_name: str) -> Optional[PlayerCumulativeStats]:
        """Looks up player stats by ID or exact/partial name."""
        query = player_id_or_name.lower()
        for pid, stats in self.players_stats.items():
            if pid.lower() == query or query in stats.name.lower():
                return stats
        return None

    def get_top_sprinters(self, top_n: int = 3) -> List[PlayerCumulativeStats]:
        """Returns the top players ranked by sprint bursts and top speed."""
        return sorted(self.players_stats.values(), key=lambda p: (p.sprint_bursts, p.highest_speed_kmh), reverse=True)[:top_n]

    def get_match_center_overview(self, home_team: Team, away_team: Team) -> Dict[str, Any]:
        """
        Computes complete Pro Match Center intelligence:
        - Attack Momentum minute-by-minute graph
        - Head-to-Head Comparative Match Statistics
        - Starting Lineups with Performance Ratings and Match MVP badge
        - Interactive Shot Map
        - Incident Timeline
        """
        home_id = home_team.team_id
        away_id = away_team.team_id

        # 1. Attack Momentum across minutes
        max_min = max([e.minute for e in self.events_log], default=1)
        momentum_points = []
        events_by_minute: Dict[int, List[MatchEvent]] = {}
        for e in self.events_log:
            events_by_minute.setdefault(e.minute, []).append(e)

        for m in range(1, max_min + 1):
            min_events = events_by_minute.get(m, [])
            val = calculate_attack_momentum(min_events, home_id)
            dominant = "home" if val > 5.0 else ("away" if val < -5.0 else "neutral")

            incidents = []
            for ev in min_events:
                if ev.event_type == EventType.GOAL:
                    incidents.append({"type": "goal", "icon": "⚽", "player": ev.player.name if ev.player else "Goal", "team": ev.team_id})
                elif ev.event_type == EventType.FOUL:
                    incidents.append({"type": "card", "icon": "🟨", "player": ev.player.name if ev.player else "Foul", "team": ev.team_id})
                elif ev.event_type == EventType.SHOT and (ev.expected_goals or 0) >= 0.35:
                    incidents.append({"type": "big_chance", "icon": "⚡", "player": ev.player.name if ev.player else "Chance", "team": ev.team_id})

            momentum_points.append({
                "minute": m,
                "value": val,
                "dominant_team": dominant,
                "incidents": incidents,
            })

        # 2. Team Comparative Statistics
        home_events = [e for e in self.events_log if e.team_id == home_id]
        away_events = [e for e in self.events_log if e.team_id == away_id]
        total_events_count = max(len(self.events_log), 1)

        possession_home = round((len(home_events) / total_events_count) * 100.0, 1)
        possession_away = round(100.0 - possession_home, 1)

        xg_home = round(sum(e.expected_goals or 0.0 for e in home_events if e.event_type in (EventType.SHOT, EventType.GOAL)), 2)
        xg_away = round(sum(e.expected_goals or 0.0 for e in away_events if e.event_type in (EventType.SHOT, EventType.GOAL)), 2)

        shots_home = len([e for e in home_events if e.event_type in (EventType.SHOT, EventType.GOAL)])
        shots_away = len([e for e in away_events if e.event_type in (EventType.SHOT, EventType.GOAL)])

        on_target_home = len([e for e in home_events if e.event_type == EventType.GOAL or (e.event_type == EventType.SHOT and e.target_player)])
        on_target_away = len([e for e in away_events if e.event_type == EventType.GOAL or (e.event_type == EventType.SHOT and e.target_player)])

        big_chances_home = len([e for e in home_events if (e.expected_goals or 0.0) >= 0.30 and e.event_type in (EventType.SHOT, EventType.GOAL)])
        big_chances_away = len([e for e in away_events if (e.expected_goals or 0.0) >= 0.30 and e.event_type in (EventType.SHOT, EventType.GOAL)])

        goals_home = len([e for e in home_events if e.event_type == EventType.GOAL])
        goals_away = len([e for e in away_events if e.event_type == EventType.GOAL])
        bcm_home = max(big_chances_home - goals_home, 0)
        bcm_away = max(big_chances_away - goals_away, 0)

        passes_home = [e for e in home_events if e.event_type == EventType.PASS]
        passes_acc_home = len([e for e in passes_home if e.is_successful])
        passes_tot_home = len(passes_home)
        pass_pct_home = round((passes_acc_home / max(passes_tot_home, 1)) * 100.0, 1)

        passes_away = [e for e in away_events if e.event_type == EventType.PASS]
        passes_acc_away = len([e for e in passes_away if e.is_successful])
        passes_tot_away = len(passes_away)
        pass_pct_away = round((passes_acc_away / max(passes_tot_away, 1)) * 100.0, 1)

        fouls_home = len([e for e in home_events if e.event_type == EventType.FOUL])
        fouls_away = len([e for e in away_events if e.event_type == EventType.FOUL])

        # Synthesize realistic corners from attacking third actions
        corners_home = max(len([e for e in home_events if e.start_coordinates.x > 85.0 and e.start_coordinates.y in (0, 100)]) // 2, shots_home // 3)
        corners_away = max(len([e for e in away_events if e.start_coordinates.x < 15.0 and e.start_coordinates.y in (0, 100)]) // 2, shots_away // 3)

        tackles_home = len([e for e in home_events if e.event_type == EventType.TACKLE])
        tackles_won_home = len([e for e in home_events if e.event_type == EventType.TACKLE and e.is_successful])
        tackles_pct_home = round((tackles_won_home / max(tackles_home, 1)) * 100.0, 1)

        tackles_away = len([e for e in away_events if e.event_type == EventType.TACKLE])
        tackles_won_away = len([e for e in away_events if e.event_type == EventType.TACKLE and e.is_successful])
        tackles_pct_away = round((tackles_won_away / max(tackles_away, 1)) * 100.0, 1)

        # 3. Lineup Ratings & MVP selection
        def format_lineup(team: Team):
            formatted = []
            for p in team.players:
                stats = self.players_stats.get(p.player_id)
                if stats:
                    rating = stats.rating
                    color = stats.rating_color
                else:
                    rating, color = calculate_player_match_rating(
                        total_passes=0, completed_passes=0, average_pass_difficulty=0.2,
                        total_shots=0, goals=0, position=p.position
                    )
                formatted.append({
                    "player_id": p.player_id,
                    "name": p.name,
                    "number": p.number,
                    "position": p.position,
                    "team_id": team.team_id,
                    "rating": rating,
                    "rating_color": color,
                    "is_mvp": False,
                    "distance_km": stats.distance_km if stats else 0.0,
                    "sprint_bursts": stats.sprint_bursts if stats else 0,
                    "goals": stats.goals if stats else 0,
                    "total_shots": stats.total_shots if stats else 0,
                    "total_passes": stats.total_passes if stats else 0,
                    "completed_passes": stats.completed_passes if stats else 0,
                    "tackles_won": stats.tackles_won if stats else 0,
                })
            return formatted

        lineup_home = format_lineup(home_team)
        lineup_away = format_lineup(away_team)

        # Determine MVP
        all_players = lineup_home + lineup_away
        if all_players:
            top_rated = max(all_players, key=lambda x: (x["rating"], x["goals"], x["distance_km"]))
            top_rated["is_mvp"] = True

        # 4. Shot Map Points
        shot_map = []
        for e in self.events_log:
            if e.event_type in (EventType.SHOT, EventType.GOAL):
                outcome = "goal" if e.event_type == EventType.GOAL else ("saved" if e.target_player else "missed")
                shot_map.append({
                    "event_id": e.event_id,
                    "minute": e.minute,
                    "second": e.second,
                    "team_id": e.team_id,
                    "player_name": e.player.name if e.player else "Shooter",
                    "x": round(e.start_coordinates.x, 1),
                    "y": round(e.start_coordinates.y, 1),
                    "xg": e.expected_goals or 0.05,
                    "outcome": outcome,
                    "shot_speed_kmh": e.shot_speed_kmh or 85.0,
                    "is_home": (e.team_id == home_id),
                })

        # 5. Incident Timeline
        timeline = []
        for e in self.events_log:
            if e.event_type == EventType.GOAL:
                timeline.append({
                    "minute": e.minute,
                    "second": e.second,
                    "type": "goal",
                    "title": f"GOAL! {e.player.name if e.player else 'Goal'}",
                    "detail": f"{round(e.shot_speed_kmh or 0.0, 1)} km/h strike (xG: {e.expected_goals or 0.1})",
                    "team_id": e.team_id,
                    "is_home": (e.team_id == home_id),
                })
            elif e.event_type == EventType.FOUL:
                timeline.append({
                    "minute": e.minute,
                    "second": e.second,
                    "type": "foul",
                    "title": f"Foul - {e.player.name if e.player else 'Opposition'}",
                    "detail": "Tactical disruption in transitional phase",
                    "team_id": e.team_id,
                    "is_home": (e.team_id == home_id),
                })

        return {
            "match_id": self.match_id,
            "home_team": {"name": home_team.name, "short_name": home_team.short_name, "color": home_team.primary_color},
            "away_team": {"name": away_team.name, "short_name": away_team.short_name, "color": away_team.primary_color},
            "attack_momentum": momentum_points,
            "comparison_stats": {
                "expected_goals": {"home": xg_home, "away": xg_away},
                "possession": {"home": possession_home, "away": possession_away},
                "total_shots": {"home": shots_home, "away": shots_away},
                "shots_on_target": {"home": on_target_home, "away": on_target_away},
                "big_chances": {"home": big_chances_home, "away": big_chances_away},
                "big_chances_missed": {"home": bcm_home, "away": bcm_away},
                "accurate_passes": {"home": f"{passes_acc_home}/{passes_tot_home} ({pass_pct_home}%)", "away": f"{passes_acc_away}/{passes_tot_away} ({pass_pct_away}%)"},
                "pass_accuracy_pct": {"home": pass_pct_home, "away": pass_pct_away},
                "fouls": {"home": fouls_home, "away": fouls_away},
                "corners": {"home": corners_home, "away": corners_away},
                "tackles_won": {"home": f"{tackles_won_home}/{tackles_home} ({tackles_pct_home}%)", "away": f"{tackles_won_away}/{tackles_away} ({tackles_pct_away}%)"},
            },
            "lineups": {
                "home": lineup_home,
                "away": lineup_away,
            },
            "shot_map": shot_map,
            "timeline": timeline,
        }



