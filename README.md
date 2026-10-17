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
   - **Grounding Verifier Agent**: Anti-hallucination auditor that validates every statement against raw event IDs (`EVT-XXXX`).
   - **Graceful Fallback**: Rule-based template fallback ensures zero broadcast interruption if external AI services experience latency.

4. **Targeted Hackathon Award Categories**:
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
   ├── Grounding Verifier Agent (Evidence ID Matching)
   └── Persona & Localization Agent
               │
               ▼
   [ Fast REST / SSE API (Azure Container Apps) ]
         │                               │
         ▼                               ▼
 [ Web Dashboard (Analyst & Fan) ]   [ Machine-Readable JSON Overlays ]
```

---

## 💻 Quick Start (Local Development)

### Prerequisites
- Python 3.10+
- Node.js 18+ (for frontend)

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

### Running the Match Event Streamer
```bash
# Generate 15 sample match events with metrics
python -m omnipitch.generator.cli --count 15

# Stream events in real time with delay
python -m omnipitch.generator.cli --stream --delay 0.8
```

### Running Tests
```bash
pytest -v
```

---

## 🔒 Security & Compliance
- **Zero Secrets**: No API keys or tokens are stored in source control. All configuration is managed via environment variables and Azure Key Vault.
- **100% Synthetic Data**: No copyrighted footage, real-world team names, or player identities are used.

---

## 📜 License
Distributed under the MIT License. See [LICENSE](LICENSE) for details.
