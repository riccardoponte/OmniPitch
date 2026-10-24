# OmniPitch architecture

## 1. Principle
Every sentence that reaches the screen or the speaker is built from structured facts and checked against them. Models are used where fluency adds value (key moments, recaps); a deterministic, pre-verified path guarantees the broadcast never stops and never invents.

## 2. Flow

```
MatchSimulationEngine.play()           kick-off · 1st half · +N board · half-time · 2nd half · +N board · full time
        │  (optional mirror → Azure Event Hubs)
        ▼
MultiAgentOrchestrator.process_event()
        │
        ├─ 1 Ingest            → MatchBlackboardMemory.record_event / match_state      (shared state)
        ├─ 2 Tactical Analyst  → control vs chaos · pressure · tempo over last 5 events
        ├─ 3 Lead Commentator  → CommentaryFacts → Foundry model (key moments) │ phrase bank
        ├─ 4 Narrator          → insight kind → headline + "why it matters" (analyst │ fan, 4 languages)
        ├─ 5 Player Focus      → spotlight stats for the chosen player
        ├─ 6 Grounding Verifier→ numbers · labelled facts · scorelines · names · goal calls
        └─ 7 Broadcast         → BroadcastOverlayPayload (+ deterministic fallback on rejection)
        │
        ├─ at half-time / full time: 8 Recap Writer → MatchRecap (Foundry │ phrase bank, verified)
        ▼
SSE  /api/match/{id}/overlays/stream   match_event · broadcast_overlay · match_recap · stream_end
MCP  /mcp/                              get_match_state · get_live_commentary · explain_moment · ...
REST /api/...                           match centre, telemetry, recap, Fabric / CSV export, Teams cards
```

## 3. Shared state
`MatchBlackboardMemory` holds the event log and per-player cumulative stats. `match_state()` derives running team totals (xG, shots, possession by passes, cards, current pass streak). Agents never pass free text to each other; they pass typed objects (`TacticalAnalysisReport`, `CommentaryFacts`, `NarrativeDraft`, `VerificationResult`) and read the blackboard.

## 4. Grounding Verifier
For any text it checks, in order:
1. **Labelled claims** — the number next to `xG`, `km/h`, metres, `%`, *control index* / *pressure index* (in all four languages) must equal that specific fact.
2. **Scorelines and pairs** — `2–1` must be the current score or the shot count pair.
3. **Other numbers** — must exist in the event facts or the blackboard (45 and 90 are always allowed).
4. **Players** — every roster surname mentioned must belong to the cited events.
5. **Goal calls** — `GOAL / GOL / RETE / TOR` only when the evidence contains a goal.

A rejected model line is replaced by the phrase-bank line; a rejected narrative triggers `FallbackNarrativeGenerator`. All outcomes are counted in `orchestrator.telemetry()` and shown in the UI. Measured quality: `foundry/evaluations/run_grounding_eval.py` (0 % false rejections, 99.8 % of injected hallucinations caught over 80 simulated matches).

## 5. Match model
- Clock owned by the engine; stoppage time drawn per half (1–4 and 3–6 minutes), announced at 45:00 / 90:00, play continues into `45+x` / `90+x`.
- Second half kicked off by the away side at 45:00 (period 2).
- Shots: goal probability = xG; otherwise saved / off target / blocked. Away team attacks towards x = 0.
- Pass completion depends on difficulty; failed passes flip possession.
- Fouls keep possession (free kick); 18 % yellow, 1.5 % straight red, second yellow = red; sent-off players leave the pool.
- Deterministic per seed (separate RNG for the clock), so demos and tests are reproducible.

## 6. Personalisation
Persona (analyst / fan) changes vocabulary and whether data tags are spoken; language switches every agent output; favourite club changes the commentator's and co-commentator's stance on goals; player spotlight follows one player; pace changes stream delay and voice rate.

## 7. Deployment
Single container (FastAPI + static dashboard + MCP) on Azure Container Apps, one replica because match sessions are in memory. Bicep provisions Log Analytics, Application Insights, Event Hubs (connection string injected as a secret) and the Container App with Foundry settings. Horizontal scale requires moving sessions to Cosmos DB or Redis (Cosmos is behind the `deployCosmos` parameter).
