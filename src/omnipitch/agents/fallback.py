"""Rule-based deterministic fallback generator to ensure zero broadcast downtime."""

from omnipitch.agents.base import BroadcastOverlayPayload
from omnipitch.models import EventType, MatchEvent


class FallbackNarrativeGenerator:
    """
    Deterministic rule-based backup engine.
    Ensures high-availability broadcast continuity if upstream LLM / Foundry agent
    experiences latency, network timeouts, or repeated verification rejections.
    """

    @staticmethod
    def generate(
        event: MatchEvent,
        persona: str = "analyst",
        language: str = "en"
    ) -> BroadcastOverlayPayload:
        match_time = f"{event.minute:02d}:{event.second:02d}"
        player_name = event.player.name if event.player else "Team"
        ctx = event.tactical_context

        if event.event_type == EventType.GOAL:
            headline = f"GOAL! {player_name}"
            narrative = f"{player_name} scores from inside the penalty box."
        elif event.event_type == EventType.SHOT:
            headline = f"Shot on Target by {player_name}"
            narrative = f"{player_name} fires a shot at {event.shot_speed_kmh or 0} km/h."
        elif event.event_type == EventType.PASS:
            headline = f"Pass Sequence: {player_name}"
            narrative = (
                f"{player_name} completes a pass ({event.pass_distance_m or 0}m, "
                f"difficulty {event.pass_difficulty_rating or 0})."
            )
        else:
            headline = f"{event.event_type.value.replace('_', ' ').title()}"
            narrative = f"{player_name} involved in {event.event_type.value} during a {ctx.game_rhythm_tempo} phase."

        # Localization if Italian
        if language == "it":
            if event.event_type == EventType.GOAL:
                headline = f"GOL! {player_name}"
                narrative = f"{player_name} segna da dentro l'area di rigore."
            elif event.event_type == EventType.SHOT:
                headline = f"Tiro in porta di {player_name}"
                narrative = f"{player_name} scaglia un tiro a {event.shot_speed_kmh or 0} km/h."
            elif event.event_type == EventType.PASS:
                headline = f"Azione di passaggio: {player_name}"
                narrative = f"{player_name} completa un passaggio di {event.pass_distance_m or 0}m (difficoltà: {event.pass_difficulty_rating or 0})."

        return BroadcastOverlayPayload(
            overlay_id=f"OVR-FB-{event.event_id}",
            match_id=event.match_id,
            match_time=match_time,
            headline=headline,
            narrative=narrative,
            persona=persona,
            language=language,
            is_verified=True,
            evidence_event_ids=[event.event_id],
            metrics={
                "ball_speed_kmh": event.ball_speed_kmh,
                "shot_speed_kmh": event.shot_speed_kmh,
                "pass_distance_m": event.pass_distance_m,
                "pass_difficulty_rating": event.pass_difficulty_rating,
                "control_vs_chaos_index": ctx.control_vs_chaos_index,
                "defensive_pressure_index": ctx.defensive_pressure_index,
                "game_rhythm_tempo": ctx.game_rhythm_tempo,
            },
            generated_by="deterministic-fallback-engine",
        )
