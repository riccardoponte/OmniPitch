# OmniPitch

**A live football broadcast written by agents — and fact-checked before it reaches air.**

OmniPitch turns a stream of synthetic match events into a full broadcast experience: live play-by-play commentary in four languages (read aloud), an on-screen "why it matters" lower third, a tactical match centre, and automated half-time and full-time reports. A chain of specialised agents shares one blackboard; a Grounding Verifier checks every number and every name against the event log, so the story never drifts from the data.

Built for **Inside the Game: Developer Hackathon** (Microsoft × Premier League). All clubs, players and competitions are fictional.

---

## What it does

| Challenge stage | In OmniPitch |
| --- | --- |
| **Ingest** | A deterministic engine plays a full match — kick-off, two 45-minute halves, the fourth official's stoppage-time board, half-time, the final whistle. Passes (completed and lost), shots (goal / saved / off target / blocked), tackles, interceptions, pressing, fouls, yellow and red cards. Optionally mirrored to **Azure Event Hubs**. |
| **Interpret** | Running xG, shots, possession, pass streaks, player ratings, attack momentum per minute (stoppage time shaded), shot map, pass difficulty, ball and shot speed. |
| **Explain** | The Narrator explains *why* a moment matters: xG context of a goal, a big save, pressing that wins the ball high, possession streaks, what a red card changes. |
| **Render** | Machine-readable overlays over SSE: headline, narrative, commentary lines, evidence event IDs, per-agent trace, display priority for the lower third. |
| **Personalize** | Analyst vs Fan voice, four languages, favourite-club commentary (it celebrates *your* goals and sounds gutted at the opponent's), player spotlight, playback pace, spoken commentary. |

### Live commentary ("telecronaca")
- **Lead commentator**: one line per event, in English, Italiano, Español or Deutsch.
- **Co-commentator**: joins on big moments with the explanation.
- **Voice**: the browser's speech synthesis reads the lines in the selected language, with a second voice for the co-commentator. Goals and red cards jump the queue; routine passes are only read when the booth is quiet, so the voice never lags the match.
- **Real match clock**: `45+2'`, `90+4'`, a stoppage-time badge on the scoreboard, a half-time pause with the half-time report, and a full-time report at the final whistle.

---

## The agents

Each event goes through the chain below; all agents read and write the same `MatchBlackboardMemory`.

| # | Agent | Role | Runs on |
| --- | --- | --- | --- |
| 1 | Ingest | Records the event, derives running state (xG, shots, possession, pass streak) | code |
| 2 | Tactical Analyst | Control vs chaos, defensive pressure, game rhythm over the recent window | code |
| 3 | Lead Commentator | Live play-by-play line, persona + language + favourite club | **Foundry model on key moments**, phrase bank otherwise |
| 4 | Narrator / Co-commentator | "Why it matters", on-screen headline | code |
| 5 | Player Focus | Spotlight on the viewer's chosen player | code |
| 6 | Grounding Verifier | Checks every number and player name; blocks goal calls without a goal | code |
| 7 | Broadcast | Emits the overlay; falls back to a deterministic line if verification fails | code |
| 8 | Recap Writer | Half-time and full-time report (xG verdict, key moments, player of the match) | **Foundry model**, phrase bank otherwise |

**Model calls go only where they matter.** The commentator calls the Microsoft Foundry deployment for goals, shots, cards and match phases; the recap writer calls it at half-time and full time. Every generated sentence must pass the verifier, or it is replaced by a pre-verified line from the phrase bank. Without a Foundry endpoint the whole system still runs on the phrase bank, and the UI says so (`Local agents` in the top bar and on the Agents tab).

### Grounding, measured

`python foundry/evaluations/run_grounding_eval.py` plays 80 full matches (10 seeds × 4 languages × 2 personas), checks every generated text, then injects one hallucination into each (a changed number, a player who was not involved, a fake goal call):

| Metric | Result |
| --- | --- |
| Faithful texts checked | 22,288 |
| False rejections | **0.0 %** |
| Injected hallucinations caught | **99.8 %** (40,228 cases) |
| — fake goal calls | 100 % |
| — wrong player | 100 % |
| — altered numbers | 98.7 % |

The remaining misses are unlabelled counts that happen to equal another number on the blackboard; labelled claims (xG, km/h, metres, %, control / pressure index, scorelines) must match their own fact exactly. Results are written to `foundry/evaluations/grounding_eval_results.json`. The live UI shows the same verifier's running totals (claims checked, grounded rate, fallbacks).

---

## Microsoft technology

- **Microsoft Foundry** — Azure OpenAI chat-completions deployment used by the Lead Commentator and Recap Writer (`agents/foundry_client.py`), with latency budget, tracing and verified fallback.
- **Model Context Protocol** — a real MCP server (official SDK, Streamable HTTP at `/mcp/` and stdio via `omnipitch-mcp`) exposing the *live* match: `get_match_state`, `get_live_commentary`, `explain_moment`, `get_match_recap`, `get_player_live_stats`, `advance_match`. Ready for **GitHub Copilot Agent Mode** via `.vscode/mcp.json`, or for a Foundry agent.
- **Azure Container Apps** — `Dockerfile` + `infra/main.bicep` (Log Analytics, Application Insights, Event Hubs, Container App with Foundry and Event Hubs secrets, health probe).
- **Azure Event Hubs** — every event can be mirrored to a hub for Functions / Fabric Eventstream consumers (`integrations/event_hubs.py`).
- **Microsoft Fabric** — Delta-ready event and player tables (`/api/match/{id}/fabric/export`, CSV export).
- **Power Automate / Teams** — Adaptive Card (v1.5) dispatcher for goals, tactical shifts and incidents.
- **GitHub Actions** — CI runs the test suite on Python 3.10–3.12.

---

## Run it

### Locally
```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
uvicorn omnipitch.api:app --port 8000
```
Open http://localhost:8000, pick a language, a club and a pace, turn the voice on, press **Kick off**. On Windows you can also double-click `START_OMNIPITCH.bat`.

### With Microsoft Foundry
Copy `.env.example` to `.env` and set:
```
AZURE_AI_FOUNDRY_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_AI_FOUNDRY_API_KEY=<key>
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini
```
The top bar switches from `Local agents` to `Foundry · <deployment>`; commentary lines written by the model carry a `Foundry` tag in the feed.

### Docker / Azure Container Apps
```bash
docker build -t omnipitch .
docker run -p 8000:8000 --env-file .env omnipitch

# One-command deploy from source
az containerapp up --name omnipitch --resource-group rg-omnipitch --location westeurope --source . --ingress external --target-port 8000

# Or the full Bicep stack (Event Hubs, App Insights, Container App)
az deployment group create -g rg-omnipitch -f infra/main.bicep -p infra/main.parameters.json -p containerImage=<registry>/omnipitch:latest
```
Match sessions live in memory, so the Container App runs a single replica; moving sessions to Cosmos DB or Redis is the path to horizontal scale.

### MCP
With the app running, point any MCP client at `http://localhost:8000/mcp/` (VS Code / GitHub Copilot picks it up from `.vscode/mcp.json`). Try: *"What's the score, and why did the last goal matter?"* — the agent calls `get_match_state` and `explain_moment`.

---

## API

| Endpoint | Purpose |
| --- | --- |
| `GET /api/match/{id}/overlays/stream?include_events=true&lang=it&persona=fan&club=avalon_city&player=Julian%20Drake` | SSE: `match_event`, `broadcast_overlay`, `match_recap`, `stream_end` |
| `GET /api/match/{id}/recap?kind=full_time&lang=de` | Automated report |
| `GET /api/match/{id}/agents/telemetry` | Per-agent latency, claims checked / rejected, LLM usage, fallbacks |
| `GET /api/match/{id}/matchcenter/overview` | Momentum, stats, line-ups, shot map, timeline |
| `POST /api/match/{id}/reset` | New match |
| `/mcp/` | Model Context Protocol (Streamable HTTP) |

Interactive docs at `/docs`.

---

## Tests
```bash
pytest -q          # 50 tests: engine timeline, stoppage time, commentary in 4 languages, verifier, recap, SSE, MCP
```

## Data and compliance
- 100 % synthetic, deterministic (seeded) match data; all clubs, players, competitions and stadiums are fictional.
- No match footage, real club names or third-party trademarks.
- No secrets in source control; Foundry and Event Hubs credentials come from environment variables / Container Apps secrets.

## Project layout
```
src/omnipitch/
  generator/engine.py        match engine: halves, stoppage time, events, cards
  agents/                    commentary, narrator, verifier, recap, orchestrator, memory, MCP server
  api/app.py                 FastAPI: SSE streams, REST, MCP mount
  integrations/              Event Hubs publisher, Power Automate cards
  web/static/                broadcast dashboard (vanilla JS + canvas)
foundry/                     agent manifest, grounding evaluation
infra/                       Bicep for Azure Container Apps
tests/                       pytest suite
```

MIT License.
