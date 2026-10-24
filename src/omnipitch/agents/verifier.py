"""Grounding Verifier Agent: anti-hallucination fact checking against raw event evidence."""

import re
from typing import Any, Dict, Iterable, List, Optional, Set

from omnipitch.agents.base import BaseAgent, NarrativeDraft, VerificationResult
from omnipitch.agents.commentary import CommentaryFacts
from omnipitch.generator.teams import create_fictitious_teams
from omnipitch.models import EventType, MatchEvent

NUMBER_RE = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)?")
# Upper-case goal calls in the four supported languages ("goes for goal" is fine, "GOAL!" is a claim)
GOAL_CALL_RE = re.compile(r"\b(GOA+L|GO+L|RETE|TOR)\b")

ROSTER_SURNAMES = sorted({p.name.split(" ")[-1] for t in create_fictitious_teams() for p in t.players})

_NUM = r"(\d+(?:[.,]\d+)?)"
# Unit- and label-aware claims: the number next to a label must be *that* fact, not just any known number
LABELLED_CLAIMS = {
    "xg": [re.compile(rf"xG\s+{_NUM}"), re.compile(rf"{_NUM}\s*(?:-\s*)?xG")],
    "speed": [re.compile(rf"{_NUM}\s*km/h")],
    "distance": [re.compile(rf"{_NUM}\s*(?:m\b|metres|meters|metri|metros|Meter)")],
    "percent": [re.compile(rf"{_NUM}\s*%")],
    "control": [re.compile(rf"(?:control index|indice di controllo|índice de control|Kontrollindex)\s+{_NUM}", re.I)],
    "pressure": [re.compile(rf"(?:pressure index|indice di pressione|índice de presión|Pressingindex)\s+{_NUM}", re.I)],
}


def _num(raw: str) -> float:
    return float(raw.replace(",", "."))


def _is_int_literal(raw: str) -> bool:
    return "." not in raw and "," not in raw


# Integer pairs such as a scoreline "2–1" / "2:1" or "shots 5–10" (decimals and percentages excluded)
PAIR_RE = re.compile(r"(?<![\d.,])(\d+)\s*[–:]\s*(\d+)(?![\d.,%])")


def _matches(value: float, allowed: Iterable[float], literal_is_int: bool = True) -> bool:
    # Rounding and percentage rules only apply to whole numbers written without decimals
    is_int = literal_is_int and float(value).is_integer()
    for a in allowed:
        a = float(a)
        if abs(value - a) <= 0.005:
            return True
        # A fraction may be quoted as a whole percentage (0.56 -> 56)
        if is_int and 0 < a < 1 and value == round(a * 100):
            return True
        # Values shown rounded to a whole number (98.4 km/h -> 98)
        if is_int and not float(a).is_integer() and value == round(a):
            return True
    return False


class GroundingVerifierAgent(BaseAgent):
    """
    Audits every generated sentence against ground truth before it reaches air:
    1. Every cited event ID exists in the match registry.
    2. Labelled numbers (xG, km/h, metres, %, control / pressure index) equal the matching fact.
    3. Every other number is backed by the event facts or the shared blackboard.
    4. Every player named was involved in the cited events.
    5. A goal is only called when the evidence contains a goal.
    """

    def __init__(self, name: str = "GroundingVerifier"):
        super().__init__(name=name)

    @staticmethod
    def _label_sets(facts: Optional[CommentaryFacts], state: Optional[Dict[str, Any]]) -> Dict[str, Set[float]]:
        sets: Dict[str, Set[float]] = {k: set() for k in LABELLED_CLAIMS}
        if facts is not None:
            for key, value in (("xg", facts.xg), ("speed", facts.speed_kmh), ("distance", facts.distance_m),
                               ("control", facts.control_index), ("pressure", facts.pressure_index)):
                if value is not None:
                    sets[key].add(value)
        if state:
            sets["xg"] |= {state.get("home_xg", 0.0), state.get("away_xg", 0.0)}
            sets["percent"] |= {state.get("poss_home", 50), state.get("poss_away", 50)}
        return sets

    def check_text(
        self,
        text: str,
        facts: Optional[CommentaryFacts] = None,
        extra_numbers: Iterable[float] = (),
        allowed_people: Iterable[str] = (),
        allow_goal_call: Optional[bool] = None,
        state: Optional[Dict[str, Any]] = None,
    ) -> VerificationResult:
        # Laws-of-the-game constants (two 45-minute halves) are always fair to mention
        allowed_numbers: List[float] = [45, 90, *extra_numbers]
        people = {p.lower() for p in allowed_people}
        if facts is not None:
            allowed_numbers += facts.numbers()
            people |= {p.lower() for name in facts.people() for p in name.split(" ")}
            if allow_goal_call is None:
                allow_goal_call = facts.event_type == EventType.GOAL.value

        claims = 0
        rejected: List[str] = []
        consumed: Set[int] = set()

        # 1. Labelled claims must match their own fact exactly
        label_sets = self._label_sets(facts, state)
        for label, patterns in LABELLED_CLAIMS.items():
            for pattern in patterns:
                for m in pattern.finditer(text):
                    start = m.start(1)
                    if start in consumed:
                        continue
                    consumed.add(start)
                    claims += 1
                    # When the fact behind a label is unknown here, fall back to the evidence pool
                    pool = label_sets[label] or allowed_numbers
                    if not _matches(_num(m.group(1)), pool, literal_is_int=_is_int_literal(m.group(1))):
                        rejected.append(f"{label} '{m.group(1)}' does not match the evidence")

        # 1b. Integer pairs must be a real pair (score, shots) rather than two unrelated numbers
        pairs = set()
        if facts is not None:
            pairs.add((facts.score_home, facts.score_away))
        if state:
            pairs.add((state.get("home_shots", 0), state.get("away_shots", 0)))
        for m in PAIR_RE.finditer(text):
            if m.start(1) in consumed or not pairs:
                continue
            consumed.update({m.start(1), m.start(2)})
            claims += 1
            if (int(m.group(1)), int(m.group(2))) not in pairs:
                rejected.append(f"pair '{m.group(1)}–{m.group(2)}' matches no score or shot count")

        # 2. Every other number must exist in the evidence
        for m in NUMBER_RE.finditer(text):
            if m.start() in consumed:
                continue
            claims += 1
            if not _matches(_num(m.group(0)), allowed_numbers, literal_is_int=_is_int_literal(m.group(0))):
                rejected.append(f"number '{m.group(0)}' has no evidence")

        # 3. Named players must be part of the cited sequence
        for name in ROSTER_SURNAMES:
            if re.search(rf"\b{re.escape(name)}\b", text):
                claims += 1
                if name.lower() not in people:
                    rejected.append(f"player '{name}' not involved in cited events")

        # 4. No goal calls without a goal
        if not allow_goal_call and GOAL_CALL_RE.search(text):
            claims += 1
            rejected.append("goal called without a goal in evidence")

        return VerificationResult(
            is_grounded=not rejected,
            confidence=1.0 if not rejected else 0.1,
            verified_event_ids=[facts.event_id] if facts else [],
            notes="All claims verified against telemetry evidence." if not rejected else "; ".join(rejected),
            claims_checked=claims,
            rejected_claims=rejected,
        )

    async def process(self, context: Dict[str, Any]) -> VerificationResult:
        draft: NarrativeDraft = context["narrative_draft"]
        events: List[MatchEvent] = context.get("all_events", [])
        facts: Optional[CommentaryFacts] = context.get("facts")
        state_numbers: Iterable[float] = context.get("state_numbers", ())
        state: Optional[Dict[str, Any]] = context.get("match_state")

        if not events or not draft.cited_event_ids:
            return VerificationResult(
                is_grounded=False,
                confidence=0.0,
                verified_event_ids=[],
                notes="Missing raw events or draft has no cited event IDs.",
            )

        event_lookup = {e.event_id: e for e in events}
        missing = [eid for eid in draft.cited_event_ids if eid not in event_lookup]
        if missing:
            return VerificationResult(
                is_grounded=False,
                confidence=0.1,
                verified_event_ids=[eid for eid in draft.cited_event_ids if eid in event_lookup],
                notes=f"Hallucination detected: cited event(s) {', '.join(missing)} not in the match registry.",
                rejected_claims=[f"unknown event {eid}" for eid in missing],
            )

        # People involved in the cited sequence, plus the event's own facts
        people: List[str] = []
        goal_cited = False
        for eid in draft.cited_event_ids:
            ev = event_lookup[eid]
            goal_cited |= ev.event_type == EventType.GOAL
            for p in (ev.player, ev.target_player):
                if p:
                    people += p.name.split(" ")

        result = self.check_text(
            f"{draft.headline}. {draft.commentary}",
            facts=facts,
            extra_numbers=state_numbers,
            allowed_people=people,
            allow_goal_call=goal_cited or (facts is not None and facts.event_type == EventType.GOAL.value),
            state=state,
        )
        result.verified_event_ids = list(draft.cited_event_ids) if result.is_grounded else []
        return result
