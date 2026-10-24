"""
Live play-by-play commentary ("telecronaca") for OmniPitch.

The CommentatorAgent turns every match event into one short broadcast line in
English, Italian, Spanish or German. Lines are built from a structured fact
sheet (`CommentaryFacts`) so the Grounding Verifier can check every name and
number. On key moments, when Microsoft Foundry is configured, the agent asks the
model for a livelier line from the same facts; anything the verifier rejects
falls back to the deterministic phrase bank below.
"""

import json
import zlib
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from omnipitch.agents.base import BaseAgent
from omnipitch.models import EventType, MatchEvent

SUPPORTED_LANGUAGES = ("en", "it", "es", "de")

TEAM_NAMES = {"avalon_city": "Avalon City", "solaria_rovers": "Solaria Rovers"}
TEAM_SHORT = {"avalon_city": "Avalon", "solaria_rovers": "Solaria"}
HOME_ID = "avalon_city"
AWAY_ID = "solaria_rovers"

KEY_EVENTS = {
    EventType.GOAL,
    EventType.SHOT,
    EventType.MATCH_START,
    EventType.HALF_TIME,
    EventType.MATCH_END,
    EventType.ADDED_TIME,
}


def surname(name: Optional[str]) -> str:
    return name.split(" ")[-1] if name else ""


class CommentaryLine(BaseModel):
    """One line of the live commentary feed."""
    speaker: str = Field(..., description="'lead' (play-by-play) or 'color' (co-commentator analysis)")
    text: str
    intensity: int = Field(1, ge=1, le=3, description="1 routine, 2 notable, 3 big moment")
    language: str = "en"
    event_id: str
    minute_label: str
    source: str = Field("phrase-bank", description="'foundry-llm' or 'phrase-bank'")


class CommentaryFacts(BaseModel):
    """Everything a commentator may say about one event — and nothing else."""
    event_id: str
    event_type: str
    minute_label: str
    period: int
    team_id: str
    team: str
    opponent: str
    player: Optional[str] = None
    player_full: Optional[str] = None
    target: Optional[str] = None
    goalkeeper: Optional[str] = None
    score_home: int
    score_away: int
    distance_m: Optional[int] = None
    pass_difficulty: Optional[float] = None
    speed_kmh: Optional[int] = None
    xg: Optional[float] = None
    shot_outcome: Optional[str] = None
    card: Optional[str] = None
    added_minutes: Optional[int] = None
    player_goals: int = 0
    pass_streak: int = 0
    is_successful: bool = True
    control_index: Optional[float] = None
    pressure_index: Optional[float] = None

    def numbers(self) -> List[float]:
        """Numbers a grounded line is allowed to contain."""
        nums = [self.score_home, self.score_away, self.period, self.player_goals, self.pass_streak]
        for v in (self.distance_m, self.pass_difficulty, self.speed_kmh, self.xg, self.added_minutes,
                  self.control_index, self.pressure_index):
            if v is not None:
                nums.append(v)
        # Minute label like 45+2' contributes 45 and 2
        for part in self.minute_label.replace("'", "").split("+"):
            if part.isdigit():
                nums.append(int(part))
        return nums

    def people(self) -> List[str]:
        return [n for n in (self.player, self.player_full, self.target, self.goalkeeper) if n]


# ---------------------------------------------------------------------------
# Phrase bank. Placeholders: {p} player surname, {P} full name, {r}/{t} receiver /
# opponent involved, {gk} keeper, {team}/{opp} team names, {home}/{away},
# {score_line}, {dist}, {speed}, {xg}, {n} added minutes, {winner}.
# ---------------------------------------------------------------------------

PHRASES: Dict[str, Dict[str, List[str]]] = {
    "kickoff_1": {
        "en": ["And we're under way at the Aethelgard Arena! {home} kick off against {away}.",
               "The referee blows — {home} against {away}, here we go!"],
        "it": ["Si parte all'Aethelgard Arena! Batte il calcio d'inizio {home}, di fronte {away}.",
               "Fischio d'inizio: {home} contro {away}, si comincia!"],
        "es": ["¡Rueda el balón en el Aethelgard Arena! Saca {home} ante {away}.",
               "Pitido inicial: {home} contra {away}, ¡arrancamos!"],
        "de": ["Der Ball rollt in der Aethelgard Arena! {home} stößt an gegen {away}.",
               "Anpfiff: {home} gegen {away}, los geht's!"],
    },
    "kickoff_2": {
        "en": ["We're back under way for the second half, {away} get it going. {score_line}."],
        "it": ["Riprende la partita: secondo tempo al via, batte {away}. {score_line}."],
        "es": ["Arranca la segunda parte, saca {away}. {score_line}."],
        "de": ["Weiter geht's mit der zweiten Halbzeit, {away} hat Anstoß. {score_line}."],
    },
    "pass_short": {
        "en": ["{p} to {r}.", "{p} finds {r}.", "Simple ball from {p} into {r}.", "{p}, keeping it moving… {r}."],
        "it": ["{p} per {r}.", "{p} serve {r}.", "Appoggio di {p} per {r}.", "{p} fa girare palla… {r}."],
        "es": ["{p} para {r}.", "{p} encuentra a {r}.", "Toque de {p} hacia {r}.", "{p} la mueve… {r}."],
        "de": ["{p} auf {r}.", "{p} findet {r}.", "Kurzer Pass von {p} zu {r}.", "{p} lässt laufen… {r}."],
    },
    "pass_long": {
        "en": ["Long ball from {p}… picks out {r}!", "{p} switches it, {dist} metres across to {r}.",
               "Raking pass from {p}, {r} brings it down."],
        "it": ["Lancio lungo di {p}… trova {r}!", "{p} cambia gioco, {dist} metri verso {r}.",
               "Gran lancio di {p}, {r} la addomestica."],
        "es": ["Balón largo de {p}… ¡encuentra a {r}!", "{p} cambia de orientación, {dist} metros hasta {r}.",
               "Gran envío de {p}, {r} la controla."],
        "de": ["Langer Ball von {p}… {r} ist da!", "{p} verlagert das Spiel, {dist} Meter zu {r}.",
               "Weiter Pass von {p}, {r} nimmt ihn an."],
    },
    "pass_key": {
        "en": ["Lovely ball from {p}, threaded through to {r}!", "{p} splits the lines — {r} is in!"],
        "it": ["Che palla di {p}! Filtrante per {r}!", "{p} taglia le linee — {r} è dentro!"],
        "es": ["¡Qué pase de {p}, al hueco para {r}!", "{p} rompe líneas — ¡{r} se queda solo!"],
        "de": ["Klasse Ball von {p}, durch die Schnittstelle zu {r}!", "{p} spielt die Linien aus — {r} ist durch!"],
    },
    "pass_failed": {
        "en": ["{p} tries to find {r}… cut out.", "Loose from {p}, that's a giveaway.", "{p} overhits it, possession gone."],
        "it": ["{p} cerca {r}… intercettato.", "Pallone perso da {p}.", "Troppo lungo il passaggio di {p}, palla persa."],
        "es": ["{p} busca a {r}… interceptado.", "Pérdida de {p}.", "Se le va largo a {p}, se pierde la posesión."],
        "de": ["{p} sucht {r}… abgefangen.", "Ballverlust von {p}.", "Zu weit von {p}, der Ball ist weg."],
    },
    "tackle": {
        "en": ["Great tackle from {p}, wins it clean off {t}.", "{p} slides in — perfectly timed!"],
        "it": ["Grande intervento di {p}, pulito su {t}.", "Scivolata di {p} — tempismo perfetto!"],
        "es": ["Gran entrada de {p}, limpia sobre {t}.", "¡Barrida de {p}, perfecta!"],
        "de": ["Starkes Tackling von {p}, sauber gegen {t}.", "{p} grätscht — perfektes Timing!"],
    },
    "interception": {
        "en": ["{p} reads it and steps in.", "Intercepted by {p}."],
        "it": ["{p} legge la traiettoria e intercetta.", "Intercetto di {p}."],
        "es": ["{p} lee la jugada y corta.", "Intercepción de {p}."],
        "de": ["{p} ahnt es und fängt ab.", "Abgefangen von {p}."],
    },
    "pressure": {
        "en": ["{p} closes down {t} and forces the turnover.", "{team} press high — {p} wins it back."],
        "it": ["{p} aggredisce {t} e recupera palla.", "Pressing alto di {team}, {p} riconquista il pallone."],
        "es": ["{p} presiona a {t} y recupera.", "Presión alta de {team}, {p} roba el balón."],
        "de": ["{p} läuft {t} an und erobert den Ball.", "Hohes Pressing von {team}, {p} holt sich den Ball."],
    },
    "foul": {
        "en": ["Foul by {p} on {t}. Free kick {opp}.", "{p} brings down {t}, and the referee blows."],
        "it": ["Fallo di {p} su {t}. Punizione per {opp}.", "{p} stende {t}, fischia l'arbitro."],
        "es": ["Falta de {p} sobre {t}. Tiro libre para {opp}.", "{p} derriba a {t}, pita el árbitro."],
        "de": ["Foul von {p} an {t}. Freistoß für {opp}.", "{p} bringt {t} zu Fall, der Schiedsrichter pfeift."],
    },
    "foul_yellow": {
        "en": ["{p} goes into the book — a yellow for that challenge on {t}.", "Yellow card! {p} cautioned for the foul on {t}."],
        "it": ["Ammonito {p}: giallo per l'intervento su {t}.", "Cartellino giallo per {p}, fallo su {t}."],
        "es": ["Amarilla para {p} por la entrada sobre {t}.", "¡Tarjeta amarilla! Amonestado {p} por la falta a {t}."],
        "de": ["Gelbe Karte für {p} nach dem Foul an {t}.", "{p} sieht Gelb für das Einsteigen gegen {t}."],
    },
    "foul_red": {
        "en": ["RED CARD! {p} is sent off! {team} are down to ten.", "Straight red for {p} — {team} must play on with ten."],
        "it": ["ESPULSO! Rosso per {p}! {team} in dieci.", "Cartellino rosso per {p}: {team} resta in inferiorità numerica."],
        "es": ["¡ROJA! ¡{p} expulsado! {team} se queda con diez.", "Tarjeta roja para {p}: {team} jugará con uno menos."],
        "de": ["ROT! {p} muss vom Platz! {team} nur noch zu zehnt.", "Platzverweis für {p}: {team} in Unterzahl."],
    },
    "shot_saved": {
        "en": ["{p} shoots… saved by {gk}!", "Strike from {p}, {speed} km/h — {gk} gets down to it!",
               "{p} lets fly! Good stop from {gk}."],
        "it": ["Tira {p}… para {gk}!", "Conclusione di {p}, {speed} km/h — risponde {gk}!", "{p} ci prova! Grande parata di {gk}."],
        "es": ["Dispara {p}… ¡para {gk}!", "Remate de {p}, {speed} km/h — ¡responde {gk}!", "¡Lo intenta {p}! Buena parada de {gk}."],
        "de": ["{p} zieht ab… {gk} hält!", "Schuss von {p}, {speed} km/h — {gk} ist zur Stelle!", "{p} versucht es! Starke Parade von {gk}."],
    },
    "shot_off_target": {
        "en": ["{p} goes for goal… wide!", "{p} from distance — over the bar.", "Off target from {p}, a let-off for {opp}."],
        "it": ["{p} calcia… fuori!", "{p} da lontano — alto sopra la traversa.", "Tiro fuori misura di {p}, sospiro di sollievo per {opp}."],
        "es": ["{p} prueba… ¡fuera!", "{p} desde lejos — por encima del larguero.", "Desviado el tiro de {p}, respira {opp}."],
        "de": ["{p} schießt… vorbei!", "{p} aus der Distanz — drüber.", "Daneben von {p}, Glück für {opp}."],
    },
    "shot_blocked": {
        "en": ["{p} shoots — blocked!", "{p} winds up… charged down."],
        "it": ["Tira {p} — respinto!", "{p} calcia… ribattuto dalla difesa."],
        "es": ["Dispara {p} — ¡bloqueado!", "{p} chuta… rechaza la defensa."],
        "de": ["{p} schießt — geblockt!", "{p} zieht ab… abgeblockt."],
    },
    "goal": {
        "en": ["GOAL! {P} scores for {team}! {score_line}!", "IT'S IN! {P}! {score_line}!",
               "{P}… GOAL! What a finish — {speed} km/h into the net!"],
        "it": ["GOOOL! Segna {P} per {team}! {score_line}!", "È DENTRO! {P}! {score_line}!",
               "{P}… RETE! Che conclusione — {speed} km/h e palla in fondo al sacco!"],
        "es": ["¡GOOOL! ¡Marca {P} para {team}! ¡{score_line}!", "¡ADENTRO! ¡{P}! ¡{score_line}!",
               "¡{P}… GOL! Qué definición — ¡{speed} km/h a la red!"],
        "de": ["TOR! {P} trifft für {team}! {score_line}!", "DRIN! {P}! {score_line}!",
               "{P}… TOR! Was für ein Abschluss — {speed} km/h ins Netz!"],
    },
    "goal_for_fav": {
        "en": ["YES! GOAL! {P}! Get in! {score_line}!"],
        "it": ["SÌ! GOOOL! {P}! Che gioia! {score_line}!"],
        "es": ["¡SÍ! ¡GOOOL! ¡{P}! ¡{score_line}!"],
        "de": ["JAAA! TOR! {P}! {score_line}!"],
    },
    "goal_against_fav": {
        "en": ["Oh no… {P} scores for {team}. {score_line}."],
        "it": ["Niente da fare… segna {P} per {team}. {score_line}."],
        "es": ["No puede ser… marca {P} para {team}. {score_line}."],
        "de": ["Bitter… {P} trifft für {team}. {score_line}."],
    },
    "added_time": {
        "en": ["The fourth official's board is up: {n} minutes of added time.", "We'll have {n} added minutes."],
        "it": ["Il quarto uomo alza la lavagnetta: {n} minuti di recupero.", "Saranno {n} i minuti di recupero."],
        "es": ["El cuarto árbitro levanta el cartel: {n} minutos de añadido.", "Habrá {n} minutos de descuento."],
        "de": ["Der vierte Offizielle zeigt an: {n} Minuten Nachspielzeit.", "Es gibt {n} Minuten Nachspielzeit."],
    },
    "half_time": {
        "en": ["The whistle goes for half-time. {score_line}.", "That's the end of the first half — {score_line}."],
        "it": ["Fischio dell'arbitro: finisce il primo tempo. {score_line}.", "Si va all'intervallo: {score_line}."],
        "es": ["Final de la primera parte. {score_line}.", "Nos vamos al descanso: {score_line}."],
        "de": ["Halbzeitpfiff. {score_line}.", "Pause — {score_line}."],
    },
    "full_time_win": {
        "en": ["It's all over! {winner} win it — {score_line}!"],
        "it": ["È finita! Vince {winner}: {score_line}!"],
        "es": ["¡Se acabó! Gana {winner}: {score_line}."],
        "de": ["Aus, aus, das Spiel ist aus! {winner} gewinnt — {score_line}!"],
    },
    "full_time_draw": {
        "en": ["Full time, and they can't be separated: {score_line}."],
        "it": ["Triplice fischio: finisce in parità, {score_line}."],
        "es": ["Final del partido, reparto de puntos: {score_line}."],
        "de": ["Abpfiff, und es bleibt beim Unentschieden: {score_line}."],
    },
}

# Data tags appended in Analyst mode so the same moment reads differently per persona
DATA_TAGS = {
    "shot": {"en": " (xG {xg})", "it": " (xG {xg})", "es": " (xG {xg})", "de": " (xG {xg})"},
    "pass": {"en": " ({dist} m, difficulty {diff})", "it": " ({dist} m, difficoltà {diff})", "es": " ({dist} m, dificultad {diff})", "de": " ({dist} m, Schwierigkeit {diff})"},
}


def pick(key: str, lang: str, seed: str) -> str:
    """Deterministic but varied template choice, stable for a given event."""
    bank = PHRASES[key].get(lang) or PHRASES[key]["en"]
    return bank[zlib.crc32(seed.encode()) % len(bank)]


def score_line(facts: CommentaryFacts) -> str:
    return f"{TEAM_NAMES[HOME_ID]} {facts.score_home}–{facts.score_away} {TEAM_NAMES[AWAY_ID]}"


def phrase_key(event: MatchEvent, facts: CommentaryFacts, favourite_club: Optional[str]) -> Optional[str]:
    et = event.event_type
    if et == EventType.MATCH_START:
        return "kickoff_1" if event.period == 1 else "kickoff_2"
    if et == EventType.ADDED_TIME:
        return "added_time"
    if et == EventType.HALF_TIME:
        return "half_time"
    if et == EventType.MATCH_END:
        return "full_time_draw" if facts.score_home == facts.score_away else "full_time_win"
    if et == EventType.GOAL:
        if favourite_club in (HOME_ID, AWAY_ID):
            return "goal_for_fav" if favourite_club == event.team_id else "goal_against_fav"
        return "goal"
    if et == EventType.SHOT:
        return {"saved": "shot_saved", "off_target": "shot_off_target", "blocked": "shot_blocked"}.get(
            event.shot_outcome or "saved", "shot_saved"
        )
    if et == EventType.PASS:
        if not event.is_successful:
            return "pass_failed"
        if (event.pass_difficulty_rating or 0) >= 0.6:
            return "pass_key"
        if (event.pass_distance_m or 0) >= 30:
            return "pass_long"
        return "pass_short"
    if et == EventType.FOUL:
        return {"yellow": "foul_yellow", "red": "foul_red"}.get(event.card or "", "foul")
    if et in (EventType.TACKLE, EventType.INTERCEPTION, EventType.PRESSURE):
        return et.value
    return None


def build_facts(event: MatchEvent, player_goals: int = 0, pass_streak: int = 0) -> CommentaryFacts:
    team = TEAM_NAMES.get(event.team_id, event.team_id)
    opp_id = AWAY_ID if event.team_id == HOME_ID else HOME_ID
    gk = surname(event.target_player.name) if (event.target_player and event.shot_outcome == "saved") else None
    return CommentaryFacts(
        event_id=event.event_id,
        event_type=event.event_type.value,
        minute_label=event.match_minute_label,
        period=event.period,
        team_id=event.team_id,
        team=team,
        opponent=TEAM_NAMES[opp_id],
        player=surname(event.player.name) if event.player else None,
        player_full=event.player.name if event.player else None,
        target=surname(event.target_player.name) if event.target_player else None,
        goalkeeper=gk,
        score_home=event.score_home,
        score_away=event.score_away,
        distance_m=round(event.pass_distance_m) if event.pass_distance_m else None,
        pass_difficulty=event.pass_difficulty_rating,
        speed_kmh=round(event.shot_speed_kmh) if event.shot_speed_kmh else None,
        xg=event.expected_goals,
        shot_outcome=event.shot_outcome,
        card=event.card,
        added_minutes=event.added_time_minutes,
        player_goals=player_goals,
        pass_streak=pass_streak,
        is_successful=event.is_successful,
        control_index=event.tactical_context.control_vs_chaos_index,
        pressure_index=event.tactical_context.defensive_pressure_index,
    )


def render(key: str, facts: CommentaryFacts, lang: str, persona: str) -> str:
    winner = facts.team if facts.score_home == facts.score_away else (
        TEAM_NAMES[HOME_ID] if facts.score_home > facts.score_away else TEAM_NAMES[AWAY_ID]
    )
    values = {
        "p": facts.player or facts.team,
        "P": facts.player_full or facts.team,
        "r": facts.target or facts.team,
        "t": facts.target or facts.opponent,
        "gk": facts.goalkeeper or "",
        "team": facts.team,
        "opp": facts.opponent,
        "home": TEAM_NAMES[HOME_ID],
        "away": TEAM_NAMES[AWAY_ID],
        "score_line": score_line(facts),
        "dist": facts.distance_m or 0,
        "speed": facts.speed_kmh or 0,
        "xg": f"{facts.xg:.2f}" if facts.xg is not None else "",
        "diff": f"{facts.pass_difficulty:.2f}" if facts.pass_difficulty is not None else "",
        "n": facts.added_minutes or 0,
        "winner": winner,
    }
    text = pick(key, lang, facts.event_id).format(**values)
    if persona == "analyst":
        tag_kind = "shot" if key.startswith(("shot", "goal")) and facts.xg is not None else (
            "pass" if key in ("pass_key", "pass_long") else None
        )
        if tag_kind:
            tag = DATA_TAGS[tag_kind][lang].format(**values)
            text = text[:-1] + tag + text[-1] if text[-1] in ".!" else text + tag
    return text


def intensity_for(event: MatchEvent) -> int:
    if event.event_type in (EventType.GOAL, EventType.MATCH_END) or event.card == "red":
        return 3
    if event.event_type in KEY_EVENTS or event.card == "yellow" or (event.pass_difficulty_rating or 0) >= 0.6:
        return 2
    return 1


LANGUAGE_NAMES = {"en": "English", "it": "Italian", "es": "Spanish", "de": "German"}


def llm_prompts(facts: CommentaryFacts, lang: str, persona: str, favourite_club: Optional[str]) -> tuple[str, str]:
    style = (
        "a data-literate analyst: you may quote xG, speeds and distances from the facts"
        if persona == "analyst"
        else "a passionate TV commentator talking to casual fans: emotional, vivid, no jargon"
    )
    bias = ""
    if favourite_club in TEAM_NAMES:
        bias = f" You are calling the game for {TEAM_NAMES[favourite_club]} supporters: celebrate their moments, sound gutted at the opponent's."
    system = (
        f"You are the live play-by-play voice of a football broadcast, speaking {LANGUAGE_NAMES.get(lang, 'English')}. "
        f"Style: {style}.{bias} Write ONE line of at most 22 words describing exactly the event in FACTS. "
        "Use only names and numbers that appear in FACTS; never invent statistics, players or score changes. "
        "Do not add hashtags, emojis or quotation marks."
    )
    user = "FACTS:\n" + json.dumps(facts.model_dump(exclude_none=True), ensure_ascii=False)
    return system, user


class CommentatorAgent(BaseAgent):
    """Lead commentator: one live line per event, in the viewer's language and persona."""

    def __init__(self, foundry_client=None, name: str = "LeadCommentator"):
        super().__init__(name=name)
        self.foundry = foundry_client

    async def process(self, context: Dict[str, Any]) -> Optional[CommentaryLine]:
        event: MatchEvent = context["latest_event"]
        facts: CommentaryFacts = context["facts"]
        lang = context.get("language", "en") if context.get("language") in SUPPORTED_LANGUAGES else "en"
        persona = context.get("persona", "analyst")
        favourite_club = context.get("favourite_club")
        verifier = context.get("verifier")

        key = phrase_key(event, facts, favourite_club)
        if key is None:
            return None

        text = render(key, facts, lang, persona)
        source = "phrase-bank"

        # Spend model latency only on the moments viewers remember
        use_llm = bool(self.foundry and self.foundry.is_configured and event.event_type in KEY_EVENTS | {EventType.FOUL} and (
            event.event_type != EventType.FOUL or event.card
        ))
        if use_llm:
            context["llm_attempted"] = True
            system, user = llm_prompts(facts, lang, persona, favourite_club)
            llm_text, _trace = await self.foundry.generate_tactical_text(system, user, temperature=0.7, max_tokens=80)
            llm_text = (llm_text or "").strip().strip('"')
            if llm_text and verifier is not None:
                verdict = verifier.check_text(llm_text, facts)
                if verdict.is_grounded:
                    text, source = llm_text, "foundry-llm"
                context.setdefault("rejections", []).extend([] if verdict.is_grounded else [verdict.notes])

        return CommentaryLine(
            speaker="lead",
            text=text,
            intensity=intensity_for(event),
            language=lang,
            event_id=event.event_id,
            minute_label=event.match_minute_label,
            source=source,
        )
