"""
Grounding evaluation for the OmniPitch Grounding Verifier.

1. Faithful set: every commentary line and on-screen explanation produced over
   several full matches, in all four languages and both personas. The verifier
   should accept all of them (false-rejection rate).
2. Adversarial set: the same texts with one injected hallucination each —
   a changed number, a player who was not involved, or a goal call on a non-goal.
   The verifier should reject all of them (detection rate).

Run:  python foundry/evaluations/run_grounding_eval.py [--seeds 10]
Writes foundry/evaluations/grounding_eval_results.json
"""

import argparse
import asyncio
import json
import random
import re
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))

from omnipitch.agents.commentary import SUPPORTED_LANGUAGES, CommentatorAgent, build_facts  # noqa: E402
from omnipitch.agents.memory import MatchBlackboardMemory  # noqa: E402
from omnipitch.agents.narrator import NarratorAgent  # noqa: E402
from omnipitch.agents.tactical_analyst import TacticalAnalystAgent  # noqa: E402
from omnipitch.agents.verifier import ROSTER_SURNAMES, GroundingVerifierAgent  # noqa: E402
from omnipitch.generator.engine import MatchSimulationEngine  # noqa: E402

GOAL_CALLS = {"en": "GOAL! ", "it": "GOOOL! ", "es": "¡GOL! ", "de": "TOR! "}
NUMBER_RE = re.compile(r"(?<![\w.])\d+(?:[.,]\d+)?")


def perturb_number(text: str, rng: random.Random):
    nums = list(NUMBER_RE.finditer(text))
    if not nums:
        return None
    m = rng.choice(nums)
    raw = m.group(0)
    if "." in raw:
        new = f"{float(raw) + rng.choice([0.17, 0.23, 0.31]):.2f}"
    else:
        new = str(int(raw) + rng.choice([13, 17, 29]))
    return text[:m.start()] + new + text[m.end():]


def perturb_player(text: str, involved: set, rng: random.Random):
    named = [s for s in ROSTER_SURNAMES if re.search(rf"\b{s}\b", text)]
    outsiders = [s for s in ROSTER_SURNAMES if s.lower() not in involved]
    if not named or not outsiders:
        return None
    return re.sub(rf"\b{rng.choice(named)}\b", rng.choice(outsiders), text, count=1)


async def collect(seed: int, lang: str, persona: str):
    """Yields (text, facts, state_numbers, involved_people, is_goal, state) for one simulated match."""
    engine = MatchSimulationEngine(seed=seed)
    memory = MatchBlackboardMemory()
    analyst, narrator, commentator = TacticalAnalystAgent(), NarratorAgent(), CommentatorAgent()
    window = []
    for event in engine.play():
        memory.record_event(event)
        window = (window + [event])[-5:]
        state = memory.match_state()
        facts = build_facts(event)
        report = await analyst.process({"recent_events": window})
        draft = await narrator.process({"tactical_report": report, "latest_event": event, "match_state": state,
                                        "persona": persona, "language": lang})
        line = await commentator.process({"latest_event": event, "facts": facts, "language": lang, "persona": persona})
        people = {n.lower() for e in window for p in (e.player, e.target_player) if p for n in p.name.split()}
        numbers = MatchBlackboardMemory.state_numbers(state)
        is_goal = event.event_type.value == "goal"
        if line:
            yield line.text, facts, [], people | {n.lower() for n in facts.people()}, is_goal, None
        yield f"{draft.headline}. {draft.commentary}", facts, numbers, people, is_goal, state


async def main(seeds: int):
    verifier = GroundingVerifierAgent()
    rng = random.Random(2026)
    totals = defaultdict(lambda: {"cases": 0, "flagged": 0})
    by_language = defaultdict(lambda: {"faithful": 0, "false_rejections": 0})
    examples = []

    for seed in range(1, seeds + 1):
        for lang in SUPPORTED_LANGUAGES:
            for persona in ("analyst", "fan"):
                async for text, facts, numbers, people, is_goal, state in collect(seed, lang, persona):
                    def check(t):
                        return verifier.check_text(t, facts, extra_numbers=numbers, allowed_people=people,
                                                   allow_goal_call=is_goal, state=state)

                    ok = check(text)
                    totals["faithful"]["cases"] += 1
                    by_language[lang]["faithful"] += 1
                    if not ok.is_grounded:
                        totals["faithful"]["flagged"] += 1
                        by_language[lang]["false_rejections"] += 1
                        examples.append({"kind": "false_rejection", "text": text, "notes": ok.notes})

                    for kind, bad in (
                        ("wrong_number", perturb_number(text, rng)),
                        ("wrong_player", perturb_player(text, people, rng)),
                        ("fake_goal", None if is_goal else GOAL_CALLS[lang] + text),
                    ):
                        if bad is None or bad == text:
                            continue
                        verdict = check(bad)
                        totals[kind]["cases"] += 1
                        if not verdict.is_grounded:
                            totals[kind]["flagged"] += 1
                        elif len(examples) < 40:
                            examples.append({"kind": f"missed_{kind}", "text": bad})

    faithful = totals["faithful"]
    adversarial = {k: v for k, v in totals.items() if k != "faithful"}
    caught = sum(v["flagged"] for v in adversarial.values())
    injected = sum(v["cases"] for v in adversarial.values())
    results = {
        "matches_simulated": seeds * len(SUPPORTED_LANGUAGES) * 2,
        "faithful_texts": faithful["cases"],
        "false_rejection_rate": round(faithful["flagged"] / max(faithful["cases"], 1), 4),
        "hallucinations_injected": injected,
        "detection_rate": round(caught / max(injected, 1), 4),
        "detection_by_type": {k: round(v["flagged"] / max(v["cases"], 1), 4) for k, v in adversarial.items()},
        "cases_by_type": {k: v["cases"] for k, v in adversarial.items()},
        "faithful_by_language": dict(by_language),
        "examples": examples[:20],
    }
    out = Path(__file__).with_name("grounding_eval_results.json")
    out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps({k: v for k, v in results.items() if k != "examples"}, indent=2))
    print(f"\nWritten to {out}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=10)
    asyncio.run(main(parser.parse_args().seeds))
