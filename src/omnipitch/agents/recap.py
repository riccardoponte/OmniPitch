"""Recap Agent: automated half-time and full-time match reports."""

import json
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field

from omnipitch.agents.base import BaseAgent
from omnipitch.agents.commentary import AWAY_ID, HOME_ID, LANGUAGE_NAMES, SUPPORTED_LANGUAGES, TEAM_NAMES


class MatchRecap(BaseModel):
    """Studio-ready recap, grounded in the event log."""
    kind: str = Field(..., description="'half_time' or 'full_time'")
    language: str
    persona: str
    title: str
    standfirst: str
    paragraphs: List[str]
    key_moments: List[Dict[str, Any]]
    player_of_the_match: Optional[Dict[str, Any]] = None
    stats: Dict[str, Any] = Field(default_factory=dict)
    evidence_event_ids: List[str] = Field(default_factory=list)
    source: str = "phrase-bank"
    verification: Optional[Dict[str, Any]] = None


T = {
    "title_win": {"en": "{winner} beat {loser} {sw}–{sl}", "it": "{winner} batte {loser} {sw}–{sl}",
                  "es": "{winner} vence a {loser} por {sw}–{sl}", "de": "{winner} schlägt {loser} {sw}:{sl}"},
    "title_draw": {"en": "{home} and {away} draw {sh}–{sa}", "it": "{home} e {away} pareggiano {sh}–{sa}",
                   "es": "{home} y {away} empatan {sh}–{sa}", "de": "{home} und {away} trennen sich {sh}:{sa}"},
    "title_half": {"en": "Half-time: {home} {sh}–{sa} {away}", "it": "Primo tempo: {home} {sh}–{sa} {away}",
                   "es": "Descanso: {home} {sh}–{sa} {away}", "de": "Halbzeit: {home} {sh}:{sa} {away}"},
    "xg_line": {"en": "On expected goals it reads {home} {hxg} – {axg} {away}: {verdict}.",
                "it": "Sugli expected goals siamo a {home} {hxg} – {axg} {away}: {verdict}.",
                "es": "En goles esperados: {home} {hxg} – {axg} {away}; {verdict}.",
                "de": "Nach Expected Goals steht es {home} {hxg} – {axg} {away}: {verdict}."},
    "v_deserved": {"en": "a scoreline the chances back up", "it": "risultato confermato dalle occasioni",
                   "es": "un marcador que avalan las ocasiones", "de": "ein Ergebnis, das die Chancen bestätigen"},
    "v_clinical": {"en": "{leader} have been more clinical than their chances suggest",
                   "it": "{leader} è stata più cinica di quanto dicano le occasioni",
                   "es": "{leader} ha sido más eficaz de lo que dicen las ocasiones",
                   "de": "{leader} war effizienter, als die Chancen vermuten lassen"},
    "v_fair": {"en": "a fair reflection of the game", "it": "un equilibrio che rispecchia la gara",
               "es": "un reflejo justo del partido", "de": "ein gerechtes Spiegelbild der Partie"},
    "v_unlucky": {"en": "{better} can feel hard done by", "it": "{better} può recriminare",
                  "es": "{better} puede sentirse perjudicado", "de": "{better} darf sich benachteiligt fühlen"},
    "numbers": {"en": "Possession {ph}%–{pa}%, shots {hs}–{as} ({hot}–{aot} on target), pass accuracy {hpa}%–{apa}%.",
                "it": "Possesso {ph}%–{pa}%, tiri {hs}–{as} ({hot}–{aot} in porta), precisione passaggi {hpa}%–{apa}%.",
                "es": "Posesión {ph}%–{pa}%, tiros {hs}–{as} ({hot}–{aot} a puerta), precisión de pase {hpa}%–{apa}%.",
                "de": "Ballbesitz {ph}%–{pa}%, Schüsse {hs}–{as} ({hot}–{aot} aufs Tor), Passquote {hpa}%–{apa}%."},
    "potm": {"en": "Player of the match: {name} ({team}), rated {rating}{extra}.",
             "it": "Migliore in campo: {name} ({team}), voto {rating}{extra}.",
             "es": "Jugador del partido: {name} ({team}), nota {rating}{extra}.",
             "de": "Spieler des Spiels: {name} ({team}), Note {rating}{extra}."},
    "potm_goals": {"en": ", with {g} goal(s)", "it": ", con {g} gol", "es": ", con {g} gol(es)", "de": ", mit {g} Tor(en)"},
    "potm_half": {"en": "Standout so far: {name} ({team}), rated {rating}{extra}.",
                  "it": "Il migliore finora: {name} ({team}), voto {rating}{extra}.",
                  "es": "El mejor hasta ahora: {name} ({team}), nota {rating}{extra}.",
                  "de": "Bester Mann bisher: {name} ({team}), Note {rating}{extra}."},
    "moments_intro": {"en": "Key moments:", "it": "Momenti chiave:", "es": "Momentos clave:", "de": "Schlüsselmomente:"},
    "no_moments": {"en": "No goals or red cards — a game decided in the margins.",
                   "it": "Nessun gol né espulsione: una partita decisa dai dettagli.",
                   "es": "Sin goles ni expulsiones: un partido de detalles.",
                   "de": "Keine Tore, keine Platzverweise — ein Spiel der Kleinigkeiten."},
    "goal": {"en": "Goal", "it": "Gol", "es": "Gol", "de": "Tor"},
    "red_card": {"en": "Red card", "it": "Espulsione", "es": "Roja", "de": "Rote Karte"},
    "fan_win": {"en": "What a game! {winner} take it {sw}–{sl} and the fans go home happy.",
                "it": "Che partita! {winner} la porta a casa {sw}–{sl} e i tifosi festeggiano.",
                "es": "¡Qué partido! {winner} se lo lleva {sw}–{sl} y su afición lo celebra.",
                "de": "Was für ein Spiel! {winner} gewinnt {sw}:{sl} und die Fans feiern."},
    "fan_draw": {"en": "Honours even at {sh}–{sa} — nobody could land the knockout blow.",
                 "it": "Finisce {sh}–{sa}, nessuno riesce a dare il colpo del ko.",
                 "es": "Tablas a {sh}–{sa}: nadie pudo dar el golpe definitivo.",
                 "de": "{sh}:{sa} — keiner konnte den entscheidenden Schlag setzen."},
    "fan_half": {"en": "Half-time and it's {home} {sh}–{sa} {away}. Grab a drink — there's a lot still to come.",
                 "it": "Intervallo sul {sh}–{sa} tra {home} e {away}. C'è ancora tanto da vedere.",
                 "es": "Descanso con {home} {sh}–{sa} {away}. Queda mucho por ver.",
                 "de": "Halbzeit, {home} {sh}:{sa} {away}. Da kommt noch einiges."},
    "stand_full": {"en": "Full time at the Aethelgard Arena after {minute} of football.",
                   "it": "Triplice fischio all'Aethelgard Arena dopo {minute} di gioco.",
                   "es": "Final en el Aethelgard Arena tras {minute} de juego.",
                   "de": "Abpfiff in der Aethelgard Arena nach {minute} Spielzeit."},
    "stand_half": {"en": "First half over at {minute}.",
                   "it": "Primo tempo concluso al {minute}.",
                   "es": "Primera parte terminada en el {minute}.",
                   "de": "Erste Halbzeit beendet nach {minute}."},
}


def t(key: str, lang: str, **values) -> str:
    return T[key].get(lang, T[key]["en"]).format(**values)


class RecapAgent(BaseAgent):
    """Writes the half-time and full-time report from the shared blackboard."""

    def __init__(self, foundry_client=None, name: str = "MatchRecapWriter"):
        super().__init__(name=name)
        self.foundry = foundry_client

    @staticmethod
    def gather(overview: Dict[str, Any], kind: str) -> Dict[str, Any]:
        stats = overview["comparison_stats"]
        status = overview["status"]
        moments = [m for m in overview["timeline"] if m["type"] in ("goal", "red_card")]
        lineup = overview["lineups"]["home"] + overview["lineups"]["away"]
        potm = next((p for p in lineup if p.get("is_mvp")), None)
        return {"stats": stats, "status": status, "moments": moments, "potm": potm, "kind": kind}

    def compose(self, data: Dict[str, Any], lang: str, persona: str) -> MatchRecap:
        stats, status, kind = data["stats"], data["status"], data["kind"]
        sh, sa = status["score"]["home"], status["score"]["away"]
        home, away = TEAM_NAMES[HOME_ID], TEAM_NAMES[AWAY_ID]
        hxg, axg = stats["expected_goals"]["home"], stats["expected_goals"]["away"]

        if sh == sa:
            winner = loser = None
        else:
            winner, loser = (home, away) if sh > sa else (away, home)
        sw, sl = max(sh, sa), min(sh, sa)

        if kind == "half_time":
            title = t("title_half", lang, home=home, away=away, sh=sh, sa=sa)
        elif winner:
            title = t("title_win", lang, winner=winner, loser=loser, sw=sw, sl=sl)
        else:
            title = t("title_draw", lang, home=home, away=away, sh=sh, sa=sa)

        # Did the scoreline follow the chances?
        better = home if hxg > axg else away
        if winner:
            winner_xg = hxg if winner == home else axg
            loser_xg = axg if winner == home else hxg
            verdict = t("v_deserved", lang) if winner_xg >= loser_xg else t("v_clinical", lang, leader=winner)
        else:
            verdict = t("v_fair", lang) if abs(hxg - axg) < 0.4 else t("v_unlucky", lang, better=better)

        moment_lines = []
        for m in data["moments"]:
            label = t("goal" if m["type"] == "goal" else "red_card", lang)
            name = m["title"].split("—")[-1].strip()
            team = TEAM_NAMES.get(m["team_id"], "")
            moment_lines.append({**m, "text": f"{m['minute_label']} {label}: {name} ({team})"})

        potm = data["potm"]
        potm_line = None
        if potm:
            extra = t("potm_goals", lang, g=potm["goals"]) if potm["goals"] else ""
            potm_line = t("potm_half" if kind == "half_time" else "potm", lang, name=potm["name"],
                          team=TEAM_NAMES.get(potm["team_id"], ""), rating=f"{potm['rating']:.1f}", extra=extra)

        numbers = t("numbers", lang, ph=round(stats["possession"]["home"]), pa=round(stats["possession"]["away"]),
                    hs=stats["total_shots"]["home"], **{"as": stats["total_shots"]["away"]},
                    hot=stats["shots_on_target"]["home"], aot=stats["shots_on_target"]["away"],
                    hpa=round(stats["pass_accuracy_pct"]["home"]), apa=round(stats["pass_accuracy_pct"]["away"]))
        xg_line = t("xg_line", lang, home=home, away=away, hxg=f"{hxg:.2f}", axg=f"{axg:.2f}", verdict=verdict)

        moments_par = (t("moments_intro", lang) + " " + "; ".join(m["text"] for m in moment_lines) + ".") \
            if moment_lines else t("no_moments", lang)

        if persona == "fan":
            lead = t("fan_half", lang, home=home, away=away, sh=sh, sa=sa) if kind == "half_time" else (
                t("fan_win", lang, winner=winner, sw=sw, sl=sl) if winner else t("fan_draw", lang, sh=sh, sa=sa))
            paragraphs = [lead, moments_par] + ([potm_line] if potm_line else [])
        else:
            paragraphs = [xg_line, moments_par, numbers] + ([potm_line] if potm_line else [])

        stand = t("stand_half" if kind == "half_time" else "stand_full", lang,
                  minute=status["minute_label"] or "90'", n=len(moment_lines))

        return MatchRecap(
            kind=kind,
            language=lang,
            persona=persona,
            title=title,
            standfirst=stand,
            paragraphs=paragraphs,
            key_moments=moment_lines,
            player_of_the_match=potm,
            stats={
                "score": {"home": sh, "away": sa},
                "xg": {"home": hxg, "away": axg},
                "shots": stats["total_shots"],
                "on_target": stats["shots_on_target"],
                "possession": stats["possession"],
                "pass_accuracy": stats["pass_accuracy_pct"],
            },
            evidence_event_ids=[m["event_id"] for m in moment_lines],
        )

    @staticmethod
    def grounding(recap: MatchRecap, data: Dict[str, Any]) -> tuple[List[float], List[str]]:
        """Numbers and names a recap may contain."""
        numbers: List[float] = []
        def collect(obj):
            if isinstance(obj, bool):
                return
            if isinstance(obj, (int, float)):
                numbers.append(obj)
            elif isinstance(obj, dict):
                for v in obj.values():
                    collect(v)
            elif isinstance(obj, list):
                for v in obj:
                    collect(v)
            elif isinstance(obj, str):
                for part in obj.replace("'", "").replace("+", " ").replace("(", " ").replace("%", " ").split():
                    try:
                        numbers.append(float(part))
                    except ValueError:
                        pass
        collect(data["stats"])
        collect(data["status"])
        collect(data["moments"])
        collect(data["potm"] or {})
        people: List[str] = []
        for m in data["moments"]:
            people += m["title"].split("—")[-1].split()
        if data["potm"]:
            people += data["potm"]["name"].split()
        return numbers, people

    async def process(self, context: Dict[str, Any]) -> MatchRecap:
        overview: Dict[str, Any] = context["overview"]
        kind: str = context.get("kind", "full_time")
        lang = context.get("language", "en") if context.get("language") in SUPPORTED_LANGUAGES else "en"
        persona = context.get("persona", "analyst")
        verifier = context.get("verifier")

        data = self.gather(overview, kind)
        recap = self.compose(data, lang, persona)

        if self.foundry and self.foundry.is_configured and verifier is not None:
            system = (
                f"You are a football journalist writing a {'half-time' if kind == 'half_time' else 'full-time'} report in "
                f"{LANGUAGE_NAMES.get(lang, 'English')} for {'data-savvy analysts' if persona == 'analyst' else 'casual fans'}. "
                "Write two short paragraphs, at most 110 words in total, using ONLY the names and numbers in FACTS. "
                "Explain why the result happened, not just what happened. No headings, no bullet points."
            )
            facts = {"recap_draft": recap.model_dump(include={"title", "paragraphs"}), **data}
            text, _trace = await self.foundry.generate_tactical_text(
                system, "FACTS:\n" + json.dumps(facts, ensure_ascii=False, default=str), temperature=0.5, max_tokens=320
            )
            if text:
                numbers, people = self.grounding(recap, data)
                verdict = verifier.check_text(text, extra_numbers=numbers, allowed_people=people,
                                              allow_goal_call=bool(data["moments"]))
                recap.verification = verdict.model_dump()
                if verdict.is_grounded:
                    recap.paragraphs = [p.strip() for p in text.strip().split("\n") if p.strip()]
                    recap.source = "foundry-llm"
        return recap
