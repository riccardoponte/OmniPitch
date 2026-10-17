# OmniPitch ⚽🤖

> **Personalized Synthetic Match Intelligence on Microsoft AI**
> *Developed for the "Inside the Game: Developer Hackathon" by Microsoft & Premier League*

---

## 🏆 Project Vision

**OmniPitch** transforms real-time synthetic football events into explainable tactical intelligence, automated match narratives, and multi-tier personalized broadcasts powered by **Microsoft Foundry**, **Microsoft Agent Framework**, and **Azure Cloud-Native Services**.

Football intelligence is not just about the scoreline. OmniPitch answers the critical question: **"Why does this moment matter?"** — decoding game rhythm, defensive pressure, and the tension between tactical control and chaos, grounded with verifiable event evidence.

---

## 🚀 Key Highlights & Hero Capabilities

1. **Deterministic & Realistic Synthetic Data Engine**:
   - 100% compliant with hackathon guidelines (fully fictional teams and rosters: *Avalon City FC* vs *Solaria Rovers*).
   - Generates pitch physics, spatial tracking $(x, y)$, pass difficulty ratings, ball/shot velocities, and defensive pressure indices.
   - Deterministic replayability via seeded RNG.

2. **Five-Stage End-to-End Pipeline**:
   - **Ingest**: High-throughput match event streaming via Azure Event Hubs / Functions.
   - **Interpret**: Real-time aggregation of pass difficulty, pressure shifts, and possession dominance.
   - **Explain**: Tactical explanation (Control vs Chaos index, Game Rhythm Tempo).
   - **Render**: Machine-readable JSON overlay feeds for synchronized live broadcast graphics.
   - **Personalize**: Adaptive multi-persona storytelling (Data Analyst Mode vs Casual Fan Mode, club/player focus, multilingual).

3. **Multi-Agent Orchestration with Verifiable Evidence Grounding**:
   - **Tactical Analyst Agent**: Decodes strategic patterns and momentum shifts.
   - **Narrator Agent**: Crafts timed broadcast commentary and match summaries.
   - **Player Focus Agent**: Tracks individual player sprints, top speeds, and tactical involvement.
   - **Grounding Verifier Agent**: Anti-hallucination auditor that validates every statement against raw event IDs (`EVT-XXXX`).
   - **Graceful Fallback**: Rule-based template fallback ensures zero broadcast interruption if external AI services experience latency.

4. **Pro Match Intelligence Center & Tactical Dynamics**:
   - **Attack Momentum**: Minute-by-minute dominance visualization with event icon markers.
   - **Head-to-Head Comparative Analytics**: Dynamic xG, ball possession %, shots on target, and tackles won.
   - **Lineup Ratings & Automated MVP**: Algorithmic performance ratings (0-10 scale) and match MVP spotlight badge.
   - **Penalty Shot Map**: Spatial half-pitch shot chart scaled by xG value and shot velocity (km/h).
   - **Tactical System Switcher**: Dynamic formation repositioning (`4-3-3`, `4-2-3-1`, `3-5-2`).
   - **Web Audio Sound Synthesizer**: Realistic whistle acoustics for kickoffs and major momentum shifts.
   - **Instant Match Report Export**: One-click download of rich JSON intelligence dossiers.

5. **Microsoft Fabric Lakehouse Integration**:
   - Automated export of structured match events and physical summaries to Delta Lake format (`fact_match_events`, `dim_player_physical_summary`).

6. **Targeted Hackathon Award Categories**:
   - 🥇 **Grand Prize**: End-to-end impact transforming synthetic football data into personalized intelligence.
   - 🛠️ **Best Use of Microsoft Foundry**: Accelerated model orchestration, tracing, and evaluation.
   - 🤖 **Best Multi-Agent System**: Purposeful multi-agent collaboration with shared state and grounding verification.
   - ☁️ **Best Azure Cloud Native Integration**: Event-driven architecture on Azure Event Hubs, Azure Functions, and Azure Container Apps.
   - 🏢 **Best Enterprise Solution**: Observable (OpenTelemetry), secure (Key Vault, zero hardcoded secrets), resilient, and scalable.

---

## 🏗️ Architecture Overview

```
 [ Synthetic Match Event Engine ]
               │
               ▼
    [ Azure Event Hubs Stream ]
               │
               ▼
 [ Azure Functions / Processing ] ──► [ Microsoft Fabric / Lakehouse ]
               │
               ▼
 [ Multi-Agent System (Microsoft Foundry & Agent Framework) ]
   ├── Tactical Analyst Agent
   ├── Broadcast Narrator Agent
   ├── Player Focus Agent
   ├── Grounding Verifier Agent (Evidence ID Matching)
   └── Persona & Localization Agent
               │
               ▼
   [ Fast REST / SSE API (Azure Container Apps) ]
         │                               │
         ▼                               ▼
 [ Web Dashboard & Match Center ]   [ Machine-Readable JSON Overlays ]
```

---

## 💻 Quick Start (Local Development)

### Prerequisites
- Python 3.10+
- Modern Web Browser

### Installation
```bash
# Clone the repository
git clone <repo-url>
cd "Hackaton MSFT PPL"

# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies in editable mode
pip install -e ".[dev]"
```

### Launching the Interactive Web Dashboard
OmniPitch comes with an interactive, dark stadium themed web dashboard with 2D pitch telemetry, Pro Match Intelligence Center, live multi-agent pipeline monitoring, and dynamic persona switching:

```bash
uvicorn omnipitch.api:app --reload --port 8000
```
Open **[http://localhost:8000](http://localhost:8000)** in your browser.

- **Tactical Analyst Mode**: High-density tactical metrics, pass difficulty, control vs chaos gauge, and pressing indicators.
- **Casual Fan Mode**: High-energy action narratives, milestone highlights, and simplified momentum visuals.
- **Localization**: Live switching between English, Italian, Spanish, and German.
- **Interactive Pitch**: Real-time canvas rendering ball coordinates $(x,y)$, pass vectors, shot velocities, and defensive pressure.
- **Pro Match Center**: Attack momentum, comparative stats, dynamic ratings, and penalty shot map.

---

## 🤖 Model Context Protocol (MCP) Tools

OmniPitch implements the **Model Context Protocol (MCP)**, allowing **GitHub Copilot Agent Mode** and **Microsoft Foundry** AI agents to autonomously query live tactical intelligence:

- `get_match_tactical_state`: Fetches Control vs Chaos index, defensive pressure, and tempo.
- `generate_broadcast_overlay`: Triggers the multi-agent reasoning chain for specified persona and language.
- `simulate_next_event`: Generates chronological physical match telemetry.

Endpoint: `GET /api/mcp/tools` and `POST /api/mcp/call`

---

## ☁️ Azure Cloud Native Deployment (Bicep)

Infrastructure as Code templates are located in [`infra/`](infra/):

```bash
az group create --name rg-omnipitch-prod --location westeurope
az deployment group create \
  --resource-group rg-omnipitch-prod \
  --template-file infra/main.bicep \
  --parameters infra/main.parameters.json
```

---

## 🧪 Automated Testing
OmniPitch includes a comprehensive suite of unit and integration tests:

```bash
pytest -v
# 23 passed in <2s
```

---

## 🔒 Security & Compliance
- **Zero Secrets**: No API keys or tokens are stored in source control. All configuration is managed via environment variables and Azure Key Vault.
- **100% Synthetic Data**: No copyrighted footage, real-world team names, or player identities are used.

---

## 📜 License
Distributed under the MIT License. See [LICENSE](LICENSE) for details.
