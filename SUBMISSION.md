# OmniPitch — Submission Kit

Everything needed for the project page on the Hackathon Website. Submission deadline: **27 October 2026, 11:59 PM PT**.

---

## Project name
OmniPitch — live match intelligence, written by agents and fact-checked before it reaches air

## Elevator pitch (≈120 words)
Football stories don't start and end with the scoreline. OmniPitch turns a live stream of synthetic match events into a complete broadcast: spoken play-by-play in English, Italian, Spanish or German, a co-commentator who explains *why* each moment matters, a tactical match centre, and automated half-time and full-time reports. Eight specialised agents share one blackboard; when a Microsoft Foundry deployment is configured, the commentator and recap writer call it only on the moments that matter, and a Grounding Verifier checks every number and every name against the event log before anything airs — catching 99.8 % of injected hallucinations with zero false rejections. Viewers choose analyst or fan voice, their language, their club and their player; external agents such as GitHub Copilot can query the live match over MCP.

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

OmniPitch is submitted as a test build: one Python package, no account, no API key and no cloud resources needed. Without a Foundry endpoint every line comes from the verified multilingual phrase bank (the top bar shows `Local agents`); add the three `AZURE_AI_FOUNDRY_*` variables from `.env.example` to switch the commentator and recap writer to your Foundry deployment.

**Start it (Python 3.10+, about one minute):**
```bash
git clone https://github.com/riccardoponte/OmniPitch.git
cd OmniPitch
python -m venv .venv
.venv\Scripts\activate          # macOS / Linux: source .venv/bin/activate
pip install -e ".[dev]"
uvicorn omnipitch.api:app --port 8000
```
On Windows you can instead double-click `START_OMNIPITCH.bat`.

**Try it:**
1. Open http://localhost:8000. In the control strip choose *Commentary* = Italiano, *Your club* = Avalon City, *View* = Fan, *Pace* = 2×.
2. Click the speaker button to turn the voice on, then **Kick off**.
3. Watch the *Live commentary* panel and listen; goals and cards are called with emphasis, and the co-commentator explains them.
4. At half-time the broadcast pauses and the half-time report opens. Close it and press **Second half**.
5. During play, open *Match centre → Agents & workflows* to see live agent latency and the verifier's running totals.
6. At the final whistle the full-time report opens; *Read aloud* speaks it.
7. Optional: connect an MCP client to `http://localhost:8000/mcp/` (VS Code / GitHub Copilot reads `.vscode/mcp.json`) and call `get_match_state`, or `explain_moment` with an event ID from the feed.

**Check the claims:** `pytest -q` (51 tests) and `python foundry/evaluations/run_grounding_eval.py` (grounding evaluation, about 3 minutes).

**Platform:** desktop or mobile browser (Chrome/Edge recommended for speech voices).

---

## Demo video

A finished cut (1:41, 1080p, English voice-over, burned-in English captions) is produced by the scripts in `demo_video/`:
`narration.py` (voice-over), `record.py` (Playwright drives a real seeded match), `cards.py` (title, closing and a live MCP call), `edit.py` (ffmpeg edit). Output: `demo_video/OmniPitch_demo.mp4` (not committed).

| Time | Scene |
| --- | --- |
| 0:00 | Title card |
| 0:11 | Live match in English, analyst view: pitch, lower third, commentary feed |
| 0:25 | Switch to Italian, fan view, Avalon City: real Italian goal call, voiced |
| 0:47 | Stoppage-time board (+4), clock 45+2, half-time pause and report |
| 0:57 | Grounding Verifier: claims verified, evidence JSON, live agent telemetry |
| 1:11 | Match centre: momentum, shot map, timeline |
| 1:21 | Live MCP call: `explain_moment` on the 67' goal, verified |
| 1:30 | Full-time report, closing card |

No music; no third-party trademarks. Upload to YouTube or Vimeo as public/unlisted and paste the URL on the project page.

---

## Pre-submission checklist
- [x] GitHub repository is **public** and `main` is up to date
- [x] Test build runs from the README in one command; CI green on Python 3.10–3.12
- [ ] Video (1:41) uploaded to YouTube/Vimeo, link copied
- [ ] Project page: description, technologies, repo URL, video URL, testing instructions
- [ ] All submission text in English
