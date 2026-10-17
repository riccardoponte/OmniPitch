/**
 * OmniPitch Live Match Intelligence & Interactive Pitch Visualizer
 * Fully featured with Multi-Agent Reasoning, Player Spotlight HUD, Zonal Heatmaps & TTS
 */

class OmniPitchApp {
  constructor() {
    this.matchId = "MATCH-2026-001";
    this.currentPersona = "analyst";
    this.currentLang = "en";
    this.currentPlayer = "";
    this.isStreaming = false;
    this.showHeatmap = false;

    // SSE EventSource instances
    this.overlaySource = null;
    this.eventSource = null;

    // Canvas setup
    this.canvas = document.getElementById("pitch-canvas");
    this.ctx = this.canvas.getContext("2d");

    // State cache
    this.eventsReceived = 0;
    this.currentBall = { x: 50, y: 50 };
    this.activePlayerNode = null;
    this.passVectors = [];
    this.homeScore = 0;
    this.awayScore = 0;
    this.latestOverlay = null;

    // Tactical formation 4-3-3 coordinates (normalized 0-100)
    this.homeFormation = [
      { id: "AVA-01", name: "Marcus Vance", num: 1, role: "GK", x: 6, y: 50 },
      { id: "AVA-02", name: "Leo Sterling", num: 2, role: "DEF", x: 22, y: 20 },
      { id: "AVA-04", name: "Tobias Thorne", num: 4, role: "DEF", x: 19, y: 40 },
      { id: "AVA-05", name: "Dorian Cole", num: 5, role: "DEF", x: 19, y: 60 },
      { id: "AVA-03", name: "Nico Lind", num: 3, role: "DEF", x: 22, y: 80 },
      { id: "AVA-06", name: "Mateo Rios", num: 6, role: "MID", x: 38, y: 50 },
      { id: "AVA-08", name: "Julian Drake", num: 8, role: "MID", x: 48, y: 32 },
      { id: "AVA-10", name: "Kaelen Cross", num: 10, role: "MID", x: 48, y: 68 },
      { id: "AVA-07", name: "Finneas Frost", num: 7, role: "FWD", x: 70, y: 22 },
      { id: "AVA-09", name: "Cyrus Kane", num: 9, role: "FWD", x: 74, y: 50 },
      { id: "AVA-11", name: "Bram Walker", num: 11, role: "FWD", x: 70, y: 78 },
    ];

    this.awayFormation = [
      { id: "SOL-01", name: "Rory Gallagher", num: 1, role: "GK", x: 94, y: 50 },
      { id: "SOL-02", name: "Axel Mercer", num: 2, role: "DEF", x: 78, y: 80 },
      { id: "SOL-05", name: "Hugo Bennett", num: 5, role: "DEF", x: 81, y: 60 },
      { id: "SOL-06", name: "Silas Brandt", num: 6, role: "DEF", x: 81, y: 40 },
      { id: "SOL-03", name: "Dante Morales", num: 3, role: "DEF", x: 78, y: 20 },
      { id: "SOL-04", name: "Jasper Holt", num: 4, role: "MID", x: 62, y: 50 },
      { id: "SOL-08", name: "Ezra Kim", num: 8, role: "MID", x: 52, y: 68 },
      { id: "SOL-10", name: "Zane Al-Mansoor", num: 10, role: "MID", x: 52, y: 32 },
      { id: "SOL-07", name: "Lucian Vega", num: 7, role: "FWD", x: 30, y: 78 },
      { id: "SOL-09", name: "Victor Sterling", num: 9, role: "FWD", x: 26, y: 50 },
      { id: "SOL-11", name: "Orion Price", num: 11, role: "FWD", x: 30, y: 22 },
    ];

    this.initDOM();
    this.initPitch();
    this.renderPitch();
  }

  initDOM() {
    // Persona toggle buttons
    const btnAnalyst = document.getElementById("btn-analyst");
    const btnFan = document.getElementById("btn-fan");

    btnAnalyst.addEventListener("click", () => this.setPersona("analyst"));
    btnFan.addEventListener("click", () => this.setPersona("fan"));

    // Player Spotlight Selector
    const playerSelect = document.getElementById("player-select");
    playerSelect.addEventListener("change", (e) => {
      this.currentPlayer = e.target.value;
      if (this.isStreaming) {
        this.restartStream();
      }
    });

    // Language selector
    const langSelect = document.getElementById("lang-select");
    langSelect.addEventListener("change", (e) => {
      this.currentLang = e.target.value;
      if (this.isStreaming) {
        this.restartStream();
      }
    });

    // Stream toggle button
    const streamBtn = document.getElementById("btn-stream-toggle");
    streamBtn.addEventListener("click", () => this.toggleStream());

    // Speech Audio Commentary button
    const speechBtn = document.getElementById("btn-speak-commentary");
    speechBtn.addEventListener("click", () => this.speakCommentary());

    // Heatmap Toggle button
    const heatmapBtn = document.getElementById("btn-toggle-heatmap");
    heatmapBtn.addEventListener("click", () => {
      this.showHeatmap = !this.showHeatmap;
      heatmapBtn.classList.toggle("active", this.showHeatmap);
      heatmapBtn.textContent = this.showHeatmap ? "🔥 Zonal Heatmap: ON" : "🔥 Zonal Heatmap: OFF";
      this.renderPitch();
    });

    // Reset button
    const resetBtn = document.getElementById("btn-reset");
    resetBtn.addEventListener("click", () => this.resetSimulation());

    // JSON Inspector toggle
    const jsonBtn = document.getElementById("btn-toggle-json");
    const jsonBox = document.getElementById("json-inspector");
    jsonBtn.addEventListener("click", () => {
      jsonBox.classList.toggle("hidden");
    });

    // Fabric Export button
    const fabricBtn = document.getElementById("btn-export-fabric");
    fabricBtn.addEventListener("click", () => {
      window.open(`/api/match/${this.matchId}/fabric/export`, "_blank");
    });
  }

  setPersona(persona) {
    this.currentPersona = persona;
    document.getElementById("btn-analyst").classList.toggle("active", persona === "analyst");
    document.getElementById("btn-fan").classList.toggle("active", persona === "fan");

    if (this.isStreaming) {
      this.restartStream();
    }
  }

  toggleStream() {
    if (this.isStreaming) {
      this.stopStream();
    } else {
      this.startStream();
    }
  }

  startStream() {
    this.isStreaming = true;
    document.getElementById("stream-icon").textContent = "⏸";
    document.getElementById("stream-text").textContent = "Pause Match Stream";
    document.getElementById("btn-stream-toggle").style.background = "linear-gradient(135deg, #e11d48, #f43f5e)";

    // Start Overlay SSE stream with player spotlight query
    let overlayUrl = `/api/match/${this.matchId}/overlays/stream?persona=${this.currentPersona}&lang=${this.currentLang}&delay=1.0`;
    if (this.currentPlayer) {
      overlayUrl += `&player=${encodeURIComponent(this.currentPlayer)}`;
    }
    this.overlaySource = new EventSource(overlayUrl);

    this.overlaySource.addEventListener("broadcast_overlay", (e) => {
      const data = JSON.parse(e.data);
      this.handleBroadcastOverlay(data);
    });

    // Start Event SSE stream
    const eventUrl = `/api/match/${this.matchId}/events/stream?delay=1.0`;
    this.eventSource = new EventSource(eventUrl);

    this.eventSource.addEventListener("match_event", (e) => {
      const data = JSON.parse(e.data);
      this.handleMatchEvent(data);
    });
  }

  stopStream() {
    this.isStreaming = false;
    document.getElementById("stream-icon").textContent = "▶";
    document.getElementById("stream-text").textContent = "Resume Match Stream";
    document.getElementById("btn-stream-toggle").style.background = "";

    if (this.overlaySource) this.overlaySource.close();
    if (this.eventSource) this.eventSource.close();
  }

  restartStream() {
    this.stopStream();
    this.startStream();
  }

  resetSimulation() {
    this.stopStream();
    this.eventsReceived = 0;
    this.homeScore = 0;
    this.awayScore = 0;
    this.passVectors = [];
    this.currentBall = { x: 50, y: 50 };
    this.activePlayerNode = null;
    this.latestOverlay = null;

    document.getElementById("home-score").textContent = "0";
    document.getElementById("away-score").textContent = "0";
    document.getElementById("match-clock").textContent = "00:00";
    document.getElementById("event-counter").textContent = "0 events received";
    document.getElementById("telemetry-list").innerHTML = `
      <div class="telemetry-placeholder">
        <div class="pulse-text">Simulation reset. Click "Start Match Stream" above.</div>
      </div>
    `;
    this.renderPitch();
  }

  speakCommentary() {
    if (!this.latestOverlay || !window.speechSynthesis) return;

    const utterance = new SpeechSynthesisUtterance(this.latestOverlay.narrative);
    const langMap = { en: "en-US", it: "it-IT", es: "es-ES", de: "de-DE" };
    utterance.lang = langMap[this.currentLang] || "en-US";
    utterance.rate = 1.05;
    window.speechSynthesis.cancel();
    window.speechSynthesis.speak(utterance);
  }

  /* -------------------------------------------------------------------------
     Real-Time Multi-Agent Handlers
     ------------------------------------------------------------------------- */

  handleBroadcastOverlay(overlay) {
    this.latestOverlay = overlay;

    // 1. Animate Multi-Agent Pipeline sequence
    this.pulsePipeline();

    // 2. Update Overlay card content
    document.getElementById("overlay-time").textContent = overlay.match_time;
    document.getElementById("overlay-headline").textContent = overlay.headline;
    document.getElementById("overlay-narrative").textContent = overlay.narrative;
    document.getElementById("overlay-genby").textContent = overlay.generated_by;

    // 3. Grounding citations
    const tagsContainer = document.getElementById("evidence-tags");
    tagsContainer.innerHTML = "";
    if (overlay.evidence_event_ids && overlay.evidence_event_ids.length > 0) {
      document.getElementById("evidence-count").textContent = `${overlay.evidence_event_ids.length} Citations`;
      overlay.evidence_event_ids.forEach((eid) => {
        const tag = document.createElement("span");
        tag.className = "tag-event";
        tag.textContent = eid;
        tagsContainer.appendChild(tag);
      });
    }

    // 4. Update Trace Telemetry badge
    if (overlay.trace) {
      const ms = overlay.trace.latency_ms || 12.0;
      const model = overlay.trace.model_name || "gpt-4o";
      document.getElementById("trace-badge").textContent = `⚡ ${model} • ${ms}ms`;
    }

    // 5. Update Player Spotlight HUD if present
    if (overlay.player_focus) {
      const pf = overlay.player_focus;
      document.getElementById("spotlight-name").textContent = pf.player_name;
      document.getElementById("spotlight-avatar").textContent = `#${pf.player_id.slice(-2)}`;
      document.getElementById("spotlight-team").textContent = `${pf.team_id.replace('_', ' ').toUpperCase()} • Spotlight Target`;
      document.getElementById("spotlight-sprints").textContent = pf.sprint_bursts_count;
      document.getElementById("spotlight-dist").textContent = `${pf.distance_covered_km.toFixed(2)} km`;
      document.getElementById("spotlight-acc").textContent = `${pf.pass_completion_rate}%`;
      document.getElementById("spotlight-narrative").textContent = pf.spotlight_narrative;
    }

    // 6. Update JSON Inspector code
    document.getElementById("json-code").textContent = JSON.stringify(overlay, null, 2);

    // 7. Update Tactical Gauges
    if (overlay.metrics) {
      const ctrl = overlay.metrics.control_vs_chaos_index ?? 0.5;
      const press = overlay.metrics.defensive_pressure_index ?? 0.5;
      const tempo = overlay.metrics.game_rhythm_tempo ?? "balanced-contest";

      document.getElementById("val-control").textContent = `${Math.round(ctrl * 100)}% Control`;
      document.getElementById("bar-control").style.width = `${Math.round(ctrl * 100)}%`;

      document.getElementById("val-pressure").textContent = `${press.toFixed(2)} (${press > 0.6 ? 'High' : 'Moderate'})`;
      document.getElementById("bar-pressure").style.width = `${Math.round(press * 100)}%`;

      document.getElementById("val-tempo").textContent = tempo;
    }
  }

  handleMatchEvent(event) {
    this.eventsReceived += 1;
    document.getElementById("event-counter").textContent = `${this.eventsReceived} events received`;

    // Clock
    const mm = String(event.minute).padStart(2, "0");
    const ss = String(event.second).padStart(2, "0");
    document.getElementById("match-clock").textContent = `${mm}:${ss}`;

    // Score if Goal
    if (event.event_type === "goal") {
      if (event.team_id === "avalon_city") {
        this.homeScore += 1;
        document.getElementById("home-score").textContent = this.homeScore;
      } else {
        this.awayScore += 1;
        document.getElementById("away-score").textContent = this.awayScore;
      }
    }

    // Append to telemetry list
    this.appendTelemetryRow(event, `${mm}:${ss}`);

    // Update Pitch Ball & Vectors
    this.currentBall = {
      x: event.end_coordinates ? event.end_coordinates.x : event.start_coordinates.x,
      y: event.end_coordinates ? event.end_coordinates.y : event.start_coordinates.y,
    };

    if (event.player) {
      this.activePlayerNode = event.player.name;
    }

    if (event.start_coordinates && event.end_coordinates) {
      this.passVectors.push({
        start: event.start_coordinates,
        end: event.end_coordinates,
        type: event.event_type,
        difficulty: event.pass_difficulty_rating || 0.3,
        team: event.team_id,
        xg: event.expected_goals,
        is_sprint: event.is_sprint_burst,
        timestamp: Date.now(),
      });
      if (this.passVectors.length > 8) this.passVectors.shift();
    }

    this.renderPitch();
  }

  appendTelemetryRow(event, timecode) {
    const list = document.getElementById("telemetry-list");
    const placeholder = list.querySelector(".telemetry-placeholder");
    if (placeholder) placeholder.remove();

    const row = document.createElement("div");
    row.className = "telemetry-item";

    const badgeClass = `tele-badge tele-badge-${event.event_type.replace('_', '')}`;
    const playerName = event.player ? event.player.name : "Team";
    const teamShort = event.team_id === "avalon_city" ? "AVA" : "SOL";

    let metricText = "";
    if (event.expected_goals) {
      metricText += `xG: ${event.expected_goals} | `;
    }
    if (event.ball_speed_kmh) {
      metricText += `${event.ball_speed_kmh} km/h `;
    }
    if (event.pass_distance_m) {
      metricText += `| ${event.pass_distance_m}m (diff: ${event.pass_difficulty_rating})`;
    }
    if (event.is_sprint_burst) {
      metricText += ` | 🔥 SPRINT`;
    }

    row.innerHTML = `
      <div class="tele-left">
        <span class="tele-time">${timecode}</span>
        <span class="${badgeClass}">${event.event_type}</span>
        <span style="font-weight: 600;">${playerName} (${teamShort})</span>
      </div>
      <div class="tele-metrics">${metricText}</div>
    `;

    list.insertBefore(row, list.firstChild);
    if (list.children.length > 30) {
      list.removeChild(list.lastChild);
    }
  }

  pulsePipeline() {
    const steps = ["step-ingest", "step-analyst", "step-narrator", "step-verifier", "step-broadcast"];
    steps.forEach((id, idx) => {
      setTimeout(() => {
        const el = document.getElementById(id);
        if (el) {
          el.classList.add("pulse");
          setTimeout(() => el.classList.remove("pulse"), 500);
        }
      }, idx * 120);
    });
  }

  /* -------------------------------------------------------------------------
     Tactical 2D Pitch Visualizer Engine (Canvas)
     ------------------------------------------------------------------------- */

  initPitch() {
    const dpr = window.devicePixelRatio || 1;
    const rect = this.canvas.getBoundingClientRect();
    this.canvas.width = rect.width * dpr;
    this.canvas.height = rect.height * dpr;
    this.ctx.scale(dpr, dpr);
    this.pitchW = rect.width;
    this.pitchH = rect.height;
  }

  toCanvasCoords(normX, normY) {
    const pad = 24;
    const w = this.pitchW - pad * 2;
    const h = this.pitchH - pad * 2;
    return {
      x: pad + (normX / 100) * w,
      y: pad + (normY / 100) * h,
    };
  }

  renderPitch() {
    const ctx = this.ctx;
    const w = this.pitchW;
    const h = this.pitchH;

    ctx.clearRect(0, 0, w, h);

    // 1. Grass texture with pitch stripes
    const stripes = 10;
    const stripeW = w / stripes;
    for (let i = 0; i < stripes; i++) {
      ctx.fillStyle = i % 2 === 0 ? "#0d2017" : "#0f261c";
      ctx.fillRect(i * stripeW, 0, stripeW, h);
    }

    // 2. Optional Zonal Heatmap Overlay
    if (this.showHeatmap) {
      const thirdW = w / 3;
      // Defensive third (Home)
      ctx.fillStyle = "rgba(0, 163, 224, 0.12)";
      ctx.fillRect(0, 0, thirdW, h);
      // Middle contest third
      ctx.fillStyle = "rgba(245, 158, 11, 0.12)";
      ctx.fillRect(thirdW, 0, thirdW, h);
      // Attacking third (Away goal)
      ctx.fillStyle = "rgba(225, 29, 72, 0.12)";
      ctx.fillRect(thirdW * 2, 0, thirdW, h);

      ctx.fillStyle = "rgba(255, 255, 255, 0.4)";
      ctx.font = "10px JetBrains Mono";
      ctx.fillText("DEFENSIVE THIRD (34%)", 30, 20);
      ctx.fillText("MIDDLE THIRD (42%)", thirdW + 30, 20);
      ctx.fillText("ATTACKING THIRD (24%)", thirdW * 2 + 30, 20);
    }

    // 3. Pitch Boundary & Lines
    const pad = 24;
    ctx.strokeStyle = "rgba(255, 255, 255, 0.35)";
    ctx.lineWidth = 2;

    ctx.strokeRect(pad, pad, w - pad * 2, h - pad * 2);

    // Halfway line & center circle
    const midX = w / 2;
    ctx.beginPath();
    ctx.moveTo(midX, pad);
    ctx.lineTo(midX, h - pad);
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(midX, h / 2, 54, 0, Math.PI * 2);
    ctx.stroke();

    ctx.fillStyle = "rgba(255, 255, 255, 0.6)";
    ctx.beginPath();
    ctx.arc(midX, h / 2, 4, 0, Math.PI * 2);
    ctx.fill();

    // Penalty Boxes
    const boxW = 80;
    const boxH = 160;
    const boxY = (h - boxH) / 2;

    ctx.strokeRect(pad, boxY, boxW, boxH);
    ctx.strokeRect(w - pad - boxW, boxY, boxW, boxH);

    // 4. Render Formations & Players
    this.renderTeamNodes(this.homeFormation, "#00A3E0", "#ffffff");
    this.renderTeamNodes(this.awayFormation, "#e11d48", "#FFD100");

    // 5. Render Pass & Shot Vectors
    this.passVectors.forEach((vec) => {
      const p1 = this.toCanvasCoords(vec.start.x, vec.start.y);
      const p2 = this.toCanvasCoords(vec.end.x, vec.end.y);

      let strokeColor = "#00f2fe";
      if (vec.type === "shot" || vec.type === "goal") strokeColor = "#ec4899";
      else if (vec.difficulty > 0.7) strokeColor = "#e11d48";
      else if (vec.difficulty > 0.45) strokeColor = "#f59e0b";

      ctx.save();
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = vec.type === "shot" || vec.type === "goal" ? 3.5 : 2.5;
      ctx.shadowColor = strokeColor;
      ctx.shadowBlur = 10;

      ctx.beginPath();
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);
      ctx.stroke();

      // Arrow head or xG callout
      ctx.fillStyle = strokeColor;
      ctx.beginPath();
      ctx.arc(p2.x, p2.y, 4, 0, Math.PI * 2);
      ctx.fill();

      if (vec.xg) {
        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 10px JetBrains Mono";
        ctx.fillText(`xG ${vec.xg}`, p2.x + 8, p2.y - 4);
      }
      ctx.restore();
    });

    // 6. Render Ball with Glow
    const ballPos = this.toCanvasCoords(this.currentBall.x, this.currentBall.y);
    ctx.save();
    ctx.shadowColor = "#00f2fe";
    ctx.shadowBlur = 20;
    ctx.fillStyle = "#ffffff";
    ctx.beginPath();
    ctx.arc(ballPos.x, ballPos.y, 7, 0, Math.PI * 2);
    ctx.fill();

    ctx.strokeStyle = "#00f2fe";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(ballPos.x, ballPos.y, 12, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
  }

  renderTeamNodes(players, kitColor, secondaryColor) {
    const ctx = this.ctx;
    players.forEach((p) => {
      const pos = this.toCanvasCoords(p.x, p.y);
      const isActive = this.activePlayerNode && this.activePlayerNode.toLowerCase().includes(p.name.toLowerCase());
      const isTargetSpotlight = this.currentPlayer && p.name.toLowerCase().includes(this.currentPlayer.toLowerCase());

      ctx.save();
      if (isActive || isTargetSpotlight) {
        ctx.strokeStyle = "#00f2fe";
        ctx.lineWidth = 2.5;
        ctx.shadowColor = "#00f2fe";
        ctx.shadowBlur = 14;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 11, 0, Math.PI * 2);
        ctx.stroke();
      }

      ctx.fillStyle = kitColor;
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, 7, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = secondaryColor;
      ctx.font = "bold 8px Outfit";
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(p.num, pos.x, pos.y);
      ctx.restore();
    });
  }
}

// Instantiate on DOMContentLoaded
window.addEventListener("DOMContentLoaded", () => {
  window.omniPitch = new OmniPitchApp();
});
