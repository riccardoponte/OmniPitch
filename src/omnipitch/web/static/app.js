/**
 * OmniPitch Live Match Intelligence & Interactive Pitch Visualizer
 */

class OmniPitchApp {
  constructor() {
    this.matchId = "MATCH-2026-001";
    this.currentPersona = "analyst";
    this.currentLang = "en";
    this.isStreaming = false;

    // SSE EventSource instances
    this.overlaySource = null;
    this.eventSource = null;

    // Canvas setup
    this.canvas = document.getElementById("pitch-canvas");
    this.ctx = this.canvas.getContext("2d");

    // State cache
    this.eventsReceived = 0;
    this.currentBall = { x: 50, y: 50 };
    this.passVectors = [];
    this.homeScore = 0;
    this.awayScore = 0;

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

    // Reset button
    const resetBtn = document.getElementById("btn-reset");
    resetBtn.addEventListener("click", () => this.resetSimulation());

    // JSON Inspector toggle
    const jsonBtn = document.getElementById("btn-toggle-json");
    const jsonBox = document.getElementById("json-inspector");
    jsonBtn.addEventListener("click", () => {
      jsonBox.classList.toggle("hidden");
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

    // Start Overlay SSE stream
    const overlayUrl = `/api/match/${this.matchId}/overlays/stream?persona=${this.currentPersona}&lang=${this.currentLang}&delay=1.0`;
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

  /* -------------------------------------------------------------------------
     Real-Time Multi-Agent Handlers
     ------------------------------------------------------------------------- */

  handleBroadcastOverlay(overlay) {
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

    // 4. Update JSON Inspector code
    document.getElementById("json-code").textContent = JSON.stringify(overlay, null, 2);

    // 5. Update Tactical Gauges
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

    if (event.start_coordinates && event.end_coordinates) {
      this.passVectors.push({
        start: event.start_coordinates,
        end: event.end_coordinates,
        type: event.event_type,
        difficulty: event.pass_difficulty_rating || 0.3,
        team: event.team_id,
        timestamp: Date.now(),
      });
      // Keep only last 8 vectors for visual clarity
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
    if (event.ball_speed_kmh) {
      metricText += `${event.ball_speed_kmh} km/h `;
    }
    if (event.pass_distance_m) {
      metricText += `| ${event.pass_distance_m}m (diff: ${event.pass_difficulty_rating})`;
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

    // Limit list rows in DOM
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
    // Set high-DPI scaling
    const dpr = window.devicePixelRatio || 1;
    const rect = this.canvas.getBoundingClientRect();
    this.canvas.width = rect.width * dpr;
    this.canvas.height = rect.height * dpr;
    this.ctx.scale(dpr, dpr);
    this.pitchW = rect.width;
    this.pitchH = rect.height;
  }

  toCanvasCoords(normX, normY) {
    // normX: 0-100, normY: 0-100
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

    // 1. Grass texture with subtle pitch stripes
    const stripes = 10;
    const stripeW = w / stripes;
    for (let i = 0; i < stripes; i++) {
      ctx.fillStyle = i % 2 === 0 ? "#0d2017" : "#0f261c";
      ctx.fillRect(i * stripeW, 0, stripeW, h);
    }

    // 2. Pitch Boundary & Lines
    const pad = 24;
    ctx.strokeStyle = "rgba(255, 255, 255, 0.35)";
    ctx.lineWidth = 2;

    // Outer boundary
    ctx.strokeRect(pad, pad, w - pad * 2, h - pad * 2);

    // Halfway line
    const midX = w / 2;
    ctx.beginPath();
    ctx.moveTo(midX, pad);
    ctx.lineTo(midX, h - pad);
    ctx.stroke();

    // Center circle
    ctx.beginPath();
    ctx.arc(midX, h / 2, 54, 0, Math.PI * 2);
    ctx.stroke();

    // Center spot
    ctx.fillStyle = "rgba(255, 255, 255, 0.6)";
    ctx.beginPath();
    ctx.arc(midX, h / 2, 4, 0, Math.PI * 2);
    ctx.fill();

    // Penalty Boxes
    const boxW = 80;
    const boxH = 160;
    const boxY = (h - boxH) / 2;

    // Left Box (Defending Goal)
    ctx.strokeRect(pad, boxY, boxW, boxH);
    // Right Box (Attacking Goal)
    ctx.strokeRect(w - pad - boxW, boxY, boxW, boxH);

    // 3. Render Pass Vectors
    const now = Date.now();
    this.passVectors.forEach((vec) => {
      const p1 = this.toCanvasCoords(vec.start.x, vec.start.y);
      const p2 = this.toCanvasCoords(vec.end.x, vec.end.y);

      // Color code by difficulty
      let strokeColor = "#00f2fe";
      if (vec.difficulty > 0.7) strokeColor = "#e11d48";
      else if (vec.difficulty > 0.45) strokeColor = "#f59e0b";

      ctx.save();
      ctx.strokeStyle = strokeColor;
      ctx.lineWidth = 2.5;
      ctx.shadowColor = strokeColor;
      ctx.shadowBlur = 8;

      ctx.beginPath();
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);
      ctx.stroke();

      // Arrow head
      const angle = Math.atan2(p2.y - p1.y, p2.x - p1.x);
      ctx.fillStyle = strokeColor;
      ctx.beginPath();
      ctx.arc(p2.x, p2.y, 4, 0, Math.PI * 2);
      ctx.fill();
      ctx.restore();
    });

    // 4. Render Ball
    const ballPos = this.toCanvasCoords(this.currentBall.x, this.currentBall.y);
    ctx.save();
    ctx.shadowColor = "#00f2fe";
    ctx.shadowBlur = 18;
    ctx.fillStyle = "#ffffff";
    ctx.beginPath();
    ctx.arc(ballPos.x, ballPos.y, 7, 0, Math.PI * 2);
    ctx.fill();

    ctx.strokeStyle = "#00f2fe";
    ctx.lineWidth = 2;
    ctx.beginPath();
    ctx.arc(ballPos.x, ballPos.y, 11, 0, Math.PI * 2);
    ctx.stroke();
    ctx.restore();
  }
}

// Instantiate on DOMContentLoaded
window.addEventListener("DOMContentLoaded", () => {
  window.omniPitch = new OmniPitchApp();
});
