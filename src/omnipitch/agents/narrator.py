"""Narrator Agent: explains why a moment matters, per persona and language."""

from typing import Any, Dict, Optional

from omnipitch.agents.base import BaseAgent, NarrativeDraft, TacticalAnalysisReport
from omnipitch.agents.commentary import AWAY_ID, HOME_ID, SUPPORTED_LANGUAGES, TEAM_NAMES, surname
from omnipitch.models import EventType, MatchEvent

# Each insight kind: headline, analyst explanation, fan explanation — per language.
# Placeholders come from NarratorAgent._values(); every number is drawn from the
# event or the shared blackboard so the Grounding Verifier can audit it.
INSIGHTS: Dict[str, Dict[str, tuple]] = {
    "goal": {
        "en": ("GOAL — {P} ({minute})",
               "{P} converts a {xg} xG chance. {team} have {team_goals} from {team_xg} xG; {opp} {opp_xg}.",
               "{P} delivers! That's {team_goals} for {team} and the whole stadium is on its feet."),
        "it": ("GOL — {P} ({minute})",
               "{P} trasforma un'occasione da {xg} xG. {team} è a quota {team_goals} con {team_xg} xG; {opp} {opp_xg}.",
               "{P} non perdona! {team} sale a {team_goals} e lo stadio esplode."),
        "es": ("GOL — {P} ({minute})",
               "{P} convierte una ocasión de {xg} xG. {team} suma {team_goals} con {team_xg} xG; {opp} {opp_xg}.",
               "¡{P} no perdona! {team} ya tiene {team_goals} y el estadio se viene abajo."),
        "de": ("TOR — {P} ({minute})",
               "{P} verwandelt eine Chance mit {xg} xG. {team} steht bei {team_goals} aus {team_xg} xG; {opp} {opp_xg}.",
               "{P} trifft eiskalt! {team} jetzt bei {team_goals}, das Stadion bebt."),
    },
    "goal_conceded": {
        "en": ("Setback — {P} scores ({minute})",
               "{P} converts a {xg} xG chance. {team} have {team_goals} from {team_xg} xG; {opp} {opp_xg}.",
               "A blow — {team} hit back through {P}. Heads up, there's still time to respond."),
        "it": ("Doccia fredda — segna {P} ({minute})",
               "{P} trasforma un'occasione da {xg} xG. {team} è a quota {team_goals} con {team_xg} xG; {opp} {opp_xg}.",
               "Doccia fredda: {team} colpisce con {P}. C'è ancora tempo per reagire."),
        "es": ("Jarro de agua fría — marca {P} ({minute})",
               "{P} convierte una ocasión de {xg} xG. {team} suma {team_goals} con {team_xg} xG; {opp} {opp_xg}.",
               "Jarro de agua fría: {team} golpea con {P}. Hay tiempo para reaccionar."),
        "de": ("Rückschlag — {P} trifft ({minute})",
               "{P} verwandelt eine Chance mit {xg} xG. {team} steht bei {team_goals} aus {team_xg} xG; {opp} {opp_xg}.",
               "Kalte Dusche: {team} trifft durch {P}. Noch ist Zeit zu reagieren."),
    },
    "red": {
        "en": ("Red card — {p}",
               "{team} drop to ten. Expect a deeper block: possession so far {team_poss}% for {team}.",
               "Big blow for {team} — they'll have to battle with ten players now."),
        "it": ("Rosso — {p}",
               "{team} in dieci. Ci si aspetta un baricentro più basso: possesso finora {team_poss}% per {team}.",
               "Colpo durissimo per {team}, ora dovrà soffrire in dieci."),
        "es": ("Roja — {p}",
               "{team} se queda con diez. Toca replegarse: posesión hasta ahora {team_poss}% para {team}.",
               "Golpe duro para {team}, ahora toca sufrir con diez."),
        "de": ("Rot — {p}",
               "{team} nur noch zu zehnt. Erwartbar ist ein tieferer Block: bisher {team_poss}% Ballbesitz für {team}.",
               "Harter Schlag für {team}, jetzt heißt es zu zehnt kämpfen."),
    },
    "yellow": {
        "en": ("Yellow card — {p}",
               "{p} is booked; a second caution would leave {team} with ten.",
               "{p} needs to be careful now — one more and it's an early bath!"),
        "it": ("Giallo — {p}",
               "{p} ammonito: un secondo giallo lascerebbe {team} in dieci.",
               "{p} deve stare attento ora, un altro giallo e va sotto la doccia!"),
        "es": ("Amarilla — {p}",
               "{p} amonestado: una segunda amarilla dejaría a {team} con diez.",
               "¡{p} tiene que medirse ahora, otra más y se va a la calle!"),
        "de": ("Gelb — {p}",
               "{p} verwarnt: eine zweite Gelbe würde {team} in Unterzahl bringen.",
               "{p} muss jetzt aufpassen, noch eine und es ist Feierabend!"),
    },
    "big_save": {
        "en": ("Big save — {gk} denies {p}",
               "{gk} stops a {xg} xG chance. {team} xG now {team_xg}, against {opp_xg} for {opp}.",
               "What a save! {gk} keeps it out and {opp} survive."),
        "it": ("Paratona — {gk} su {p}",
               "{gk} neutralizza un'occasione da {xg} xG. Gli xG di {team} salgono a {team_xg}, contro {opp_xg} di {opp}.",
               "Che parata! {gk} dice di no e {opp} resta in piedi."),
        "es": ("Paradón — {gk} ante {p}",
               "{gk} detiene una ocasión de {xg} xG. Los xG de {team} suben a {team_xg}, por {opp_xg} de {opp}.",
               "¡Qué parada! {gk} lo evita y {opp} sigue viva."),
        "de": ("Glanzparade — {gk} gegen {p}",
               "{gk} pariert eine Chance mit {xg} xG. {team} steht jetzt bei {team_xg} xG, {opp} bei {opp_xg}.",
               "Was für eine Parade! {gk} rettet {opp}."),
    },
    "shot": {
        "en": ("Chance for {team}",
               "Shot {team_shots} for {team} ({xg} xG). Running xG: {home} {home_xg} – {away_xg} {away}.",
               "{team} are knocking on the door — that's {team_shots} attempts now."),
        "it": ("Occasione per {team}",
               "Tiro numero {team_shots} di {team} ({xg} xG). xG totali: {home} {home_xg} – {away_xg} {away}.",
               "{team} spinge, sono già {team_shots} conclusioni!"),
        "es": ("Ocasión para {team}",
               "Disparo número {team_shots} de {team} ({xg} xG). xG acumulado: {home} {home_xg} – {away_xg} {away}.",
               "¡{team} aprieta, ya van {team_shots} disparos!"),
        "de": ("Chance für {team}",
               "Schuss Nummer {team_shots} von {team} ({xg} xG). xG gesamt: {home} {home_xg} – {away_xg} {away}.",
               "{team} drückt, schon {team_shots} Abschlüsse!"),
    },
    "streak": {
        "en": ("{team} in total control",
               "{streak} consecutive passes for {team}; control index {ctrl}. They are dictating tempo, not reacting.",
               "{team} are keeping the ball beautifully — {streak} passes in a row!"),
        "it": ("{team} padrone del gioco",
               "{streak} passaggi consecutivi per {team}; indice di controllo {ctrl}. Dettano il ritmo invece di subirlo.",
               "{team} fa girare palla alla grande — {streak} passaggi di fila!"),
        "es": ("{team} manda en el partido",
               "{streak} pases seguidos de {team}; índice de control {ctrl}. Marcan el ritmo en lugar de reaccionar.",
               "¡{team} toca y toca — {streak} pases seguidos!"),
        "de": ("{team} hat alles im Griff",
               "{streak} Pässe in Folge für {team}; Kontrollindex {ctrl}. Sie bestimmen das Tempo, statt zu reagieren.",
               "{team} lässt den Ball wunderbar laufen — {streak} Pässe am Stück!"),
    },
    "press_win": {
        "en": ("High press pays off",
               "Ball won at pressure index {press}. Winning it this high shortens the road to goal for {team}.",
               "{team} hunt the ball down and win it back!"),
        "it": ("Il pressing alto paga",
               "Palla recuperata con indice di pressione {press}: recuperarla così in alto accorcia la strada verso la porta per {team}.",
               "{team} aggredisce e si riprende il pallone!"),
        "es": ("La presión alta da frutos",
               "Balón recuperado con índice de presión {press}: robar tan arriba acerca a {team} a la portería.",
               "¡{team} muerde arriba y recupera!"),
        "de": ("Hohes Pressing zahlt sich aus",
               "Ballgewinn bei Pressingindex {press}: so weit vorne verkürzt sich für {team} der Weg zum Tor.",
               "{team} jagt den Ball und holt ihn sich zurück!"),
    },
    "added_time": {
        "en": ("{n} minutes added",
               "Stoppage time: {n} minutes. {score_line}; xG {home_xg} – {away_xg}.",
               "{n} more minutes to play — can anyone find a late twist?"),
        "it": ("{n} minuti di recupero",
               "Recupero: {n} minuti. {score_line}; xG {home_xg} – {away_xg}.",
               "Altri {n} minuti — ci sarà un colpo di scena?"),
        "es": ("{n} minutos de añadido",
               "Añadido: {n} minutos. {score_line}; xG {home_xg} – {away_xg}.",
               "Quedan {n} minutos más — ¿habrá giro final?"),
        "de": ("{n} Minuten Nachspielzeit",
               "Nachspielzeit: {n} Minuten. {score_line}; xG {home_xg} – {away_xg}.",
               "Noch {n} Minuten — gibt es eine späte Wende?"),
    },
    "half_time": {
        "en": ("Half-time: {score_line}",
               "xG {home} {home_xg} – {away_xg} {away}; shots {home_shots}–{away_shots}; possession {poss_home}%–{poss_away}%.",
               "Half-time — {score_line}. Plenty still to play for!"),
        "it": ("Intervallo: {score_line}",
               "xG {home} {home_xg} – {away_xg} {away}; tiri {home_shots}–{away_shots}; possesso {poss_home}%–{poss_away}%.",
               "Intervallo: {score_line}. Ancora tutto da giocare!"),
        "es": ("Descanso: {score_line}",
               "xG {home} {home_xg} – {away_xg} {away}; tiros {home_shots}–{away_shots}; posesión {poss_home}%–{poss_away}%.",
               "Descanso: {score_line}. ¡Queda mucho partido!"),
        "de": ("Halbzeit: {score_line}",
               "xG {home} {home_xg} – {away_xg} {away}; Schüsse {home_shots}–{away_shots}; Ballbesitz {poss_home}%–{poss_away}%.",
               "Halbzeit: {score_line}. Noch ist alles drin!"),
    },
    "full_time": {
        "en": ("Full-time: {score_line}",
               "xG {home} {home_xg} – {away_xg} {away}; shots {home_shots}–{away_shots}; possession {poss_home}%–{poss_away}%.",
               "Full-time — {score_line}. What a match!"),
        "it": ("Finale: {score_line}",
               "xG {home} {home_xg} – {away_xg} {away}; tiri {home_shots}–{away_shots}; possesso {poss_home}%–{poss_away}%.",
               "Finita: {score_line}. Che partita!"),
        "es": ("Final: {score_line}",
               "xG {home} {home_xg} – {away_xg} {away}; tiros {home_shots}–{away_shots}; posesión {poss_home}%–{poss_away}%.",
               "Final: {score_line}. ¡Qué partidazo!"),
        "de": ("Abpfiff: {score_line}",
               "xG {home} {home_xg} – {away_xg} {away}; Schüsse {home_shots}–{away_shots}; Ballbesitz {poss_home}%–{poss_away}%.",
               "Abpfiff: {score_line}. Was für ein Spiel!"),
    },
    "kickoff_1": {
        "en": ("Kick-off",
               "Live tracking is on: every pass, shot and sprint is measured and cited as evidence.",
               "Here we go — settle in for 90 minutes plus stoppage time!"),
        "it": ("Calcio d'inizio",
               "Tracking live attivo: ogni passaggio, tiro e sprint viene misurato e citato come evidenza.",
               "Si parte — mettetevi comodi per 90 minuti più recupero!"),
        "es": ("Saque inicial",
               "Seguimiento en vivo activo: cada pase, disparo y sprint se mide y se cita como evidencia.",
               "¡Arrancamos — 90 minutos más el añadido por delante!"),
        "de": ("Anstoß",
               "Live-Tracking läuft: Jeder Pass, Schuss und Sprint wird gemessen und als Beleg zitiert.",
               "Los geht's — 90 Minuten plus Nachspielzeit!"),
    },
    "kickoff_2": {
        "en": ("Second half under way",
               "Restart with xG {home} {home_xg} – {away_xg} {away} from the first half.",
               "The second half is on — let's go!"),
        "it": ("Inizia la ripresa",
               "Si riparte con xG {home} {home_xg} – {away_xg} {away} nel primo tempo.",
               "Si riparte — forza!"),
        "es": ("Arranca la segunda parte",
               "Se reanuda con xG {home} {home_xg} – {away_xg} {away} en la primera parte.",
               "¡Empieza la segunda parte, vamos!"),
        "de": ("Zweite Halbzeit läuft",
               "Wiederanpfiff bei xG {home} {home_xg} – {away_xg} {away} aus der ersten Hälfte.",
               "Die zweite Hälfte läuft — auf geht's!"),
    },
    "structured-possession": {
        "en": ("Sustained control: {team}",
               "Control index {ctrl}: {team} are circulating with low turnover risk.",
               "{team} are calm on the ball and in charge right now."),
        "it": ("Controllo costante: {team}",
               "Indice di controllo {ctrl}: {team} fa circolare palla con basso rischio di perderla.",
               "{team} gestisce con calma e comanda il gioco."),
        "es": ("Control sostenido: {team}",
               "Índice de control {ctrl}: {team} circula con poco riesgo de pérdida.",
               "{team} está tranquilo con el balón y manda ahora mismo."),
        "de": ("Volle Kontrolle: {team}",
               "Kontrollindex {ctrl}: {team} lässt den Ball mit geringem Verlustrisiko laufen.",
               "{team} ist ruhig am Ball und hat das Spiel im Griff."),
    },
    "frantic-transition": {
        "en": ("End-to-end chaos",
               "Control index {ctrl}: the ball keeps changing hands, so transitions decide this phase.",
               "It's frantic out there — nobody can keep the ball!"),
        "it": ("Caos totale",
               "Indice di controllo {ctrl}: il pallone cambia continuamente padrone, decidono le transizioni.",
               "È una battaglia senza respiro — nessuno tiene palla!"),
        "es": ("Ida y vuelta",
               "Índice de control {ctrl}: el balón cambia de dueño sin parar, deciden las transiciones.",
               "¡Esto es un caos, nadie se queda con el balón!"),
        "de": ("Wildes Hin und Her",
               "Kontrollindex {ctrl}: Der Ball wechselt ständig, die Umschaltmomente entscheiden.",
               "Es geht hin und her — niemand behält den Ball!"),
    },
    "high-block-siege": {
        "en": ("{team} camped in the final third",
               "Pressure index {press} as {team} pin {opp} back near their box.",
               "{team} have {opp} pinned back — something has to give!"),
        "it": ("{team} schiaccia l'avversario",
               "Indice di pressione {press}: {team} costringe {opp} a difendersi vicino all'area.",
               "{team} tiene {opp} schiacciata in area — qualcosa deve succedere!"),
        "es": ("{team} encierra a su rival",
               "Índice de presión {press}: {team} mete a {opp} cerca de su área.",
               "¡{team} tiene a {opp} encerrado, algo tiene que pasar!"),
        "de": ("{team} schnürt den Gegner ein",
               "Pressingindex {press}: {team} drängt {opp} an den eigenen Strafraum.",
               "{team} hat {opp} eingeschnürt — da muss etwas passieren!"),
    },
    "balanced-contest": {
        "en": ("Evenly poised",
               "Control index {ctrl}, pressure index {press}: neither side has taken over yet.",
               "It's a real battle in midfield — all to play for."),
        "it": ("Partita in equilibrio",
               "Indice di controllo {ctrl}, indice di pressione {press}: nessuna squadra ha ancora preso il comando.",
               "Battaglia vera a centrocampo — tutto aperto."),
        "es": ("Partido igualado",
               "Índice de control {ctrl}, índice de presión {press}: nadie ha tomado el mando todavía.",
               "Batalla en el centro del campo — todo por decidir."),
        "de": ("Ausgeglichenes Spiel",
               "Kontrollindex {ctrl}, Pressingindex {press}: Noch hat keine Seite übernommen.",
               "Echter Kampf im Mittelfeld — alles offen."),
    },
}

# Kinds worth a co-commentator line in the live commentary feed
COLOR_KINDS = {"goal", "goal_conceded", "red", "yellow", "big_save", "streak", "added_time", "half_time", "full_time", "kickoff_2"}
PATTERN_KINDS = {"streak", "press_win", "structured-possession", "frantic-transition", "high-block-siege", "balanced-contest"}


class NarratorAgent(BaseAgent):
    """
    Turns tactical metrics into the on-screen story and the co-commentator's voice.
    - Persona: 'analyst' (numbers and mechanisms) vs 'fan' (plain-language emotion)
    - Languages: English, Italian, Spanish, German
    """

    def __init__(self, name: str = "BroadcastNarrator"):
        super().__init__(name=name)

    @staticmethod
    def insight_kind(event: MatchEvent, report: TacticalAnalysisReport, state: Dict[str, Any],
                     favourite_club: Optional[str] = None) -> str:
        et = event.event_type
        if et == EventType.GOAL:
            return "goal_conceded" if favourite_club in (HOME_ID, AWAY_ID) and favourite_club != event.team_id else "goal"
        if et == EventType.MATCH_START:
            return "kickoff_1" if event.period == 1 else "kickoff_2"
        if et == EventType.ADDED_TIME:
            return "added_time"
        if et == EventType.HALF_TIME:
            return "half_time"
        if et == EventType.MATCH_END:
            return "full_time"
        if et == EventType.FOUL and event.card == "red":
            return "red"
        if et == EventType.FOUL and event.card == "yellow":
            return "yellow"
        if et == EventType.SHOT:
            return "big_save" if event.shot_outcome == "saved" and (event.expected_goals or 0) >= 0.25 else "shot"
        if et == EventType.PASS and event.is_successful and state.get("pass_streak", 0) in (6, 9, 12, 15):
            return "streak"
        if et in (EventType.TACKLE, EventType.INTERCEPTION, EventType.PRESSURE) and \
                event.tactical_context.defensive_pressure_index >= 0.6:
            return "press_win"
        return report.metrics_snapshot.get("game_rhythm_tempo") or event.tactical_context.game_rhythm_tempo

    @staticmethod
    def _values(event: MatchEvent, report: TacticalAnalysisReport, state: Dict[str, Any]) -> Dict[str, Any]:
        is_home = event.team_id == HOME_ID
        side, other = ("home", "away") if is_home else ("away", "home")
        snap = report.metrics_snapshot
        gk = surname(event.target_player.name) if (event.target_player and event.shot_outcome == "saved") else ""
        return {
            "p": surname(event.player.name) if event.player else TEAM_NAMES.get(event.team_id, ""),
            "P": event.player.name if event.player else TEAM_NAMES.get(event.team_id, ""),
            "gk": gk,
            "minute": event.match_minute_label,
            "team": TEAM_NAMES.get(event.team_id, event.team_id),
            "opp": TEAM_NAMES[AWAY_ID if is_home else HOME_ID],
            "home": TEAM_NAMES[HOME_ID],
            "away": TEAM_NAMES[AWAY_ID],
            "score_line": f"{TEAM_NAMES[HOME_ID]} {event.score_home}–{event.score_away} {TEAM_NAMES[AWAY_ID]}",
            "xg": f"{event.expected_goals:.2f}" if event.expected_goals is not None else "0.00",
            "team_goals": event.score_home if is_home else event.score_away,
            "team_xg": f"{state[f'{side}_xg']:.2f}",
            "opp_xg": f"{state[f'{other}_xg']:.2f}",
            "home_xg": f"{state['home_xg']:.2f}",
            "away_xg": f"{state['away_xg']:.2f}",
            "team_shots": state[f"{side}_shots"],
            "home_shots": state["home_shots"],
            "away_shots": state["away_shots"],
            "team_poss": state[f"poss_{side}"],
            "poss_home": state["poss_home"],
            "poss_away": state["poss_away"],
            "streak": state.get("pass_streak", 0),
            "ctrl": f"{snap.get('control_vs_chaos_index', event.tactical_context.control_vs_chaos_index):.2f}",
            "press": f"{snap.get('defensive_pressure_index', event.tactical_context.defensive_pressure_index):.2f}",
            "n": event.added_time_minutes or 0,
        }

    async def process(self, context: Dict[str, Any]) -> NarrativeDraft:
        report: TacticalAnalysisReport = context["tactical_report"]
        event: MatchEvent = context["latest_event"]
        state: Dict[str, Any] = context.get("match_state") or {}
        persona: str = context.get("persona", "analyst").lower()
        language: str = context.get("language", "en").lower()
        lang = language if language in SUPPORTED_LANGUAGES else "en"

        kind = self.insight_kind(event, report, state, context.get("favourite_club"))
        bank = INSIGHTS.get(kind, INSIGHTS["balanced-contest"])
        headline_t, analyst_t, fan_t = bank.get(lang) or bank["en"]
        values = self._values(event, report, state)

        # Pattern insights rest on the recent window, single moments on the event itself
        cited = [event.event_id]
        if kind in PATTERN_KINDS:
            cited = report.key_event_ids[-3:] or cited

        return NarrativeDraft(
            headline=headline_t.format(**values),
            commentary=(analyst_t if persona == "analyst" else fan_t).format(**values),
            persona=persona,
            language=lang,
            cited_event_ids=cited,
            insight_kind=kind,
            is_color_moment=kind in COLOR_KINDS,
        )
