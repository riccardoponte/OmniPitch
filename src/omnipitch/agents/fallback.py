"""Rule-based deterministic fallback generator to ensure zero broadcast downtime."""

from omnipitch.agents.base import BroadcastOverlayPayload
from omnipitch.models import EventType, MatchEvent

# headline, narrative per event family and language — minimal, factual, always safe to air
FALLBACK_TEXT = {
    "goal": {
        "en": ("GOAL! {p}", "{p} scores. {score}."),
        "it": ("GOL! {p}", "Segna {p}. {score}."),
        "es": ("¡GOL! {p}", "Marca {p}. {score}."),
        "de": ("TOR! {p}", "{p} trifft. {score}."),
    },
    "shot": {
        "en": ("Shot by {p}", "{p} shoots at {speed} km/h."),
        "it": ("Tiro di {p}", "{p} calcia a {speed} km/h."),
        "es": ("Disparo de {p}", "{p} dispara a {speed} km/h."),
        "de": ("Schuss von {p}", "{p} schießt mit {speed} km/h."),
    },
    "pass": {
        "en": ("Pass: {p}", "{p} plays a {dist} m pass (difficulty {diff})."),
        "it": ("Passaggio: {p}", "{p} gioca un passaggio di {dist} m (difficoltà {diff})."),
        "es": ("Pase: {p}", "{p} da un pase de {dist} m (dificultad {diff})."),
        "de": ("Pass: {p}", "{p} spielt einen Pass über {dist} m (Schwierigkeit {diff})."),
    },
    "other": {
        "en": ("{kind}", "{score}."),
        "it": ("{kind}", "{score}."),
        "es": ("{kind}", "{score}."),
        "de": ("{kind}", "{score}."),
    },
}


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
        player_name = event.player.name if event.player else "Team"
        ctx = event.tactical_context
        lang = language if language in ("en", "it", "es", "de") else "en"

        if event.event_type == EventType.GOAL:
            family = "goal"
        elif event.event_type == EventType.SHOT:
            family = "shot"
        elif event.event_type == EventType.PASS:
            family = "pass"
        else:
            family = "other"

        headline_t, narrative_t = FALLBACK_TEXT[family][lang]
        values = {
            "p": player_name,
            "speed": round(event.shot_speed_kmh or 0),
            "dist": round(event.pass_distance_m or 0),
            "diff": event.pass_difficulty_rating or 0,
            "score": f"Avalon City {event.score_home}–{event.score_away} Solaria Rovers",
            "kind": event.event_type.value.replace("_", " ").title(),
        }

        return BroadcastOverlayPayload(
            overlay_id=f"OVR-FB-{event.event_id}",
            match_id=event.match_id,
            match_time=event.match_clock,
            headline=headline_t.format(**values),
            narrative=narrative_t.format(**values),
            persona=persona,
            language=lang,
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
