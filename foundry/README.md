# Microsoft Foundry: agents and evaluation

## Agent manifest
`agents_manifest.json` describes the eight agents exactly as they run in `src/omnipitch/agents/`: role, whether they execute as code or call the Foundry model, their tools and their handoff. The API serves it at `GET /api/foundry/agents`, enriched with live per-agent latency and verifier telemetry.

Two agents call the Foundry deployment:

| Agent | When | Guardrail |
| --- | --- | --- |
| Lead Commentator | goals, shots, cards, kick-off, stoppage-time board, half-time, full time | line must pass the Grounding Verifier, else the phrase-bank line airs |
| Recap Writer | half-time and full time | report must pass the verifier, else the template report is used |

Configure with `AZURE_AI_FOUNDRY_ENDPOINT`, `AZURE_AI_FOUNDRY_API_KEY`, `AZURE_OPENAI_DEPLOYMENT_NAME` (any chat-completions deployment, e.g. `gpt-4o-mini`). Calls have a 2.5 s budget; timeouts and errors fall back silently and are reported in telemetry.

## Grounding evaluation
```bash
python foundry/evaluations/run_grounding_eval.py --seeds 10
```
Plays 10 seeds × 4 languages × 2 personas (80 full matches), verifies every commentary line and narrative, then injects one hallucination into each (altered number, uninvolved player, fake goal call) and measures how many the verifier catches. Latest results (`grounding_eval_results.json`):

- 22,288 faithful texts — 0 false rejections
- 40,228 injected hallucinations — 99.8 % caught (fake goals 100 %, wrong players 100 %, altered numbers 98.7 %)

`eval_dataset.json` holds hand-written scenarios with ground-truth claims for model-graded evaluation in Foundry.
