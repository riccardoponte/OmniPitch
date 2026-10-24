"""Match Blackboard & Episodic Memory for Multi-Agent coordination."""

from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field
from omnipitch.analytics.metrics import calculate_attack_momentum, calculate_player_match_rating
from omnipitch.models import EventType, MatchEvent, Player, Team


PHASE_EVENTS = {EventType.MATCH_START, EventType.HALF_TIME, EventType.MATCH_END, EventType.ADDED_TIME}


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
        if event.target_player and event.event_type == EventType.SHOT and event.shot_outcome in (None, "saved"):
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

    def match_state(self, home_id: str = "avalon_city") -> Dict[str, Any]:
        """Running team totals every agent reads from (xG, shots, possession, pass streak)."""
        state: Dict[str, Any] = {
            "home_xg": 0.0, "away_xg": 0.0, "home_shots": 0, "away_shots": 0,
            "home_passes": 0, "away_passes": 0, "home_cards": 0, "away_cards": 0,
            "pass_streak": 0, "streak_team": None,
        }
        for e in self.events_log:
            side = "home" if e.team_id == home_id else "away"
            if e.event_type in (EventType.SHOT, EventType.GOAL):
                state[f"{side}_shots"] += 1
                state[f"{side}_xg"] += e.expected_goals or 0.0
            if e.event_type == EventType.PASS:
                state[f"{side}_passes"] += 1
            if e.card:
                state[f"{side}_cards"] += 1
            # Consecutive completed passes by the team in possession
            if e.event_type == EventType.PASS and e.is_successful:
                if state["streak_team"] == e.team_id:
                    state["pass_streak"] += 1
                else:
                    state["streak_team"], state["pass_streak"] = e.team_id, 1
            elif e.event_type not in (EventType.FOUL,):
                state["streak_team"], state["pass_streak"] = None, 0
        total_passes = state["home_passes"] + state["away_passes"]
        state["poss_home"] = round(state["home_passes"] / total_passes * 100) if total_passes else 50
        state["poss_away"] = 100 - state["poss_home"]
        state["home_xg"] = round(state["home_xg"], 2)
        state["away_xg"] = round(state["away_xg"], 2)
        return state

    @staticmethod
    def state_numbers(state: Dict[str, Any]) -> List[float]:
        """Numbers from the blackboard that generated text may legitimately quote."""
        return [v for v in state.values() if isinstance(v, (int, float)) and not isinstance(v, bool)]

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
        - Attack Momentum minute-by-minute graph (per half, stoppage time included)
        - Head-to-Head Comparative Match Statistics
        - Starting Lineups with Performance Ratings and Match MVP badge
        - Interactive Shot Map
        - Incident Timeline (goals, cards, stoppage time, half-time, full time)
        """
        home_id = home_team.team_id
        away_id = away_team.team_id
        in_play = [e for e in self.events_log if e.event_type not in PHASE_EVENTS]

        # 1. Attack Momentum: one slot per played minute, in order, halves kept apart
        momentum_points = []
        buckets: Dict[tuple, List[MatchEvent]] = {}
        for e in self.events_log:
            bucket = buckets.setdefault((e.period, e.minute), [])
            if e.event_type not in PHASE_EVENTS:
                bucket.append(e)
        # Fill silent minutes so the x-axis stays continuous within each half
        slots: List[tuple] = []
        for period in (1, 2):
            minutes = [m for (p, m) in buckets if p == period]
            if minutes:
                slots += [(period, m) for m in range(min(minutes), max(minutes) + 1)]
        for period, minute in slots:
            min_events = buckets.get((period, minute), [])
            val = calculate_attack_momentum(min_events, home_id)
            regulation = 45 if period == 1 else 90
            label = f"{regulation}+{minute - regulation + 1}'" if minute >= regulation else f"{minute + 1}'"
            incidents = []
            for ev in min_events:
                name = ev.player.name if ev.player else ""
                if ev.event_type == EventType.GOAL:
                    incidents.append({"type": "goal", "player": name, "team": ev.team_id, "event_id": ev.event_id})
                elif ev.card:
                    incidents.append({"type": f"{ev.card}_card", "player": name, "team": ev.team_id, "event_id": ev.event_id})
                elif ev.event_type == EventType.SHOT and (ev.expected_goals or 0) >= 0.3:
                    incidents.append({"type": "big_chance", "player": name, "team": ev.team_id, "event_id": ev.event_id})
            momentum_points.append({
                "minute": minute + 1,
                "period": period,
                "label": label,
                "is_stoppage": minute >= regulation,
                "value": val,
                "dominant_team": "home" if val > 5.0 else ("away" if val < -5.0 else "neutral"),
                "incidents": incidents,
            })

        # 2. Team Comparative Statistics
        home_events = [e for e in in_play if e.team_id == home_id]
        away_events = [e for e in in_play if e.team_id == away_id]

        def shots(events):
            return [e for e in events if e.event_type in (EventType.SHOT, EventType.GOAL)]

        def on_target(events):
            return [e for e in shots(events) if e.shot_outcome in ("goal", "saved") or
                    (e.shot_outcome is None and (e.event_type == EventType.GOAL or e.target_player))]

        passes_home = [e for e in home_events if e.event_type == EventType.PASS]
        passes_away = [e for e in away_events if e.event_type == EventType.PASS]
        total_passes = len(passes_home) + len(passes_away)
        possession_home = round(len(passes_home) / total_passes * 100.0, 1) if total_passes else 50.0
        possession_away = round(100.0 - possession_home, 1)

        def pass_line(passes):
            done = len([e for e in passes if e.is_successful])
            pct = round(done / len(passes) * 100.0, 1) if passes else 0.0
            return done, len(passes), pct

        acc_h, tot_h, pct_h = pass_line(passes_home)
        acc_a, tot_a, pct_a = pass_line(passes_away)

        def xg(events):
            return round(sum(e.expected_goals or 0.0 for e in shots(events)), 2)

        def big_chances(events):
            return [e for e in shots(events) if (e.expected_goals or 0.0) >= 0.30]

        goals_home = len([e for e in home_events if e.event_type == EventType.GOAL])
        goals_away = len([e for e in away_events if e.event_type == EventType.GOAL])

        def corners(events):
            # Saved and blocked attempts are the usual source of corners
            return len([e for e in shots(events) if e.shot_outcome in ("blocked", "saved")]) // 2 + len(big_chances(events)) // 2

        def tackles(events):
            all_t = [e for e in events if e.event_type == EventType.TACKLE]
            won = [e for e in all_t if e.is_successful]
            pct = round(len(won) / len(all_t) * 100.0, 1) if all_t else 0.0
            return f"{len(won)}/{len(all_t)} ({pct}%)"

        def cards(events, colour):
            return len([e for e in events if e.card == colour])

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
                    "saves": stats.saves if stats else 0,
                })
            return formatted

        lineup_home = format_lineup(home_team)
        lineup_away = format_lineup(away_team)

        all_players = lineup_home + lineup_away
        if all_players and in_play:
            top_rated = max(all_players, key=lambda x: (x["rating"], x["goals"], x["distance_km"]))
            top_rated["is_mvp"] = True

        # 4. Shot Map Points
        shot_map = []
        for e in shots(in_play):
            outcome = e.shot_outcome or ("goal" if e.event_type == EventType.GOAL else ("saved" if e.target_player else "off_target"))
            shot_map.append({
                "event_id": e.event_id,
                "minute": e.minute,
                "second": e.second,
                "minute_label": e.match_minute_label,
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
            item = None
            name = e.player.name if e.player else ""
            if e.event_type == EventType.GOAL:
                item = {"type": "goal", "title": f"Goal — {name}",
                        "detail": f"{round(e.shot_speed_kmh or 0.0)} km/h strike, xG {e.expected_goals or 0.0:.2f} · {e.score_home}–{e.score_away}"}
            elif e.card:
                victim = e.target_player.name if e.target_player else "an opponent"
                item = {"type": f"{e.card}_card", "title": f"{e.card.title()} card — {name}", "detail": f"Foul on {victim}"}
            elif e.event_type == EventType.ADDED_TIME:
                item = {"type": "added_time", "title": f"+{e.added_time_minutes} minutes added", "detail": "Fourth official's board"}
            elif e.event_type == EventType.HALF_TIME:
                item = {"type": "half_time", "title": "Half-time", "detail": f"{e.score_home}–{e.score_away}"}
            elif e.event_type == EventType.MATCH_END:
                item = {"type": "full_time", "title": "Full-time", "detail": f"{e.score_home}–{e.score_away}"}
            if item:
                timeline.append({
                    **item,
                    "minute": e.minute,
                    "second": e.second,
                    "minute_label": e.match_minute_label,
                    "period": e.period,
                    "event_id": e.event_id,
                    "team_id": e.team_id,
                    "is_home": e.team_id == home_id,
                    "is_phase": e.event_type in PHASE_EVENTS,
                })

        last = self.events_log[-1] if self.events_log else None
        if last is None:
            phase = "pre_match"
        elif last.event_type == EventType.MATCH_END:
            phase = "full_time"
        elif last.event_type == EventType.HALF_TIME:
            phase = "half_time"
        else:
            phase = "live"

        return {
            "match_id": self.match_id,
            "home_team": {"name": home_team.name, "short_name": home_team.short_name, "color": home_team.primary_color},
            "away_team": {"name": away_team.name, "short_name": away_team.short_name, "color": away_team.primary_color},
            "status": {
                "period": last.period if last else 1,
                "clock": last.match_clock if last else "00:00",
                "minute_label": last.match_minute_label if last else "",
                "phase": phase,
                "score": {"home": last.score_home if last else 0, "away": last.score_away if last else 0},
            },
            "attack_momentum": momentum_points,
            "comparison_stats": {
                "expected_goals": {"home": xg(home_events), "away": xg(away_events)},
                "possession": {"home": possession_home, "away": possession_away},
                "total_shots": {"home": len(shots(home_events)), "away": len(shots(away_events))},
                "shots_on_target": {"home": len(on_target(home_events)), "away": len(on_target(away_events))},
                "big_chances": {"home": len(big_chances(home_events)), "away": len(big_chances(away_events))},
                "big_chances_missed": {
                    "home": max(len(big_chances(home_events)) - goals_home, 0),
                    "away": max(len(big_chances(away_events)) - goals_away, 0),
                },
                "accurate_passes": {"home": f"{acc_h}/{tot_h} ({pct_h}%)", "away": f"{acc_a}/{tot_a} ({pct_a}%)"},
                "pass_accuracy_pct": {"home": pct_h, "away": pct_a},
                "fouls": {"home": len([e for e in home_events if e.event_type == EventType.FOUL]),
                          "away": len([e for e in away_events if e.event_type == EventType.FOUL])},
                "yellow_cards": {"home": cards(home_events, "yellow"), "away": cards(away_events, "yellow")},
                "red_cards": {"home": cards(home_events, "red"), "away": cards(away_events, "red")},
                "corners": {"home": corners(home_events), "away": corners(away_events)},
                "tackles_won": {"home": tackles(home_events), "away": tackles(away_events)},
            },
            "lineups": {
                "home": lineup_home,
                "away": lineup_away,
            },
            "shot_map": shot_map,
            "timeline": timeline,
        }
