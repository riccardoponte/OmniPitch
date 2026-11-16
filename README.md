🌐 **Lingua / Language:** [🇮🇹 Italiano](#italiano) · [🇬🇧 English](#english)

---
<a id="italiano"></a>

# OmniPitch

**Una trasmissione calcistica in diretta scritta da agenti — e verificata prima di andare in onda.**

OmniPitch trasforma un flusso di eventi di gara sintetici in un'esperienza di trasmissione completa: telecronaca play-by-play in diretta in quattro lingue (letta ad alta voce), un sottopancia ("lower third") sullo schermo con la spiegazione "perché è importante", un match center tattico e report automatizzati di fine primo tempo e fine partita. Una catena di agenti specializzati condivide una lavagna comune (`MatchBlackboardMemory`); un Grounding Verifier verifica ogni numero e ogni nome rispetto al registro degli eventi, affinché la narrazione non si discosti mai dai dati.

Sviluppato per **Inside the Game: Developer Hackathon** (Microsoft × Premier League). Tutti i club, i giocatori e le competizioni sono fittizi.

---

## Cosa fa

| Fase della sfida | In OmniPitch |
| --- | --- |
| **Ingest** | Un motore deterministico simula un'intera partita — calcio d'inizio, due tempi da 45 minuti, la lavagna dei minuti di recupero del quarto uomo, intervallo, fischio finale. Passaggi (riusciti e persi), tiri (gol / parati / fuori bersaglio / respinti), contrasti, intercettazioni, pressing, falli, cartellini gialli e rossi. Opzionalmente replicato su **Azure Event Hubs**. |
| **Interpret** | xG progressivi, tiri, possesso palla, serie di passaggi, valutazioni dei giocatori, momentum d'attacco per minuto (recupero ombreggiato), mappa dei tiri, difficoltà dei passaggi, velocità della palla e del tiro. |
| **Explain** | Il Narratore spiega *perché* un momento è importante: contesto xG di un gol, una grande parata, pressing che recupera palla alto, serie di possesso, cosa cambia con un cartellino rosso. |
| **Render** | Overlay machine-readable via SSE: titolo, narrazione, battute di telecronaca, ID degli eventi di evidenza, tracciamento per singolo agente, priorità di visualizzazione per il sottopancia. |
| **Personalize** | Voce Analista vs Tifoso, quattro lingue, telecronaca per club del cuore (esulta per i *tuoi* gol e si rammarica per quelli dell'avversario), riflettori sul singolo giocatore, velocità di riproduzione, telecronaca parlata. |

### Telecronaca in diretta ("telecronaca")
- **Telecronista principale**: una riga per evento, in English, Italiano, Español o Deutsch.
- **Seconda voce (co-commentatore)**: interviene nei momenti chiave con la spiegazione.
- **Voce**: la sintesi vocale del browser legge le battute nella lingua selezionata, con una seconda voce per il commentatore tecnico. I gol e i cartellini rossi saltano la coda; i passaggi di routine vengono letti solo quando la cabina di commento è libera, evitando che la voce accumuli ritardo rispetto alla partita.
- **Orologio di gara reale**: `45+2'`, `90+4'`, badge dei minuti di recupero sul tabellone, pausa all'intervallo con report del primo tempo e report conclusivo al fischio finale.

---

## Gli agenti

Ogni evento attraversa la catena seguente; tutti gli agenti leggono e scrivono sulla stessa `MatchBlackboardMemory`.

| # | Agente | Ruolo | Eseguito su |
| --- | --- | --- | --- |
| 1 | Ingest | Registra l'evento, calcola lo stato progressivo (xG, tiri, possesso, serie di passaggi) | code |
| 2 | Tactical Analyst | Controllo vs caos, pressione difensiva, ritmo di gara nella finestra temporale recente | code |
| 3 | Lead Commentator | Riga play-by-play in diretta, persona + lingua + squadra del cuore | **Modello Foundry nei momenti chiave**, phrase bank altrimenti |
| 4 | Narrator / Co-commentator | "Perché è importante", titolo in sovrimpressione | code |
| 5 | Player Focus | Riflettori puntati sul giocatore scelto dallo spettatore | code |
| 6 | Grounding Verifier | Controlla ogni numero e nome di giocatore; blocca le chiamate di gol in assenza di gol | code |
| 7 | Broadcast | Emette l'overlay; ricorre a una riga deterministica se la verifica fallisce | code |
| 8 | Recap Writer | Report di fine primo tempo e fine partita (verdetto xG, momenti chiave, migliore in campo) | **Modello Foundry**, phrase bank altrimenti |

**Le chiamate ai modelli avvengono solo dove conta.** Il telecronista chiama il deployment Microsoft Foundry per gol, tiri, cartellini e fasi della partita; il recap writer lo chiama all'intervallo e al fischio finale. Ogni frase generata deve superare il verificatore, altrimenti viene sostituita da una riga pre-verificata della phrase bank. Senza un endpoint Foundry l'intero sistema funziona comunque tramite la phrase bank, e la UI lo segnala (`Local agents` nella barra superiore e nella scheda Agents).

### Grounding, misurato

`python foundry/evaluations/run_grounding_eval.py` gioca 80 partite complete (10 seed × 4 lingue × 2 personas), verifica ogni testo generato, quindi inietta un'allucinazione in ciascuno (un numero modificato, un giocatore non coinvolto, una finta chiamata di gol):

| Metrica | Risultato |
| --- | --- |
| Testi fedeli verificati | 22.288 |
| Falsi rifiuti | **0.0 %** |
| Allucinazioni iniettate rilevate | **99.8 %** (40.228 casi) |
| — finte chiamate di gol | 100 % |
| — giocatore errato | 100 % |
| — numeri alterati | 98.7 % |

I restanti casi mancati sono conteggi privi di etichetta che per coincidenza risultano uguali a un altro numero sulla lavagna; le affermazioni etichettate (xG, km/h, metri, %, indice di controllo / pressione, punteggi) devono corrispondere esattamente al fatto rispettivo. I risultati vengono scritti in `foundry/evaluations/grounding_eval_results.json`. L'interfaccia utente live mostra i totali progressivi dello stesso verificatore (affermazioni verificate, percentuale di grounding, fallback).

---

## Tecnologie Microsoft

- **Microsoft Foundry** — Deployment Azure OpenAI chat-completions utilizzato dal Lead Commentator e dal Recap Writer (`agents/foundry_client.py`), con budget di latenza, tracciamento e fallback verificato.
- **Model Context Protocol** — Un vero server MCP (SDK ufficiale, Streamable HTTP su `/mcp/` e stdio tramite `omnipitch-mcp`) che espone la partita *in tempo reale*: `get_match_state`, `get_live_commentary`, `explain_moment`, `get_match_recap`, `get_player_live_stats`, `advance_match`. Pronto per la **Modalità Agente di GitHub Copilot** tramite `.vscode/mcp.json`, o per un agente Foundry.
- **Azure Container Apps** — `Dockerfile` + `infra/main.bicep` (Log Analytics, Application Insights, Event Hubs, Container App con secret di Foundry ed Event Hubs, probe di integrità).
- **Azure Event Hubs** — Ogni evento può essere replicato su un hub per i consumer di Functions / Fabric Eventstream (`integrations/event_hubs.py`).
- **Microsoft Fabric** — Tabelle eventi e giocatori pronte per Delta (`/api/match/{id}/fabric/export`, esportazione CSV).
- **Power Automate / Teams** — Dispatcher di Adaptive Card (v1.5) per gol, cambi tattici e incidenti.
- **GitHub Actions** — CI che esegue la suite di test su Python 3.10–3.12.

---

## Esecuzione

### In locale
```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -e ".[dev]"
uvicorn omnipitch.api:app --port 8000
```
Apri http://localhost:8000, scegli una lingua, una squadra e un ritmo, attiva la voce, premi **Kick off**. Su Windows puoi anche fare doppio clic su `START_OMNIPITCH.bat`.

### Con Microsoft Foundry
Copia `.env.example` in `.env` e imposta:
```
AZURE_AI_FOUNDRY_ENDPOINT=https://<your-resource>.openai.azure.com/
AZURE_AI_FOUNDRY_API_KEY=<key>
AZURE_OPENAI_DEPLOYMENT_NAME=gpt-4o-mini
```
La barra superiore passa da `Local agents` a `Foundry · <deployment>`; le righe di commento scritte dal modello mostrano il tag `Foundry` nel feed.

### Docker / Azure Container Apps
```bash
docker build -t omnipitch .
docker run -p 8000:8000 --env-file .env omnipitch

# Distribuzione con un solo comando dal sorgente
az containerapp up --name omnipitch --resource-group rg-omnipitch --location westeurope --source . --ingress external --target-port 8000

# Oppure l'intero stack Bicep (Event Hubs, App Insights, Container App)
az deployment group create -g rg-omnipitch -f infra/main.bicep -p infra/main.parameters.json -p containerImage=<registry>/omnipitch:latest
```
Le sessioni di gara risiedono in memoria, quindi la Container App viene eseguita con una singola replica; spostare le sessioni su Cosmos DB o Redis è la strada per la scalabilità orizzontale.

### MCP
Con l'applicazione in esecuzione, punta qualsiasi client MCP su `http://localhost:8000/mcp/` (VS Code / GitHub Copilot lo rileva automaticamente da `.vscode/mcp.json`). Prova: *"Qual è il punteggio, e perché l'ultimo gol è stato importante?"* — l'agente chiama `get_match_state` ed `explain_moment`.

---

## API

| Endpoint | Scopo |
| --- | --- |
| `GET /api/match/{id}/overlays/stream?include_events=true&lang=it&persona=fan&club=avalon_city&player=Julian%20Drake` | SSE: `match_event`, `broadcast_overlay`, `match_recap`, `stream_end` |
| `GET /api/match/{id}/recap?kind=full_time&lang=de` | Report automatizzato |
| `GET /api/match/{id}/agents/telemetry` | Latenza per agente, claim verificati / respinti, utilizzo LLM, fallback |
| `GET /api/match/{id}/matchcenter/overview` | Momentum, statistiche, formazioni, mappa dei tiri, cronologia (timeline) |
| `POST /api/match/{id}/reset` | Nuova partita |
| `/mcp/` | Model Context Protocol (Streamable HTTP) |

Documentazione interattiva su `/docs`.

---

## Test
```bash
pytest -q          # 50 test: timeline del motore, recupero, telecronaca in 4 lingue, verificatore, recap, SSE, MCP
```

## Dati e conformità
- Dati di gara al 100% sintetici e deterministici (con seed); tutti i club, i giocatori, le competizioni e gli stadi sono fittizi.
- Nessun filmato di gara, nomi di club reali o marchi registrati di terze parti.
- Nessun segreto nel controllo versione; le credenziali di Foundry ed Event Hubs provengono da variabili d'ambiente / secret di Container Apps.

## Struttura del progetto
```
src/omnipitch/
  generator/engine.py        motore di gara: tempi, recupero, eventi, cartellini
  agents/                    telecronaca, narratore, verificatore, recap, orchestratore, memoria, server MCP
  api/app.py                 FastAPI: stream SSE, REST, mount MCP
  integrations/              publisher Event Hubs, schede Power Automate
  web/static/                dashboard di trasmissione (vanilla JS + canvas)
foundry/                     manifest dell'agente, valutazione del grounding
infra/                       Bicep per Azure Container Apps
tests/                       suite di test pytest
```

Licenza MIT.

---
<a id="english"></a>

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
