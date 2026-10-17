"""Narrator Agent for generating persona-driven, multilingual broadcast commentary."""

from typing import Any, Dict, List
from omnipitch.agents.base import BaseAgent, NarrativeDraft, TacticalAnalysisReport
from omnipitch.models import EventType, MatchEvent


class NarratorAgent(BaseAgent):
    """
    Transforms tactical metrics into broadcast narratives.
    Supports:
    - Persona: 'analyst' (tactical/data-rich) vs 'fan' (emotional/action-driven)
    - Localization: English ('en'), Italian ('it'), Spanish ('es'), German ('de')
    """

    def __init__(self, name: str = "BroadcastNarrator"):
        super().__init__(name=name)

    async def process(self, context: Dict[str, Any]) -> NarrativeDraft:
        report: TacticalAnalysisReport = context["tactical_report"]
        latest_event: MatchEvent = context["latest_event"]
        persona: str = context.get("persona", "analyst").lower()
        language: str = context.get("language", "en").lower()

        # Headline generation
        headline = self._generate_headline(latest_event, report, persona, language)
        commentary = self._generate_commentary(latest_event, report, persona, language)

        return NarrativeDraft(
            headline=headline,
            commentary=commentary,
            persona=persona,
            language=language,
            cited_event_ids=report.key_event_ids[-3:] if report.key_event_ids else [latest_event.event_id],
        )

    def _generate_headline(
        self, event: MatchEvent, report: TacticalAnalysisReport, persona: str, lang: str
    ) -> str:
        player_name = event.player.name if event.player else "Team"

        if event.event_type == EventType.GOAL:
            if lang == "it":
                return f"GOAL! {player_name} sblocca il match!"
            elif lang == "es":
                return f"¡GOL! ¡{player_name} rompe el empate!"
            elif lang == "de":
                return f"TOR! {player_name} trifft zur Führung!"
            return f"GOAL! {player_name} strikes with authority!"

        elif event.event_type == EventType.SHOT:
            if lang == "it":
                return f"Conclusione potente di {player_name} ({event.shot_speed_kmh or 0} km/h)"
            return f"Thunderous Strike by {player_name} ({event.shot_speed_kmh or 0} km/h)"

        elif report.metrics_snapshot.get("control_vs_chaos_index", 0.5) > 0.70:
            if lang == "it":
                return "Assedio e controllo totale del possesso"
            return "Sustained Zonal Control & High Possession"

        elif report.metrics_snapshot.get("defensive_pressure_index", 0.5) > 0.65:
            if lang == "it":
                return "Pressing asfissiante nella trequarti"
            return "Suffocating High Press in Final Third"

        return "Tactical Transition in Progress"

    def _generate_commentary(
        self, event: MatchEvent, report: TacticalAnalysisReport, persona: str, lang: str
    ) -> str:
        player_name = event.player.name if event.player else "The attacker"
        metrics = report.metrics_snapshot
        tempo = metrics.get("game_rhythm_tempo", "balanced-contest")
        diff = event.pass_difficulty_rating or 0.0
        ball_speed = event.ball_speed_kmh or 0.0

        if persona == "analyst":
            # Analyst: Data-driven, tactical explanation
            if lang == "it":
                return (
                    f"Minuto {event.minute:02d}:{event.second:02d}. Nel pattern '{tempo}', {player_name} "
                    f"completa una giocata con indice di difficoltà {diff} e velocità palla di {ball_speed} km/h. "
                    f"L'indice controllo/caos si attesta a {metrics.get('control_vs_chaos_index', 0.5):.2f}, "
                    f"dimostrando {report.control_vs_chaos_assessment.lower()}"
                )
            return (
                f"Minute {event.minute:02d}:{event.second:02d}. Operating within a '{tempo}' phase, {player_name} "
                f"completes an action with a difficulty rating of {diff} at {ball_speed} km/h. "
                f"Possession control index stands at {metrics.get('control_vs_chaos_index', 0.5):.2f}, "
                f"reflecting {report.control_vs_chaos_assessment.lower()}"
            )

        else:
            # Fan: High enthusiasm, action focus
            if lang == "it":
                if event.event_type == EventType.GOAL:
                    return f"Incredibile momento di calcio! {player_name} fa esplodere l'arena con un tiro formidabile!"
                return (
                    f"{player_name} trascina la squadra con grande determinazione! "
                    f"Il ritmo è altissimo e la pressione sale di minuto in minuto!"
                )
            if event.event_type == EventType.GOAL:
                return f"What an unbelievable moment! {player_name} sends the stadium into pure ecstasy with a lethal strike!"
            return (
                f"{player_name} keeps the crowd on the edge of their seats with relentless drive! "
                f"The intensity is electric as the pressure mounts!"
            )
