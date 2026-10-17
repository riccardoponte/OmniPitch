const pptxgen = require("pptxgenjs");
const path = require("path");

function createOmniPitchDeck() {
  const pres = new pptxgen();
  pres.layout = "LAYOUT_16x9"; // 10" x 5.625"
  pres.author = "OmniPitch Engineering Team";
  pres.company = "Microsoft & Premier League Hackathon";
  pres.title = "OmniPitch - Pitch Deck";

  // Palette (Hex without #)
  const BG_DARK = "070D1E";
  const CARD_BG = "121D38";
  const CARD_BORDER = "1E3A5F";
  const TEXT_WHITE = "FFFFFF";
  const TEXT_MUTED = "94A3B8";
  const ACCENT_CYAN = "00F2FE";
  const ACCENT_GREEN = "10B981";
  const ACCENT_GOLD = "FBBF24";

  // Helper to add card container
  function addCard(slide, x, y, w, h, fill = CARD_BG, line = CARD_BORDER) {
    slide.addShape(pres.ShapeType.rect, {
      x, y, w, h,
      fill: { color: fill },
      line: { color: line, width: 1 },
    });
  }

  // =========================================================================
  // SLIDE 1: Title & Executive Overview
  // =========================================================================
  {
    const s1 = pres.addSlide();
    s1.background = { color: BG_DARK };

    // Header Tag
    s1.addText("MICROSOFT & PREMIER LEAGUE HACKATHON  |  GRAND PRIZE SUBMISSION", {
      x: 0.8, y: 0.6, w: 8.4, h: 0.3,
      fontSize: 10, bold: true, color: ACCENT_CYAN, fontFace: "Calibri", charSpacing: 2,
    });

    // Title
    s1.addText("OmniPitch", {
      x: 0.8, y: 0.95, w: 8.4, h: 0.9,
      fontSize: 44, bold: true, color: TEXT_WHITE, fontFace: "Calibri", margin: 0,
    });

    // Subtitle
    s1.addText("Personalized Synthetic Match Intelligence on Microsoft AI", {
      x: 0.8, y: 1.85, w: 8.4, h: 0.4,
      fontSize: 18, color: ACCENT_GREEN, fontFace: "Calibri", bold: true, margin: 0,
    });

    // Vision statement card
    addCard(s1, 0.8, 2.45, 8.4, 1.25);
    s1.addText("Transforming high-frequency synthetic football telemetry into explainable tactical intelligence, automated multi-persona broadcast narratives, and longitudinal performance analytics—grounded by an anti-hallucination verification auditor and powered by Microsoft AI Foundry, Fabric Lakehouse, and MCP.", {
      x: 1.0, y: 2.55, w: 8.0, h: 1.05,
      fontSize: 13, color: TEXT_MUTED, fontFace: "Calibri", lineSpacing: 20,
    });

    // 4 Key Stat Pill Cards
    const stats = [
      { val: "5", label: "Autonomous AI Agents", sub: "Blackboard Collaboration" },
      { val: "100%", label: "Synthetic Physics Data", sub: "Zero Copyright Footprint" },
      { val: "< 10ms", label: "Inference Latency", sub: "Graceful Cloud Fallback" },
      { val: "23 / 23", label: "Automated Tests", sub: "CI/CD Production Ready" }
    ];

    stats.forEach((st, i) => {
      const bx = 0.8 + i * 2.15;
      addCard(s1, bx, 3.9, 1.95, 1.15);
      s1.addText(st.val, {
        x: bx, y: 4.0, w: 1.95, h: 0.45,
        fontSize: 22, bold: true, color: ACCENT_CYAN, fontFace: "Calibri", align: "center", margin: 0,
      });
      s1.addText(st.label, {
        x: bx, y: 4.45, w: 1.95, h: 0.25,
        fontSize: 9.5, bold: true, color: TEXT_WHITE, fontFace: "Calibri", align: "center", margin: 0,
      });
      s1.addText(st.sub, {
        x: bx, y: 4.7, w: 1.95, h: 0.25,
        fontSize: 8, color: TEXT_MUTED, fontFace: "Calibri", align: "center", margin: 0,
      });
    });

    s1.addNotes("Good day esteemed judges. Welcome to OmniPitch, a personalized synthetic match intelligence platform developed for the Microsoft and Premier League Hackathon. OmniPitch bridges the gap between raw match data and deep, understandable football intelligence.");
  }

  // =========================================================================
  // SLIDE 2: The Core Problem & Industry Challenge
  // =========================================================================
  {
    const s2 = pres.addSlide();
    s2.background = { color: BG_DARK };

    s2.addText("THE OPPORTUNITY", {
      x: 0.8, y: 0.5, w: 8.4, h: 0.25,
      fontSize: 10, bold: true, color: ACCENT_CYAN, fontFace: "Calibri", charSpacing: 2,
    });
    s2.addText("Why Traditional Sports Analytics Fall Short", {
      x: 0.8, y: 0.75, w: 8.4, h: 0.5,
      fontSize: 26, bold: true, color: TEXT_WHITE, fontFace: "Calibri", margin: 0,
    });

    const challenges = [
      {
        title: "1. One-Size-Fits-All Broadcasts",
        desc: "Broadcast graphics today are static. Casual fans get overwhelmed by raw stats like pass completion %, while tactical analysts lack deep context on defensive compactness and packing rate.",
        accent: "E11D48"
      },
      {
        title: "2. The LLM Hallucination Risk",
        desc: "Generative AI applied naively to live sports fabricates events, scores, and player actions. Live broadcasting cannot tolerate unverified narratives during high-stakes matches.",
        accent: "F59E0B"
      },
      {
        title: "3. Disconnected Data Silos",
        desc: "Spatial coordinate telemetry, physical sprint data, and qualitative match reports live in disparate tools (Hudl, WyScout, Opta), requiring manual curation and hours of post-match review.",
        accent: "3B82F6"
      }
    ];

    challenges.forEach((ch, idx) => {
      const cx = 0.8 + idx * 2.85;
      addCard(s2, cx, 1.45, 2.7, 3.5);
      
      // Accent header bar
      s2.addShape(pres.ShapeType.rect, {
        x: cx, y: 1.45, w: 2.7, h: 0.08,
        fill: { color: ch.accent },
        line: { color: ch.accent, width: 0 },
      });

      s2.addText(ch.title, {
        x: cx + 0.2, y: 1.7, w: 2.3, h: 0.6,
        fontSize: 14, bold: true, color: TEXT_WHITE, fontFace: "Calibri", margin: 0,
      });

      s2.addText(ch.desc, {
        x: cx + 0.2, y: 2.4, w: 2.3, h: 2.3,
        fontSize: 11.5, color: TEXT_MUTED, fontFace: "Calibri", lineSpacing: 18, margin: 0,
      });
    });

    s2.addNotes("Modern sports broadcasting faces three fundamental bottlenecks: a generic broadcast feed that doesn't adapt to whether a fan or an analyst is watching, the dangerous hallucination risk of ungrounded LLMs, and fragmented data architectures. OmniPitch solves all three.");
  }

  // =========================================================================
  // SLIDE 3: Multi-Agent Blackboard Architecture
  // =========================================================================
  {
    const s3 = pres.addSlide();
    s3.background = { color: BG_DARK };

    s3.addText("INNOVATION PILLAR 1: MULTI-AGENT REASONING", {
      x: 0.8, y: 0.5, w: 8.4, h: 0.25,
      fontSize: 10, bold: true, color: ACCENT_CYAN, fontFace: "Calibri", charSpacing: 2,
    });
    s3.addText("Autonomous Multi-Agent System & Verifier", {
      x: 0.8, y: 0.75, w: 8.4, h: 0.5,
      fontSize: 26, bold: true, color: TEXT_WHITE, fontFace: "Calibri", margin: 0,
    });

    const agents = [
      { name: "Tactical Analyst Agent", role: "Calculates Control vs Chaos gauge, territorial dominance, and pressing compactness.", icon: "TACTICS" },
      { name: "Player Focus Agent", role: "Monitors longitudinal sprints (>25 km/h), physical strain, and spatial pitch heatmaps.", icon: "PHYSICAL" },
      { name: "Narrator Agent", role: "Tailors commentary dynamically for Analyst vs Casual Fan in 4 languages (EN, IT, ES, DE).", icon: "NARRATIVE" },
      { name: "Grounding Verifier Agent", role: "Anti-hallucination auditor. Math-checks claims against exact event telemetry IDs (EVT-XXXX).", icon: "VERIFIED" },
      { name: "Broadcaster Overlay Agent", role: "Generates synchronized, low-latency JSON payloads for live TV and streaming overlays.", icon: "OVERLAY" },
    ];

    agents.forEach((ag, i) => {
      const ay = 1.45 + i * 0.74;
      addCard(s3, 0.8, ay, 8.4, 0.65);

      s3.addText(ag.icon, {
        x: 1.0, y: ay + 0.18, w: 1.1, h: 0.3,
        fontSize: 9, bold: true, color: ACCENT_CYAN, fontFace: "Calibri",
      });

      s3.addText(ag.name, {
        x: 2.2, y: ay + 0.16, w: 2.6, h: 0.32,
        fontSize: 12.5, bold: true, color: TEXT_WHITE, fontFace: "Calibri", margin: 0,
      });

      s3.addText(ag.role, {
        x: 4.8, y: ay + 0.16, w: 4.2, h: 0.35,
        fontSize: 10.5, color: TEXT_MUTED, fontFace: "Calibri", margin: 0,
      });
    });

    s3.addNotes("Rather than a monolithic prompt, OmniPitch implements a cooperative multi-agent architecture with a shared episodic blackboard. Crucially, the Grounding Verifier Agent reviews every narrative against the underlying telemetry event IDs, ensuring mathematical factual precision.");
  }

  // =========================================================================
  // SLIDE 4: Full Microsoft AI & Cloud-Native Stack
  // =========================================================================
  {
    const s4 = pres.addSlide();
    s4.background = { color: BG_DARK };

    s4.addText("INNOVATION PILLAR 2: MICROSOFT ECOSYSTEM", {
      x: 0.8, y: 0.5, w: 8.4, h: 0.25,
      fontSize: 10, bold: true, color: ACCENT_CYAN, fontFace: "Calibri", charSpacing: 2,
    });
    s4.addText("End-to-End Microsoft Cloud Architecture", {
      x: 0.8, y: 0.75, w: 8.4, h: 0.5,
      fontSize: 26, bold: true, color: TEXT_WHITE, fontFace: "Calibri", margin: 0,
    });

    const msftPillars = [
      {
        tech: "Microsoft AI Foundry & Azure OpenAI",
        detail: "Leverages GPT-4o for real-time narrative synthesis with integrated OpenTelemetry tracing, latency profiling, and graceful local fallback.",
        tag: "LLM Orchestration"
      },
      {
        tech: "Model Context Protocol (MCP)",
        detail: "Full MCP server implementation allowing Microsoft Copilot Studio and autonomous agents to query live match intelligence via standardized tools.",
        tag: "Copilot Integration"
      },
      {
        tech: "Microsoft Fabric Lakehouse",
        detail: "Built-in Delta Lake export engine populating fact_match_events and dim_player_physical_summary tables for long-term analytical intelligence.",
        tag: "Enterprise Data"
      },
      {
        tech: "Azure Bicep IaC & Container Apps",
        detail: "Declarative infrastructure as code provisioning Container Apps, Cosmos DB, and Event Hubs with automated GitHub Actions CI/CD pipelines.",
        tag: "Cloud Native"
      }
    ];

    msftPillars.forEach((p, i) => {
      const col = i % 2;
      const row = Math.floor(i / 2);
      const px = 0.8 + col * 4.3;
      const py = 1.45 + row * 1.8;
      addCard(s4, px, py, 4.1, 1.65);

      s4.addText(p.tag.toUpperCase(), {
        x: px + 0.2, y: py + 0.15, w: 3.7, h: 0.25,
        fontSize: 9, bold: true, color: ACCENT_GREEN, fontFace: "Calibri",
      });

      s4.addText(p.tech, {
        x: px + 0.2, y: py + 0.4, w: 3.7, h: 0.4,
        fontSize: 13, bold: true, color: TEXT_WHITE, fontFace: "Calibri", margin: 0,
      });

      s4.addText(p.detail, {
        x: px + 0.2, y: py + 0.8, w: 3.7, h: 0.75,
        fontSize: 10.5, color: TEXT_MUTED, fontFace: "Calibri", lineSpacing: 16, margin: 0,
      });
    });

    s4.addNotes("OmniPitch is built natively on the Microsoft AI stack. It connects Microsoft AI Foundry for reasoning, exposes Model Context Protocol tools for Microsoft Copilot, exports high-dimensional match tables directly into Microsoft Fabric Lakehouse, and packages cleanly with Azure Bicep.");
  }

  // =========================================================================
  // SLIDE 5: Pro Match Intelligence Center Capabilities
  // =========================================================================
  {
    const s5 = pres.addSlide();
    s5.background = { color: BG_DARK };

    s5.addText("INNOVATION PILLAR 3: USER EXPERIENCE & ANALYTICS", {
      x: 0.8, y: 0.5, w: 8.4, h: 0.25,
      fontSize: 10, bold: true, color: ACCENT_CYAN, fontFace: "Calibri", charSpacing: 2,
    });
    s5.addText("Pro Match Intelligence Center", {
      x: 0.8, y: 0.75, w: 8.4, h: 0.5,
      fontSize: 26, bold: true, color: TEXT_WHITE, fontFace: "Calibri", margin: 0,
    });

    // Left card: Feature checklist
    addCard(s5, 0.8, 1.45, 4.1, 3.5);
    s5.addText("Hero Broadcast Capabilities", {
      x: 1.0, y: 1.6, w: 3.7, h: 0.35,
      fontSize: 14, bold: true, color: ACCENT_CYAN, fontFace: "Calibri", margin: 0,
    });

    const feats = [
      { t: "Attack Momentum Graph", d: "Minute-by-minute dominance bar chart with key match events." },
      { t: "Head-to-Head Analytics", d: "Comparative xG, possession %, shots, and tackles won." },
      { t: "Dynamic Player Ratings", d: "0-10 algorithmic rating system with automated MVP spotlight." },
      { t: "Penalty Shot Map", d: "Spatial half-pitch chart scaled by xG and shot speed in km/h." },
      { t: "Tactical System Switcher", d: "Live formation repositioning (4-3-3, 4-2-3-1, 3-5-2)." },
      { t: "Acoustic Whistle Engine", d: "Web Audio synthesis for kickoffs and major momentum shifts." },
    ];

    feats.forEach((ft, idx) => {
      const fy = 2.05 + idx * 0.45;
      s5.addText([
        { text: ft.t + ": ", options: { bold: true, color: TEXT_WHITE, fontSize: 10.5 } },
        { text: ft.d, options: { color: TEXT_MUTED, fontSize: 9.5 } }
      ], { x: 1.0, y: fy, w: 3.7, h: 0.4, fontFace: "Calibri", margin: 0 });
    });

    // Right card: Native Chart
    addCard(s5, 5.1, 1.45, 4.1, 3.5);
    s5.addText("Comparative Attack Momentum (Sample)", {
      x: 5.3, y: 1.6, w: 3.7, h: 0.35,
      fontSize: 13, bold: true, color: TEXT_WHITE, fontFace: "Calibri", margin: 0,
    });

    const chartData = [
      {
        name: "Avalon City FC",
        labels: ["15'", "30'", "45'", "60'", "75'", "90'"],
        values: [42, 68, 55, 74, 62, 85],
      },
      {
        name: "Solaria Rovers",
        labels: ["15'", "30'", "45'", "60'", "75'", "90'"],
        values: [35, 45, 60, 48, 70, 40],
      }
    ];

    s5.addChart(pres.ChartType.bar, chartData, {
      x: 5.2, y: 2.0, w: 3.9, h: 2.8,
      chartColors: [ACCENT_CYAN, "E11D48"],
      showTitle: false,
      showLegend: true,
      legendPos: "b",
      legendColor: TEXT_MUTED,
      legendFontSize: 9,
      catAxisLabelColor: TEXT_MUTED,
      valAxisLabelColor: TEXT_MUTED,
      valGridLine: { color: CARD_BORDER, size: 0.5 },
      catGridLine: { style: "none" },
    });

    s5.addNotes("The frontend user interface features the Pro Match Intelligence Center: interactive attack momentum graphs, head-to-head statistics, algorithmic player ratings, xG shot maps, and an instant match report export engine.");
  }

  // =========================================================================
  // SLIDE 6: Verification, Compliance & Quality
  // =========================================================================
  {
    const s6 = pres.addSlide();
    s6.background = { color: BG_DARK };

    s6.addText("ENGINEERING EXCELLENCE & COMPLIANCE", {
      x: 0.8, y: 0.5, w: 8.4, h: 0.25,
      fontSize: 10, bold: true, color: ACCENT_CYAN, fontFace: "Calibri", charSpacing: 2,
    });
    s6.addText("100% Synthetic, Tested & Production Ready", {
      x: 0.8, y: 0.75, w: 8.4, h: 0.5,
      fontSize: 26, bold: true, color: TEXT_WHITE, fontFace: "Calibri", margin: 0,
    });

    const pillars = [
      {
        title: "100% Synthetic Football Data",
        subtitle: "Zero Copyright Risk",
        desc: "Strictly adheres to hackathon guidelines. Teams (Avalon City FC vs Solaria Rovers) and players are generated via a physics-based, seeded stochastic engine with spatial coordinates, pass difficulties, and stamina models."
      },
      {
        title: "23 Automated Pytest Tests",
        subtitle: "100% Green Suite (< 2s)",
        desc: "Covers multi-agent orchestration, grounding verifiers, xG mathematics, attack momentum, player ratings, FastAPI endpoints, and Microsoft Fabric lakehouse table schema validation."
      },
      {
        title: "Zero Secrets Security",
        subtitle: "Enterprise Governance",
        desc: "Strict environment separation via .env.example, Azure Key Vault integration, and no hardcoded credentials. Ready for enterprise compliance review."
      }
    ];

    pillars.forEach((p, idx) => {
      const px = 0.8 + idx * 2.85;
      addCard(s6, px, 1.45, 2.7, 3.5);

      s6.addText(p.subtitle.toUpperCase(), {
        x: px + 0.2, y: 1.7, w: 2.3, h: 0.25,
        fontSize: 9, bold: true, color: ACCENT_GREEN, fontFace: "Calibri",
      });

      s6.addText(p.title, {
        x: px + 0.2, y: 1.95, w: 2.3, h: 0.6,
        fontSize: 14, bold: true, color: TEXT_WHITE, fontFace: "Calibri", margin: 0,
      });

      s6.addText(p.desc, {
        x: px + 0.2, y: 2.65, w: 2.3, h: 2.1,
        fontSize: 11, color: TEXT_MUTED, fontFace: "Calibri", lineSpacing: 17, margin: 0,
      });
    });

    s6.addNotes("OmniPitch is built with absolute engineering rigor. It uses 100% synthetic data with zero copyright entanglements, passes 23 unit and integration tests in under two seconds, and strictly observes enterprise security practices.");
  }

  // =========================================================================
  // SLIDE 7: Summary & Grand Prize Case
  // =========================================================================
  {
    const s7 = pres.addSlide();
    s7.background = { color: BG_DARK };

    s7.addText("CONCLUSION & IMPACT", {
      x: 0.8, y: 0.5, w: 8.4, h: 0.25,
      fontSize: 10, bold: true, color: ACCENT_CYAN, fontFace: "Calibri", charSpacing: 2,
    });
    s7.addText("Why OmniPitch Deserves the Grand Prize", {
      x: 0.8, y: 0.75, w: 8.4, h: 0.5,
      fontSize: 26, bold: true, color: TEXT_WHITE, fontFace: "Calibri", margin: 0,
    });

    addCard(s7, 0.8, 1.45, 8.4, 3.5);

    const summaries = [
      { cat: "Deep Multi-Agent Innovation", detail: "5 collaborative agents with shared blackboard memory and mathematical anti-hallucination verification." },
      { cat: "Full Microsoft AI Stack", detail: "Seamless integration across Microsoft AI Foundry (GPT-4o), Fabric Lakehouse, MCP for Copilot, and Azure Bicep IaC." },
      { cat: "Real-World Broadcast Value", detail: "Transforms raw data into high-engagement narratives for casual fans and high-density telemetry for technical staff." },
      { cat: "Production Software Standards", detail: "FastAPI SSE streaming, responsive dark stadium UI, Web Audio synthesis, and 23/23 passing automated tests." },
    ];

    summaries.forEach((sm, idx) => {
      const sy = 1.65 + idx * 0.75;
      s7.addShape(pres.ShapeType.rect, {
        x: 1.0, y: sy + 0.05, w: 0.15, h: 0.45,
        fill: { color: ACCENT_CYAN },
        line: { color: ACCENT_CYAN, width: 0 },
      });

      s7.addText(sm.cat, {
        x: 1.3, y: sy, w: 7.6, h: 0.25,
        fontSize: 13, bold: true, color: TEXT_WHITE, fontFace: "Calibri", margin: 0,
      });

      s7.addText(sm.detail, {
        x: 1.3, y: sy + 0.25, w: 7.6, h: 0.35,
        fontSize: 11, color: TEXT_MUTED, fontFace: "Calibri", margin: 0,
      });
    });

    // Call to action banner at bottom
    s7.addText("Thank you! Explore the live interactive dashboard: http://localhost:8000", {
      x: 1.0, y: 4.5, w: 8.0, h: 0.35,
      fontSize: 12, bold: true, color: ACCENT_GREEN, fontFace: "Calibri", align: "center",
    });

    s7.addNotes("In conclusion, OmniPitch demonstrates how Microsoft AI can transform synthetic sports data into verifiable, personalized, broadcast-grade intelligence. It meets and exceeds every hackathon criteria. Thank you.");
  }

  // Save presentation
  const outPath = path.resolve(__dirname, "OmniPitch_Pitch_Deck.pptx");
  pres.writeFile({ fileName: outPath })
    .then((fileName) => {
      console.log(`PPTX created successfully at: ${fileName}`);
    })
    .catch((err) => {
      console.error("PPTX creation error:", err);
      process.exit(1);
    });
}

createOmniPitchDeck();
