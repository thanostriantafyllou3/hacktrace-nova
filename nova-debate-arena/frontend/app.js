const els = {
  caseList: document.getElementById("caseList"),
  casePreview: document.getElementById("casePreview"),
  modelInput: document.getElementById("modelInput"),
  tempInput: document.getElementById("tempInput"),
  rebutInput: document.getElementById("rebutInput"),
  startBtn: document.getElementById("startBtn"),
  stopBtn: document.getElementById("stopBtn"),
  phasePill: document.getElementById("phasePill"),
  connDot: document.getElementById("connDot"),
  connText: document.getElementById("connText"),
  arenaMeta: document.getElementById("arenaMeta"),
  transcript: document.getElementById("transcript"),
  verdictPanel: document.getElementById("verdictPanel"),

  cardAdvocate: document.getElementById("cardAdvocate"),
  cardSkeptic: document.getElementById("cardSkeptic"),
  cardFact: document.getElementById("cardFact"),
  cardJudge: document.getElementById("cardJudge"),

  bubbleAdvocate: document.querySelector("#bubbleAdvocate .bubbleInner"),
  bubbleSkeptic: document.querySelector("#bubbleSkeptic .bubbleInner"),
  bubbleFact: document.querySelector("#bubbleFact .bubbleInner"),
  bubbleJudge: document.querySelector("#bubbleJudge .bubbleInner"),
};

let selectedCase = null;
let currentPhase = "Idle";
let socket = null;
let activeTurnId = null;
let activeBase = null;

const bubbleByBase = {
  "Advocate": els.bubbleAdvocate,
  "Skeptic": els.bubbleSkeptic,
  "Fact-Checker": els.bubbleFact,
  "Judge": els.bubbleJudge,
};

const bubbleBoxByBase = {
  "Advocate": document.getElementById("bubbleAdvocate"),
  "Skeptic": document.getElementById("bubbleSkeptic"),
  "Fact-Checker": document.getElementById("bubbleFact"),
  "Judge": document.getElementById("bubbleJudge"),
};

const cardByBase = {
  "Advocate": els.cardAdvocate,
  "Skeptic": els.cardSkeptic,
  "Fact-Checker": els.cardFact,
  "Judge": els.cardJudge,
};

function wsUrl(path) {
  const proto = window.location.protocol === "https:" ? "wss" : "ws";
  return `${proto}://${window.location.host}${path}`;
}

function setConn(online, text) {
  els.connText.textContent = text;
  els.connDot.style.background = online ? "#2ecc71" : "#aaa";
}

function setPhase(name) {
  currentPhase = name || "";
  els.phasePill.textContent = currentPhase;
}

function baseAgent(agentName) {
  if (!agentName) return "";
  if (agentName.startsWith("Advocate")) return "Advocate";
  if (agentName.startsWith("Skeptic")) return "Skeptic";
  if (agentName.startsWith("Fact-Checker")) return "Fact-Checker";
  if (agentName.startsWith("Judge")) return "Judge";
  return agentName;
}

function clearArena() {
  els.transcript.innerHTML = "";
  els.verdictPanel.querySelector(".verdictBody").textContent = "No verdict yet.";
  bubbleByBase["Advocate"].textContent = "";
  bubbleByBase["Skeptic"].textContent = "";
  bubbleByBase["Fact-Checker"].textContent = "";
  bubbleByBase["Judge"].textContent = "";
  for (const base of Object.keys(cardByBase)) {
    cardByBase[base].classList.remove("speaking");
  }
  setPhase("Idle");
  els.arenaMeta.textContent = "Preparing...";
}

function addTranscriptTurn(agent, content) {
  const turn = document.createElement("div");
  turn.className = "turn";

  const header = document.createElement("div");
  header.className = "turnHeader";

  const agentEl = document.createElement("div");
  agentEl.className = "turnAgent";
  agentEl.textContent = agent;

  const phaseEl = document.createElement("div");
  phaseEl.className = "turnPhase";
  phaseEl.textContent = currentPhase;

  header.appendChild(agentEl);
  header.appendChild(phaseEl);

  const body = document.createElement("div");
  body.className = "turnBody";
  body.textContent = content;

  turn.appendChild(header);
  turn.appendChild(body);

  els.transcript.appendChild(turn);
  els.transcript.scrollTop = els.transcript.scrollHeight;
}

function renderVerdict(verdict) {
  const v = verdict?.verdict || "";
  const conf = Math.max(0, Math.min(1, Number(verdict?.confidence ?? 0)));

  let tagClass = "tagYellow";
  if (v === "FAITHFUL") tagClass = "tagGreen";
  if (v === "MUTATED") tagClass = "tagRed";

  const body = els.verdictPanel.querySelector(".verdictBody");
  body.innerHTML = "";

  const tag = document.createElement("div");
  tag.className = `tag ${tagClass}`;
  tag.textContent = v || "(no label)";

  const confText = document.createElement("div");
  confText.style.marginTop = "8px";
  confText.style.fontWeight = "800";
  confText.textContent = `Confidence: ${(conf * 100).toFixed(0)}%`;

  const bar = document.createElement("div");
  bar.className = "bar";
  const fill = document.createElement("div");
  fill.className = "barFill";
  fill.style.width = `${(conf * 100).toFixed(0)}%`;
  bar.appendChild(fill);

  const summary = document.createElement("div");
  summary.style.marginTop = "10px";
  summary.style.whiteSpace = "pre-wrap";
  summary.textContent = verdict?.one_sentence_summary || "";

  const bullets = document.createElement("ul");
  bullets.style.margin = "10px 0 0 18px";
  bullets.style.padding = "0";
  (verdict?.rationale || []).slice(0, 6).forEach((b) => {
    const li = document.createElement("li");
    li.textContent = b;
    bullets.appendChild(li);
  });

  body.appendChild(tag);
  body.appendChild(confText);
  body.appendChild(bar);
  if (summary.textContent) body.appendChild(summary);
  if (bullets.childElementCount) body.appendChild(bullets);
}

function setBubble(base, text) {
  const el = bubbleByBase[base];
  if (!el) return;
  el.textContent = text;
}

function appendBubble(base, delta) {
  const el = bubbleByBase[base];
  if (!el) return;
  el.textContent += delta;
}

function setSpeaking(base, on) {
  const card = cardByBase[base];
  if (!card) return;
  if (on) card.classList.add("speaking");
  else card.classList.remove("speaking");
}

function setPreview(c) {
  const body = els.casePreview.querySelector(".previewBody");
  if (!c) {
    body.textContent = "Choose a case to preview truth/claim.";
    return;
  }
  body.textContent = `Row ${c.row_id}\n\nTRUTH:\n${c.truth}\n\nCLAIM:\n${c.claim}`;
}

function snippet(text, n = 110) {
  const t = String(text || "").replace(/\s+/g, " ").trim();
  return t.length <= n ? t : t.slice(0, n) + "…";
}

async function loadCases() {
  const res = await fetch("/api/cases");
  const data = await res.json();
  const cases = data.cases || [];

  els.caseList.innerHTML = "";
  cases.forEach((c) => {
    const item = document.createElement("div");
    item.className = "caseItem";
    item.dataset.rowId = c.row_id;

    const header = document.createElement("div");
    header.className = "caseHeader";

    const left = document.createElement("div");
    left.className = "caseId";
    left.textContent = `Row ${c.row_id}`;

    const right = document.createElement("div");
    right.className = "star";
    right.textContent = c.is_default ? "★" : "";

    header.appendChild(left);
    header.appendChild(right);

    const snip = document.createElement("div");
    snip.className = "caseSnippet";
    snip.textContent = snippet(c.claim);

    item.appendChild(header);
    item.appendChild(snip);

    item.addEventListener("click", () => {
      document.querySelectorAll(".caseItem").forEach((x) => x.classList.remove("active"));
      item.classList.add("active");
      selectedCase = c;
      setPreview(c);
    });

    els.caseList.appendChild(item);
  });

  // Auto-select the first default case if present
  const firstDefault = cases.find((c) => c.is_default) || cases[0];
  if (firstDefault) {
    selectedCase = firstDefault;
    setPreview(firstDefault);
    const el = els.caseList.querySelector(`[data-row-id="${firstDefault.row_id}"]`);
    if (el) el.classList.add("active");
  }
}

function stopDebate() {
  if (socket) {
    try { socket.close(); } catch (_) {}
  }
  socket = null;
  els.stopBtn.disabled = true;
  els.startBtn.disabled = false;
  setConn(false, "offline");
  setSpeaking("Advocate", false);
  setSpeaking("Skeptic", false);
  setSpeaking("Fact-Checker", false);
  setSpeaking("Judge", false);
  activeTurnId = null;
  activeBase = null;
}

function startDebate() {
  if (!selectedCase) {
    alert("Pick a case first.");
    return;
  }

  clearArena();

  const model = els.modelInput.value.trim() || "gpt-4o-mini";
  const temperature = Number(els.tempInput.value || 0.2);
  const rebuttals = Number(els.rebutInput.value || 1);

  els.startBtn.disabled = true;
  els.stopBtn.disabled = false;

  socket = new WebSocket(wsUrl("/ws/debate"));

  socket.addEventListener("open", () => {
    setConn(true, "connected");
    els.arenaMeta.textContent = `Row ${selectedCase.row_id} • streaming...`;

    socket.send(JSON.stringify({
      action: "start",
      row_id: selectedCase.row_id,
      model,
      temperature,
      rebuttal_rounds: rebuttals,
    }));
  });

  socket.addEventListener("close", () => {
    setConn(false, "offline");
    els.stopBtn.disabled = true;
    els.startBtn.disabled = false;
  });

  socket.addEventListener("error", () => {
    setConn(false, "error");
  });

  socket.addEventListener("message", (ev) => {
    const msg = JSON.parse(ev.data);

    if (msg.type === "meta") {
      els.arenaMeta.textContent = `Model ${msg.model} • temp ${msg.temperature} • rebuttals ${msg.rebuttal_rounds}`;
      return;
    }

    if (msg.type === "phase") {
      setPhase(msg.name);
      return;
    }

    if (msg.type === "case_file") {
      // keep preview updated in case claim_override is added later
      return;
    }

    if (msg.type === "turn_start") {
      activeTurnId = msg.turn_id;
      activeBase = baseAgent(msg.agent);

      // clear the bubble for the active agent and animate
      setBubble(activeBase, "");
      setSpeaking("Advocate", false);
      setSpeaking("Skeptic", false);
      setSpeaking("Fact-Checker", false);
      setSpeaking("Judge", false);
      setSpeaking(activeBase, true);

      // small pop animation
      const bubbleBox = bubbleBoxByBase[activeBase];
      if (bubbleBox) {
        bubbleBox.classList.remove("pop");
        void bubbleBox.offsetWidth;
        bubbleBox.classList.add("pop");
      }
      return;
    }

    if (msg.type === "turn_delta") {
      const base = baseAgent(msg.agent);
      appendBubble(base, msg.delta || "");
      return;
    }

    if (msg.type === "turn_end") {
      const base = baseAgent(msg.agent);
      setSpeaking(base, false);

      // Only add completed turns to transcript to keep it readable.
      addTranscriptTurn(msg.agent, msg.content || "");
      return;
    }

    if (msg.type === "verdict") {
      renderVerdict(msg.verdict);
      return;
    }

    if (msg.type === "error") {
      const body = els.verdictPanel.querySelector(".verdictBody");
      body.textContent = `Error: ${msg.message}`;
      return;
    }

    if (msg.type === "done") {
      els.arenaMeta.textContent = "Debate complete.";
      els.stopBtn.disabled = true;
      els.startBtn.disabled = false;
      return;
    }
  });
}

els.startBtn.addEventListener("click", startDebate);
els.stopBtn.addEventListener("click", stopDebate);

(async function init() {
  setConn(false, "offline");
  setPhase("Idle");

  try {
    const healthRes = await fetch("/api/health");
    const health = await healthRes.json();
    if (health?.default_model) {
      els.modelInput.value = health.default_model;
    }
  } catch (_) {}

  await loadCases();
})();
