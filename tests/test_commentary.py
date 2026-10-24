"""Tests for match timeline, live commentary, grounding verification and recaps."""

import pytest

from omnipitch.agents.commentary import SUPPORTED_LANGUAGES, CommentatorAgent, build_facts
from omnipitch.agents.orchestrator import MultiAgentOrchestrator
from omnipitch.agents.verifier import GroundingVerifierAgent
from omnipitch.generator.engine import MatchSimulationEngine
from omnipitch.models import EventType


def _full_match(seed: int = 42):
    return list(MatchSimulationEngine(seed=seed).play())


def test_match_has_regulation_halves_and_stoppage_time():
    events = _full_match()
    types = [e.event_type for e in events]
    assert types[0] == EventType.MATCH_START and events[0].match_clock == "00:00"
    assert types[-1] == EventType.MATCH_END

    added = [e for e in events if e.event_type == EventType.ADDED_TIME]
    assert [e.period for e in added] == [1, 2]
    assert [e.match_clock for e in added] == ["45:00", "90:00"]
    assert all(1 <= e.added_time_minutes <= 6 for e in added)

    # Nothing happens after the announced stoppage time has run out (plus a little leeway)
    for period, regulation in ((1, 45), (2, 90)):
        board = next(e for e in added if e.period == period)
        last = max((e for e in events if e.period == period), key=lambda e: e.minute * 60 + e.second)
        overrun = (last.minute * 60 + last.second) - (regulation + board.added_time_minutes) * 60
        assert 0 <= overrun <= 25

    # Clock labels follow broadcast convention in stoppage time
    stoppage = [e for e in events if e.period == 1 and e.minute >= 45 and e.event_type != EventType.ADDED_TIME]
    assert stoppage and all(e.match_clock.startswith("45+") for e in stoppage)
    assert all(e.match_minute_label.startswith("45+") for e in stoppage)


def test_match_is_deterministic_and_scores_are_consistent():
    a, b = _full_match(7), _full_match(7)
    assert [e.event_id for e in a] == [e.event_id for e in b]
    goals_home = sum(1 for e in a if e.event_type == EventType.GOAL and e.team_id == "avalon_city")
    goals_away = sum(1 for e in a if e.event_type == EventType.GOAL and e.team_id == "solaria_rovers")
    assert (a[-1].score_home, a[-1].score_away) == (goals_home, goals_away)


def test_both_teams_shoot_at_the_correct_goal():
    events = [e for seed in range(5) for e in _full_match(seed)]
    shots = [e for e in events if e.shot_outcome]
    assert {e.team_id for e in shots} == {"avalon_city", "solaria_rovers"}
    for shot in shots:
        if shot.shot_outcome in ("goal", "saved", "off_target"):
            expected_goal_line = 100.0 if shot.team_id == "avalon_city" else 0.0
            assert shot.end_coordinates.x == expected_goal_line


def test_verifier_rejects_invented_numbers_players_and_goals():
    events = _full_match()
    shot = next(e for e in events if e.event_type == EventType.SHOT and e.shot_outcome == "saved")
    facts = build_facts(shot)
    verifier = GroundingVerifierAgent()

    ok = verifier.check_text(f"{facts.player} shoots at {facts.speed_kmh} km/h, saved by {facts.goalkeeper}!", facts)
    assert ok.is_grounded and ok.claims_checked >= 3

    bad_number = verifier.check_text(f"{facts.player} shoots at 187 km/h!", facts)
    assert not bad_number.is_grounded and "187" in bad_number.notes

    outsider = next(p for p in ("Kane", "Drake", "Holt", "Price") if p not in facts.people())
    bad_player = verifier.check_text(f"{outsider} shoots!", facts)
    assert not bad_player.is_grounded

    fake_goal = verifier.check_text(f"GOAL! {facts.player}!", facts)
    assert not fake_goal.is_grounded


@pytest.mark.asyncio
@pytest.mark.parametrize("lang", SUPPORTED_LANGUAGES)
async def test_commentator_speaks_every_language_and_is_grounded(lang):
    commentator = CommentatorAgent()
    verifier = GroundingVerifierAgent()
    lines = []
    for event in _full_match():
        facts = build_facts(event)
        line = await commentator.process({"latest_event": event, "facts": facts, "language": lang, "persona": "analyst"})
        assert line is not None
        assert verifier.check_text(line.text, facts).is_grounded, line.text
        lines.append(line)
    assert all(line.language == lang for line in lines)
    assert max(line.intensity for line in lines) == 3


@pytest.mark.asyncio
async def test_personas_and_favourite_club_change_the_story():
    events = _full_match()
    goal = next(e for e in events if e.event_type == EventType.GOAL)
    facts = build_facts(goal)
    commentator = CommentatorAgent()

    neutral = await commentator.process({"latest_event": goal, "facts": facts, "language": "en", "persona": "analyst"})
    rival = "solaria_rovers" if goal.team_id == "avalon_city" else "avalon_city"
    partisan_for = await commentator.process({"latest_event": goal, "facts": facts, "language": "en",
                                              "persona": "fan", "favourite_club": goal.team_id})
    partisan_against = await commentator.process({"latest_event": goal, "facts": facts, "language": "en",
                                                  "persona": "fan", "favourite_club": rival})
    assert "xG" in neutral.text
    assert "YES" in partisan_for.text
    assert "Oh no" in partisan_against.text


@pytest.mark.asyncio
async def test_orchestrator_full_match_is_fully_grounded_with_recap():
    orchestrator = MultiAgentOrchestrator()
    for event in MatchSimulationEngine(seed=3).play():
        overlay = await orchestrator.process_event(event, persona="analyst", language="de")
        assert overlay.generated_by == "omnipitch-multiagent"
        assert [t["agent"] for t in overlay.agent_trace][:2] == ["ingest", "tactical_analyst"]

    telemetry = orchestrator.telemetry()
    assert telemetry["claims_rejected"] == 0 and telemetry["grounding_rate"] == 1.0

    recap = await orchestrator.build_recap("full_time", "de", "analyst")
    assert recap.kind == "full_time" and recap.language == "de"
    xg = recap.stats["xg"]
    assert f"{xg['home']:.2f}" in recap.paragraphs[0] and f"{xg['away']:.2f}" in recap.paragraphs[0]
    assert recap.player_of_the_match is not None
