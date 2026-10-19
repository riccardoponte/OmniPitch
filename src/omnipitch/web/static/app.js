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
    this.matchCenterData = null;
    this.currentFormation = "4-3-3";
    this.pitchMode = "telemetry"; // "telemetry" or "formations"
    this.liveTableRows = [];
    this.currentDataTableFilter = "all";
    this.activeModalPlayerName = "";
    this.activeModalPlayerId = "";

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
    this.fetchMatchCenterOverview();
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

    // Tactical Formation Switcher
    const formationSelect = document.getElementById("formation-select");
    if (formationSelect) {
      formationSelect.addEventListener("change", (e) => {
        this.applyFormation(e.target.value);
      });
    }

    // Match Report Export button
    const reportBtn = document.getElementById("btn-export-match-report");
    if (reportBtn) {
      reportBtn.addEventListener("click", () => this.exportMatchReport());
    }

    // Pitch Mode Toggle button (Tactical XI Formations vs Live Telemetry)
    const btnPitchMode = document.getElementById("btn-toggle-pitch-mode");
    if (btnPitchMode) {
      btnPitchMode.addEventListener("click", () => {
        this.pitchMode = this.pitchMode === "telemetry" ? "formations" : "telemetry";
        btnPitchMode.classList.toggle("active", this.pitchMode === "formations");
        btnPitchMode.textContent = this.pitchMode === "formations" ? "👥 Formations: ON" : "👥 Tactical XI View";
        this.renderPitch();
      });
    }

    // Match Center Tabs Switching
    const mcTabs = document.querySelectorAll(".mc-tab-btn");
    mcTabs.forEach((btn) => {
      btn.addEventListener("click", () => {
        mcTabs.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        const targetId = btn.getAttribute("data-tab");
        document.querySelectorAll(".mc-tab-content").forEach((c) => c.classList.remove("active"));
        const target = document.getElementById(targetId);
        if (target) target.classList.add("active");

        if (targetId === "tab-momentum") this.renderAttackMomentum();
        if (targetId === "tab-shotmap") this.renderShotMap();
        if (targetId === "tab-datatable") this.fetchLiveDataTable();
        if (targetId === "tab-foundry") this.fetchFoundryHubData();
      });
    });

    // Momentum canvas hover
    const momCanvas = document.getElementById("momentum-canvas");
    if (momCanvas) {
      momCanvas.addEventListener("mousemove", (e) => this.handleMomentumHover(e));
      momCanvas.addEventListener("mouseleave", () => {
        const tip = document.getElementById("momentum-tooltip");
        if (tip) tip.classList.add("hidden");
      });
    }

    // Shot map canvas hover
    const shotCanvas = document.getElementById("shotmap-canvas");
    if (shotCanvas) {
      shotCanvas.addEventListener("mousemove", (e) => this.handleShotMapHover(e));
      shotCanvas.addEventListener("mouseleave", () => {
        const tip = document.getElementById("shotmap-tooltip");
        if (tip) tip.classList.add("hidden");
      });
    }

    // Team Standings & Club Profile Triggers
    const homeTeamTriggers = [
      document.getElementById("home-team-trigger"),
      document.getElementById("lineup-home-team-trigger"),
    ];
    homeTeamTriggers.forEach((trigger) => {
      if (trigger) {
        trigger.addEventListener("click", () => this.openTeamModal("avalon_city"));
      }
    });

    const awayTeamTriggers = [
      document.getElementById("away-team-trigger"),
      document.getElementById("lineup-away-team-trigger"),
    ];
    awayTeamTriggers.forEach((trigger) => {
      if (trigger) {
        trigger.addEventListener("click", () => this.openTeamModal("solaria_rovers"));
      }
    });

    // Team Modal Close & Tab Switching
    const btnCloseTeamModal = document.getElementById("btn-close-team-modal");
    if (btnCloseTeamModal) {
      btnCloseTeamModal.addEventListener("click", () => this.closeTeamModal());
    }

    const teamModal = document.getElementById("team-modal");
    if (teamModal) {
      teamModal.addEventListener("click", (e) => {
        if (e.target === teamModal) this.closeTeamModal();
      });
    }

    const modalTabBtns = document.querySelectorAll("#team-modal .modal-tab-btn");
    modalTabBtns.forEach((btn) => {
      btn.addEventListener("click", () => {
        modalTabBtns.forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        const targetPaneId = btn.getAttribute("data-modaltab");
        document.querySelectorAll("#team-modal .modal-tab-pane").forEach((p) => p.classList.remove("active"));
        const targetPane = document.getElementById(targetPaneId);
        if (targetPane) targetPane.classList.add("active");
      });
    });

    // Player Dossier Modal Close & Spotlight Focus
    const btnClosePlayerModal = document.getElementById("btn-close-player-modal");
    if (btnClosePlayerModal) {
      btnClosePlayerModal.addEventListener("click", () => this.closePlayerModal());
    }

    const playerModal = document.getElementById("player-modal");
    if (playerModal) {
      playerModal.addEventListener("click", (e) => {
        if (e.target === playerModal) this.closePlayerModal();
      });
    }

    const btnSpotlightFromModal = document.getElementById("btn-spotlight-from-modal");
    if (btnSpotlightFromModal) {
      btnSpotlightFromModal.addEventListener("click", () => {
        if (this.activeModalPlayerName) {
          this.selectSpotlightPlayer(this.activeModalPlayerName);
          this.closePlayerModal();
        }
      });
    }

    // ESC key closes any open modal
    window.addEventListener("keydown", (e) => {
      if (e.key === "Escape") {
        this.closeTeamModal();
        this.closePlayerModal();
      }
    });

    // Live Data Table Filters & Search
    const dtSearch = document.getElementById("datatable-search");
    if (dtSearch) {
      dtSearch.addEventListener("input", () => this.renderLiveDataTable());
    }

    const dtPills = document.querySelectorAll("#datatable-pills .type-pill");
    dtPills.forEach((pill) => {
      pill.addEventListener("click", () => {
        dtPills.forEach((p) => p.classList.remove("active"));
        pill.classList.add("active");
        this.currentDataTableFilter = pill.getAttribute("data-type") || "all";
        this.renderLiveDataTable();
      });
    });

    // CSV Telemetry Export button
    const btnDownloadCsv = document.getElementById("btn-download-csv");
    if (btnDownloadCsv) {
      btnDownloadCsv.addEventListener("click", () => {
        window.open(`/api/match/${this.matchId}/events/csv`, "_blank");
      });
    }

    // Tab 7: Power Automate & Adaptive Card Controls
    const btnDispatchPa = document.getElementById("btn-dispatch-pa");
    if (btnDispatchPa) {
      btnDispatchPa.addEventListener("click", () => this.dispatchPowerAutomateWorkflow());
    }

    const paEventSelect = document.getElementById("pa-event-type-select");
    if (paEventSelect) {
      paEventSelect.addEventListener("change", () => this.updateAdaptiveCardPreview());
    }

    const btnCopyCardJson = document.getElementById("btn-copy-card-json");
    if (btnCopyCardJson) {
      btnCopyCardJson.addEventListener("click", () => {
        const code = document.getElementById("ac-json-code");
        if (code && navigator.clipboard) {
          navigator.clipboard.writeText(code.textContent);
          btnCopyCardJson.textContent = "✓ Copied!";
          setTimeout(() => (btnCopyCardJson.textContent = "📋 Copy JSON"), 2000);
        }
      });
    }
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
    this.playWhistleSound();

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

  async resetSimulation() {
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

    try {
      await fetch(`/api/match/${this.matchId}/reset`, { method: "POST" });
      await this.fetchMatchCenterOverview();
    } catch (e) {
      console.warn("Error resetting match backend session:", e);
    }
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

    // Update Pro Match Center Live Data Table
    this.prependLiveTableRow(event, `${mm}:${ss}`);

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

    // Dynamically update match center overview on live stream events
    if (this.eventsReceived % 2 === 0 || event.event_type === "goal" || event.event_type === "shot") {
      this.fetchMatchCenterOverview();
    }
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

    this.canvas.addEventListener("click", (e) => this.handlePitchClick(e));
    this.canvas.addEventListener("mousemove", (e) => this.handlePitchMouseMove(e));
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

    // Branch to full tactical formations head-to-head comparison if toggled
    if (this.pitchMode === "formations") {
      this.renderTacticalFormations(ctx, w, h);
      return;
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

  /* ==============================================================================
     Pro Match Intelligence Center & Tactical Dynamics Methods
     ============================================================================== */

  playWhistleSound() {
    try {
      const audioCtx = new (window.AudioContext || window.webkitAudioContext)();
      const osc = audioCtx.createOscillator();
      const gain = audioCtx.createGain();
      osc.type = "sine";
      osc.frequency.setValueAtTime(2400, audioCtx.currentTime);
      osc.frequency.exponentialRampToValueAtTime(1800, audioCtx.currentTime + 0.15);
      gain.gain.setValueAtTime(0.12, audioCtx.currentTime);
      gain.gain.exponentialRampToValueAtTime(0.01, audioCtx.currentTime + 0.25);
      osc.connect(gain);
      gain.connect(audioCtx.destination);
      osc.start();
      osc.stop(audioCtx.currentTime + 0.26);
    } catch (e) {}
  }

  applyFormation(fmt) {
    this.currentFormation = fmt;
    const badge = document.getElementById("lineup-home-formation-badge");
    if (badge) badge.textContent = fmt;

    if (fmt === "4-2-3-1") {
      this.homeFormation[0] = { id: "AVA-01", name: "Marcus Vance", num: 1, role: "GK", x: 6, y: 50 };
      this.homeFormation[1] = { id: "AVA-02", name: "Leo Sterling", num: 2, role: "DEF", x: 22, y: 20 };
      this.homeFormation[2] = { id: "AVA-04", name: "Tobias Thorne", num: 4, role: "DEF", x: 19, y: 40 };
      this.homeFormation[3] = { id: "AVA-05", name: "Dorian Cole", num: 5, role: "DEF", x: 19, y: 60 };
      this.homeFormation[4] = { id: "AVA-03", name: "Nico Lind", num: 3, role: "DEF", x: 22, y: 80 };
      this.homeFormation[5] = { id: "AVA-06", name: "Mateo Rios", num: 6, role: "MID", x: 36, y: 38 };
      this.homeFormation[6] = { id: "AVA-08", name: "Julian Drake", num: 8, role: "MID", x: 36, y: 62 };
      this.homeFormation[7] = { id: "AVA-10", name: "Kaelen Cross", num: 10, role: "MID", x: 52, y: 50 };
      this.homeFormation[8] = { id: "AVA-07", name: "Finneas Frost", num: 7, role: "FWD", x: 54, y: 22 };
      this.homeFormation[9] = { id: "AVA-09", name: "Cyrus Kane", num: 9, role: "FWD", x: 74, y: 50 };
      this.homeFormation[10] = { id: "AVA-11", name: "Bram Walker", num: 11, role: "FWD", x: 54, y: 78 };
    } else if (fmt === "3-5-2") {
      this.homeFormation[0] = { id: "AVA-01", name: "Marcus Vance", num: 1, role: "GK", x: 6, y: 50 };
      this.homeFormation[1] = { id: "AVA-02", name: "Leo Sterling", num: 2, role: "DEF", x: 19, y: 30 };
      this.homeFormation[2] = { id: "AVA-04", name: "Tobias Thorne", num: 4, role: "DEF", x: 18, y: 50 };
      this.homeFormation[3] = { id: "AVA-05", name: "Dorian Cole", num: 5, role: "DEF", x: 19, y: 70 };
      this.homeFormation[4] = { id: "AVA-03", name: "Nico Lind", num: 3, role: "DEF", x: 36, y: 16 };
      this.homeFormation[5] = { id: "AVA-06", name: "Mateo Rios", num: 6, role: "MID", x: 40, y: 40 };
      this.homeFormation[6] = { id: "AVA-08", name: "Julian Drake", num: 8, role: "MID", x: 40, y: 60 };
      this.homeFormation[7] = { id: "AVA-10", name: "Kaelen Cross", num: 10, role: "MID", x: 50, y: 50 };
      this.homeFormation[8] = { id: "AVA-07", name: "Finneas Frost", num: 7, role: "FWD", x: 36, y: 84 };
      this.homeFormation[9] = { id: "AVA-09", name: "Cyrus Kane", num: 9, role: "FWD", x: 72, y: 40 };
      this.homeFormation[10] = { id: "AVA-11", name: "Bram Walker", num: 11, role: "FWD", x: 72, y: 60 };
    } else {
      // Default 4-3-3
      this.homeFormation[0] = { id: "AVA-01", name: "Marcus Vance", num: 1, role: "GK", x: 6, y: 50 };
      this.homeFormation[1] = { id: "AVA-02", name: "Leo Sterling", num: 2, role: "DEF", x: 22, y: 20 };
      this.homeFormation[2] = { id: "AVA-04", name: "Tobias Thorne", num: 4, role: "DEF", x: 19, y: 40 };
      this.homeFormation[3] = { id: "AVA-05", name: "Dorian Cole", num: 5, role: "DEF", x: 19, y: 60 };
      this.homeFormation[4] = { id: "AVA-03", name: "Nico Lind", num: 3, role: "DEF", x: 22, y: 80 };
      this.homeFormation[5] = { id: "AVA-06", name: "Mateo Rios", num: 6, role: "MID", x: 38, y: 50 };
      this.homeFormation[6] = { id: "AVA-08", name: "Julian Drake", num: 8, role: "MID", x: 48, y: 32 };
      this.homeFormation[7] = { id: "AVA-10", name: "Kaelen Cross", num: 10, role: "MID", x: 48, y: 68 };
      this.homeFormation[8] = { id: "AVA-07", name: "Finneas Frost", num: 7, role: "FWD", x: 70, y: 22 };
      this.homeFormation[9] = { id: "AVA-09", name: "Cyrus Kane", num: 9, role: "FWD", x: 74, y: 50 };
      this.homeFormation[10] = { id: "AVA-11", name: "Bram Walker", num: 11, role: "FWD", x: 70, y: 78 };
    }
    this.renderPitch();
  }

  exportMatchReport() {
    if (!this.matchCenterData) return;
    const blob = new Blob([JSON.stringify(this.matchCenterData, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `OmniPitch-MatchReport-${this.matchId}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }

  async fetchMatchCenterOverview() {
    try {
      const res = await fetch(`/api/match/${this.matchId}/matchcenter/overview`);
      if (!res.ok) return;
      const data = await res.json();
      this.matchCenterData = data;

      this.renderAttackMomentum();
      this.renderH2HComparison();
      this.renderLineupsRatings();
      this.renderShotMap();
      this.renderTimeline();
    } catch (err) {
      console.warn("Match center overview fetch error:", err);
    }
  }

  renderAttackMomentum() {
    const canvas = document.getElementById("momentum-canvas");
    if (!canvas || !this.matchCenterData) return;
    const ctx = canvas.getContext("2d");
    const pts = this.matchCenterData.attack_momentum || [];
    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);

    // Background & center zero line
    ctx.fillStyle = "rgba(0, 0, 0, 0.45)";
    ctx.fillRect(0, 0, w, h);

    const centerY = h / 2;
    ctx.strokeStyle = "rgba(255, 255, 255, 0.15)";
    ctx.lineWidth = 1;
    ctx.setLineDash([4, 4]);
    ctx.beginPath();
    ctx.moveTo(40, centerY);
    ctx.lineTo(w - 20, centerY);
    ctx.stroke();
    ctx.setLineDash([]);

    // Minute markers every 15 min
    ctx.fillStyle = "#64748b";
    ctx.font = "10px JetBrains Mono";
    ctx.textAlign = "center";
    for (let m = 15; m <= 90; m += 15) {
      const x = 40 + (m / 90) * (w - 70);
      ctx.fillText(`${m}'`, x, centerY + 14);
      ctx.strokeStyle = "rgba(255, 255, 255, 0.06)";
      ctx.beginPath();
      ctx.moveTo(x, 15);
      ctx.lineTo(x, h - 15);
      ctx.stroke();
    }

    ctx.fillText("0", 25, centerY + 3);

    if (!pts.length) {
      ctx.fillStyle = "#64748b";
      ctx.font = "600 13px Outfit";
      ctx.textAlign = "center";
      ctx.fillText("Awaiting match kickoff — Dynamic momentum curve activates with live match stream", w / 2, centerY - 25);
      return;
    }

    // Render bars
    const totalSlots = Math.max(pts.length, 45);
    const availableWidth = w - 70;
    const barWidth = Math.max(availableWidth / totalSlots - 3, 4);

    pts.forEach((pt, idx) => {
      const x = 40 + (idx / totalSlots) * availableWidth;
      const barH = (Math.abs(pt.value) / 100.0) * (centerY - 30);

      ctx.save();
      if (pt.value > 0) {
        // Home dominance (Upward)
        ctx.fillStyle = "#00f2fe";
        ctx.shadowColor = "rgba(0, 242, 254, 0.5)";
        ctx.shadowBlur = 6;
        ctx.fillRect(x, centerY - barH, barWidth, barH);
      } else if (pt.value < 0) {
        // Away dominance (Downward)
        ctx.fillStyle = "#e11d48";
        ctx.shadowColor = "rgba(225, 29, 72, 0.5)";
        ctx.shadowBlur = 6;
        ctx.fillRect(x, centerY, barWidth, barH);
      } else {
        // Neutral
        ctx.fillStyle = "#334155";
        ctx.fillRect(x, centerY - 2, barWidth, 4);
      }
      ctx.restore();

      // Render incident icons if any
      if (pt.incidents && pt.incidents.length > 0) {
        pt.incidents.forEach((inc) => {
          const iconY = pt.value >= 0 ? Math.max(centerY - barH - 14, 18) : Math.min(centerY + barH + 18, h - 8);
          ctx.font = "13px sans-serif";
          ctx.textAlign = "center";
          ctx.fillText(inc.icon || "⚽", x + barWidth / 2, iconY);
        });
      }
    });
  }

  handleMomentumHover(e) {
    const canvas = document.getElementById("momentum-canvas");
    const tip = document.getElementById("momentum-tooltip");
    if (!canvas || !tip || !this.matchCenterData) return;

    const rect = canvas.getBoundingClientRect();
    const mouseX = ((e.clientX - rect.left) / rect.width) * canvas.width;
    const pts = this.matchCenterData.attack_momentum || [];
    if (!pts.length) return;

    const totalSlots = Math.max(pts.length, 45);
    const availableWidth = canvas.width - 70;
    const relX = mouseX - 40;
    const idx = Math.floor((relX / availableWidth) * totalSlots);

    if (idx >= 0 && idx < pts.length) {
      const pt = pts[idx];
      const domName = pt.value > 5 ? "Avalon City FC" : (pt.value < -5 ? "Solaria Rovers" : "Neutral Contest");
      let incidentText = "";
      if (pt.incidents && pt.incidents.length > 0) {
        incidentText = `<div style="color: #fbbf24; margin-top: 4px;">${pt.incidents.map(i => `${i.icon} ${i.player}`).join(', ')}</div>`;
      }

      tip.innerHTML = `
        <div style="font-weight: 800; color: #00f2fe; margin-bottom: 2px;">Minute ${pt.minute}'</div>
        <div>Dominance: <span style="color: #ffffff; font-weight: 600;">${domName}</span> (${pt.value > 0 ? '+' : ''}${pt.value})</div>
        ${incidentText}
      `;
      tip.style.left = `${Math.min(e.clientX - rect.left + 15, rect.width - 220)}px`;
      tip.style.top = `${Math.min(e.clientY - rect.top + 10, rect.height - 60)}px`;
      tip.classList.remove("hidden");
    } else {
      tip.classList.add("hidden");
    }
  }

  renderH2HComparison() {
    const container = document.getElementById("h2h-stats-container");
    if (!container || !this.matchCenterData) return;
    const stats = this.matchCenterData.comparison_stats;
    if (!stats) return;

    const metrics = [
      { key: "expected_goals", label: "Expected Goals (xG)", isFloat: true },
      { key: "possession", label: "Ball Possession %", isFloat: true, suffix: "%" },
      { key: "total_shots", label: "Total Shots" },
      { key: "shots_on_target", label: "Shots on Target" },
      { key: "big_chances", label: "Big Chances" },
      { key: "big_chances_missed", label: "Big Chances Missed" },
      { key: "accurate_passes", label: "Accurate Passes", customVal: true },
      { key: "corners", label: "Corner Kicks" },
      { key: "tackles_won", label: "Tackles Won", customVal: true },
      { key: "fouls", label: "Fouls" },
    ];

    container.innerHTML = metrics.map((m) => {
      const data = stats[m.key] || { home: 0, away: 0 };
      let homeDisplay = data.home;
      let awayDisplay = data.away;

      let homeVal = typeof data.home === "number" ? data.home : parseFloat(data.home);
      let awayVal = typeof data.away === "number" ? data.away : parseFloat(data.away);

      if (m.isFloat) {
        if (typeof data.home === "number") homeDisplay = data.home.toFixed(2);
        if (typeof data.away === "number") awayDisplay = data.away.toFixed(2);
      }

      if (m.suffix && !m.customVal) {
        homeDisplay = `${typeof data.home === "number" ? data.home.toFixed(1) : data.home}%`;
        awayDisplay = `${typeof data.away === "number" ? data.away.toFixed(1) : data.away}%`;
      }

      const total = (homeVal + awayVal) || 0;
      let homePct = 50;
      let awayPct = 50;
      let isHomeLeader = false;
      let isAwayLeader = false;

      if (total > 0 && homeVal !== awayVal) {
        homePct = Math.round((homeVal / total) * 100);
        awayPct = 100 - homePct;
        isHomeLeader = homeVal > awayVal;
        isAwayLeader = awayVal > homeVal;
      }

      return `
        <div class="h2h-stat-row">
          <div class="h2h-values">
            <span class="h2h-val-home ${isHomeLeader ? 'leader' : ''}">${homeDisplay}</span>
            <span class="h2h-label">${m.label}</span>
            <span class="h2h-val-away ${isAwayLeader ? 'leader' : ''}">${awayDisplay}</span>
          </div>
          <div class="h2h-bar-track">
            <div class="h2h-bar-home ${isHomeLeader ? 'leader' : ''}" style="width: ${homePct}%;"></div>
            <div class="h2h-bar-away ${isAwayLeader ? 'leader' : ''}" style="width: ${awayPct}%;"></div>
          </div>
        </div>
      `;
    }).join("");
  }

  renderLineupsRatings() {
    if (!this.matchCenterData || !this.matchCenterData.lineups) return;
    const homeList = document.getElementById("home-player-ratings");
    const awayList = document.getElementById("away-player-ratings");
    if (!homeList || !awayList) return;

    const renderPlayers = (players) => {
      return players.map((p) => {
        const ratingClass = p.rating_color === "green" ? "rating-green" : (p.rating_color === "red" ? "rating-red" : "rating-orange");
        const mvpBadge = p.is_mvp ? `<span class="mvp-badge">⭐ MVP</span>` : "";

        return `
          <div class="player-rating-card" onclick="window.omniPitch.openPlayerModal('${p.player_id || ''}', '${p.name}')" title="Click to view ${p.name}'s Sporting CV & Scouting Dossier" style="cursor: pointer;">
            <div class="player-info-left">
              <span class="player-jersey-badge">${p.number}</span>
              <span class="player-pos-badge">${p.position}</span>
              <span class="player-rating-name">${p.name}</span>
            </div>
            <div class="player-rating-right">
              ${mvpBadge}
              <span class="pro-rating-pill ${ratingClass}">${p.rating.toFixed(1)}</span>
            </div>
          </div>
        `;
      }).join("");
    };

    homeList.innerHTML = renderPlayers(this.matchCenterData.lineups.home || []);
    awayList.innerHTML = renderPlayers(this.matchCenterData.lineups.away || []);
  }

  selectSpotlightPlayer(name) {
    const sel = document.getElementById("player-select");
    if (sel) {
      let found = false;
      for (let i = 0; i < sel.options.length; i++) {
        if (sel.options[i].value === name || sel.options[i].text.includes(name)) {
          sel.selectedIndex = i;
          found = true;
          break;
        }
      }
      if (!found) {
        const opt = new Option(name, name, true, true);
        sel.add(opt);
      }
      this.currentPlayer = name;
      if (this.isStreaming) this.restartStream();
    }
  }

  renderShotMap() {
    const canvas = document.getElementById("shotmap-canvas");
    if (!canvas || !this.matchCenterData) return;
    const ctx = canvas.getContext("2d");
    const shots = this.matchCenterData.shot_map || [];
    const w = canvas.width;
    const h = canvas.height;

    ctx.clearRect(0, 0, w, h);

    // Draw football pitch penalty half
    ctx.fillStyle = "#0c2016";
    ctx.fillRect(0, 0, w, h);

    // Pitch markings
    ctx.strokeStyle = "rgba(255, 255, 255, 0.25)";
    ctx.lineWidth = 2;

    // Outer boundary
    ctx.strokeRect(30, 30, w - 60, h - 60);

    // Goal mouth
    ctx.strokeRect(w - 30, h / 2 - 50, 18, 100);

    // Penalty Area
    ctx.strokeRect(w - 240, h / 2 - 140, 210, 280);

    // 6-yard Box
    ctx.strokeRect(w - 100, h / 2 - 70, 70, 140);

    // Penalty Spot
    ctx.fillStyle = "#ffffff";
    ctx.beginPath();
    ctx.arc(w - 140, h / 2, 3, 0, Math.PI * 2);
    ctx.fill();

    // Penalty Arc
    ctx.beginPath();
    ctx.arc(w - 140, h / 2, 55, Math.PI * 0.65, Math.PI * 1.35);
    ctx.stroke();

    // Render Shots
    shots.forEach((s) => {
      const sx = 30 + (s.x / 100.0) * (w - 70);
      const sy = 30 + (s.y / 100.0) * (h - 60);
      const r = Math.max((s.xg || 0.1) * 22, 5);

      ctx.save();
      if (s.outcome === "goal") {
        ctx.fillStyle = "#10b981";
        ctx.shadowColor = "#10b981";
        ctx.shadowBlur = 12;
        ctx.beginPath();
        ctx.arc(sx, sy, r, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = "#ffffff";
        ctx.font = "bold 9px JetBrains Mono";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText("⚽", sx, sy);
      } else if (s.outcome === "saved") {
        ctx.fillStyle = "#00f2fe";
        ctx.shadowColor = "#00f2fe";
        ctx.shadowBlur = 8;
        ctx.beginPath();
        ctx.arc(sx, sy, r, 0, Math.PI * 2);
        ctx.fill();
      } else {
        ctx.strokeStyle = "#94a3b8";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(sx, sy, r, 0, Math.PI * 2);
        ctx.stroke();
      }
      ctx.restore();
    });

    // Update Shot Map Summary Sidebar
    const summary = document.getElementById("shotmap-summary");
    if (summary) {
      const goals = shots.filter(s => s.outcome === "goal").length;
      const totalXg = shots.reduce((sum, s) => sum + (s.xg || 0), 0).toFixed(2);
      const conversion = shots.length > 0 ? Math.round((goals / shots.length) * 100) : 0;

      summary.innerHTML = `
        <div class="stat-pill"><span class="stat-num">${shots.length}</span><span class="stat-lbl">Total Shots</span></div>
        <div class="stat-pill"><span class="stat-num" style="color: #10b981;">${goals}</span><span class="stat-lbl">Goals Scored</span></div>
        <div class="stat-pill"><span class="stat-num" style="color: #00f2fe;">${totalXg}</span><span class="stat-lbl">Total xG Created</span></div>
        <div class="stat-pill"><span class="stat-num">${conversion}%</span><span class="stat-lbl">Conversion Rate</span></div>
      `;
    }
  }

  handleShotMapHover(e) {
    const canvas = document.getElementById("shotmap-canvas");
    const tip = document.getElementById("shotmap-tooltip");
    if (!canvas || !tip || !this.matchCenterData) return;

    const rect = canvas.getBoundingClientRect();
    const mx = ((e.clientX - rect.left) / rect.width) * canvas.width;
    const my = ((e.clientY - rect.top) / rect.height) * canvas.height;
    const shots = this.matchCenterData.shot_map || [];

    const w = canvas.width;
    const h = canvas.height;

    const hovered = shots.find((s) => {
      const sx = 30 + (s.x / 100.0) * (w - 70);
      const sy = 30 + (s.y / 100.0) * (h - 60);
      const dist = Math.hypot(mx - sx, my - sy);
      return dist <= Math.max((s.xg || 0.1) * 22, 10);
    });

    if (hovered) {
      tip.innerHTML = `
        <div style="font-weight: 800; color: #00f2fe;">${hovered.player_name} (${hovered.minute}')</div>
        <div>Outcome: <b style="text-transform: uppercase;">${hovered.outcome}</b></div>
        <div>xG: <b>${(hovered.xg || 0).toFixed(2)}</b> &bull; Speed: <b>${hovered.shot_speed_kmh} km/h</b></div>
      `;
      tip.style.left = `${Math.min(e.clientX - rect.left + 15, rect.width - 200)}px`;
      tip.style.top = `${Math.min(e.clientY - rect.top + 10, rect.height - 70)}px`;
      tip.classList.remove("hidden");
    } else {
      tip.classList.add("hidden");
    }
  }

  renderTimeline() {
    const list = document.getElementById("timeline-stream-list");
    if (!list || !this.matchCenterData) return;
    const timeline = this.matchCenterData.timeline || [];

    if (!timeline.length) {
      list.innerHTML = `<div style="text-align: center; color: #64748b; padding: 20px;">No incidents recorded yet. Awaiting match stream kickoff.</div>`;
      return;
    }

    list.innerHTML = timeline.map((item) => {
      const sideClass = item.is_home ? "home" : "away";
      const icon = item.type === "goal" ? "⚽" : (item.type === "card" ? "🟨" : "⚡");

      return `
        <div class="timeline-event-card ${sideClass}">
          <span class="timeline-minute">${item.minute}'</span>
          <span class="timeline-icon">${icon}</span>
          <div class="timeline-details">
            <span class="timeline-title">${item.title}</span>
            <span class="timeline-desc">${item.detail}</span>
          </div>
        </div>
      `;
    }).join("");
  }

  /* ==============================================================================
     Tactical Formations Head-to-Head Visualizer
     ============================================================================== */

  handlePitchClick(e) {
    const rect = this.canvas.getBoundingClientRect();
    const clickX = e.clientX - rect.left;
    const clickY = e.clientY - rect.top;

    const allPlayers = [...this.homeFormation, ...this.awayFormation];
    for (const p of allPlayers) {
      const pos = this.toCanvasCoords(p.x, p.y);
      const dist = Math.hypot(clickX - pos.x, clickY - pos.y);
      if (dist <= 22) {
        this.openPlayerModal(p.id, p.name);
        return;
      }
    }
  }

  handlePitchMouseMove(e) {
    const rect = this.canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;

    const allPlayers = [...this.homeFormation, ...this.awayFormation];
    const hovered = allPlayers.some((p) => {
      const pos = this.toCanvasCoords(p.x, p.y);
      return Math.hypot(mx - pos.x, my - pos.y) <= 22;
    });

    this.canvas.style.cursor = hovered ? "pointer" : "default";
  }

  renderTacticalFormations(ctx, w, h) {
    const pad = 24;

    // Pitch Boundary & Lines
    ctx.strokeStyle = "rgba(255, 255, 255, 0.4)";
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

    // Penalty Boxes
    const boxW = 80;
    const boxH = 160;
    const boxY = (h - boxH) / 2;
    ctx.strokeRect(pad, boxY, boxW, boxH);
    ctx.strokeRect(w - pad - boxW, boxY, boxW, boxH);

    // Tactical Unit Connecting Lines (Defenders, Midfielders, Forwards)
    const drawUnitLines = (players, color) => {
      ctx.save();
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 4]);

      // Group by role
      const defs = players.filter(p => p.role === "DEF");
      const mids = players.filter(p => p.role === "MID");
      const fwds = players.filter(p => p.role === "FWD");

      [defs, mids, fwds].forEach(unit => {
        if (unit.length > 1) {
          ctx.beginPath();
          unit.forEach((p, idx) => {
            const pos = this.toCanvasCoords(p.x, p.y);
            if (idx === 0) ctx.moveTo(pos.x, pos.y);
            else ctx.lineTo(pos.x, pos.y);
          });
          ctx.stroke();
        }
      });
      ctx.restore();
    };

    drawUnitLines(this.homeFormation, "rgba(0, 163, 224, 0.45)");
    drawUnitLines(this.awayFormation, "rgba(225, 29, 72, 0.45)");

    // Banner watermark
    ctx.fillStyle = "rgba(255, 255, 255, 0.55)";
    ctx.font = "600 11px Outfit";
    ctx.textAlign = "center";
    ctx.fillText("TACTICAL HEAD-TO-HEAD FORMATIONS • CLICK ANY PLAYER TO VIEW SPORTING CV & STATS", w / 2, 16);

    // Render Players for both teams
    const renderFormationXI = (players, kitColor, secondaryColor, teamName) => {
      players.forEach((p) => {
        const pos = this.toCanvasCoords(p.x, p.y);
        const isActive = this.activePlayerNode && this.activePlayerNode.toLowerCase().includes(p.name.toLowerCase());
        const isTargetSpotlight = this.currentPlayer && p.name.toLowerCase().includes(this.currentPlayer.toLowerCase());

        // Find live rating if available
        let ratingVal = null;
        let ratingColor = "orange";
        if (this.matchCenterData && this.matchCenterData.lineups) {
          const allLineup = [...(this.matchCenterData.lineups.home || []), ...(this.matchCenterData.lineups.away || [])];
          const matched = allLineup.find(lp => lp.player_id === p.id || lp.name.toLowerCase() === p.name.toLowerCase());
          if (matched) {
            ratingVal = matched.rating;
            ratingColor = matched.rating_color;
          }
        }

        ctx.save();

        // Glowing halo if active or spotlight target
        if (isActive || isTargetSpotlight) {
          ctx.strokeStyle = "#00f2fe";
          ctx.lineWidth = 3;
          ctx.shadowColor = "#00f2fe";
          ctx.shadowBlur = 18;
          ctx.beginPath();
          ctx.arc(pos.x, pos.y, 18, 0, Math.PI * 2);
          ctx.stroke();
        }

        // Tactical node body
        ctx.fillStyle = kitColor;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, 13, 0, Math.PI * 2);
        ctx.fill();

        ctx.strokeStyle = "rgba(255, 255, 255, 0.85)";
        ctx.lineWidth = 1.5;
        ctx.stroke();

        // Jersey number
        ctx.fillStyle = secondaryColor;
        ctx.font = "bold 10px Outfit";
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(p.num, pos.x, pos.y);

        // Role badge above
        ctx.fillStyle = "rgba(0, 0, 0, 0.65)";
        ctx.fillRect(pos.x - 12, pos.y - 25, 24, 10);
        ctx.fillStyle = "#94a3b8";
        ctx.font = "bold 7px JetBrains Mono";
        ctx.fillText(p.role, pos.x, pos.y - 20);

        // Name plate below
        const surname = p.name.split(" ").slice(-1)[0];
        ctx.font = "600 9px Outfit";
        const nameWidth = ctx.measureText(surname).width;
        ctx.fillStyle = "rgba(8, 14, 25, 0.85)";
        ctx.fillRect(pos.x - nameWidth / 2 - 4, pos.y + 16, nameWidth + 8, 13);
        ctx.strokeStyle = "rgba(255, 255, 255, 0.15)";
        ctx.lineWidth = 1;
        ctx.strokeRect(pos.x - nameWidth / 2 - 4, pos.y + 16, nameWidth + 8, 13);

        ctx.fillStyle = "#ffffff";
        ctx.fillText(surname, pos.x, pos.y + 22.5);

        // Dynamic Rating Pill next to name if available
        if (ratingVal !== null) {
          const pillColor = ratingColor === "green" ? "#10b981" : (ratingColor === "red" ? "#ef4444" : "#f59e0b");
          ctx.fillStyle = pillColor;
          ctx.fillRect(pos.x + nameWidth / 2 + 6, pos.y + 16, 18, 13);
          ctx.fillStyle = "#ffffff";
          ctx.font = "bold 8px JetBrains Mono";
          ctx.fillText(ratingVal.toFixed(1), pos.x + nameWidth / 2 + 15, pos.y + 22.5);
        }

        ctx.restore();
      });
    };

    renderFormationXI(this.homeFormation, "#00A3E0", "#ffffff", "Avalon City FC");
    renderFormationXI(this.awayFormation, "#e11d48", "#FFD100", "Solaria Rovers");
  }

  /* ==============================================================================
     Team Standings & Club Intelligence Modal
     ============================================================================== */

  async openTeamModal(teamId) {
    this.currentModalTeamId = teamId || "avalon_city";
    const modal = document.getElementById("team-modal");
    if (!modal) return;

    try {
      const [standingsRes, teamRes] = await Promise.all([
        fetch("/api/league/standings"),
        fetch(`/api/teams/${this.currentModalTeamId}`),
      ]);

      if (!standingsRes.ok || !teamRes.ok) return;

      const standings = await standingsRes.json();
      const team = await teamRes.json();

      // Populate Header
      document.getElementById("modal-team-name").textContent = team.name;
      document.getElementById("modal-team-meta").textContent = `${team.stadium} (${team.capacity.toLocaleString()} seats) • Founded ${team.founded}`;
      const colorBox = document.getElementById("modal-team-color-box");
      if (colorBox) {
        colorBox.style.background = this.currentModalTeamId === "avalon_city" ? "#00A3E0" : "#e11d48";
      }

      // Populate Standings Table
      const tbody = document.getElementById("standings-tbody");
      if (tbody) {
        tbody.innerHTML = standings.map((club) => {
          const isSelected = club.team_id === this.currentModalTeamId;
          const isMatch = club.team_id === "avalon_city" || club.team_id === "solaria_rovers";
          const formDots = (club.form || []).map((f) => {
            const cls = f === "W" ? "form-w" : (f === "D" ? "form-d" : "form-l");
            return `<span class="form-dot ${cls}">${f}</span>`;
          }).join("");

          return `
            <tr class="${isMatch ? 'current-match-team' : ''}" style="${isSelected ? 'background: rgba(0, 242, 254, 0.16);' : ''}">
              <td><b>${club.rank}</b></td>
              <td style="font-weight: 700; cursor: pointer; color: ${isSelected ? '#00f2fe' : '#ffffff'};" onclick="window.omniPitch.openTeamModal('${club.team_id}')" title="Inspect club profile">
                ${club.team_name}
              </td>
              <td>${club.played}</td>
              <td>${club.won}</td>
              <td>${club.drawn}</td>
              <td>${club.lost}</td>
              <td>${club.goals_for}</td>
              <td>${club.goals_against}</td>
              <td>${club.goal_diff > 0 ? '+' : ''}${club.goal_diff}</td>
              <td style="font-weight: 800; color: #00f2fe;">${club.points}</td>
              <td><div class="form-badge-group">${formDots}</div></td>
            </tr>
          `;
        }).join("");
      }

      // Populate Club Profile
      const profContainer = document.getElementById("team-profile-content");
      if (profContainer) {
        const recentRows = (team.recent_matches || []).map((m) => {
          const resClass = m.result === "W" ? "form-w" : (m.result === "D" ? "form-d" : "form-l");
          return `
            <div class="stat-metric-row">
              <span class="metric-lbl">vs ${m.opponent} (${m.competition})</span>
              <span class="metric-val"><span class="form-dot ${resClass}">${m.result}</span> ${m.score}</span>
            </div>
          `;
        }).join("");

        profContainer.innerHTML = `
          <div class="profile-card-block">
            <h4>Tactical DNA & Philosophy</h4>
            <div class="stat-metric-row"><span class="metric-lbl">Head Coach / Manager:</span><span class="metric-val">${team.manager}</span></div>
            <div class="stat-metric-row"><span class="metric-lbl">Team Captain:</span><span class="metric-val">${team.captain}</span></div>
            <div class="stat-metric-row"><span class="metric-lbl">Tactical System:</span><span class="metric-val" style="color: #00f2fe;">${team.tactical_style}</span></div>
            <div class="stat-metric-row"><span class="metric-lbl">Preferred Formation:</span><span class="metric-val">${team.preferred_formation}</span></div>
            <div class="stat-metric-row"><span class="metric-lbl">PPDA Pressing Index:</span><span class="metric-val">${team.ppda} (Suffocating Press)</span></div>
            <div class="stat-metric-row"><span class="metric-lbl">Home Stadium:</span><span class="metric-val">${team.stadium}</span></div>
          </div>
          <div class="profile-card-block">
            <h4>Recent Results & Form Guide</h4>
            ${recentRows}
          </div>
        `;
      }

      modal.classList.remove("hidden");
    } catch (err) {
      console.warn("Failed to load team standings/profile:", err);
    }
  }

  closeTeamModal() {
    const modal = document.getElementById("team-modal");
    if (modal) modal.classList.add("hidden");
  }

  /* ==============================================================================
     Player Dossier, Sporting CV & Career Statistics Modal
     ============================================================================== */

  async openPlayerModal(playerId, playerName) {
    const modal = document.getElementById("player-modal");
    if (!modal) return;

    try {
      const query = playerId || playerName;
      const res = await fetch(`/api/players/${encodeURIComponent(query)}?match_id=${this.matchId}`);
      if (!res.ok) return;

      const data = await res.json();
      this.activeModalPlayerId = data.player_id;
      this.activeModalPlayerName = data.name;

      // Header Identity
      document.getElementById("modal-player-num").textContent = `#${data.number}`;
      document.getElementById("modal-player-pos").textContent = data.position;
      document.getElementById("modal-player-team").textContent = data.club_name;
      document.getElementById("modal-player-name").textContent = data.name;
      document.getElementById("modal-player-archetype").textContent = data.archetype;

      // Bio Ribbon
      document.getElementById("bio-age").textContent = data.bio.age;
      document.getElementById("bio-nat").textContent = data.bio.nationality;
      document.getElementById("bio-height").textContent = `${data.bio.height_cm} cm`;
      document.getElementById("bio-foot").textContent = data.bio.preferred_foot;
      document.getElementById("bio-val").textContent = data.bio.market_value_eur;
      document.getElementById("bio-contract").textContent = data.bio.contract_until;

      // Sporting CV & Career
      document.getElementById("cv-academy").textContent = data.career.youth_academy;
      document.getElementById("cv-caps").textContent = data.career.international_caps;

      const clubsList = document.getElementById("cv-clubs-list");
      if (clubsList) {
        clubsList.innerHTML = (data.career.trajectory || []).map((c) => `
          <div class="club-trajectory-row">
            <span><b>${c.period}</b>: ${c.club}</span>
            <span style="color: #94a3b8;">${c.appearances} apps (${c.goals} goals)</span>
          </div>
        `).join("");
      }

      const honorsList = document.getElementById("cv-honors-list");
      if (honorsList) {
        honorsList.innerHTML = (data.career.honours || []).map((h) => `
          <span class="honor-tag">${h}</span>
        `).join("");
      }

      document.getElementById("cv-scouting-text").textContent = data.scouting_summary;

      // Live Match Contribution
      const live = data.live_match_stats || {};
      const ratingCls = live.rating_color === "green" ? "rating-green" : (live.rating_color === "red" ? "rating-red" : "rating-orange");
      const liveContainer = document.getElementById("modal-live-metrics");
      if (liveContainer) {
        liveContainer.innerHTML = `
          <div class="metric-card-mini">
            <span class="num"><span class="pro-rating-pill ${ratingCls}">${(live.rating || 6.5).toFixed(1)}</span></span>
            <span class="lbl">Live Rating</span>
          </div>
          <div class="metric-card-mini">
            <span class="num" style="color: #00f2fe;">${live.distance_km || 0.0} km</span>
            <span class="lbl">Distance Covered</span>
          </div>
          <div class="metric-card-mini">
            <span class="num" style="color: #f59e0b;">${live.sprint_bursts || 0}</span>
            <span class="lbl">Sprint Bursts</span>
          </div>
          <div class="metric-card-mini">
            <span class="num">${live.pass_accuracy || 0}%</span>
            <span class="lbl">Pass Acc (${live.completed_passes || 0}/${live.total_passes || 0})</span>
          </div>
          <div class="metric-card-mini">
            <span class="num" style="color: #10b981;">${live.goals || 0} G / ${live.total_shots || 0} S</span>
            <span class="lbl">Goals / Shots</span>
          </div>
          <div class="metric-card-mini">
            <span class="num">${live.tackles_won || 0}</span>
            <span class="lbl">Tackles Won</span>
          </div>
        `;
      }

      // Season 2025/26 Longitudinal Metrics
      const s = data.season_2025_26 || {};
      const seasonContainer = document.getElementById("modal-season-metrics");
      if (seasonContainer) {
        seasonContainer.innerHTML = `
          <div class="metric-card-mini">
            <span class="num">${s.appearances || 0}</span>
            <span class="lbl">Season Appearances</span>
          </div>
          <div class="metric-card-mini">
            <span class="num" style="color: #10b981;">${s.goals || 0} G / ${s.assists || 0} A</span>
            <span class="lbl">Goals & Assists</span>
          </div>
          <div class="metric-card-mini">
            <span class="num" style="color: #00f2fe;">${(s.xg_per_90 || 0).toFixed(2)}</span>
            <span class="lbl">xG / 90 Minutes</span>
          </div>
          <div class="metric-card-mini">
            <span class="num">${s.pass_completion_rate || 0}%</span>
            <span class="lbl">Pass Completion</span>
          </div>
          <div class="metric-card-mini" style="grid-column: span 2;">
            <span class="num" style="color: #f59e0b;">${s.top_speed_kmh || 0} km/h</span>
            <span class="lbl">Peak Sprint Velocity Recorded</span>
          </div>
        `;
      }

      modal.classList.remove("hidden");
    } catch (err) {
      console.warn("Failed to load player dossier:", err);
    }
  }

  closePlayerModal() {
    const modal = document.getElementById("player-modal");
    if (modal) modal.classList.add("hidden");
  }

  /* ==============================================================================
     Live Data Table (Microsoft Fabric OneLake Telemetry Stream)
     ============================================================================== */

  async fetchLiveDataTable() {
    try {
      const res = await fetch(`/api/match/${this.matchId}/events/table`);
      if (!res.ok) return;
      const data = await res.json();
      this.liveTableRows = data.rows || [];
      const badge = document.getElementById("datatable-count-badge");
      if (badge) badge.textContent = `${this.liveTableRows.length} Ingested Records`;
      this.renderLiveDataTable();
    } catch (err) {
      console.warn("Failed to fetch live data table:", err);
    }
  }

  prependLiveTableRow(event, timecode) {
    const row = {
      event_id: event.event_id,
      match_time: timecode,
      minute: event.minute,
      second: event.second,
      team_id: event.team_id,
      team_name: event.team_id === "avalon_city" ? "Avalon City FC" : "Solaria Rovers",
      player_id: event.player ? event.player.player_id : "N/A",
      player_name: event.player ? event.player.name : "System",
      player_number: event.player ? event.player.number : 0,
      event_type: event.event_type,
      start_x: event.start_coordinates ? event.start_coordinates.x.toFixed(1) : "0.0",
      start_y: event.start_coordinates ? event.start_coordinates.y.toFixed(1) : "0.0",
      expected_goals: (event.expected_goals || 0.0).toFixed(3),
      pass_difficulty: (event.pass_difficulty_rating || 0.0).toFixed(2),
      shot_speed_kmh: (event.shot_speed_kmh || 0.0).toFixed(1),
      is_successful: Boolean(event.is_successful),
      is_sprint: Boolean(event.is_sprint_burst),
      fabric_verified: true,
    };

    this.liveTableRows.unshift(row);
    if (this.liveTableRows.length > 200) this.liveTableRows.pop();

    const badge = document.getElementById("datatable-count-badge");
    if (badge) badge.textContent = `${this.liveTableRows.length} Ingested Records`;

    // Re-render if table tab is currently visible
    const activeTab = document.querySelector(".mc-tab-btn.active");
    if (activeTab && activeTab.getAttribute("data-tab") === "tab-datatable") {
      this.renderLiveDataTable();
    }
  }

  renderLiveDataTable() {
    const tbody = document.getElementById("live-events-tbody");
    if (!tbody) return;

    const searchInput = document.getElementById("datatable-search");
    const query = (searchInput ? searchInput.value : "").toLowerCase().trim();

    const filtered = this.liveTableRows.filter((r) => {
      // Type pill filter
      if (this.currentDataTableFilter !== "all") {
        if (this.currentDataTableFilter === "shot") {
          if (r.event_type !== "shot" && r.event_type !== "goal") return false;
        } else if (r.event_type !== this.currentDataTableFilter) {
          return false;
        }
      }

      // Text search filter
      if (query) {
        const matchesPlayer = (r.player_name || "").toLowerCase().includes(query);
        const matchesTeam = (r.team_name || "").toLowerCase().includes(query);
        const matchesType = (r.event_type || "").toLowerCase().includes(query);
        const matchesId = (r.event_id || "").toLowerCase().includes(query);
        if (!matchesPlayer && !matchesTeam && !matchesType && !matchesId) return false;
      }

      return true;
    });

    if (filtered.length === 0) {
      tbody.innerHTML = `
        <tr>
          <td colspan="9" style="text-align: center; color: #64748b; padding: 28px;">
            ${this.liveTableRows.length === 0 ? 'Awaiting telemetry ingest. Start match stream above or inspect simulated dataset.' : 'No events match the active search or type filter.'}
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = filtered.slice(0, 50).map((r) => {
      const isHome = r.team_id === "avalon_city";
      const teamColor = isHome ? "#00A3E0" : "#e11d48";
      const typeBadgeClass = `tele-badge tele-badge-${r.event_type.replace('_', '')}`;
      const xgHighlight = parseFloat(r.expected_goals) > 0.15 ? 'color: #ec4899; font-weight: 800;' : '';

      return `
        <tr>
          <td><span class="mono">${r.match_time}</span></td>
          <td style="color: ${teamColor}; font-weight: 600; cursor: pointer;" onclick="window.omniPitch.openTeamModal('${r.team_id}')" title="Inspect ${r.team_name}">
            ${r.team_name}
          </td>
          <td style="cursor: pointer; font-weight: 600;" onclick="window.omniPitch.openPlayerModal('${r.player_id}', '${r.player_name}')" title="Open ${r.player_name}'s sporting CV">
            ⭐ ${r.player_name} <span style="color: #64748b;">(#${r.player_number})</span>
          </td>
          <td><span class="${typeBadgeClass}">${r.event_type}</span></td>
          <td><span class="mono">(${r.start_x}, ${r.start_y})</span></td>
          <td><span class="mono" style="${xgHighlight}">${r.expected_goals}</span></td>
          <td><span class="mono">${r.pass_difficulty}</span></td>
          <td><span class="mono">${r.shot_speed_kmh} km/h</span></td>
          <td><span class="fabric-badge">✓ OneLake Delta</span></td>
        </tr>
      `;
    }).join("");
  }

  /* ==============================================================================
     Microsoft AI Foundry Multi-Agent Hub & Power Automate Workflows
     ============================================================================== */

  async fetchFoundryHubData() {
    try {
      const [agentsRes, previewRes] = await Promise.all([
        fetch("/api/foundry/agents"),
        fetch("/api/integrations/power-automate/preview"),
      ]);

      if (agentsRes.ok) {
        this.foundryAgentsData = await agentsRes.json();
        this.renderFoundryAgents(this.foundryAgentsData.agents || []);
      }

      if (previewRes.ok) {
        this.adaptiveCardsPreview = await previewRes.json();
        this.updateAdaptiveCardPreview();
      }
    } catch (err) {
      console.warn("Failed to fetch Foundry hub data:", err);
    }
  }

  renderFoundryAgents(agents) {
    const grid = document.getElementById("foundry-agents-grid");
    if (!grid) return;

    grid.innerHTML = agents.map((agent) => {
      const toolsText = agent.tools ? agent.tools.map(t => t.replace(/_/g, " ")).slice(0, 2).join(", ") : "Blackboard Memory";
      const handoffTarget = agent.handoff_to ? agent.handoff_to.replace(/_/g, " ") : "Client";

      return `
        <div class="agent-pipeline-card">
          <div class="agent-card-top">
            <span class="agent-model-pill">${agent.model || 'gpt-4o'}</span>
            <span class="agent-status-dot" title="Status: Online & Ready"></span>
          </div>
          <div class="agent-name">${agent.name}</div>
          <div class="agent-role-pill">${agent.role}</div>
          <div class="agent-tools-list">🔧 Tools: ${toolsText}</div>
          <div class="agent-handoff-flow">➔ Handoff: ${handoffTarget} (${agent.latency_ms || 25}ms)</div>
        </div>
      `;
    }).join("");
  }

  updateAdaptiveCardPreview() {
    if (!this.adaptiveCardsPreview) return;
    const select = document.getElementById("pa-event-type-select");
    const eventType = select ? select.value : "goal";

    let card = this.adaptiveCardsPreview.goal_card;
    if (eventType === "tactical_shift") card = this.adaptiveCardsPreview.tactical_shift_card;
    if (eventType === "incident") card = this.adaptiveCardsPreview.incident_card;

    this.renderAdaptiveCardVisual(card);
    const jsonPre = document.getElementById("ac-json-code");
    if (jsonPre) jsonPre.textContent = JSON.stringify(card, null, 2);
  }

  async dispatchPowerAutomateWorkflow() {
    const select = document.getElementById("pa-event-type-select");
    const eventType = select ? select.value : "goal";
    const webhookInput = document.getElementById("pa-webhook-url");
    const webhookUrl = webhookInput ? webhookInput.value.trim() : "";
    const statusBox = document.getElementById("pa-dispatch-status");
    const btn = document.getElementById("btn-dispatch-pa");

    if (btn) {
      btn.textContent = "⏳ Triggering Flow...";
      btn.disabled = true;
    }

    try {
      const res = await fetch("/api/integrations/power-automate/dispatch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event_type: eventType,
          webhook_url: webhookUrl || null,
          match_id: this.matchId
        })
      });

      const data = await res.json();
      if (statusBox) {
        statusBox.classList.remove("hidden");
        const isSimulated = data.status === "simulated_success";
        statusBox.innerHTML = `
          <strong>✓ Power Automate Trigger ${isSimulated ? 'Validated (Simulation Mode)' : 'Delivered'}!</strong>
          <div>Event: <b>${data.event_type.toUpperCase()}</b> • Timestamp: ${data.timestamp} • Status: ${data.status}</div>
          <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 2px;">
            ${isSimulated ? 'Enterprise payload verified against Microsoft Adaptive Card v1.5 schema and ready for Microsoft Teams channel webhook.' : `Webhook delivered with HTTP ${data.status_code}.`}
          </div>
        `;
      }

      if (data.adaptive_card) {
        this.renderAdaptiveCardVisual(data.adaptive_card);
        const jsonPre = document.getElementById("ac-json-code");
        if (jsonPre) jsonPre.textContent = JSON.stringify(data.adaptive_card, null, 2);
      }
    } catch (err) {
      console.warn("Power Automate dispatch error:", err);
      if (statusBox) {
        statusBox.classList.remove("hidden");
        statusBox.innerHTML = `<span style="color: #ef4444;">Dispatch failed: ${err.message}</span>`;
      }
    } finally {
      if (btn) {
        btn.textContent = "⚡ Dispatch Workflow";
        btn.disabled = false;
      }
    }
  }

  renderAdaptiveCardVisual(card) {
    const container = document.getElementById("ac-rendered-body");
    if (!container || !card) return;

    const body = card.body || [];
    let html = "";

    body.forEach((block) => {
      if (block.type === "Container" && block.style) {
        const styleClass = block.style === "warning" ? "warning" : (block.style === "attention" ? "attention" : "");
        const innerText = block.items && block.items[0] && block.items[0].text ? block.items[0].text : (block.items && block.items[0] && block.items[0].columns ? "MATCH EVENT" : "");
        html += `<div class="ac-card-banner ${styleClass}">${innerText}</div>`;
      } else if (block.type === "TextBlock") {
        const isBolder = block.weight === "Bolder";
        const fontSize = block.size === "Large" ? "1.1rem" : (block.size === "ExtraLarge" ? "1.4rem" : "0.85rem");
        html += `<div class="ac-narrative-text" style="font-size: ${fontSize}; font-weight: ${isBolder ? '800' : '400'};">${block.text}</div>`;
      } else if (block.type === "FactSet") {
        html += `<table class="ac-fact-table">`;
        (block.facts || []).forEach((f) => {
          html += `<tr><td class="ac-fact-title">${f.title}</td><td class="ac-fact-value">${f.value}</td></tr>`;
        });
        html += `</table>`;
      }
    });

    if (card.actions && card.actions.length > 0) {
      html += `<div class="ac-actions-row">`;
      card.actions.forEach((act) => {
        html += `<a href="${act.url || '#'}" target="_blank" class="ac-action-btn">${act.title}</a>`;
      });
      html += `</div>`;
    }

    container.innerHTML = html;
  }
}

// Global initialization & public API exposure
window.addEventListener("DOMContentLoaded", () => {
  window.omniPitch = new OmniPitchApp();
});



