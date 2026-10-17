"""Synthetic football match simulation engine."""

import random
from typing import Generator, List, Optional
from omnipitch.analytics.metrics import (
    calculate_euclidean_distance,
    calculate_pass_difficulty,
    evaluate_tactical_state,
)
from omnipitch.generator.models import (
    Coordinates,
    EventType,
    MatchEvent,
    MatchMetadata,
    MatchScore,
    Player,
    Team,
)
from omnipitch.generator.teams import create_fictitious_teams


class MatchSimulationEngine:
    """
    Deterministic & realistic synthetic football match simulator.
    Uses seeded RNG to ensure reproducible event timelines for demos, tests, and broadcasts.
    """

    def __init__(self, match_id: str = "MATCH-2026-001", seed: Optional[int] = 42):
        self.match_id = match_id
        self.seed = seed
        self.rng = random.Random(seed)

        teams = create_fictitious_teams()
        self.home_team = teams[0]
        self.away_team = teams[1]

        self.score = MatchScore(home_score=0, away_score=0)
        self.metadata = MatchMetadata(
            match_id=self.match_id,
            home_team=self.home_team,
            away_team=self.away_team,
            stadium="Aethelgard Arena",
            weather="Clear, 16°C",
            score=self.score,
        )

        self.current_event_index = 0
        self.consecutive_passes = 0
        self.recent_turnovers = 0
        self.active_team = self.home_team
        self.defending_team = self.away_team
        self.current_ball_pos = Coordinates(x=50.0, y=50.0)

    def _get_random_outfield_player(self, team: Team) -> Player:
        outfield = [p for p in team.players if p.position != "GK"]
        return self.rng.choice(outfield)

    def _get_goalkeeper(self, team: Team) -> Player:
        gk = next((p for p in team.players if p.position == "GK"), team.players[0])
        return gk

    def _update_player_tracking(self, player: Player, burst_speed: float, distance_delta: float):
        player.speed_kmh = round(burst_speed, 1)
        player.distance_covered_km = round(player.distance_covered_km + (distance_delta / 1000.0), 3)

    def generate_event(self, minute: int, second: int) -> MatchEvent:
        """Generates a single plausible tactical event during the match."""
        self.current_event_index += 1
        event_id = f"EVT-{self.current_event_index:04d}"

        # Evaluate tactical context
        tactical_ctx = evaluate_tactical_state(
            consecutive_passes=self.consecutive_passes,
            turnovers_last_5_min=self.recent_turnovers,
            pitch_zone_x=self.current_ball_pos.x,
        )

        # Decide event type based on field position and tactical state
        rand_val = self.rng.random()
        attacker = self._get_random_outfield_player(self.active_team)

        # In attacking third (x > 75)
        if self.current_ball_pos.x > 75.0 and rand_val < 0.40:
            # Shot event
            shot_speed = round(self.rng.uniform(78.0, 118.0), 1)
            target_x = 100.0 if self.active_team == self.home_team else 0.0
            target_y = self.rng.uniform(42.0, 58.0)
            target_coords = Coordinates(x=target_x, y=target_y)

            self._update_player_tracking(attacker, burst_speed=shot_speed * 0.28, distance_delta=12.0)

            # Determine goal vs save vs block
            goal_roll = self.rng.random()
            if goal_roll < 0.25:
                # GOAL!
                if self.active_team == self.home_team:
                    self.score.home_score += 1
                else:
                    self.score.away_score += 1

                event = MatchEvent(
                    event_id=event_id,
                    match_id=self.match_id,
                    minute=minute,
                    second=second,
                    event_type=EventType.GOAL,
                    team_id=self.active_team.team_id,
                    player=attacker,
                    start_coordinates=self.current_ball_pos,
                    end_coordinates=target_coords,
                    shot_speed_kmh=shot_speed,
                    ball_speed_kmh=shot_speed,
                    is_successful=True,
                    tactical_context=tactical_ctx,
                )
                # Reset to center kick-off
                self.current_ball_pos = Coordinates(x=50.0, y=50.0)
                self.consecutive_passes = 0
                self.active_team, self.defending_team = self.defending_team, self.active_team
                return event
            else:
                # SAVE or SHOT
                gk = self._get_goalkeeper(self.defending_team)
                event = MatchEvent(
                    event_id=event_id,
                    match_id=self.match_id,
                    minute=minute,
                    second=second,
                    event_type=EventType.SHOT,
                    team_id=self.active_team.team_id,
                    player=attacker,
                    target_player=gk,
                    start_coordinates=self.current_ball_pos,
                    end_coordinates=target_coords,
                    shot_speed_kmh=shot_speed,
                    ball_speed_kmh=shot_speed,
                    is_successful=False,
                    tactical_context=tactical_ctx,
                )
                # Turnover / Keeper possession
                self.active_team, self.defending_team = self.defending_team, self.active_team
                self.current_ball_pos = Coordinates(x=20.0, y=50.0)
                self.consecutive_passes = 0
                return event

        # Turnover / Pressure / Tackle event
        elif rand_val < 0.25:
            defender = self._get_random_outfield_player(self.defending_team)
            self._update_player_tracking(defender, burst_speed=self.rng.uniform(22.0, 31.0), distance_delta=18.0)
            self.recent_turnovers += 1
            self.consecutive_passes = 0

            event_type = EventType.TACKLE if rand_val < 0.15 else EventType.PRESSURE
            event = MatchEvent(
                event_id=event_id,
                match_id=self.match_id,
                minute=minute,
                second=second,
                event_type=event_type,
                team_id=self.defending_team.team_id,
                player=defender,
                target_player=attacker,
                start_coordinates=self.current_ball_pos,
                end_coordinates=self.current_ball_pos,
                is_successful=True,
                tactical_context=tactical_ctx,
            )

            # Possession flips
            self.active_team, self.defending_team = self.defending_team, self.active_team
            return event

        # Standard Pass sequence
        else:
            receiver = self._get_random_outfield_player(self.active_team)
            while receiver.player_id == attacker.player_id:
                receiver = self._get_random_outfield_player(self.active_team)

            # Progressive movement
            dx = self.rng.uniform(5.0, 28.0) if self.active_team == self.home_team else self.rng.uniform(-28.0, -5.0)
            dy = self.rng.uniform(-22.0, 22.0)

            new_x = min(max(self.current_ball_pos.x + dx, 5.0), 95.0)
            new_y = min(max(self.current_ball_pos.y + dy, 5.0), 95.0)
            end_coords = Coordinates(x=round(new_x, 1), y=round(new_y, 1))

            dist_m, diff_rating = calculate_pass_difficulty(
                start=self.current_ball_pos,
                end=end_coords,
                defensive_pressure=tactical_ctx.defensive_pressure_index,
            )

            pass_speed = round(self.rng.uniform(32.0, 68.0), 1)
            player_speed = round(self.rng.uniform(14.0, 28.5), 1)
            self._update_player_tracking(attacker, burst_speed=player_speed, distance_delta=dist_m * 0.4)

            self.consecutive_passes += 1
            event = MatchEvent(
                event_id=event_id,
                match_id=self.match_id,
                minute=minute,
                second=second,
                event_type=EventType.PASS,
                team_id=self.active_team.team_id,
                player=attacker,
                target_player=receiver,
                start_coordinates=self.current_ball_pos,
                end_coordinates=end_coords,
                ball_speed_kmh=pass_speed,
                pass_distance_m=dist_m,
                pass_difficulty_rating=diff_rating,
                is_successful=True,
                tactical_context=tactical_ctx,
            )

            self.current_ball_pos = end_coords
            return event

    def generate_stream(
        self,
        start_minute: int = 0,
        end_minute: int = 90,
        step_seconds: int = 30
    ) -> Generator[MatchEvent, None, None]:
        """Streams synthetic match events through time."""
        current_time_sec = start_minute * 60
        end_time_sec = end_minute * 60

        while current_time_sec <= end_time_sec:
            minute = current_time_sec // 60
            second = current_time_sec % 60
            yield self.generate_event(minute, second)
            current_time_sec += step_seconds

    def generate_full_match(self, event_count: int = 120) -> List[MatchEvent]:
        """Generates a complete batch of events representing a full match."""
        events = []
        step_sec = (90 * 60) // max(event_count, 1)
        for i in range(event_count):
            total_sec = i * step_sec
            minute = total_sec // 60
            second = total_sec % 60
            events.append(self.generate_event(minute, second))
        return events
