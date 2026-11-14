// KRISHI-X diagrams (Mermaid, vendored in vendor/mermaid.min.js so they render offline).
// Used by index.html (appendix slides) and diagrams.html. Facts mirror docs/ARCHITECTURE.md, docs/STRUCTURE.md, services/ops.py.
window.DIAGRAMS = {
journey: `sequenceDiagram
  autonumber
  actor F as Farmer
  participant V as KRISHI-X app (voice)
  participant A as Action agent + intake
  participant O as Orchestrator (12 agents)
  participant S as Ops service
  actor T as Transporter
  actor W as Warehouse / FPO
  F->>V: "50 quintal onion, 20 tomato near Nashik" (mr / hi / en)
  V->>A: POST /api/agent (session, text, lang)
  A->>A: extract crops, amounts, units, village (offline gazetteer)
  A-->>F: asks only what is missing: ready now? can you store?
  A-->>F: read-back - "Is this correct?"
  F->>A: "yes"
  A->>O: run(profile)
  O-->>A: options ranked by net in hand + forecast gate + weather
  A-->>F: "Sell at Pimpalgaon Baswant - you keep Rs 2,06,788" + map
  F->>A: "create the order"
  A-->>F: "Shall I create the sale order? yes or no"
  F->>A: "yes"
  A->>S: create sale order + transport request
  S-->>T: booking token TR-xxxx with ESTIMATED fare
  T->>S: accept, pick up, deliver
  S-->>F: notification at every step
  opt farmer can store / FPO pooling
    A->>S: storage request or pooled load
    S-->>W: confirm or reject
  end
  F->>S: confirm sale - order closed`,

arch: `flowchart TB
  subgraph C["Clients"]
    direction LR
    W1["Farmer app<br/>Next.js 14 · voice-first<br/>en · hi · mr"]
    W2["Partner portals<br/>FPO · Transporter<br/>Warehouse · Admin"]
    W3["Browser speech<br/>STT + TTS fallback"]
  end
  subgraph B["FastAPI backend"]
    direction LR
    R["API routes<br/>agent · chat · market<br/>ops · orders · voice"]
    AA["Action agent<br/>rules router + yes/no gate"]
    IN["Intake + Profile agent<br/>multi-crop slots, read-back"]
    BR["Brain<br/>LLM tool planner<br/>validated calls only"]
    OR["Orchestrator<br/>12 typed agents"]
    SV["Services<br/>costs · spoilage · crops<br/>OR-Tools logistics · forecast"]
    OPS["Ops<br/>orders · booking tokens<br/>storage · notifications"]
  end
  subgraph AI["Local AI (no cloud bill)"]
    direction LR
    LLM["Ollama 'krishix'<br/>fine-tuned qwen3:4b"]
    PI["Piper TTS"]
    WH["faster-whisper STT"]
  end
  subgraph D["Data"]
    direction LR
    PG[("PostgreSQL + PostGIS<br/>mandis · prices · history<br/>forecast cache · ops")]
    GZ[("GeoNames gazetteer<br/>5.6 L places · 1.55 L pincodes")]
  end
  subgraph X["Free and open sources"]
    direction LR
    AG["data.gov.in Agmarknet<br/>+ keyless Mandi API"]
    OM["Open-Meteo weather"]
    OSM["OpenStreetMap + OSRM"]
    NO["Nominatim (fallback)"]
  end
  W1 --> R
  W2 --> R
  W3 -.-> W1
  R --> AA
  AA --> IN
  AA -- "unclear phrasing" --> BR
  BR --> LLM
  AA --> OR
  OR --> SV
  AA --> OPS
  R --> PI
  R --> WH
  SV --> PG
  IN --> GZ
  OPS --> PG
  AG -- "6-hourly import" --> PG
  OM --> SV
  NO -.-> IN
  OSM -.-> W1
  classDef c fill:#e1f2ec,stroke:#5a7c6a,color:#1f2429
  classDef b fill:#ffffff,stroke:#5a7c6a,color:#1f2429
  classDef ai fill:#ece6fa,stroke:#8a76c8,color:#1f2429
  classDef d fill:#fff4d3,stroke:#d4b14a,color:#1f2429
  classDef x fill:#fbe3ef,stroke:#d68aae,color:#1f2429
  class W1,W2,W3 c
  class R,AA,IN,BR,OR,SV,OPS b
  class LLM,PI,WH ai
  class PG,GZ d
  class AG,OM,OSM,NO x`,

agents: `flowchart TB
  U(["Farmer speaks<br/>mr · hi · en · Hinglish<br/>(echo-filtered)"]) --> Q{"Plan<br/>exists?"}
  Q -- "no" --> I["Intake + read-back<br/>crops → qty → place<br/>→ ready → store"]
  I --> Y1{"Farmer<br/>says yes?"}
  Y1 -- "change" --> I
  Q -- "yes" --> RT["Rules router<br/>compare · forecast · price<br/>add / remove crop · order<br/>weather · schemes"]
  RT -- "unclear" --> BR["Local LLM brain<br/>picks tool + args only<br/>(validated)"]
  BR --> TOOL["Run tool"]
  RT --> TOOL
  subgraph ORC["Orchestrator · 12 agents · deterministic maths"]
    direction LR
    P1["1 Mandi Discovery · 2 Price Intelligence<br/>3 Market Activity · 4 Buyer Discovery"] --> P2["5 Cold Storage · 6 Transport<br/>7 Shared Load · 8 Spoilage"]
    P2 --> P3["9 Price Forecast (backtest gate)<br/>10 Sell vs Hold · 11 Net Realization<br/>12 Recommendation"]
  end
  Y1 -- "yes" --> P1
  TOOL -- "needs plan" --> P1
  TOOL -- "order · truck · storage" --> Y2{"yes / no<br/>gate"}
  Y2 -- "yes" --> OPS["Ops: order · booking token<br/>storage · notify all sides"]
  P3 --> OUT(["Reply in en / hi / mr<br/>+ plan · map · order"])
  OPS --> OUT
  classDef io fill:#e1f2ec,stroke:#5a7c6a,color:#1f2429
  classDef gate fill:#fff4d3,stroke:#d4b14a,color:#1f2429
  classDef llm fill:#ece6fa,stroke:#8a76c8,color:#1f2429
  classDef ag fill:#ffffff,stroke:#5a7c6a,color:#1f2429
  class U,OUT io
  class Q,Y1,Y2 gate
  class BR llm
  class P1,P2,P3 ag`,

order: `stateDiagram-v2
  direction TB
  [*] --> created: farmer says yes
  created --> transport_requested: request truck (yes)
  transport_requested --> transport_accepted: transporter accepts token
  transport_accepted --> transport_requested: transporter releases
  transport_accepted --> in_transit: pickup
  in_transit --> delivered: deliver
  delivered --> sale_confirmed: farmer confirms sale
  sale_confirmed --> [*]
  created --> cancelled: cancel
  transport_requested --> cancelled: cancel
  transport_accepted --> cancelled: cancel
  cancelled --> [*]`
};

window.renderDiagrams = async function (els) {
  if (!window.mermaid) return;
  mermaid.initialize({
    startOnLoad: false, theme: "base", securityLevel: "loose",
    fontFamily: "Plus Jakarta Sans, Inter, sans-serif",
    themeVariables: {
      fontFamily: "Plus Jakarta Sans, Inter, sans-serif", fontSize: "18px",
      primaryColor: "#e1f2ec", primaryBorderColor: "#5a7c6a", primaryTextColor: "#1f2429",
      secondaryColor: "#ece6fa", tertiaryColor: "#fff4d3", lineColor: "#5a7c6a", textColor: "#1f2429",
      clusterBkg: "#faf9f7", clusterBorder: "#d8d4cb", edgeLabelBackground: "#faf9f7",
      actorBkg: "#e1f2ec", actorBorder: "#5a7c6a", actorTextColor: "#1f2429", actorLineColor: "#a8b0b8",
      signalColor: "#3a4046", signalTextColor: "#1f2429", noteBkgColor: "#fff4d3", noteBorderColor: "#d4b14a",
      labelBoxBkgColor: "#ece6fa", labelBoxBorderColor: "#8a76c8", loopTextColor: "#3a4046",
      activationBkgColor: "#fbe3ef", sequenceNumberColor: "#ffffff",
    },
    flowchart: { curve: "basis", padding: 14, nodeSpacing: 34, rankSpacing: 46, useMaxWidth: true },
    sequence: { useMaxWidth: true, actorMargin: 46, messageMargin: 26, boxMargin: 8, mirrorActors: false, showSequenceNumbers: true },
    state: { useMaxWidth: true },
  });
  let n = 0;
  for (const el of els) {
    const key = el.dataset.mmd;
    try { const { svg } = await mermaid.render(`mmd-${key}-${n++}`, DIAGRAMS[key]); el.innerHTML = svg; }
    catch (e) { el.innerHTML = `<pre style="color:#b44;font-size:16px;white-space:pre-wrap">${key}: ${e.message || e}</pre>`; }
  }
};
