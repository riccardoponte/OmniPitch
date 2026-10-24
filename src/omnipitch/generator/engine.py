"""Synthetic football match simulation engine."""

import random
from typing import Dict, Generator, List, Optional
from omnipitch.analytics.metrics import (
    calculate_expected_goals,
    calculate_pass_difficulty,
    evaluate_tactical_state,
    is_sprint_speed,
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

HALF_LENGTH_SEC = 45 * 60
FULL_LENGTH_SEC = 90 * 60


class MatchSimulationEngine:
    """
    Deterministic & realistic synthetic football match simulator.
    Uses seeded RNG to ensure reproducible event timelines for demos, tests, and broadcasts.

    The engine owns the match clock: kick-off, two 45-minute halves, announced stoppage
    time, half-time and the final whistle. `play()` yields the whole match in order and
    can be consumed across several streaming sessions (pause / resume keeps the clock).
    """

    def __init__(self, match_id: str = "MATCH-2026-001", seed: Optional[int] = 42):
        self.match_id = match_id
        self.seed = seed
        self.rng = random.Random(seed)
        # Separate stream for the clock so timing changes don't reshuffle event content
        self.clock_rng = random.Random((seed or 0) + 7919)

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

        # Match timeline state
        self.period = 1
        self.clock_sec = 0
        self.phase = "pre_match"  # pre_match | live | half_time | finished
        self.stoppage_minutes: Dict[int, int] = {
            1: self.clock_rng.randint(1, 4),
            2: self.clock_rng.randint(3, 6),
        }
        self.stoppage_announced: Dict[int, bool] = {1: False, 2: False}
        self.yellow_cards: Dict[str, int] = {}
        self.sent_off: set = set()

    # ------------------------------------------------------------------ helpers

    def _attacks_right(self, team: Team) -> bool:
        """Home attacks towards x=100 in both halves (coordinates are broadcast-normalised)."""
        return team.team_id == self.home_team.team_id

    def _progress(self, team: Team, pos: Coordinates) -> float:
        """How far up the pitch `team` is with the ball (0 = own goal line, 100 = opponent's)."""
        return pos.x if self._attacks_right(team) else 100.0 - pos.x

    def _available(self, team: Team) -> List[Player]:
        return [p for p in team.players if p.player_id not in self.sent_off]

    def _get_random_outfield_player(self, team: Team) -> Player:
        outfield = [p for p in self._available(team) if p.position != "GK"]
        return self.rng.choice(outfield or team.players)

    def _get_goalkeeper(self, team: Team) -> Player:
        gk = next((p for p in team.players if p.position == "GK"), team.players[0])
        return gk

    def _update_player_tracking(self, player: Player, burst_speed: float, distance_delta: float):
        player.speed_kmh = round(burst_speed, 1)
        player.distance_covered_km = round(player.distance_covered_km + (distance_delta / 1000.0), 3)

    def _flip_possession(self):
        self.active_team, self.defending_team = self.defending_team, self.active_team

    def _next_id(self) -> str:
        self.current_event_index += 1
        return f"EVT-{self.current_event_index:04d}"

    def _tactical_context(self):
        return evaluate_tactical_state(
            consecutive_passes=self.consecutive_passes,
            turnovers_last_5_min=self.recent_turnovers,
            pitch_zone_x=self._progress(self.active_team, self.current_ball_pos),
        )

    def _stamp(self, event: MatchEvent) -> MatchEvent:
        event.period = self.period
        event.score_home = self.score.home_score
        event.score_away = self.score.away_score
        return event

    # ------------------------------------------------------------------ timeline

    def _phase_event(self, event_type: EventType, team: Team, added: Optional[int] = None) -> MatchEvent:
        minute, second = divmod(self.clock_sec, 60)
        return self._stamp(MatchEvent(
            event_id=self._next_id(),
            match_id=self.match_id,
            minute=minute,
            second=second,
            event_type=event_type,
            team_id=team.team_id,
            start_coordinates=Coordinates(x=50.0, y=50.0),
            added_time_minutes=added,
            tactical_context=self._tactical_context(),
        ))

    def next_event(self) -> Optional[MatchEvent]:
        """Advances the match clock and returns the next event, or None after full time."""
        if self.phase == "finished":
            return None

        if self.phase == "pre_match":
            self.phase = "live"
            self.active_team, self.defending_team = self.home_team, self.away_team
            return self._phase_event(EventType.MATCH_START, self.home_team)

        if self.phase == "half_time":
            # Second half: the away side kicks off
            self.phase = "live"
            self.period = 2
            self.clock_sec = HALF_LENGTH_SEC
            self.current_ball_pos = Coordinates(x=50.0, y=50.0)
            self.consecutive_passes = 0
            self.recent_turnovers = 0
            self.active_team, self.defending_team = self.away_team, self.home_team
            return self._phase_event(EventType.MATCH_START, self.away_team)

        regulation_end = HALF_LENGTH_SEC if self.period == 1 else FULL_LENGTH_SEC
        stoppage = self.stoppage_minutes[self.period]
        step = self.clock_rng.randint(24, 62)
        next_clock = self.clock_sec + step

        # Fourth official's board goes up as the regulation 45/90 is reached
        if not self.stoppage_announced[self.period] and next_clock >= regulation_end:
            self.stoppage_announced[self.period] = True
            self.clock_sec = regulation_end
            return self._phase_event(EventType.ADDED_TIME, self.active_team, added=stoppage)

        if next_clock >= regulation_end + stoppage * 60:
            # Referees rarely blow exactly on time: allow a few seconds over
            self.clock_sec = regulation_end + stoppage * 60 + self.clock_rng.randint(0, 25)
            if self.period == 1:
                self.phase = "half_time"
                return self._phase_event(EventType.HALF_TIME, self.active_team)
            self.phase = "finished"
            return self._phase_event(EventType.MATCH_END, self.active_team)

        self.clock_sec = next_clock
        # Decay the turnover memory so "chaos" reflects recent play, not the whole match
        if self.recent_turnovers and self.clock_rng.random() < 0.3:
            self.recent_turnovers -= 1
        minute, second = divmod(self.clock_sec, 60)
        return self.generate_event(minute, second)

    def play(self) -> Generator[MatchEvent, None, None]:
        """Yields the rest of the match, from the current clock to the final whistle."""
        while True:
            event = self.next_event()
            if event is None:
                return
            yield event

    @property
    def is_finished(self) -> bool:
        return self.phase == "finished"

    # ------------------------------------------------------------------ events

    def generate_event(self, minute: int, second: int) -> MatchEvent:
        """Generates a single plausible in-play event at the given match time."""
        event_id = self._next_id()
        tactical_ctx = self._tactical_context()
        attacking_right = self._attacks_right(self.active_team)
        progress = self._progress(self.active_team, self.current_ball_pos)

        rand_val = self.rng.random()
        attacker = self._get_random_outfield_player(self.active_team)

        base = dict(
            event_id=event_id,
            match_id=self.match_id,
            minute=minute,
            second=second,
            tactical_context=tactical_ctx,
        )

        # Final third: shooting chance
        if progress > 72.0 and rand_val < 0.38:
            shot_speed = round(self.rng.uniform(78.0, 118.0), 1)
            goal_x = 100.0 if attacking_right else 0.0
            self._update_player_tracking(attacker, burst_speed=shot_speed * 0.28, distance_delta=12.0)
            xg_val = calculate_expected_goals(
                self.current_ball_pos, tactical_ctx.defensive_pressure_index, attacking_right=attacking_right
            )
            gk = self._get_goalkeeper(self.defending_team)

            roll = self.rng.random()
            if roll < xg_val:
                outcome = "goal"
            else:
                rest = self.rng.random()
                outcome = "saved" if rest < 0.45 else ("off_target" if rest < 0.85 else "blocked")

            if outcome == "goal":
                target = Coordinates(x=goal_x, y=round(self.rng.uniform(45.0, 55.0), 1))
            elif outcome == "saved":
                target = Coordinates(x=goal_x, y=round(self.rng.uniform(44.0, 56.0), 1))
            elif outcome == "off_target":
                wide = self.rng.choice([self.rng.uniform(32.0, 43.0), self.rng.uniform(57.0, 68.0)])
                target = Coordinates(x=goal_x, y=round(wide, 1))
            else:
                step = 4.0 if attacking_right else -4.0
                target = Coordinates(
                    x=round(min(max(self.current_ball_pos.x + step, 0.0), 100.0), 1),
                    y=self.current_ball_pos.y,
                )

            if outcome == "goal":
                if self.active_team == self.home_team:
                    self.score.home_score += 1
                else:
                    self.score.away_score += 1

            event = MatchEvent(
                **base,
                event_type=EventType.GOAL if outcome == "goal" else EventType.SHOT,
                team_id=self.active_team.team_id,
                player=attacker,
                target_player=gk if outcome == "saved" else None,
                start_coordinates=self.current_ball_pos,
                end_coordinates=target,
                shot_speed_kmh=shot_speed,
                ball_speed_kmh=shot_speed,
                expected_goals=xg_val,
                is_sprint_burst=is_sprint_speed(shot_speed * 0.28),
                is_successful=outcome == "goal",
                shot_outcome=outcome,
            )

            self.consecutive_passes = 0
            if outcome == "goal":
                # Conceding side restarts from the centre spot
                self.current_ball_pos = Coordinates(x=50.0, y=50.0)
                self._flip_possession()
            elif outcome == "blocked":
                # Loose ball in the box, recycled by the defence
                self.current_ball_pos = target
                self._flip_possession()
            else:
                # Goal kick or keeper's ball, restarted from the defending side's own box
                self._flip_possession()
                self.current_ball_pos = Coordinates(x=88.0 if attacking_right else 12.0, y=50.0)
            return self._stamp(event)

        # Defensive actions: tackle, interception, pressure, foul
        if rand_val < 0.27:
            defender = self._get_random_outfield_player(self.defending_team)
            self._update_player_tracking(defender, burst_speed=self.rng.uniform(22.0, 31.5), distance_delta=18.0)
            self.consecutive_passes = 0

            if rand_val < 0.07:
                event_type = EventType.TACKLE
            elif rand_val < 0.13:
                event_type = EventType.INTERCEPTION
            elif rand_val < 0.21:
                event_type = EventType.PRESSURE
            else:
                event_type = EventType.FOUL

            card = None
            if event_type == EventType.FOUL:
                card_roll = self.rng.random()
                if card_roll < 0.015:
                    card = "red"
                elif card_roll < 0.20:
                    card = "yellow"
                    self.yellow_cards[defender.player_id] = self.yellow_cards.get(defender.player_id, 0) + 1
                    if self.yellow_cards[defender.player_id] >= 2:
                        card = "red"
                if card == "red":
                    self.sent_off.add(defender.player_id)
            else:
                self.recent_turnovers += 1

            event = MatchEvent(
                **base,
                event_type=event_type,
                team_id=self.defending_team.team_id,
                player=defender,
                target_player=attacker,
                start_coordinates=self.current_ball_pos,
                end_coordinates=self.current_ball_pos,
                is_sprint_burst=is_sprint_speed(defender.speed_kmh),
                is_successful=True,
                card=card,
            )

            # A foul gives the attacking side a free kick; anything else wins the ball back
            if event_type != EventType.FOUL:
                self._flip_possession()
            return self._stamp(event)

        # Pass
        receiver = self._get_random_outfield_player(self.active_team)
        while receiver.player_id == attacker.player_id:
            receiver = self._get_random_outfield_player(self.active_team)

        dx = self.rng.uniform(-6.0, 26.0)
        dx = dx if attacking_right else -dx
        dy = self.rng.uniform(-22.0, 22.0)
        new_x = min(max(self.current_ball_pos.x + dx, 4.0), 96.0)
        new_y = min(max(self.current_ball_pos.y + dy, 4.0), 96.0)
        end_coords = Coordinates(x=round(new_x, 1), y=round(new_y, 1))

        dist_m, diff_rating = calculate_pass_difficulty(
            start=self.current_ball_pos,
            end=end_coords,
            defensive_pressure=tactical_ctx.defensive_pressure_index,
            attacking_right=attacking_right,
        )

        pass_speed = round(self.rng.uniform(32.0, 68.0), 1)
        player_speed = round(self.rng.uniform(14.0, 30.5), 1)
        self._update_player_tracking(attacker, burst_speed=player_speed, distance_delta=dist_m * 0.4)

        # Harder passes fail more often (roughly 80-90% completion over a match)
        completed = self.rng.random() > diff_rating * 0.32

        event = MatchEvent(
            **base,
            event_type=EventType.PASS,
            team_id=self.active_team.team_id,
            player=attacker,
            target_player=receiver,
            start_coordinates=self.current_ball_pos,
            end_coordinates=end_coords,
            ball_speed_kmh=pass_speed,
            pass_distance_m=dist_m,
            pass_difficulty_rating=diff_rating,
            is_sprint_burst=is_sprint_speed(player_speed),
            is_successful=completed,
        )

        self.current_ball_pos = end_coords
        if completed:
            self.consecutive_passes += 1
        else:
            self.consecutive_passes = 0
            self.recent_turnovers += 1
            self._flip_possession()
        return self._stamp(event)

    # ------------------------------------------------------------------ batch helpers

    def generate_stream(
        self,
        start_minute: int = 0,
        end_minute: int = 90,
        step_seconds: int = 30,
        start_second: int = 0,
    ) -> Generator[MatchEvent, None, None]:
        """Legacy fixed-step stream of in-play events (no phases); prefer `play()`."""
        current_time_sec = start_minute * 60 + start_second
        end_time_sec = end_minute * 60

        while current_time_sec <= end_time_sec:
            minute = current_time_sec // 60
            second = current_time_sec % 60
            self.period = 1 if current_time_sec < HALF_LENGTH_SEC else 2
            yield self.generate_event(minute, second)
            current_time_sec += step_seconds

    def generate_full_match(self, event_count: int = 120) -> List[MatchEvent]:
        """Generates a batch of in-play events evenly spread over 90 minutes."""
        events = []
        step_sec = (90 * 60) // max(event_count, 1)
        for i in range(event_count):
            total_sec = i * step_sec
            minute = total_sec // 60
            second = total_sec % 60
            self.period = 1 if total_sec < HALF_LENGTH_SEC else 2
            events.append(self.generate_event(minute, second))
        return events
