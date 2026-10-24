/**
 * OmniPitch Live Match Intelligence & Interactive Pitch Visualizer
 * Multi-agent overlays, player spotlight, tactical canvases, match centre & Foundry hub.
 */

// Canvas palette — mirrors the CSS custom properties in style.css
const C = {
  home: "#2fa6ff",
  away: "#ff5140",
  accent: "#d2ff3c",
  accentInk: "#11140a",
  text: "#ecebe6",
  text2: "#a3a39d",
  text3: "#6c6c67",
  good: "#3fd28b",
  warn: "#f5a524",
  bad: "#ff5140",
  bg: "#0b0c0e",
  bg2: "#121316",
  bg4: "#222429",
  grassA: "#15351f",
  grassB: "#183a23",
  grassOut: "#123019",
  line: "rgba(236, 235, 230, 0.55)",
  gridLine: "rgba(236, 235, 230, 0.07)",
};

const FONT = {
  display: "'Barlow Condensed', 'Arial Narrow', sans-serif",
  mono: "'IBM Plex Mono', ui-monospace, monospace",
};

const TEAM_NAMES = { avalon_city: "Avalon City", solaria_rovers: "Solaria Rovers" };

// Optional portrait assets, keyed by player id
const PLAYER_PHOTOS = { "AVA-08": "/static/img/julian_drake.jpg" };

const rgba = (hex, a) => {
  const n = parseInt(hex.slice(1), 16);
  return `rgba(${(n >> 16) & 255}, ${(n >> 8) & 255}, ${n & 255}, ${a})`;
};

const esc = (v) =>
  String(v ?? "").replace(/[&<>"']/g, (ch) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[ch]);

/** Size a canvas to its CSS box at device pixel ratio; returns {ctx, w, h} in CSS pixels. */
function fitCanvas(canvas) {
  const dpr = window.devicePixelRatio || 1;
  const rect = canvas.getBoundingClientRect();
  const w = Math.max(rect.width, 1);
  const h = Math.max(rect.height, 1);
  if (canvas.width !== Math.round(w * dpr) || canvas.height !== Math.round(h * dpr)) {
    canvas.width = Math.round(w * dpr);
    canvas.height = Math.round(h * dpr);
  }
  const ctx = canvas.getContext("2d");
  ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
  return { ctx, w, h };
}

class OmniPitchApp {
  constructor() {
    this.matchId = "MATCH-2026-001";
    this.currentPersona = "analyst";
    this.currentLang = "en";
    this.currentPlayer = "";
    this.isStreaming = false;
    this.showHeatmap = false;

    // SSE stream (events + overlays) and where to resume it
    this.overlaySource = null;
    this.fullTime = false;

    // Canvas setup
    this.canvas = document.getElementById("pitch-canvas");
    this.ctx = this.canvas.getContext("2d");

    // State cache
    this.eventsReceived = 0;
    this.currentBall = { x: 50, y: 50 };
    this.displayBall = { x: 50, y: 50 };
    this.ballAnim = null;
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
    this.momentumHoverSlot = null;

    // Personalisation & live commentary
    this.favouriteClub = "";
    this.speed = 1;
    this.voiceOn = false;
    this.speechQueue = [];
    this.speaking = false;
    this.lastLowerThirdAt = 0;
    this.latestRecap = null;
    this.phaseLabel = "Pre-match";
    this.claimsVerified = 0;

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
    this.setSpotlightAvatar("AVA-08", 8, "avalon_city");
    this.fetchMatchCenterOverview();
    this.fetchAgentTelemetry();

    // Canvas text uses web fonts — redraw once they are ready
    if (document.fonts && document.fonts.ready) {
      document.fonts.ready.then(() => this.redrawAll());
    }
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
      this.renderPitch();
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

    // Commentary voice toggle
    const speechBtn = document.getElementById("btn-speak-commentary");
    speechBtn.addEventListener("click", () => this.toggleVoice());

    // Favourite club: commentary takes that side
    document.getElementById("club-select").addEventListener("change", (e) => {
      this.favouriteClub = e.target.value;
      if (this.isStreaming) this.restartStream();
    });

    // Playback pace
    document.querySelectorAll("#speed-toggle .seg-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        document.querySelectorAll("#speed-toggle .seg-btn").forEach((b) => b.classList.toggle("active", b === btn));
        this.speed = Number(btn.dataset.speed) || 1;
        if (this.isStreaming) this.restartStream();
      });
    });

    // Commentary / raw event feed tabs
    document.querySelectorAll(".feed-tab").forEach((tab) => {
      tab.addEventListener("click", () => {
        document.querySelectorAll(".feed-tab").forEach((t) => t.classList.toggle("active", t === tab));
        document.querySelectorAll(".feed-pane").forEach((p) => p.classList.toggle("hidden", p.id !== tab.dataset.feed));
      });
    });

    // Match report
    document.getElementById("btn-open-recap").addEventListener("click", () => this.openRecap());
    document.getElementById("btn-close-recap").addEventListener("click", () => this.closeRecap());
    document.getElementById("recap-modal").addEventListener("click", (e) => {
      if (e.target.id === "recap-modal") this.closeRecap();
    });
    document.getElementById("btn-speak-recap").addEventListener("click", () => this.speakRecap());

    // Heatmap Toggle button
    const heatmapBtn = document.getElementById("btn-toggle-heatmap");
    heatmapBtn.addEventListener("click", () => {
      this.showHeatmap = !this.showHeatmap;
      heatmapBtn.classList.toggle("active", this.showHeatmap);
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
      jsonBtn.classList.toggle("active", !jsonBox.classList.contains("hidden"));
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
        this.renderPitch();
      });
    }

    // Match Center Tabs Switching
    document.querySelectorAll(".mc-tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => this.activateTab(btn.getAttribute("data-tab")));
    });

    // Top nav shortcuts that open a specific match centre tab
    document.querySelectorAll("[data-jump-tab]").forEach((link) => {
      link.addEventListener("click", () => this.activateTab(link.getAttribute("data-jump-tab")));
    });

    // Momentum canvas hover
    const momCanvas = document.getElementById("momentum-canvas");
    if (momCanvas) {
      momCanvas.addEventListener("mousemove", (e) => this.handleMomentumHover(e));
      momCanvas.addEventListener("mouseleave", () => {
        const tip = document.getElementById("momentum-tooltip");
        if (tip) tip.classList.add("hidden");
        this.momentumHoverSlot = null;
        this.renderAttackMomentum();
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
    ["home-team-trigger", "lineup-home-team-trigger"].forEach((id) => {
      const trigger = document.getElementById(id);
      if (trigger) trigger.addEventListener("click", () => this.openTeamModal("avalon_city"));
    });
    ["away-team-trigger", "lineup-away-team-trigger"].forEach((id) => {
      const trigger = document.getElementById(id);
      if (trigger) trigger.addEventListener("click", () => this.openTeamModal("solaria_rovers"));
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
        this.closeRecap();
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
        const label = btnCopyCardJson.querySelector("span");
        if (code && navigator.clipboard) {
          navigator.clipboard.writeText(code.textContent);
          label.textContent = "Copied";
          setTimeout(() => (label.textContent = "Copy"), 2000);
        }
      });
    }

    // Keep canvases crisp when the layout changes
    let resizeTimer = null;
    window.addEventListener("resize", () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(() => this.redrawAll(), 80);
    });
  }

  activateTab(targetId) {
    document.querySelectorAll(".mc-tab-btn").forEach((b) => {
      b.classList.toggle("active", b.getAttribute("data-tab") === targetId);
    });
    document.querySelectorAll(".mc-tab-content").forEach((c) => c.classList.toggle("active", c.id === targetId));

    if (targetId === "tab-momentum") this.renderAttackMomentum();
    if (targetId === "tab-shotmap") this.renderShotMap();
    if (targetId === "tab-datatable") this.fetchLiveDataTable();
    if (targetId === "tab-foundry") this.fetchFoundryHubData();
  }

  redrawAll() {
    this.renderPitch();
    this.renderAttackMomentum();
    this.renderShotMap();
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

  setStreamUi(live, idleLabel) {
    const btn = document.getElementById("btn-stream-toggle");
    document.getElementById("stream-icon").setAttribute("href", live ? "#i-pause" : "#i-play");
    document.getElementById("stream-text").textContent = live ? "Pause" : idleLabel;
    btn.classList.toggle("is-live", live);
    document.body.classList.toggle("is-live", live && !this.fullTime);
    let label = this.phaseLabel;
    if (!live && this.eventsReceived && !this.fullTime && this.phaseLabel !== "Half-time") label = "Paused";
    document.querySelector(".live-label").textContent = label;
  }

  setPhase(label) {
    this.phaseLabel = label;
    document.querySelector(".live-label").textContent = label;
  }

  startStream() {
    if (this.fullTime) {
      this.resetSimulation().then(() => this.startStream());
      return;
    }
    this.isStreaming = true;
    this.setStreamUi(true);
    if (!this.eventsReceived) this.playWhistleSound();

    // One SSE stream carries each match_event followed by the overlay built from it,
    // so pitch, scoreboard and commentary always describe the same moment. The match
    // clock lives on the server, so reconnecting simply continues the match.
    const delay = Math.max(0.25, 1 / this.speed).toFixed(2);
    let overlayUrl = `/api/match/${this.matchId}/overlays/stream?persona=${this.currentPersona}&lang=${this.currentLang}` +
      `&delay=${delay}&include_events=true&max_overlays=200`;
    if (this.currentPlayer) overlayUrl += `&player=${encodeURIComponent(this.currentPlayer)}`;
    if (this.favouriteClub) overlayUrl += `&club=${this.favouriteClub}`;

    const source = new EventSource(overlayUrl);
    this.overlaySource = source;

    source.addEventListener("match_event", (e) => this.handleMatchEvent(JSON.parse(e.data)));
    source.addEventListener("broadcast_overlay", (e) => this.handleBroadcastOverlay(JSON.parse(e.data)));
    source.addEventListener("match_recap", (e) => {
      const recap = JSON.parse(e.data);
      // Half-time is a real break: pause the broadcast while the report is on screen
      if (recap.kind === "half_time") this.stopStream("Second half");
      this.showRecap(recap);
    });
    source.addEventListener("stream_end", (e) => {
      const data = JSON.parse(e.data);
      if (data.full_time) {
        this.fullTime = true;
        this.stopStream("Replay");
      } else {
        this.stopStream();
      }
      this.fetchAgentTelemetry();
    });
    // Don't let EventSource silently reconnect and replay
    source.onerror = () => {
      if (this.overlaySource === source && this.isStreaming) this.stopStream();
    };
  }

  stopStream(idleLabel = "Resume") {
    this.isStreaming = false;
    this.setStreamUi(false, idleLabel);
    if (this.overlaySource) this.overlaySource.close();
  }

  restartStream() {
    this.stopStream();
    this.startStream();
  }

  async resetSimulation() {
    this.eventsReceived = 0;
    this.fullTime = false;
    this.phaseLabel = "Pre-match";
    this.claimsVerified = 0;
    this.latestRecap = null;
    this.stopStream("Kick off");
    this.homeScore = 0;
    this.awayScore = 0;
    this.passVectors = [];
    this.currentBall = { x: 50, y: 50 };
    this.displayBall = { x: 50, y: 50 };
    this.ballAnim = null;
    this.activePlayerNode = null;
    this.latestOverlay = null;
    this.liveTableRows = [];
    this.speechQueue = [];
    if (window.speechSynthesis) window.speechSynthesis.cancel();

    document.getElementById("home-score").textContent = "0";
    document.getElementById("away-score").textContent = "0";
    document.getElementById("match-clock").textContent = "00:00";
    document.getElementById("added-badge").classList.add("hidden");
    document.getElementById("event-counter").textContent = "0 events";
    document.getElementById("pipeline-claims").textContent = "0 claims verified";
    document.getElementById("overlay-time").textContent = "00:00";
    document.getElementById("overlay-headline").textContent = "Waiting for kick-off";
    document.getElementById("overlay-narrative").textContent =
      "Simulation reset. Press Kick off to replay the match from the first whistle.";
    document.getElementById("overlay-genby").textContent = "";
    document.getElementById("evidence-count").textContent = "0 events";
    document.getElementById("evidence-tags").innerHTML = `<span class="tag-empty">No citations yet</span>`;
    document.getElementById("telemetry-list").innerHTML = `
      <div class="telemetry-placeholder"><div class="pulse-text">Simulation reset — press Kick off.</div></div>`;
    document.getElementById("commentary-list").innerHTML = `
      <div class="telemetry-placeholder"><div class="pulse-text">Commentary starts at kick-off.</div></div>`;
    this.setPhase("Pre-match");
    this.renderPitch();

    try {
      await fetch(`/api/match/${this.matchId}/reset`, { method: "POST" });
      await this.fetchMatchCenterOverview();
      this.fetchAgentTelemetry();
    } catch (e) {
      console.warn("Error resetting match backend session:", e);
    }
  }

  /* -------------------------------------------------------------------------
     Live commentary voice (Web Speech API, in the viewer's language)
     ------------------------------------------------------------------------- */

  toggleVoice() {
    const btn = document.getElementById("btn-speak-commentary");
    if (!window.speechSynthesis) {
      btn.title = "Speech synthesis is not available in this browser";
      return;
    }
    this.voiceOn = !this.voiceOn;
    btn.setAttribute("aria-pressed", String(this.voiceOn));
    if (!this.voiceOn) {
      this.speechQueue = [];
      window.speechSynthesis.cancel();
      this.speaking = false;
    } else if (this.latestOverlay && this.latestOverlay.commentary && this.latestOverlay.commentary.length) {
      this.enqueueSpeech(this.latestOverlay.commentary[0]);
    }
  }

  pickVoice(speaker) {
    const langMap = { en: "en", it: "it", es: "es", de: "de" };
    const prefix = langMap[this.currentLang] || "en";
    const voices = (window.speechSynthesis.getVoices() || []).filter((v) => v.lang.toLowerCase().startsWith(prefix));
    if (!voices.length) return null;
    // Lead and co-commentator get different voices when the system has more than one
    return speaker === "color" && voices.length > 1 ? voices[1] : voices[0];
  }

  enqueueSpeech(line) {
    if (!this.voiceOn || !window.speechSynthesis || !line) return;
    if (line.intensity >= 2) {
      // Big moments jump the queue and cut routine chatter
      this.speechQueue = this.speechQueue.filter((l) => l.intensity >= 2).slice(-2);
      if (this.speaking && this.currentUtteranceIntensity < 2) window.speechSynthesis.cancel();
      this.speechQueue.push(line);
    } else if (!this.speaking && this.speechQueue.length === 0) {
      // Routine play-by-play only when the booth is quiet, so the voice never lags the match
      this.speechQueue.push(line);
    }
    this.drainSpeech();
  }

  drainSpeech() {
    if (this.speaking || !this.speechQueue.length) return;
    const line = this.speechQueue.shift();
    const utterance = new SpeechSynthesisUtterance(line.text.replace(/[—–]/g, ", "));
    const langMap = { en: "en-GB", it: "it-IT", es: "es-ES", de: "de-DE" };
    utterance.lang = langMap[this.currentLang] || "en-GB";
    const voice = this.pickVoice(line.speaker);
    if (voice) utterance.voice = voice;
    utterance.rate = (line.intensity === 3 ? 1.12 : 1.05) * Math.min(1 + (this.speed - 1) * 0.12, 1.35);
    utterance.pitch = line.intensity === 3 ? 1.15 : (line.speaker === "color" ? 0.92 : 1.0);
    this.currentUtteranceIntensity = line.intensity;
    this.speaking = true;
    const done = () => {
      this.speaking = false;
      document.querySelectorAll(".cm-line.speaking").forEach((el) => el.classList.remove("speaking"));
      this.drainSpeech();
    };
    utterance.onend = done;
    utterance.onerror = done;
    const el = document.querySelector(`.cm-line[data-key="${line.event_id}-${line.speaker}"]`);
    if (el) el.classList.add("speaking");
    window.speechSynthesis.speak(utterance);
  }

  appendCommentary(lines) {
    const list = document.getElementById("commentary-list");
    const placeholder = list.querySelector(".telemetry-placeholder");
    if (placeholder) placeholder.remove();

    lines.forEach((line) => {
      const row = document.createElement("div");
      row.className = `cm-line ${line.speaker} i${line.intensity}`;
      row.dataset.key = `${line.event_id}-${line.speaker}`;
      const who = line.speaker === "lead" ? "Commentator" : "Co-commentator";
      const llm = line.source === "foundry-llm" ? `<span class="cm-source" title="Generated by the Foundry model and verified">· Foundry</span>` : "";
      row.innerHTML = `
        <span class="cm-minute">${esc(line.minute_label)}</span>
        <span class="cm-speaker">${who}${llm}</span>
        <span class="cm-text">${esc(line.text)}</span>
      `;
      list.insertBefore(row, list.firstChild);
    });
    while (list.children.length > 120) list.removeChild(list.lastChild);

    // Lead first, then the co-commentator's explanation
    lines.forEach((line) => this.enqueueSpeech(line));
  }

  speakRecap() {
    if (!this.latestRecap || !window.speechSynthesis) return;
    window.speechSynthesis.cancel();
    this.speechQueue = [];
    const r = this.latestRecap;
    const text = [r.title, ...r.paragraphs].join(". ");
    const utterance = new SpeechSynthesisUtterance(text);
    const langMap = { en: "en-GB", it: "it-IT", es: "es-ES", de: "de-DE" };
    utterance.lang = langMap[r.language] || "en-GB";
    const voice = this.pickVoice("lead");
    if (voice) utterance.voice = voice;
    window.speechSynthesis.speak(utterance);
  }

  /* -------------------------------------------------------------------------
     Recap (half-time / full-time report)
     ------------------------------------------------------------------------- */

  showRecap(recap) {
    this.latestRecap = recap;
    const kindLabel = recap.kind === "half_time" ? "Half-time report" : "Full-time report";
    document.getElementById("recap-kind").textContent = kindLabel;
    document.getElementById("recap-title").textContent = recap.title;
    document.getElementById("recap-standfirst").textContent = recap.standfirst;

    const st = recap.stats || {};
    const pair = (o, digits = 0) => (o ? `${Number(o.home).toFixed(digits)}–${Number(o.away).toFixed(digits)}` : "—");
    const moments = (recap.key_moments || []).map((m) => `
      <li><span class="mono">${esc(m.minute_label)}</span><span>${esc(m.text.replace(m.minute_label, "").trim())}</span></li>`).join("");

    // Key moments get their own list below, so skip the paragraph that repeats them
    const firstMoment = (recap.key_moments || [])[0];
    const paragraphs = recap.paragraphs.filter((p) => !(firstMoment && p.includes(firstMoment.text)));
    document.getElementById("recap-body").innerHTML = `
      ${paragraphs.map((p) => `<p>${esc(p)}</p>`).join("")}
      <div class="recap-stats">
        <div><span class="num">${pair(st.score)}</span><span class="lbl">Score</span></div>
        <div><span class="num">${pair(st.xg, 2)}</span><span class="lbl">Expected goals</span></div>
        <div><span class="num">${pair(st.shots)}</span><span class="lbl">Shots</span></div>
        <div><span class="num">${pair(st.possession)}</span><span class="lbl">Possession %</span></div>
      </div>
      ${moments ? `<ul class="recap-moments">${moments}</ul>` : ""}
    `;
    const ver = recap.verification;
    document.getElementById("recap-source").textContent = recap.source === "foundry-llm"
      ? `Written by the Foundry model · ${ver ? ver.claims_checked : 0} claims verified`
      : `Written from the event log · evidence ${recap.evidence_event_ids.join(", ") || "—"}`;

    document.getElementById("recap-modal").classList.remove("hidden");
    if (this.voiceOn) this.speakRecap();
  }

  async openRecap() {
    try {
      const kind = this.fullTime || this.phaseLabel === "2nd half" ? "full_time" : "half_time";
      const res = await fetch(`/api/match/${this.matchId}/recap?kind=${kind}&lang=${this.currentLang}&persona=${this.currentPersona}`);
      if (res.ok) this.showRecap(await res.json());
    } catch (err) {
      console.warn("Recap fetch failed:", err);
    }
  }

  closeRecap() {
    document.getElementById("recap-modal").classList.add("hidden");
  }

  /* -------------------------------------------------------------------------
     Real-Time Multi-Agent Handlers
     ------------------------------------------------------------------------- */

  handleBroadcastOverlay(overlay) {
    this.latestOverlay = overlay;

    // 1. Pipeline: light up each agent with its measured time
    this.pulsePipeline(overlay.agent_trace || []);
    if (overlay.verification) {
      this.claimsVerified += overlay.verification.claims_checked - overlay.verification.rejected.length;
      document.getElementById("pipeline-claims").textContent = `${this.claimsVerified} claims verified`;
    }

    // 2. Live commentary
    if (overlay.commentary && overlay.commentary.length) this.appendCommentary(overlay.commentary);

    // 3. Lower third: must-show moments at once, notable ones after a 2.5 s dwell,
    //    routine insight at most every 6 s, so on-screen text always stays readable
    const now = Date.now();
    const priority = overlay.display_priority || 1;
    const dwell = now - this.lastLowerThirdAt;
    if (priority >= 3 || (priority === 2 && dwell > 2500) || dwell > 6000) {
      this.lastLowerThirdAt = now;
      const body = document.querySelector(".broadcast-body");
      body.classList.remove("flash");
      void body.offsetWidth;
      body.classList.add("flash");

      document.getElementById("overlay-time").textContent = overlay.minute_label || overlay.match_time;
      document.getElementById("overlay-headline").textContent = overlay.headline;
      document.getElementById("overlay-narrative").textContent = overlay.narrative;
      document.getElementById("overlay-genby").textContent = overlay.generated_by ? `via ${overlay.generated_by}` : "";

      const tagsContainer = document.getElementById("evidence-tags");
      const ids = overlay.evidence_event_ids || [];
      document.getElementById("evidence-count").textContent = `${ids.length} event${ids.length === 1 ? "" : "s"}`;
      tagsContainer.innerHTML = "";
      ids.forEach((eid, i) => {
        const tag = document.createElement("span");
        tag.className = "tag-event";
        tag.style.animationDelay = `${i * 40}ms`;
        tag.textContent = eid;
        tagsContainer.appendChild(tag);
      });
      if (!ids.length) tagsContainer.innerHTML = `<span class="tag-empty">No citations for this moment</span>`;
    }

    // 4. Trace badge
    if (overlay.trace) {
      const v = overlay.verification;
      document.getElementById("trace-badge").textContent =
        `${overlay.trace.model_name} · ${overlay.trace.latency_ms} ms${v ? ` · ${v.claims_checked} claims checked` : ""}`;
    }

    // 5. Player Spotlight HUD
    if (overlay.player_focus) {
      const pf = overlay.player_focus;
      document.getElementById("spotlight-name").textContent = pf.player_name;
      this.setSpotlightAvatar(pf.player_id, parseInt(pf.player_id.slice(-2), 10), pf.team_id);
      document.getElementById("spotlight-team").textContent = `${TEAM_NAMES[pf.team_id] || pf.team_id} · Spotlight`;
      document.getElementById("spotlight-sprints").textContent = pf.sprint_bursts_count;
      document.getElementById("spotlight-dist").textContent = `${pf.distance_covered_km.toFixed(2)} km`;
      document.getElementById("spotlight-acc").textContent = `${pf.pass_completion_rate}%`;
      document.getElementById("spotlight-narrative").textContent = pf.spotlight_narrative;
    }

    // 6. JSON inspector
    document.getElementById("json-code").textContent = JSON.stringify(overlay, null, 2);

    // 7. Tactical gauges
    if (overlay.metrics) {
      const ctrl = overlay.metrics.control_vs_chaos_index ?? 0.5;
      const press = overlay.metrics.defensive_pressure_index ?? 0.5;
      const tempo = overlay.metrics.game_rhythm_tempo ?? "balanced-contest";

      document.getElementById("val-control").textContent = `${Math.round(ctrl * 100)}% Control`;
      document.getElementById("bar-control").style.width = `${Math.round(ctrl * 100)}%`;
      document.getElementById("val-pressure").textContent = `${press.toFixed(2)} (${press > 0.6 ? "High" : "Moderate"})`;
      document.getElementById("bar-pressure").style.width = `${Math.round(press * 100)}%`;
      document.getElementById("val-tempo").textContent = tempo.replace(/-/g, " ");
    }
  }

  setSpotlightAvatar(playerId, number, teamId) {
    const avatar = document.getElementById("spotlight-avatar");
    const card = document.getElementById("player-spotlight-panel");
    const photo = PLAYER_PHOTOS[playerId];
    const teamColor = teamId === "solaria_rovers" ? C.away : C.home;
    avatar.textContent = Number.isFinite(number) ? number : "";
    avatar.style.backgroundColor = teamColor;
    avatar.style.backgroundImage = photo ? `url("${photo}")` : "";
    avatar.classList.toggle("has-photo", Boolean(photo));
    card.style.borderLeftColor = teamColor;
  }

  handleMatchEvent(event) {
    this.eventsReceived += 1;
    document.getElementById("event-counter").textContent = `${this.eventsReceived} events`;
    document.getElementById("match-clock").textContent = event.match_clock;

    // Match phases
    const badge = document.getElementById("added-badge");
    if (event.event_type === "match_start") {
      this.setPhase(event.period === 1 ? "1st half" : "2nd half");
      badge.classList.add("hidden");
      if (event.period === 2) this.playWhistleSound();
    } else if (event.event_type === "added_time") {
      badge.textContent = `+${event.added_time_minutes}`;
      badge.classList.remove("hidden");
    } else if (event.event_type === "half_time") {
      this.setPhase("Half-time");
      this.playWhistleSound();
    } else if (event.event_type === "match_end") {
      this.setPhase("Full time");
      this.playWhistleSound();
    }

    // Score comes from the event itself, so a reconnect can never double count
    [["home-score", event.score_home, "homeScore"], ["away-score", event.score_away, "awayScore"]].forEach(([id, value, key]) => {
      if (value !== this[key]) {
        this[key] = value;
        const digit = document.getElementById(id);
        digit.textContent = value;
        digit.classList.remove("bump");
        void digit.offsetWidth;
        digit.classList.add("bump");
      }
    });

    this.appendTelemetryRow(event, event.match_clock);
    this.prependLiveTableRow(event, event.match_clock);

    // Pitch: ball & vectors
    this.currentBall = {
      x: event.end_coordinates ? event.end_coordinates.x : event.start_coordinates.x,
      y: event.end_coordinates ? event.end_coordinates.y : event.start_coordinates.y,
    };
    if (["match_start", "half_time", "match_end"].includes(event.event_type)) this.passVectors = [];

    if (event.player) this.activePlayerNode = event.player.name;

    if (event.start_coordinates && event.end_coordinates && event.player) {
      this.passVectors.push({
        start: event.start_coordinates,
        end: event.end_coordinates,
        type: event.event_type,
        difficulty: event.pass_difficulty_rating || 0.3,
        team: event.team_id,
        xg: event.expected_goals,
        is_sprint: event.is_sprint_burst,
        failed: event.event_type === "pass" && !event.is_successful,
        timestamp: Date.now(),
      });
      if (this.passVectors.length > 8) this.passVectors.shift();
    }

    this.animateBall();

    // Keep the match centre in step with the stream
    const important = ["goal", "shot", "foul", "half_time", "match_end", "added_time"].includes(event.event_type);
    if (this.eventsReceived % 3 === 0 || important) this.fetchMatchCenterOverview();
    if (this.eventsReceived % 10 === 0 || important) this.fetchAgentTelemetry();
  }

  animateBall() {
    this.ballAnim = { from: { ...this.displayBall }, to: { ...this.currentBall }, start: performance.now(), dur: 520 / Math.min(this.speed, 2) };
    const step = (now) => {
      if (!this.ballAnim) return;
      const t = Math.min((now - this.ballAnim.start) / this.ballAnim.dur, 1);
      const e = 1 - Math.pow(1 - t, 3);
      this.displayBall = {
        x: this.ballAnim.from.x + (this.ballAnim.to.x - this.ballAnim.from.x) * e,
        y: this.ballAnim.from.y + (this.ballAnim.to.y - this.ballAnim.from.y) * e,
      };
      this.renderPitch();
      if (t < 1) requestAnimationFrame(step);
      else this.ballAnim = null;
    };
    requestAnimationFrame(step);
  }

  appendTelemetryRow(event, timecode) {
    const list = document.getElementById("telemetry-list");
    const placeholder = list.querySelector(".telemetry-placeholder");
    if (placeholder) placeholder.remove();

    const row = document.createElement("div");
    row.className = "telemetry-item";

    const badgeClass = `tele-badge tele-badge-${event.event_type.replace(/_/g, "")}`;
    const side = event.team_id === "avalon_city" ? "home" : "away";
    let who = event.player ? event.player.name : TEAM_NAMES[event.team_id] || "Match";
    if (event.event_type === "added_time") who = `+${event.added_time_minutes} min`;
    if (["half_time", "match_end"].includes(event.event_type)) who = `${event.score_home}–${event.score_away}`;

    const metrics = [];
    if (event.expected_goals) metrics.push(`xG ${event.expected_goals}`);
    if (event.shot_outcome) metrics.push(event.shot_outcome.replace("_", " "));
    if (event.card) metrics.push(`${event.card} card`);
    if (event.ball_speed_kmh) metrics.push(`${event.ball_speed_kmh} km/h`);
    if (event.pass_distance_m) metrics.push(`${event.pass_distance_m} m · diff ${event.pass_difficulty_rating}${event.is_successful ? "" : " · lost"}`);
    if (event.is_sprint_burst) metrics.push(`<span class="tele-sprint">sprint</span>`);

    row.innerHTML = `
      <div class="tele-left">
        <span class="tele-time">${esc(timecode)}</span>
        <span class="${badgeClass}">${esc(event.event_type.replace(/_/g, " "))}</span>
        <span class="tele-team ${side}"></span>
        <span>${esc(who)}</span>
      </div>
      <div class="tele-metrics">${metrics.join(" · ")}</div>
    `;

    list.insertBefore(row, list.firstChild);
    if (list.children.length > 60) list.removeChild(list.lastChild);
  }

  pulsePipeline(trace) {
    const byAgent = {};
    trace.forEach((t) => { byAgent[t.agent] = t; });
    ["ingest", "tactical_analyst", "lead_commentator", "narrator", "verifier", "broadcast"].forEach((id, idx) => {
      setTimeout(() => {
        const el = document.getElementById(`step-${id}`);
        if (!el) return;
        const t = byAgent[id];
        const role = el.querySelector(".step-role");
        if (t) {
          role.textContent = `${t.ms < 1 ? t.ms.toFixed(2) : t.ms.toFixed(1)} ms${t.detail === "foundry-llm" ? " · Foundry" : ""}`;
          role.classList.add("timed");
        }
        el.classList.add("pulse", "active");
        setTimeout(() => el.classList.remove("pulse"), 420);
      }, idx * Math.max(40, 110 / this.speed));
    });
  }

  async fetchAgentTelemetry() {
    try {
      const res = await fetch(`/api/match/${this.matchId}/agents/telemetry`);
      if (!res.ok) return;
      const t = await res.json();
      this.agentTelemetry = t;
      document.getElementById("sys-status-text").textContent = t.foundry_configured ? `Foundry · ${t.model}` : "Local agents";
      document.getElementById("sys-status").title = t.foundry_configured
        ? "Key moments and recaps are generated by the Foundry model and verified"
        : "No Foundry endpoint configured: commentary comes from the verified phrase bank";
      this.renderTelemetryRibbon(t);
    } catch (err) {
      console.warn("Telemetry fetch failed:", err);
    }
  }

  renderTelemetryRibbon(t) {
    const set = (id, v) => { const el = document.getElementById(id); if (el) el.textContent = v; };
    set("tel-grounding", t.claims_checked ? `${(t.grounding_rate * 100).toFixed(1)}%` : "—");
    set("tel-claims", t.claims_checked.toLocaleString());
    set("tel-fallbacks", t.fallbacks_used);
    set("tel-latency", t.events_processed ? `${t.pipeline_latency_ms.toFixed(2)} ms` : "—");
    const status = document.getElementById("foundry-model-status");
    if (status) {
      status.classList.toggle("live", t.foundry_configured);
      status.innerHTML = t.foundry_configured
        ? `<b>Foundry model live:</b> <code>${esc(t.model)}</code> · ${t.llm_attempts} calls on key moments, ${t.llm_lines_accepted} lines accepted, ${t.llm_lines_rejected} rejected by the verifier.`
        : `<b>Foundry endpoint not configured</b> — every line comes from the multilingual phrase bank. Set <code>AZURE_AI_FOUNDRY_ENDPOINT</code>, <code>AZURE_AI_FOUNDRY_API_KEY</code> and <code>AZURE_OPENAI_DEPLOYMENT_NAME</code> to let the commentator and recap writer use your deployment; the verifier gates their output either way.`;
    }
  }

  /* -------------------------------------------------------------------------
     Tactical 2D Pitch Visualizer Engine (Canvas)
     ------------------------------------------------------------------------- */

  initPitch() {
    this.sizePitch();
    this.canvas.addEventListener("click", (e) => this.handlePitchClick(e));
    this.canvas.addEventListener("mousemove", (e) => this.handlePitchMouseMove(e));
  }

  sizePitch() {
    const { ctx, w, h } = fitCanvas(this.canvas);
    this.ctx = ctx;
    this.pitchW = w;
    this.pitchH = h;
    const padX = Math.round(w * 0.035);
    const padY = Math.round(h * 0.05);
    this.field = { x: padX, y: padY, w: w - padX * 2, h: h - padY * 2 };
  }

  toCanvasCoords(normX, normY) {
    const f = this.field;
    return {
      x: f.x + (normX / 100) * f.w,
      y: f.y + (normY / 100) * f.h,
    };
  }

  /** Draws grass and regulation markings (105 x 68 m) into the field rect. */
  drawPitchSurface(ctx, w, h) {
    const f = this.field;
    const sx = f.w / 105;
    const sy = f.h / 68;
    const s = Math.min(sx, sy);

    ctx.fillStyle = C.grassOut;
    ctx.fillRect(0, 0, w, h);

    const stripes = 14;
    const stripeW = f.w / stripes;
    for (let i = 0; i < stripes; i++) {
      ctx.fillStyle = i % 2 === 0 ? C.grassA : C.grassB;
      ctx.fillRect(f.x + i * stripeW, f.y, stripeW + 0.5, f.h);
    }

    // Floodlight vignette
    const vg = ctx.createRadialGradient(w / 2, h / 2, Math.min(w, h) * 0.25, w / 2, h / 2, Math.max(w, h) * 0.75);
    vg.addColorStop(0, "rgba(0,0,0,0)");
    vg.addColorStop(1, "rgba(0,0,0,0.38)");
    ctx.fillStyle = vg;
    ctx.fillRect(0, 0, w, h);

    ctx.strokeStyle = C.line;
    ctx.fillStyle = C.line;
    ctx.lineWidth = Math.max(1.2, w / 600);

    const midX = f.x + f.w / 2;
    const midY = f.y + f.h / 2;

    ctx.strokeRect(f.x, f.y, f.w, f.h);

    ctx.beginPath();
    ctx.moveTo(midX, f.y);
    ctx.lineTo(midX, f.y + f.h);
    ctx.stroke();

    ctx.beginPath();
    ctx.arc(midX, midY, 9.15 * s, 0, Math.PI * 2);
    ctx.stroke();
    ctx.beginPath();
    ctx.arc(midX, midY, Math.max(2, s * 0.35), 0, Math.PI * 2);
    ctx.fill();

    const arcA = Math.acos((16.5 - 11) / 9.15);
    [0, 1].forEach((side) => {
      const dir = side === 0 ? 1 : -1;
      const gx = side === 0 ? f.x : f.x + f.w;

      // Penalty area, goal area
      ctx.strokeRect(side === 0 ? gx : gx - 16.5 * sx, midY - 20.16 * sy, 16.5 * sx, 40.32 * sy);
      ctx.strokeRect(side === 0 ? gx : gx - 5.5 * sx, midY - 9.16 * sy, 5.5 * sx, 18.32 * sy);

      // Penalty spot & arc
      const spotX = gx + dir * 11 * sx;
      ctx.beginPath();
      ctx.arc(spotX, midY, Math.max(1.6, s * 0.3), 0, Math.PI * 2);
      ctx.fill();
      ctx.beginPath();
      if (side === 0) ctx.arc(spotX, midY, 9.15 * s, -arcA, arcA);
      else ctx.arc(spotX, midY, 9.15 * s, Math.PI - arcA, Math.PI + arcA);
      ctx.stroke();

      // Goal frame
      ctx.strokeRect(side === 0 ? gx - 2 * sx : gx, midY - 3.66 * sy, 2 * sx, 7.32 * sy);
    });

    // Corner arcs
    const cr = 1.2 * s;
    [[f.x, f.y, 0, 0.5], [f.x + f.w, f.y, 0.5, 1], [f.x + f.w, f.y + f.h, 1, 1.5], [f.x, f.y + f.h, 1.5, 2]].forEach(([cx, cy, a0, a1]) => {
      ctx.beginPath();
      ctx.arc(cx, cy, cr, a0 * Math.PI, a1 * Math.PI);
      ctx.stroke();
    });
  }

  renderPitch() {
    if (!this.field) return;
    this.sizePitch();
    const ctx = this.ctx;
    const w = this.pitchW;
    const h = this.pitchH;
    const f = this.field;

    ctx.clearRect(0, 0, w, h);
    this.drawPitchSurface(ctx, w, h);

    // Branch to full tactical formations head-to-head comparison if toggled
    if (this.pitchMode === "formations") {
      this.renderTacticalFormations(ctx, w, h);
      return;
    }

    // Optional zonal overlay (thirds)
    if (this.showHeatmap) {
      const thirdW = f.w / 3;
      const zones = [
        { c: C.home, a: 0.16, label: "Defensive third", pct: "34%" },
        { c: C.warn, a: 0.1, label: "Middle third", pct: "42%" },
        { c: C.away, a: 0.16, label: "Attacking third", pct: "24%" },
      ];
      zones.forEach((z, i) => {
        ctx.fillStyle = rgba(z.c, z.a);
        ctx.fillRect(f.x + thirdW * i, f.y, thirdW, f.h);
        ctx.fillStyle = "rgba(236,235,230,0.85)";
        ctx.font = `700 ${Math.round(w / 34)}px ${FONT.display}`;
        ctx.textAlign = "left";
        ctx.textBaseline = "top";
        ctx.fillText(z.pct, f.x + thirdW * i + 10, f.y + 10);
        ctx.font = `500 ${Math.max(9, Math.round(w / 90))}px ${FONT.mono}`;
        ctx.fillStyle = "rgba(236,235,230,0.6)";
        ctx.fillText(z.label.toUpperCase(), f.x + thirdW * i + 10, f.y + 12 + w / 34);
      });
    }

    // Formations & players
    this.renderTeamNodes(this.homeFormation, C.home, "#04131f");
    this.renderTeamNodes(this.awayFormation, C.away, "#1f0604");

    // Pass & shot vectors — newest drawn strongest
    const n = this.passVectors.length;
    this.passVectors.forEach((vec, i) => {
      const p1 = this.toCanvasCoords(vec.start.x, vec.start.y);
      const p2 = this.toCanvasCoords(vec.end.x, vec.end.y);
      const isShot = vec.type === "shot" || vec.type === "goal";
      const alpha = 0.25 + 0.75 * ((i + 1) / n);
      const base = isShot ? C.accent : (vec.failed ? "#8a8a85" : (vec.team === "avalon_city" ? "#9fd4ff" : "#ffb0a8"));

      ctx.save();
      ctx.globalAlpha = alpha;
      ctx.strokeStyle = base;
      ctx.fillStyle = base;
      ctx.lineWidth = isShot ? 2.5 : 1.6;
      if ((vec.difficulty > 0.6 || vec.failed) && !isShot) ctx.setLineDash([5, 4]);

      ctx.beginPath();
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);
      ctx.stroke();
      ctx.setLineDash([]);

      // Arrowhead
      const ang = Math.atan2(p2.y - p1.y, p2.x - p1.x);
      const ah = isShot ? 9 : 7;
      ctx.beginPath();
      ctx.moveTo(p2.x, p2.y);
      ctx.lineTo(p2.x - ah * Math.cos(ang - 0.42), p2.y - ah * Math.sin(ang - 0.42));
      ctx.lineTo(p2.x - ah * Math.cos(ang + 0.42), p2.y - ah * Math.sin(ang + 0.42));
      ctx.closePath();
      ctx.fill();

      if (vec.xg) {
        const label = `xG ${vec.xg}`;
        ctx.font = `600 11px ${FONT.mono}`;
        const tw = ctx.measureText(label).width;
        // Flip the tag to the left of the arrow when it would leave the canvas
        const lx = p2.x + 8 + tw + 10 > w ? p2.x - 8 - tw - 10 : p2.x + 8;
        const ly = Math.max(p2.y - 20, 2);
        ctx.globalAlpha = 1;
        ctx.fillStyle = C.accent;
        ctx.fillRect(lx, ly, tw + 10, 17);
        ctx.fillStyle = C.accentInk;
        ctx.textAlign = "left";
        ctx.textBaseline = "middle";
        ctx.fillText(label, lx + 5, ly + 8.5);
      }
      ctx.restore();
    });

    // Ball
    const ballPos = this.toCanvasCoords(this.displayBall.x, this.displayBall.y);
    const br = Math.max(4.5, w / 150);
    ctx.save();
    ctx.strokeStyle = rgba(C.accent, 0.75);
    ctx.lineWidth = 1.5;
    ctx.beginPath();
    ctx.arc(ballPos.x, ballPos.y, br * 2.4, 0, Math.PI * 2);
    ctx.stroke();
    ctx.fillStyle = "rgba(0,0,0,0.35)";
    ctx.beginPath();
    ctx.ellipse(ballPos.x + 1.5, ballPos.y + 2.5, br, br * 0.7, 0, 0, Math.PI * 2);
    ctx.fill();
    ctx.fillStyle = "#ffffff";
    ctx.strokeStyle = C.bg;
    ctx.lineWidth = 1.2;
    ctx.beginPath();
    ctx.arc(ballPos.x, ballPos.y, br, 0, Math.PI * 2);
    ctx.fill();
    ctx.stroke();
    ctx.restore();
  }

  isHighlighted(p) {
    const isActive = this.activePlayerNode && this.activePlayerNode.toLowerCase().includes(p.name.toLowerCase());
    const isTargetSpotlight = this.currentPlayer && p.name.toLowerCase().includes(this.currentPlayer.toLowerCase());
    return { isActive, isTargetSpotlight };
  }

  renderTeamNodes(players, kitColor, numberColor) {
    const ctx = this.ctx;
    const r = Math.max(7, this.pitchW / 78);
    players.forEach((p) => {
      const pos = this.toCanvasCoords(p.x, p.y);
      const { isActive, isTargetSpotlight } = this.isHighlighted(p);

      ctx.save();
      if (isActive || isTargetSpotlight) {
        ctx.strokeStyle = isTargetSpotlight ? C.accent : "rgba(236,235,230,0.9)";
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, r + 5, 0, Math.PI * 2);
        ctx.stroke();
      }

      ctx.fillStyle = "rgba(0,0,0,0.3)";
      ctx.beginPath();
      ctx.arc(pos.x + 1, pos.y + 2, r, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = kitColor;
      ctx.beginPath();
      ctx.arc(pos.x, pos.y, r, 0, Math.PI * 2);
      ctx.fill();

      ctx.fillStyle = numberColor;
      ctx.font = `700 ${Math.round(r * 1.25)}px ${FONT.display}`;
      ctx.textAlign = "center";
      ctx.textBaseline = "middle";
      ctx.fillText(p.num, pos.x, pos.y + 0.5);
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

    const layouts = {
      "4-2-3-1": [[6, 50], [22, 20], [19, 40], [19, 60], [22, 80], [36, 38], [36, 62], [52, 50], [54, 22], [74, 50], [54, 78]],
      "3-5-2": [[6, 50], [19, 30], [18, 50], [19, 70], [36, 16], [40, 40], [40, 60], [50, 50], [36, 84], [72, 40], [72, 60]],
      "4-3-3": [[6, 50], [22, 20], [19, 40], [19, 60], [22, 80], [38, 50], [48, 32], [48, 68], [70, 22], [74, 50], [70, 78]],
    };
    // 3-5-2 pushes the left-back and right winger into wing-back roles
    const roles = fmt === "3-5-2"
      ? ["GK", "DEF", "DEF", "DEF", "MID", "MID", "MID", "MID", "MID", "FWD", "FWD"]
      : ["GK", "DEF", "DEF", "DEF", "DEF", "MID", "MID", "MID", "FWD", "FWD", "FWD"];
    const coords = layouts[fmt] || layouts["4-3-3"];
    this.homeFormation.forEach((p, i) => {
      p.x = coords[i][0];
      p.y = coords[i][1];
      p.role = roles[i];
    });
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
      if (this.pitchMode === "formations") this.renderPitch();
    } catch (err) {
      console.warn("Match center overview fetch error:", err);
    }
  }

  renderAttackMomentum() {
    const canvas = document.getElementById("momentum-canvas");
    if (!canvas || !canvas.offsetParent || !this.matchCenterData) return;
    const { ctx, w, h } = fitCanvas(canvas);
    const pts = this.matchCenterData.attack_momentum || [];
    ctx.clearRect(0, 0, w, h);

    const padL = 44;
    const padR = 12;
    const padT = 14;
    const padB = 28;
    const plotW = w - padL - padR;
    const half = (h - padT - padB) / 2;
    const centerY = padT + half;

    // One slot per played minute; a blank slot separates the halves. Until the match is
    // over, reserve room for a typical 90 + stoppage so the chart fills left to right.
    const slots = [];
    pts.forEach((pt, i) => {
      if (i > 0 && pt.period !== pts[i - 1].period) slots.push(null);
      slots.push(pt);
    });
    const finished = this.matchCenterData.status && this.matchCenterData.status.phase === "full_time";
    const totalSlots = finished ? Math.max(slots.length, 1) : Math.max(slots.length, 98);
    const slotW = plotW / totalSlots;
    this.momGeom = { padL, slotW, slots };
    const xFor = (i) => padL + i * slotW;

    // Gridlines
    ctx.strokeStyle = C.gridLine;
    ctx.lineWidth = 1;
    [-1, -0.5, 0.5, 1].forEach((k) => {
      ctx.beginPath();
      ctx.moveTo(padL, centerY - k * half);
      ctx.lineTo(w - padR, centerY - k * half);
      ctx.stroke();
    });

    // Team side labels
    ctx.textAlign = "left";
    ctx.textBaseline = "middle";
    ctx.font = `600 11px ${FONT.mono}`;
    ctx.fillStyle = C.home;
    ctx.fillText("AVA", 6, centerY - half / 2);
    ctx.fillStyle = C.away;
    ctx.fillText("SOL", 6, centerY + half / 2);

    if (!pts.length) {
      ctx.strokeStyle = "rgba(236,235,230,0.22)";
      ctx.beginPath();
      ctx.moveTo(padL, centerY);
      ctx.lineTo(w - padR, centerY);
      ctx.stroke();
      ctx.font = `500 11px ${FONT.mono}`;
      ctx.fillStyle = C.text3;
      ctx.textAlign = "center";
      ctx.textBaseline = "top";
      [[0, "0'"], [0.25, "22'"], [0.5, "HT"], [0.75, "67'"], [1, "90'"]].forEach(([f, l]) => ctx.fillText(l, padL + f * plotW, h - padB + 10));
      ctx.font = `500 13px ${FONT.mono}`;
      ctx.textBaseline = "middle";
      ctx.fillText("Momentum builds once the match kicks off", padL + plotW / 2, centerY - 22);
      return;
    }

    // Stoppage time shading and half-time divider
    slots.forEach((pt, i) => {
      if (pt === null) {
        ctx.save();
        ctx.setLineDash([3, 4]);
        ctx.strokeStyle = "rgba(236,235,230,0.25)";
        ctx.beginPath();
        ctx.moveTo(xFor(i) + slotW / 2, padT);
        ctx.lineTo(xFor(i) + slotW / 2, h - padB);
        ctx.stroke();
        ctx.restore();
      } else if (pt.is_stoppage) {
        ctx.fillStyle = "rgba(245,165,36,0.07)";
        ctx.fillRect(xFor(i), padT, slotW, h - padT - padB);
      }
    });

    // Axis labels: every 15', stoppage start, half-time
    ctx.font = `500 11px ${FONT.mono}`;
    ctx.fillStyle = C.text3;
    ctx.textAlign = "center";
    ctx.textBaseline = "top";
    let lastLabelX = -Infinity;
    slots.forEach((pt, i) => {
      let label = null;
      if (pt === null) label = "HT";
      else if (!pt.is_stoppage && pt.minute % 15 === 0 && pt.minute !== 45 && pt.minute !== 90) label = `${pt.minute}'`;
      else if (pt.is_stoppage && i > 0 && slots[i - 1] && !slots[i - 1].is_stoppage) label = pt.period === 1 ? "45'" : "90'";
      else if (i === 0) label = "0'";
      const x = xFor(i) + slotW / 2;
      if (label && x - lastLabelX > 26) {
        ctx.fillStyle = pt && pt.is_stoppage ? C.warn : C.text3;
        ctx.fillText(label, x, h - padB + 10);
        lastLabelX = x;
      }
    });

    // Bars
    const gap = slotW > 6 ? 2 : 1;
    slots.forEach((pt, i) => {
      if (!pt) return;
      const x = xFor(i) + gap / 2;
      const bw = Math.max(slotW - gap, 1);
      const mag = Math.min(Math.abs(pt.value), 100) / 100;
      const barH = mag * half;
      const hovered = this.momentumHoverSlot === i;
      const alpha = hovered ? 1 : 0.35 + 0.6 * mag;

      if (pt.value > 0) {
        ctx.fillStyle = rgba(C.home, alpha);
        ctx.fillRect(x, centerY - barH, bw, barH);
      } else if (pt.value < 0) {
        ctx.fillStyle = rgba(C.away, alpha);
        ctx.fillRect(x, centerY, bw, barH);
      }
      if (hovered) {
        ctx.fillStyle = "rgba(236,235,230,0.06)";
        ctx.fillRect(x - gap / 2, padT, slotW, h - padT - padB);
      }
    });

    // Trend line (5-minute rolling mean), drawn per half
    ctx.save();
    ctx.strokeStyle = "rgba(236,235,230,0.85)";
    ctx.lineWidth = 1.5;
    ctx.lineJoin = "round";
    [1, 2].forEach((period) => {
      const idx = slots.map((pt, i) => (pt && pt.period === period ? i : -1)).filter((i) => i >= 0);
      if (idx.length < 2) return;
      ctx.beginPath();
      idx.forEach((i, k) => {
        const win = idx.slice(Math.max(0, k - 2), k + 3).map((j) => slots[j].value);
        const avg = win.reduce((s, v) => s + v, 0) / win.length;
        const y = centerY - (Math.max(-100, Math.min(100, avg)) / 100) * half;
        if (k === 0) ctx.moveTo(xFor(i) + slotW / 2, y);
        else ctx.lineTo(xFor(i) + slotW / 2, y);
      });
      ctx.stroke();
    });
    ctx.restore();

    // Zero line
    ctx.strokeStyle = "rgba(236,235,230,0.3)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.moveTo(padL, centerY);
    ctx.lineTo(w - padR, centerY);
    ctx.stroke();

    // Incident markers
    slots.forEach((pt, i) => {
      if (!pt || !pt.incidents || !pt.incidents.length) return;
      const cx = xFor(i) + slotW / 2;
      const barH = (Math.min(Math.abs(pt.value), 100) / 100) * half;
      pt.incidents.forEach((inc, k) => {
        const up = inc.team === "avalon_city";
        const cy = up ? Math.max(centerY - barH - 9 - k * 14, padT + 5) : Math.min(centerY + barH + 9 + k * 14, h - padB - 5);
        this.drawIncidentMarker(ctx, inc.type, cx, cy);
      });
    });
  }

  drawIncidentMarker(ctx, type, x, y) {
    ctx.save();
    if (type === "goal") {
      ctx.fillStyle = C.accent;
      ctx.strokeStyle = C.bg;
      ctx.lineWidth = 2;
      ctx.beginPath();
      ctx.arc(x, y, 5.5, 0, Math.PI * 2);
      ctx.fill();
      ctx.stroke();
    } else if (type === "yellow_card" || type === "red_card" || type === "card") {
      ctx.fillStyle = type === "red_card" ? C.bad : "#ffd23f";
      ctx.fillRect(x - 3.5, y - 5, 7, 10);
    } else {
      ctx.fillStyle = C.warn;
      ctx.beginPath();
      ctx.moveTo(x, y - 5);
      ctx.lineTo(x + 5, y + 4);
      ctx.lineTo(x - 5, y + 4);
      ctx.closePath();
      ctx.fill();
    }
    ctx.restore();
  }

  handleMomentumHover(e) {
    const canvas = document.getElementById("momentum-canvas");
    const tip = document.getElementById("momentum-tooltip");
    if (!canvas || !tip || !this.momGeom) return;

    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const slot = Math.floor((mx - this.momGeom.padL) / this.momGeom.slotW);
    const pt = this.momGeom.slots[slot];

    if (pt) {
      if (this.momentumHoverSlot !== slot) {
        this.momentumHoverSlot = slot;
        this.renderAttackMomentum();
      }
      const domName = pt.value > 5 ? "Avalon City" : (pt.value < -5 ? "Solaria Rovers" : "Even");
      const incidentText = pt.incidents && pt.incidents.length
        ? `<div class="tt-inc">${pt.incidents.map((i) => `${esc(i.type.replace("_", " "))} — ${esc(i.player)}`).join("<br>")}</div>`
        : "";

      tip.innerHTML = `
        <div class="tt-title">${esc(pt.label)}${pt.is_stoppage ? " · stoppage time" : ""}</div>
        <div>Dominance <b>${domName}</b> (${pt.value > 0 ? "+" : ""}${pt.value})</div>
        ${incidentText}
      `;
      tip.style.left = `${Math.min(mx + 14, rect.width - 220)}px`;
      tip.style.top = `${Math.min(e.clientY - rect.top + 12, rect.height - 70)}px`;
      tip.classList.remove("hidden");
    } else {
      tip.classList.add("hidden");
      if (this.momentumHoverSlot !== null) {
        this.momentumHoverSlot = null;
        this.renderAttackMomentum();
      }
    }
  }

  renderH2HComparison() {
    const container = document.getElementById("h2h-stats-container");
    if (!container || !this.matchCenterData) return;
    const stats = this.matchCenterData.comparison_stats;
    if (!stats) return;

    const metrics = [
      { key: "expected_goals", label: "Expected goals (xG)", isFloat: true },
      { key: "possession", label: "Possession", isFloat: true, suffix: "%" },
      { key: "total_shots", label: "Shots" },
      { key: "shots_on_target", label: "Shots on target" },
      { key: "big_chances", label: "Big chances" },
      { key: "big_chances_missed", label: "Big chances missed" },
      { key: "accurate_passes", label: "Accurate passes", customVal: true },
      { key: "corners", label: "Corners" },
      { key: "tackles_won", label: "Tackles won", customVal: true },
      { key: "fouls", label: "Fouls" },
      { key: "yellow_cards", label: "Yellow cards" },
      { key: "red_cards", label: "Red cards" },
    ];

    container.innerHTML = metrics.map((m) => {
      const data = stats[m.key] || { home: 0, away: 0 };
      let homeDisplay = data.home;
      let awayDisplay = data.away;

      const homeVal = typeof data.home === "number" ? data.home : parseFloat(data.home);
      const awayVal = typeof data.away === "number" ? data.away : parseFloat(data.away);

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
            <span class="h2h-val-home ${isHomeLeader ? "leader" : ""}">${esc(homeDisplay)}</span>
            <span class="h2h-label">${m.label}</span>
            <span class="h2h-val-away ${isAwayLeader ? "leader" : ""}">${esc(awayDisplay)}</span>
          </div>
          <div class="h2h-bar-track">
            <div class="h2h-half home"><div class="h2h-bar-home ${isHomeLeader ? "leader" : ""}" style="width: ${total > 0 ? homePct : 0}%;"></div></div>
            <div class="h2h-half away"><div class="h2h-bar-away ${isAwayLeader ? "leader" : ""}" style="width: ${total > 0 ? awayPct : 0}%;"></div></div>
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
        const mvpBadge = p.is_mvp ? `<span class="mvp-badge"><svg class="ic"><use href="#i-star"/></svg>MVP</span>` : "";

        return `
          <div class="player-rating-card" data-player-id="${esc(p.player_id || "")}" data-player-name="${esc(p.name)}" title="Open ${esc(p.name)}'s dossier" style="cursor: pointer;">
            <div class="player-info-left">
              <span class="player-jersey-badge">${p.number}</span>
              <span class="player-pos-badge">${esc(p.position)}</span>
              <span class="player-rating-name">${esc(p.name)}</span>
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

    [homeList, awayList].forEach((list) => {
      list.querySelectorAll(".player-rating-card").forEach((card) => {
        card.addEventListener("click", () => this.openPlayerModal(card.dataset.playerId, card.dataset.playerName));
      });
    });
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
      this.renderPitch();
      if (this.isStreaming) this.restartStream();
    }
  }

  /**
   * Shots are mirrored so every attempt attacks the same goal, then drawn on a
   * vertical final-40m view (goal at the top) at true pitch proportions.
   */
  shotToCanvas(shot, geom) {
    const x = shot.is_home === false ? 100 - shot.x : shot.x;
    const y = shot.is_home === false ? 100 - shot.y : shot.y;
    const depth = Math.min(Math.max(105 - (x / 100) * 105, 0), geom.depth - 1);
    return {
      x: geom.x + (y / 100) * 68 * geom.s,
      y: geom.y + depth * geom.s,
    };
  }

  renderShotMap() {
    const canvas = document.getElementById("shotmap-canvas");
    if (!canvas || !canvas.offsetParent || !this.matchCenterData) return;
    const { ctx, w, h } = fitCanvas(canvas);
    const shots = this.matchCenterData.shot_map || [];
    ctx.clearRect(0, 0, w, h);

    // Final 40 m of a 68 m-wide pitch, goal at the top
    const depth = 40;
    const s = Math.min((w - 24) / 68, (h - 18) / (depth + 2.2));
    const fw = 68 * s;
    const fh = depth * s;
    const geom = { x: (w - fw) / 2, y: h - fh, s, depth };
    this.shotGeom = geom;
    const cx = geom.x + fw / 2;
    const gy = geom.y;

    ctx.fillStyle = C.grassOut;
    ctx.fillRect(0, 0, w, h);
    const stripes = 8;
    for (let i = 0; i < stripes; i++) {
      ctx.fillStyle = i % 2 === 0 ? C.grassA : C.grassB;
      ctx.fillRect(geom.x, gy + (i * fh) / stripes, fw, fh / stripes + 0.5);
    }

    ctx.strokeStyle = C.line;
    ctx.fillStyle = C.line;
    ctx.lineWidth = 1.4;
    ctx.beginPath();
    ctx.moveTo(geom.x, h);
    ctx.lineTo(geom.x, gy);
    ctx.lineTo(geom.x + fw, gy);
    ctx.lineTo(geom.x + fw, h);
    ctx.stroke();
    ctx.strokeRect(cx - 20.16 * s, gy, 40.32 * s, 16.5 * s);
    ctx.strokeRect(cx - 9.16 * s, gy, 18.32 * s, 5.5 * s);
    ctx.strokeRect(cx - 3.66 * s, gy - 2 * s, 7.32 * s, 2 * s);
    ctx.beginPath();
    ctx.arc(cx, gy + 11 * s, 2, 0, Math.PI * 2);
    ctx.fill();
    const arcA = Math.asin((16.5 - 11) / 9.15);
    ctx.beginPath();
    ctx.arc(cx, gy + 11 * s, 9.15 * s, arcA, Math.PI - arcA);
    ctx.stroke();

    // Distance guides
    ctx.font = `500 10px ${FONT.mono}`;
    ctx.fillStyle = "rgba(236,235,230,0.4)";
    ctx.textAlign = "right";
    ctx.textBaseline = "middle";
    [20, 30].forEach((m) => {
      ctx.fillText(`${m}m`, geom.x + fw - 6, gy + m * s);
      ctx.fillRect(geom.x + fw - 4, gy + m * s, 4, 1);
    });

    if (!shots.length) {
      ctx.fillStyle = "rgba(236,235,230,0.55)";
      ctx.font = `500 13px ${FONT.mono}`;
      ctx.textAlign = "center";
      ctx.fillText("No shots yet", cx, gy + 28 * s);
    }

    // Shots — bigger circle, bigger chance
    shots.forEach((shot) => {
      const p = this.shotToCanvas(shot, geom);
      const r = Math.max(Math.sqrt(shot.xg || 0.05) * 26, 5);
      const team = shot.is_home === false ? C.away : C.home;

      ctx.save();
      if (shot.outcome === "goal") {
        ctx.fillStyle = C.accent;
        ctx.strokeStyle = C.bg;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
        ctx.strokeStyle = team;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(p.x, p.y, r + 3, 0, Math.PI * 2);
        ctx.stroke();
      } else if (shot.outcome === "saved") {
        ctx.fillStyle = rgba(team, 0.25);
        ctx.strokeStyle = team;
        ctx.lineWidth = 2;
        ctx.beginPath();
        ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
        ctx.fill();
        ctx.stroke();
      } else {
        ctx.strokeStyle = rgba(team, 0.75);
        ctx.lineWidth = 1.5;
        ctx.setLineDash([3, 3]);
        ctx.beginPath();
        ctx.arc(p.x, p.y, r, 0, Math.PI * 2);
        ctx.stroke();
      }
      ctx.restore();
    });

    // Summary sidebar
    const summary = document.getElementById("shotmap-summary");
    if (summary) {
      const goals = shots.filter((sh) => sh.outcome === "goal").length;
      const totalXg = shots.reduce((sum, sh) => sum + (sh.xg || 0), 0).toFixed(2);
      const conversion = shots.length > 0 ? Math.round((goals / shots.length) * 100) : 0;

      summary.innerHTML = `
        <div class="stat-pill"><span class="stat-num">${shots.length}</span><span class="stat-lbl">Shots</span></div>
        <div class="stat-pill"><span class="stat-num accent">${goals}</span><span class="stat-lbl">Goals</span></div>
        <div class="stat-pill"><span class="stat-num">${totalXg}</span><span class="stat-lbl">Total xG</span></div>
        <div class="stat-pill"><span class="stat-num">${conversion}%</span><span class="stat-lbl">Conversion</span></div>
      `;
    }
  }

  handleShotMapHover(e) {
    const canvas = document.getElementById("shotmap-canvas");
    const tip = document.getElementById("shotmap-tooltip");
    if (!canvas || !tip || !this.matchCenterData || !this.shotGeom) return;

    const rect = canvas.getBoundingClientRect();
    const mx = e.clientX - rect.left;
    const my = e.clientY - rect.top;
    const shots = this.matchCenterData.shot_map || [];

    const hovered = shots.find((shot) => {
      const p = this.shotToCanvas(shot, this.shotGeom);
      return Math.hypot(mx - p.x, my - p.y) <= Math.max(Math.sqrt(shot.xg || 0.05) * 26, 10);
    });

    if (hovered) {
      tip.innerHTML = `
        <div class="tt-title">${esc(hovered.player_name)} · ${esc(hovered.minute_label || hovered.minute + "'")}</div>
        <div>Outcome <b>${esc(hovered.outcome.replace("_", " "))}</b></div>
        <div>xG <b>${(hovered.xg || 0).toFixed(2)}</b> · <b>${hovered.shot_speed_kmh ?? "—"}</b> km/h</div>
      `;
      tip.style.left = `${Math.min(mx + 14, rect.width - 200)}px`;
      tip.style.top = `${Math.min(my + 12, rect.height - 80)}px`;
      tip.classList.remove("hidden");
      canvas.style.cursor = "pointer";
    } else {
      tip.classList.add("hidden");
      canvas.style.cursor = "default";
    }
  }

  renderTimeline() {
    const list = document.getElementById("timeline-stream-list");
    if (!list || !this.matchCenterData) return;
    const timeline = this.matchCenterData.timeline || [];

    list.classList.toggle("is-empty", !timeline.length);
    if (!timeline.length) {
      list.innerHTML = `<div class="empty-state">No incidents yet. Goals, cards, stoppage time and the whistles appear here as the match unfolds.</div>`;
      return;
    }

    list.innerHTML = timeline.map((item) => {
      const icons = { goal: "ti-goal", yellow_card: "ti-card", red_card: "ti-red", added_time: "ti-added" };
      const iconClass = icons[item.type] || "ti-whistle";
      const sideClass = item.is_phase ? "phase" : (item.is_home ? "home" : "away");

      return `
        <div class="timeline-event-card ${sideClass}" title="${esc(item.event_id)}">
          <span class="timeline-minute">${esc(item.minute_label || item.minute + "'")}</span>
          <span class="timeline-icon"><span class="${iconClass}"></span></span>
          <div class="timeline-details">
            <span class="timeline-title">${esc(item.title)}</span>
            <span class="timeline-desc">${esc(item.detail)}</span>
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
    ctx.fillStyle = "rgba(0,0,0,0.18)";
    ctx.fillRect(0, 0, w, h);

    // Tactical unit connecting lines (defence, midfield, attack)
    const drawUnitLines = (players, color) => {
      ctx.save();
      ctx.strokeStyle = color;
      ctx.lineWidth = 1.5;
      ctx.setLineDash([4, 4]);
      ["DEF", "MID", "FWD"].forEach((role) => {
        const unit = players.filter((p) => p.role === role).sort((a, b) => a.y - b.y);
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

    drawUnitLines(this.homeFormation, rgba(C.home, 0.55));
    drawUnitLines(this.awayFormation, rgba(C.away, 0.55));

    // Formation labels
    ctx.font = `700 ${Math.round(w / 40)}px ${FONT.display}`;
    ctx.textBaseline = "top";
    ctx.fillStyle = C.home;
    ctx.textAlign = "left";
    ctx.fillText(`AVA ${this.currentFormation}`, this.field.x + 10, this.field.y + 8);
    ctx.fillStyle = C.away;
    ctx.textAlign = "right";
    ctx.fillText("4-3-3 SOL", this.field.x + this.field.w - 10, this.field.y + 8);

    ctx.font = `500 ${Math.max(9, Math.round(w / 95))}px ${FONT.mono}`;
    ctx.fillStyle = "rgba(236,235,230,0.55)";
    ctx.textAlign = "center";
    ctx.textBaseline = "bottom";
    ctx.fillText("CLICK A PLAYER FOR THE FULL DOSSIER", w / 2, this.field.y + this.field.h - 8);

    const lineup = this.matchCenterData && this.matchCenterData.lineups
      ? [...(this.matchCenterData.lineups.home || []), ...(this.matchCenterData.lineups.away || [])]
      : [];

    const r = Math.max(10, w / 64);
    // Away plates sit above the node so mirrored opponents on the same line don't collide
    const renderFormationXI = (players, kitColor, numberColor, plateAbove) => {
      players.forEach((p) => {
        const pos = this.toCanvasCoords(p.x, p.y);
        const { isActive, isTargetSpotlight } = this.isHighlighted(p);
        const matched = lineup.find((lp) => lp.player_id === p.id || lp.name.toLowerCase() === p.name.toLowerCase());

        ctx.save();

        if (isActive || isTargetSpotlight) {
          ctx.strokeStyle = isTargetSpotlight ? C.accent : "rgba(236,235,230,0.9)";
          ctx.lineWidth = 2;
          ctx.beginPath();
          ctx.arc(pos.x, pos.y, r + 5, 0, Math.PI * 2);
          ctx.stroke();
        }

        ctx.fillStyle = "rgba(0,0,0,0.35)";
        ctx.beginPath();
        ctx.arc(pos.x + 1, pos.y + 2, r, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = kitColor;
        ctx.beginPath();
        ctx.arc(pos.x, pos.y, r, 0, Math.PI * 2);
        ctx.fill();

        ctx.fillStyle = numberColor;
        ctx.font = `800 ${Math.round(r * 1.15)}px ${FONT.display}`;
        ctx.textAlign = "center";
        ctx.textBaseline = "middle";
        ctx.fillText(p.num, pos.x, pos.y + 0.5);

        // Name plate (+ live rating)
        const surname = p.name.split(" ").slice(-1)[0].toUpperCase();
        ctx.font = `700 ${Math.max(10, Math.round(r * 0.9))}px ${FONT.display}`;
        const nameW = ctx.measureText(surname).width;
        const ratingW = matched ? 26 : 0;
        const plateW = nameW + 10 + ratingW;
        const plateH = Math.max(14, r * 1.1);
        const px = pos.x - plateW / 2;
        const py = plateAbove ? pos.y - r - 5 - plateH : pos.y + r + 5;

        ctx.fillStyle = "rgba(11,12,14,0.88)";
        ctx.fillRect(px, py, plateW, plateH);
        ctx.fillStyle = C.text;
        ctx.textAlign = "left";
        ctx.fillText(surname, px + 5, py + plateH / 2 + 0.5);

        if (matched) {
          const pillColor = matched.rating_color === "green" ? C.good : (matched.rating_color === "red" ? C.bad : C.warn);
          ctx.fillStyle = pillColor;
          ctx.fillRect(px + plateW - ratingW, py, ratingW, plateH);
          ctx.fillStyle = C.bg;
          ctx.font = `600 ${Math.max(9, Math.round(r * 0.72))}px ${FONT.mono}`;
          ctx.textAlign = "center";
          ctx.fillText(matched.rating.toFixed(1), px + plateW - ratingW / 2, py + plateH / 2 + 0.5);
        }

        ctx.restore();
      });
    };

    renderFormationXI(this.homeFormation, C.home, "#04131f", false);
    renderFormationXI(this.awayFormation, C.away, "#1f0604", true);
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

      if (!standingsRes.ok) return;

      const league = await standingsRes.json();
      const table = league.standings || [];
      // Only the two match clubs have full profiles; others fall back to their table row
      const team = teamRes.ok ? await teamRes.json() : null;
      const row = table.find((club) => club.team_id === this.currentModalTeamId) || {};
      const teamColor = this.currentModalTeamId === "avalon_city" ? C.home : (this.currentModalTeamId === "solaria_rovers" ? C.away : (row.primary_color || C.text3));

      // Populate Header
      document.getElementById("modal-team-name").textContent = team ? team.name : row.team_name;
      document.getElementById("modal-team-meta").textContent = team
        ? `${team.nickname} · ${team.stadium} (${team.stadium_capacity.toLocaleString()}) · Founded ${team.founded}`
        : `${league.league_name} · ${row.rank}${["st", "nd", "rd"][row.rank - 1] || "th"} place`;
      const colorBox = document.getElementById("modal-team-color-box");
      if (colorBox) colorBox.style.background = teamColor;

      // Populate Standings Table
      const tbody = document.getElementById("standings-tbody");
      if (tbody) {
        const zoneClass = { continental_elite: "zone-cl", continental_cup: "zone-el", relegation: "zone-rel" };
        tbody.innerHTML = table.map((club) => {
          const isSelected = club.team_id === this.currentModalTeamId;
          const formDots = (club.form || []).map((f) => {
            const cls = f === "W" ? "form-w" : (f === "D" ? "form-d" : "form-l");
            return `<span class="form-dot ${cls}">${esc(f)}</span>`;
          }).join("");

          return `
            <tr class="${zoneClass[club.zone] || ""} ${club.is_current_match ? "current-match-team" : ""} ${isSelected ? "is-selected" : ""}">
              <td>${club.rank}</td>
              <td class="club-col" data-team-id="${esc(club.team_id)}" title="Open club">${esc(club.team_name)}</td>
              <td>${club.played}</td>
              <td>${club.won}</td>
              <td>${club.drawn}</td>
              <td>${club.lost}</td>
              <td>${club.goals_for}</td>
              <td>${club.goals_against}</td>
              <td>${club.goal_difference > 0 ? "+" : ""}${club.goal_difference}</td>
              <td class="pts-col">${club.points}</td>
              <td><div class="form-badge-group">${formDots}</div></td>
            </tr>
          `;
        }).join("");
        tbody.querySelectorAll(".club-col").forEach((cell) => {
          cell.addEventListener("click", () => this.openTeamModal(cell.dataset.teamId));
        });
      }

      // Populate Club Profile
      const profTab = document.querySelector('#team-modal .modal-tab-btn[data-modaltab="team-tab-profile"]');
      if (profTab) {
        profTab.classList.toggle("hidden", !team);
        if (!team) document.querySelector('#team-modal .modal-tab-btn[data-modaltab="team-tab-standings"]').click();
      }

      const profContainer = document.getElementById("team-profile-content");
      if (profContainer && team) {
        const st = team.season_stats || {};
        const recentRows = (team.recent_matches || []).map((m) => {
          const resClass = m.outcome === "W" ? "form-w" : (m.outcome === "D" ? "form-d" : "form-l");
          return `
            <div class="stat-metric-row">
              <span class="metric-lbl">vs ${esc(m.opponent)} <span class="cell-num">${esc(m.venue)}</span></span>
              <span class="metric-val"><span class="mono">${esc(m.result)}</span><span class="form-dot ${resClass}">${esc(m.outcome)}</span></span>
            </div>
          `;
        }).join("");
        const traits = (team.tactical_traits || []).map((t) => `<li>${esc(t)}</li>`).join("");

        profContainer.innerHTML = `
          <div class="profile-card-block">
            <h4>Tactical identity</h4>
            <div class="stat-metric-row"><span class="metric-lbl">Head coach</span><span class="metric-val">${esc(team.head_coach)}</span></div>
            <div class="stat-metric-row"><span class="metric-lbl">System</span><span class="metric-val accent">${esc(team.tactical_system)}</span></div>
            <div class="stat-metric-row"><span class="metric-lbl">Season record</span><span class="metric-val">${esc(team.season_record)}</span></div>
            <div class="stat-metric-row"><span class="metric-lbl">Goals for / against</span><span class="metric-val">${st.goals_scored} / ${st.goals_conceded}</span></div>
            <div class="stat-metric-row"><span class="metric-lbl">Possession · PPDA</span><span class="metric-val">${st.avg_possession}% · ${st.ppda}</span></div>
            <div class="stat-metric-row"><span class="metric-lbl">Top scorer</span><span class="metric-val">${esc(st.top_scorer)}</span></div>
            <div class="stat-metric-row"><span class="metric-lbl">Top assister</span><span class="metric-val">${esc(st.top_assister)}</span></div>
          </div>
          <div class="profile-card-block">
            <h4>Recent results</h4>
            ${recentRows}
            <h4 class="traits-title">Tactical traits</h4>
            <ul class="traits-list">${traits}</ul>
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
      const photoEl = document.getElementById("modal-player-photo");
      const photo = PLAYER_PHOTOS[data.player_id];
      photoEl.classList.toggle("hidden", !photo);
      photoEl.style.backgroundImage = photo ? `url("${photo}")` : "";
      document.getElementById("modal-player-num").textContent = data.number;
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
            <span><span class="cell-num">${esc(c.period)}</span>&nbsp; ${esc(c.club)}</span>
            <span class="muted">${c.appearances} apps · ${c.goals} gls</span>
          </div>
        `).join("");
      }

      const honorsList = document.getElementById("cv-honors-list");
      if (honorsList) {
        honorsList.innerHTML = (data.career.honours || []).map((hn) => `<span class="honor-tag">${esc(hn)}</span>`).join("");
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
            <span class="lbl">Live rating</span>
          </div>
          <div class="metric-card-mini">
            <span class="num">${live.distance_km || 0.0}<small> km</small></span>
            <span class="lbl">Distance</span>
          </div>
          <div class="metric-card-mini">
            <span class="num">${live.sprint_bursts || 0}</span>
            <span class="lbl">Sprints</span>
          </div>
          <div class="metric-card-mini">
            <span class="num">${live.pass_accuracy || 0}%</span>
            <span class="lbl">Passing ${live.completed_passes || 0}/${live.total_passes || 0}</span>
          </div>
          <div class="metric-card-mini">
            <span class="num">${live.goals || 0} / ${live.total_shots || 0}</span>
            <span class="lbl">Goals / shots</span>
          </div>
          <div class="metric-card-mini">
            <span class="num">${live.tackles_won || 0}</span>
            <span class="lbl">Tackles won</span>
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
            <span class="lbl">Appearances</span>
          </div>
          <div class="metric-card-mini">
            <span class="num">${s.goals || 0} <small>G</small> · ${s.assists || 0} <small>A</small></span>
            <span class="lbl">Goals &amp; assists</span>
          </div>
          <div class="metric-card-mini">
            <span class="num">${(s.xg_per_90 || 0).toFixed(2)}</span>
            <span class="lbl">xG per 90</span>
          </div>
          <div class="metric-card-mini">
            <span class="num">${s.pass_completion_rate || 0}%</span>
            <span class="lbl">Pass completion</span>
          </div>
          <div class="metric-card-mini" style="grid-column: span 2;">
            <span class="num accent">${s.top_speed_kmh || 0}<small> km/h</small></span>
            <span class="lbl">Top speed this season</span>
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
      if (badge) badge.textContent = `${this.liveTableRows.length} records`;
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
    if (badge) badge.textContent = `${this.liveTableRows.length} records`;

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
          <td colspan="9" class="empty-state">
            ${this.liveTableRows.length === 0 ? "No events ingested yet. Kick off the stream to fill the table." : "No events match this search or filter."}
          </td>
        </tr>
      `;
      return;
    }

    tbody.innerHTML = filtered.slice(0, 50).map((r) => {
      const isHome = r.team_id === "avalon_city";
      const typeBadgeClass = `tele-badge tele-badge-${r.event_type.replace(/_/g, "")}`;
      const xgHot = parseFloat(r.expected_goals) > 0.15 ? "xg-hot" : "";

      return `
        <tr>
          <td><span class="mono">${esc(r.match_time)}</span></td>
          <td><span class="cell-team cell-link" style="--team: ${isHome ? C.home : C.away}" data-team-id="${esc(r.team_id)}">${esc(r.team_name)}</span></td>
          <td><span class="cell-link" data-player-id="${esc(r.player_id)}" data-player-name="${esc(r.player_name)}">${esc(r.player_name)}</span> <span class="cell-num">#${r.player_number}</span></td>
          <td><span class="${typeBadgeClass}">${esc(r.event_type.replace(/_/g, " "))}</span></td>
          <td><span class="mono">${r.start_x}, ${r.start_y}</span></td>
          <td class="num-col"><span class="mono ${xgHot}">${r.expected_goals}</span></td>
          <td class="num-col"><span class="mono">${r.pass_difficulty}</span></td>
          <td class="num-col"><span class="mono">${r.shot_speed_kmh}</span></td>
          <td><span class="fabric-badge"><svg class="ic"><use href="#i-check"/></svg>OneLake</span></td>
        </tr>
      `;
    }).join("");

    tbody.querySelectorAll("[data-team-id]").forEach((el) => {
      el.addEventListener("click", () => this.openTeamModal(el.dataset.teamId));
    });
    tbody.querySelectorAll("[data-player-name]").forEach((el) => {
      el.addEventListener("click", () => this.openPlayerModal(el.dataset.playerId, el.dataset.playerName));
    });
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
        if (this.foundryAgentsData.telemetry) this.renderTelemetryRibbon(this.foundryAgentsData.telemetry);
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
      const usesModel = (agent.execution || "").startsWith("foundry");
      const tools = (agent.tools || []).slice(0, 2).join(", ");
      const ms = typeof agent.latency_ms === "number" && agent.latency_ms > 0 ? `${agent.latency_ms.toFixed(2)} ms avg` : "idle";
      return `
        <div class="agent-pipeline-card">
          <div class="agent-card-top">
            <span class="agent-model-pill">${usesModel ? "Foundry model" : "code"}</span>
            <span class="agent-status-dot" title="Online"></span>
          </div>
          <div class="agent-name">${esc(agent.name)}</div>
          <div class="agent-role-pill">${esc(agent.role)}</div>
          <div class="agent-tools-list">${esc(tools)}</div>
          <div class="agent-handoff-flow">→ ${esc(agent.handoff_to)} · ${ms}</div>
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
    const btnLabel = btn ? btn.querySelector("span") : null;

    if (btn) {
      btnLabel.textContent = "Sending…";
      btn.disabled = true;
    }

    try {
      const res = await fetch("/api/integrations/power-automate/dispatch", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          event_type: eventType,
          webhook_url: webhookUrl || null,
          match_id: this.matchId,
        }),
      });

      const data = await res.json();
      if (statusBox) {
        statusBox.classList.remove("hidden", "error");
        const isSimulated = data.status === "simulated_success";
        statusBox.innerHTML = `
          <strong>${isSimulated ? "Validated in simulation mode" : "Delivered to webhook"}</strong>
          <div class="mono">${esc(data.event_type)} · ${esc(data.timestamp)} · ${esc(data.status)}</div>
          <div>${isSimulated ? "Payload checked against Adaptive Card v1.5 and ready for a Teams channel webhook." : `Webhook responded with HTTP ${esc(data.status_code)}.`}</div>
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
        statusBox.classList.add("error");
        statusBox.innerHTML = `<strong>Dispatch failed</strong><div>${esc(err.message)}</div>`;
      }
    } finally {
      if (btn) {
        btnLabel.textContent = "Dispatch";
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
        html += `<div class="ac-card-banner ${styleClass}">${esc(innerText)}</div>`;
      } else if (block.type === "TextBlock") {
        const isBolder = block.weight === "Bolder";
        const fontSize = block.size === "Large" ? "1.1rem" : (block.size === "ExtraLarge" ? "1.4rem" : "0.85rem");
        html += `<div class="ac-narrative-text" style="font-size: ${fontSize}; font-weight: ${isBolder ? "700" : "400"};">${esc(block.text)}</div>`;
      } else if (block.type === "FactSet") {
        html += `<table class="ac-fact-table">`;
        (block.facts || []).forEach((f) => {
          html += `<tr><td class="ac-fact-title">${esc(f.title)}</td><td class="ac-fact-value">${esc(f.value)}</td></tr>`;
        });
        html += `</table>`;
      }
    });

    if (card.actions && card.actions.length > 0) {
      html += `<div class="ac-actions-row">`;
      card.actions.forEach((act) => {
        html += `<a href="${esc(act.url || "#")}" target="_blank" rel="noopener" class="ac-action-btn">${esc(act.title)}</a>`;
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
