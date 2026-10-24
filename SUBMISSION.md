# OmniPitch — Submission Kit

Everything needed for the project page on the Hackathon Website. Submission deadline: **27 October 2026, 11:59 PM PT**.

---

## Project name
OmniPitch — live match intelligence, written by agents and fact-checked before it reaches air

## Elevator pitch (≈120 words)
Football stories don't start and end with the scoreline. OmniPitch turns a live stream of synthetic match events into a complete broadcast: spoken play-by-play in English, Italian, Spanish or German, a co-commentator who explains *why* each moment matters, a tactical match centre, and automated half-time and full-time reports. Eight specialised agents share one blackboard; the commentator and recap writer call a Microsoft Foundry model only on the moments that matter, and a Grounding Verifier checks every number and every name against the event log before anything airs — catching 99.8 % of injected hallucinations with zero false rejections. Viewers choose analyst or fan voice, their language, their club and their player; external agents such as GitHub Copilot can query the live match over MCP.

## What we built
- Deterministic synthetic match engine with real match structure: kick-off, two halves, announced stoppage time, half-time, final whistle; passes (completed/lost), shots (goal/saved/off target/blocked), tackles, interceptions, pressing, fouls, yellow and red cards; xG, pass difficulty, ball and shot speed, sprint detection.
- Multi-agent pipeline on a shared blackboard: Ingest → Tactical Analyst → Lead Commentator → Narrator → Player Focus → Grounding Verifier → Broadcast, plus a Recap Writer.
- Live commentary in four languages with speech synthesis (two voices), favourite-club bias, analyst/fan personas.
- Broadcast dashboard: animated pitch, lower third with evidence IDs, per-agent latency, attack momentum with stoppage time, statistics, ratings, shot map, timeline, event data, Teams Adaptive Cards.
- MCP server (official SDK) over the live match; grounding evaluation harness with measured results.

## Microsoft & Azure technologies
Microsoft Foundry (Azure OpenAI deployment), Model Context Protocol with GitHub Copilot Agent Mode, Azure Container Apps, Azure Event Hubs, Application Insights / Log Analytics, Microsoft Fabric (Delta-ready exports), Power Automate + Microsoft Teams Adaptive Cards, GitHub Actions, Bicep.

## Problem it solves
Broadcasters and streaming platforms need commentary and graphics for every market, every language and every kind of fan — instantly, and without inventing facts. Generative AI writes fluently but hallucinates; rules-based graphics are accurate but generic. OmniPitch combines both: models write where they add value, a verifier guarantees every claim is in the data, and the same intelligence becomes a different experience for an analyst in Berlin and a casual fan in Milan.

## Categories
- Grand Prize (complete pipeline: ingest → interpret → explain → render → personalize)
- Best Multi-Agent System (distinct roles, shared state, handoffs, verifier gate, fallback recovery)

---

## Testing instructions (for judges)

**Hosted demo:** `<paste the Azure Container Apps URL here>` — no login required.

1. Open the URL. In the control strip choose *Commentary* = Italiano, *Your club* = Avalon City, *View* = Fan, *Pace* = 2×.
2. Click the speaker button to turn the voice on, then **Kick off**.
3. Watch the *Live commentary* panel and listen; goals and cards are called with emphasis, and the co-commentator explains them.
4. At half-time the broadcast pauses and the half-time report opens. Close it and press **Second half**.
5. During play, open *Match centre → Agents & workflows* to see live agent latency and the verifier's running totals.
6. At the final whistle the full-time report opens; *Read aloud* speaks it.
7. Optional: connect an MCP client to `<URL>/mcp/` and call `get_match_state` or `explain_moment` with an event ID from the feed.

**Run locally:** `pip install -e ".[dev]"` then `uvicorn omnipitch.api:app --port 8000` (Python 3.10+). Tests: `pytest -q`. Grounding evaluation: `python foundry/evaluations/run_grounding_eval.py`.

**Platform:** desktop or mobile browser (Chrome/Edge recommended for speech voices).

---

## Demo video

A finished cut (1:41, 1080p, English voice-over, burned-in English captions) is produced by the scripts in `demo_video/`:
`narration.py` (voice-over), `record.py` (Playwright drives a real seeded match), `cards.py` (title, closing and a live MCP call), `edit.py` (ffmpeg edit). Output: `demo_video/OmniPitch_demo.mp4` (not committed).

### Original script (target 1:50, must stay under 2:00)

No copyrighted music; use the app's own whistle and the synthetic commentary voice.

| Time | On screen | Voice-over |
| --- | --- | --- |
| 0:00–0:08 | Scoreboard, press **Kick off** (English, Analyst, 2×) | "Football stories don't end at the scoreline. This is OmniPitch." |
| 0:08–0:28 | Pitch animating, live commentary panel scrolling, voice on | "Eight agents turn every synthetic event into live commentary — in four languages, spoken — and explain why each moment matters." |
| 0:28–0:45 | Switch to Italiano + Fan + Avalon City; a goal is called in Italian with the partisan line | "Same match, different fan: Italian, casual, and on Avalon's side." |
| 0:45–1:02 | Pipeline bar with per-agent ms; JSON inspector with evidence IDs; Agents tab telemetry | "Every number and name is checked against the event log before it airs. In our evaluation the verifier caught 99.8 % of injected hallucinations, with zero false alarms." |
| 1:02–1:15 | Board shows +3, clock 45+2, half-time pause and report | "Real match time — stoppage time, half-time, and an automated report at the break." |
| 1:15–1:30 | Momentum chart (stoppage shaded), timeline, shot map | "Analysts get momentum, xG, ratings and a shot map, all from the same blackboard." |
| 1:30–1:42 | VS Code: Copilot Agent Mode asks "Why did the last goal matter?" → `explain_moment` via MCP | "And any agent — like GitHub Copilot — can query the live match over MCP." |
| 1:42–1:52 | Full-time report; closing card: Foundry · MCP · Container Apps · Event Hubs · Fabric · Teams | "Built on Microsoft Foundry and Azure. OmniPitch — every match, made for every fan." |

Upload to YouTube or Vimeo as public/unlisted and paste the URL on the project page.

---

## Pre-submission checklist
- [ ] GitHub repository is **public** and contains this branch merged into `main`
- [ ] Hosted demo URL works in a private window
- [ ] Video under 2:00, public URL, no third-party trademarks or copyrighted music
- [ ] Project page: description, technologies, repo URL, video URL, testing instructions
- [ ] All submission text in English
