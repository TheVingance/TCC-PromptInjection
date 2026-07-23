/* ──────────────────────────────────────────────────────────────────────────────
   FinSecAI — Research Dashboard JavaScript
   Handles auth, chat, metrics, interaction history, and latency visualization
   ────────────────────────────────────────────────────────────────────────────── */

const API_BASE = "http://localhost:8000/api/v1";

// ─── State ────────────────────────────────────────────────────────────────────
let token = localStorage.getItem("finsec_token") || null;
let currentUser = JSON.parse(localStorage.getItem("finsec_user") || "null");
let sessionId = crypto.randomUUID();
let latencyHistory = [];
let allAdversarialMode = false;
let lastMetricsData = null; // guarda últimos dados de métricas para redesenhar o gráfico

// ─── Token Helpers ────────────────────────────────────────────────────────────
function isTokenExpired(t) {
  if (!t) return true;
  try {
    const payload = JSON.parse(atob(t.split('.')[1]));
    return Date.now() >= payload.exp * 1000;
  } catch {
    return true;
  }
}

// ─── DOM Refs ─────────────────────────────────────────────────────────────────
const $ = id => document.getElementById(id);
const loginForm      = $("loginForm");
const userInfo       = $("userInfo");
const btnLogin       = $("btnLogin");
const btnLogout      = $("btnLogout");
const loginEmail     = $("loginEmail");
const loginPassword  = $("loginPassword");
const userNameDisplay = $("userNameDisplay");
const userEmailDisplay = $("userEmailDisplay");
const providerSelect = $("providerSelect");
const ollamaModelGroup = $("ollamaModelGroup");
const ollamaModelSelect = $("ollamaModelSelect");
const customModelGroup = $("customModelGroup");
const customModelInput = $("customModelInput");
const adversarialMode = $("adversarialMode");
const adversarialOptions = $("adversarialOptions");
const threatCategory = $("threatCategory");
const researcherNotes = $("researcherNotes");
const quickPrompts   = $("quickPrompts");
const messages       = $("messages");
const messageInput   = $("messageInput");
const btnSend        = $("btnSend");
const chatStatus     = $("chatStatus");
const sessionBadge   = $("sessionBadge");
const currentProvider = $("currentProvider");
const connectionStatus = $("connectionStatus");
const metricsGrid    = $("metricsGrid");
const interactionsList = $("interactionsList");
const filterAll      = $("filterAll");
const filterAdv      = $("filterAdv");
const modal          = $("interactionModal");
const modalContent   = $("modalContent");
const btnCloseModal  = $("btnCloseModal");
const btnRefreshMetrics = $("btnRefreshMetrics");
const latencyCanvas  = $("latencyChart");
const attacksCanvas  = $("attacksChart");
const btnOpenAll     = $("btnOpenAllInteractions");

// ─── Open All Interactions (nova janela) ──────────────────────────────────────
if (btnOpenAll) {
  btnOpenAll.addEventListener("click", () => {
    window.open("interactions.html", "_blank");
  });
}

// ─── Init ─────────────────────────────────────────────────────────────────────
async function init() {
  checkApiHealth();
  // Verifica se token armazenado ainda é válido
  if (token && isTokenExpired(token)) {
    token = null;
    currentUser = null;
    localStorage.removeItem("finsec_token");
    localStorage.removeItem("finsec_user");
  }
  if (token && currentUser) {
    showUserInfo();
    refreshAll();
  }
  updateSessionBadge();
  setupLatencyCanvas();
  setupAttacksCanvas();
  updateModelSelectorsVisibility();
}

async function checkApiHealth() {
  try {
    const res = await fetch("http://localhost:8000/health");
    if (res.ok) {
      setConnectionStatus(true);
    } else {
      setConnectionStatus(false);
    }
  } catch {
    setConnectionStatus(false);
  }
}

function setConnectionStatus(online) {
  const dot = connectionStatus.querySelector(".status-dot");
  const text = connectionStatus.querySelector(".status-text");
  if (online) {
    dot.className = "status-dot online";
    text.textContent = "API Online";
  } else {
    dot.className = "status-dot offline";
    text.textContent = "API Offline";
  }
}

// ─── Auth ──────────────────────────────────────────────────────────────────────
btnLogin.addEventListener("click", login);
btnLogout.addEventListener("click", logout);

async function login() {
  const email = loginEmail.value.trim();
  const password = loginPassword.value.trim();
  if (!email || !password) return;

  btnLogin.textContent = "Entrando...";
  btnLogin.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password }),
    });

    if (!res.ok) {
      const err = await res.json();
      // FastAPI validation errors return detail as an array of objects
      const msg = Array.isArray(err.detail)
        ? err.detail.map(e => `${e.loc?.slice(-1)[0] ?? ''}: ${e.msg}`).join('\n')
        : (err.detail || "Credenciais inválidas");
      alert("Erro: " + msg);
      return;
    }

    const data = await res.json();
    token = data.access_token;
    currentUser = data.user;
    localStorage.setItem("finsec_token", token);
    localStorage.setItem("finsec_user", JSON.stringify(currentUser));

    showUserInfo();
    refreshAll();
    addSystemMessage(`✅ Autenticado como **${currentUser.full_name}**. Sessão iniciada.`);
    updateSessionBadge();
  } catch (e) {
    alert("Erro de conexão: " + e.message);
  } finally {
    btnLogin.textContent = "Entrar";
    btnLogin.disabled = false;
  }
}

function logout() {
  token = null;
  currentUser = null;
  localStorage.removeItem("finsec_token");
  localStorage.removeItem("finsec_user");
  hideUserInfo();
  addSystemMessage("🚪 Sessão encerrada.");
}

function showUserInfo() {
  loginForm.classList.add("hidden");
  userInfo.classList.remove("hidden");
  userNameDisplay.textContent = currentUser.full_name;
  userEmailDisplay.textContent = currentUser.email;
  btnSend.disabled = false;
}

function hideUserInfo() {
  userInfo.classList.add("hidden");
  loginForm.classList.remove("hidden");
  btnSend.disabled = true;
  interactionsList.innerHTML = '<p class="empty-state">Autentique-se para ver o histórico.</p>';
}

// ─── Adversarial Mode ─────────────────────────────────────────────────────────
adversarialMode.addEventListener("change", () => {
  allAdversarialMode = adversarialMode.checked;
  if (allAdversarialMode) {
    adversarialOptions.classList.remove("hidden");
    document.querySelector(".chat-input-wrapper").classList.add("adversarial-active");
  } else {
    adversarialOptions.classList.add("hidden");
    document.querySelector(".chat-input-wrapper").classList.remove("adversarial-active");
  }
});

// ─── Provider & Model Selection ────────────────────────────────────────────────
const providerLabels = { ollama: "Ollama" };

function updateModelSelectorsVisibility() {
  if (providerSelect.value === "ollama") {
    ollamaModelGroup.classList.remove("hidden");
    if (ollamaModelSelect.value === "custom") {
      customModelGroup.classList.remove("hidden");
    } else {
      customModelGroup.classList.add("hidden");
    }
  } else {
    ollamaModelGroup.classList.add("hidden");
    customModelGroup.classList.add("hidden");
  }

  // Update header text
  let modelLabel = providerLabels[providerSelect.value] || providerSelect.value;
  if (providerSelect.value === "ollama") {
    let specificModel = ollamaModelSelect.value === "custom" ? (customModelInput.value.trim() || "personalizado") : ollamaModelSelect.value;
    modelLabel = `Ollama (${specificModel})`;
  }
  currentProvider.textContent = modelLabel;
}

providerSelect.addEventListener("change", updateModelSelectorsVisibility);
ollamaModelSelect.addEventListener("change", updateModelSelectorsVisibility);
customModelInput.addEventListener("input", updateModelSelectorsVisibility);

// ─── Quick Prompts ────────────────────────────────────────────────────────────
if (quickPrompts) {
  quickPrompts.addEventListener("click", e => {
    const btn = e.target.closest(".quick-btn");
    if (!btn) return;
    messageInput.value = btn.dataset.prompt;
    if (btn.dataset.adversarial === "true") {
      adversarialMode.checked = true;
      allAdversarialMode = true;
      adversarialOptions.classList.remove("hidden");
      document.querySelector(".chat-input-wrapper").classList.add("adversarial-active");
      if (btn.dataset.threat) {
        threatCategory.value = btn.dataset.threat;
      }
    }
    messageInput.focus();
    autoResize(messageInput);
  });
}

// ─── Chat ──────────────────────────────────────────────────────────────────────
btnSend.addEventListener("click", sendMessage);
messageInput.addEventListener("keydown", e => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    sendMessage();
  }
});
messageInput.addEventListener("input", () => autoResize(messageInput));

function autoResize(el) {
  el.style.height = "auto";
  el.style.height = Math.min(el.scrollHeight, 120) + "px";
}

async function sendMessage() {
  const text = messageInput.value.trim();
  if (!text || !token) return;

  // Verifica expiração do token antes de enviar
  if (isTokenExpired(token)) {
    logout();
    addSystemMessage("⏰ Sua sessão expirou. Por favor, **faça login novamente** para continuar.");
    return;
  }

  const isAdv = allAdversarialMode;
  addUserMessage(text, isAdv);
  messageInput.value = "";
  autoResize(messageInput);

  const typingId = addTypingIndicator();
  btnSend.disabled = true;
  setStatus("Enviando para " + (providerLabels[providerSelect.value] || providerSelect.value) + "...");

  try {
    let resolvedModelName = null;
    if (providerSelect.value === "ollama") {
      resolvedModelName = ollamaModelSelect.value === "custom" 
        ? customModelInput.value.trim() 
        : ollamaModelSelect.value;
    }

    const body = {
      message: text,
      session_id: sessionId,
      provider: providerSelect.value,
      model_name: resolvedModelName,
      is_adversarial: isAdv,
      threat_category: isAdv ? (threatCategory.value || "none") : "none",
      researcher_notes: isAdv ? (researcherNotes.value || null) : null,
    };

    const start = Date.now();
    const res = await fetch(`${API_BASE}/ai/chat`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "Authorization": `Bearer ${token}`,
      },
      body: JSON.stringify(body),
    });

    removeTypingIndicator(typingId);

    if (!res.ok) {
      const err = await res.json();
      if (res.status === 401) {
        // Token expirado ou inválido — faz logout e pede novo login
        logout();
        addSystemMessage("⏰ Sua sessão expirou. Por favor, **faça login novamente** para continuar.");
      } else {
        addBotMessage(`❌ Erro: ${err.detail || "Falha na requisição"}`, false, false);
      }
      return;
    }

    const data = await res.json();
    addBotMessage(data.response, data.safety_triggered, isAdv, data.latency_ms);

    // Update latency chart
    latencyHistory.push(data.latency_ms || 0);
    if (latencyHistory.length > 20) latencyHistory.shift();
    drawLatencyChart();

    setStatus(`✓ ${data.provider} · ${Math.round(data.latency_ms)}ms · ${data.tokens_used || "?"} tokens`);
    refreshAll();
  } catch (e) {
    removeTypingIndicator(typingId);
    addBotMessage(`❌ Erro de conexão: ${e.message}`, false, false);
    setStatus("Erro de conexão");
  } finally {
    btnSend.disabled = false;
  }
}

function addUserMessage(text, isAdv) {
  const el = document.createElement("div");
  el.className = "message message-user" + (isAdv ? " message-adversarial" : "");
  el.innerHTML = `
    <div class="message-avatar">👤</div>
    <div class="message-bubble">
      ${isAdv ? `<div class="adversarial-badge">⚠️ ADVERSARIAL · ${threatCategory.value || "none"}</div>` : ""}
      <p>${escapeHtml(text)}</p>
    </div>`;
  messages.appendChild(el);
  scrollToBottom();
}

function addBotMessage(text, safetyTriggered, isAdv, latencyMs) {
  const el = document.createElement("div");
  el.className = "message message-bot";
  el.innerHTML = `
    <div class="message-avatar">🏦</div>
    <div class="message-bubble">
      ${safetyTriggered ? `<div class="safety-badge">🛡️ SAFETY TRIGGERED</div>` : ""}
      <p>${formatMarkdown(escapeHtml(text))}</p>
      ${latencyMs ? `<p class="msg-hint">⚡ ${Math.round(latencyMs)}ms</p>` : ""}
    </div>`;
  messages.appendChild(el);
  scrollToBottom();
}

function addSystemMessage(text) {
  const el = document.createElement("div");
  el.className = "message message-bot";
  el.innerHTML = `
    <div class="message-avatar">⚙️</div>
    <div class="message-bubble"><p class="msg-hint">${formatMarkdown(escapeHtml(text))}</p></div>`;
  messages.appendChild(el);
  scrollToBottom();
}

function addTypingIndicator() {
  const id = "typing-" + Date.now();
  const el = document.createElement("div");
  el.className = "message message-bot";
  el.id = id;
  el.innerHTML = `
    <div class="message-avatar">🏦</div>
    <div class="message-bubble">
      <div class="typing-indicator">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    </div>`;
  messages.appendChild(el);
  scrollToBottom();
  return id;
}

function removeTypingIndicator(id) {
  const el = document.getElementById(id);
  if (el) el.remove();
}

function scrollToBottom() {
  messages.scrollTop = messages.scrollHeight;
}

function setStatus(text) {
  chatStatus.textContent = text;
}

// ─── Session ──────────────────────────────────────────────────────────────────
function updateSessionBadge() {
  sessionBadge.textContent = `Sessão: ${sessionId.split("-")[0]}`;
}

// ─── Metrics ──────────────────────────────────────────────────────────────────
const metricsModelSelect = $("metricsModelSelect");
if (metricsModelSelect) {
  metricsModelSelect.addEventListener("change", refreshAll);
}
btnRefreshMetrics.addEventListener("click", refreshAll);

async function fetchMetrics() {
  if (!token) return;
  try {
    const selectedModel = metricsModelSelect ? metricsModelSelect.value : "";
    const url = `${API_BASE}/research/metrics${selectedModel ? `?model_name=${encodeURIComponent(selectedModel)}` : ""}`;
    const res = await fetch(url, {
      headers: { "Authorization": `Bearer ${token}` },
    });
    if (!res.ok) return;
    const data = await res.json();
    $("metricTotal").textContent = data.total_interactions;
    $("metricAdversarial").textContent = data.adversarial_interactions;
    $("metricSafety").textContent = data.safety_triggered_count;
    $("metricRate").textContent = data.safety_trigger_rate + "%";
    $("metricAsr").textContent = data.attack_success_rate + "%";
    $("metricAsp").textContent = data.attack_success_probability + "%";
    lastMetricsData = data; // persiste para redesenho do canvas
    drawAttacksChart(data);
  } catch {}
}

// ─── Interaction History ──────────────────────────────────────────────────────
let showOnlyAdversarial = false;

filterAll.addEventListener("click", () => {
  showOnlyAdversarial = false;
  filterAll.classList.add("active");
  filterAdv.classList.remove("active");
  fetchInteractions();
});

filterAdv.addEventListener("click", () => {
  showOnlyAdversarial = true;
  filterAdv.classList.add("active");
  filterAll.classList.remove("active");
  fetchInteractions();
});

async function fetchInteractions() {
  if (!token) return;
  try {
    const selectedModel = metricsModelSelect ? metricsModelSelect.value : "";
    let url = `${API_BASE}/ai/interactions?limit=30${showOnlyAdversarial ? "&adversarial_only=true" : ""}`;
    if (selectedModel) {
      url += `&model_name=${encodeURIComponent(selectedModel)}`;
    }
    const res = await fetch(url, {
      headers: { "Authorization": `Bearer ${token}` },
    });
    if (!res.ok) return;
    const data = await res.json();
    renderInteractions(data);
  } catch {}
}

function renderInteractions(items) {
  if (!items.length) {
    interactionsList.innerHTML = '<p class="empty-state">Nenhuma interação registrada.</p>';
    return;
  }
  interactionsList.innerHTML = "";
  items.forEach(item => {
    const el = document.createElement("div");
    el.className = "interaction-item" + (item.is_adversarial ? " adversarial" : "") + (item.safety_triggered ? " safety" : "");
    const time = new Date(item.created_at).toLocaleTimeString("pt-BR", { hour: "2-digit", minute: "2-digit" });
    el.innerHTML = `
      <div class="interaction-meta">
        <span class="interaction-provider">${item.provider}</span>
        ${item.is_adversarial ? '<span class="tag tag-adv">ADV</span>' : ""}
        ${item.safety_triggered ? '<span class="tag tag-safe">SAFE</span>' : ""}
        <span class="interaction-time">${time}</span>
      </div>
      <div class="interaction-prompt">${escapeHtml(item.user_prompt)}</div>`;
    el.addEventListener("click", () => openInteractionModal(item));
    interactionsList.appendChild(el);
  });
}

function openInteractionModal(item) {
  modalContent.innerHTML = `
    <div class="modal-field">
      <div class="modal-field-label">Provider / Model</div>
      <div class="modal-field-value">${item.provider} · ${item.model_name}</div>
    </div>
    <div class="modal-field">
      <div class="modal-field-label">Session</div>
      <div class="modal-field-value">${item.session_id}</div>
    </div>
    <div class="modal-field">
      <div class="modal-field-label">Threat Category</div>
      <div class="modal-field-value">${item.threat_category} ${item.is_adversarial ? "⚠️" : ""}</div>
    </div>
    <div class="modal-field">
      <div class="modal-field-label">Safety Triggered</div>
      <div class="modal-field-value">${item.safety_triggered ? "✅ SIM" : "❌ NÃO"}</div>
    </div>
    <div class="modal-field">
      <div class="modal-field-label">Prompt do Usuário</div>
      <div class="modal-field-value">${escapeHtml(item.user_prompt)}</div>
    </div>
    <div class="modal-field">
      <div class="modal-field-label">Resposta do Assistente</div>
      <div class="modal-field-value">${escapeHtml(item.assistant_response || "—")}</div>
    </div>
    ${item.researcher_notes ? `
    <div class="modal-field">
      <div class="modal-field-label">Notas do Pesquisador</div>
      <div class="modal-field-value">${escapeHtml(item.researcher_notes)}</div>
    </div>` : ""}
    <div class="modal-field">
      <div class="modal-field-label">Latência / Tokens</div>
      <div class="modal-field-value">${Math.round(item.latency_ms || 0)}ms · ${item.tokens_used || "?"} tokens</div>
    </div>
    <div class="modal-field">
      <div class="modal-field-label">Timestamp</div>
      <div class="modal-field-value">${new Date(item.created_at).toLocaleString("pt-BR")}</div>
    </div>`;
  modal.classList.remove("hidden");
}

btnCloseModal.addEventListener("click", () => modal.classList.add("hidden"));
modal.addEventListener("click", e => { if (e.target === modal) modal.classList.add("hidden"); });

// ─── Attacks & Volume Chart (Canvas) ─────────────────────────────────────────
function setupAttacksCanvas() {
  if (!attacksCanvas) return;
  attacksCanvas.width = attacksCanvas.parentElement.offsetWidth || 300;
  attacksCanvas.height = 130;
}

function drawAttacksChart(m) {
  if (!attacksCanvas) return;
  const ctx = attacksCanvas.getContext("2d");
  const w = attacksCanvas.width;
  const h = attacksCanvas.height;
  ctx.clearRect(0, 0, w, h);

  if (!m) return;

  const total = m.total_interactions || 0;
  const adv = m.adversarial_interactions || 0;
  const safe = m.safety_triggered_count || 0;
  const succ = m.successful_attacks || 0;
  const asr = m.attack_success_rate || 0;
  const asp = m.attack_success_probability || 0;

  const maxVal = Math.max(total, 1);
  const bars = [
    { label: "Total", val: total, color: "#00bcd4" },
    { label: "Adversariais", val: adv, color: "#ffb038" },
    { label: "Defesas (Safety)", val: safe, color: "#00d9a3" },
    { label: "Ataques Sucesso", val: succ, color: "#ff4d6d" },
  ];

  const startY = 15;
  const barHeight = 16;
  const gap = 24;

  bars.forEach((b, i) => {
    const y = startY + i * gap;
    const barWidth = Math.max((b.val / maxVal) * (w - 140), 2);

    // Label
    ctx.fillStyle = "rgba(125, 160, 187, 0.9)";
    ctx.font = "11px Inter, sans-serif";
    ctx.textAlign = "left";
    ctx.fillText(b.label, 0, y + 12);

    // Bar BG
    ctx.fillStyle = "rgba(255, 255, 255, 0.06)";
    ctx.beginPath();
    ctx.roundRect(110, y, w - 160, barHeight, 4);
    ctx.fill();

    // Bar Fill
    ctx.fillStyle = b.color;
    ctx.beginPath();
    ctx.roundRect(110, y, barWidth, barHeight, 4);
    ctx.fill();

    // Value Text
    ctx.fillStyle = "rgba(240, 246, 255, 0.95)";
    ctx.font = "bold 11px 'JetBrains Mono', monospace";
    ctx.textAlign = "right";
    ctx.fillText(b.val.toString(), w - 5, y + 12);
  });
}

// ─── Latency Chart (Canvas) ───────────────────────────────────────────────────
function setupLatencyCanvas() {
  if (!latencyCanvas) return;
  latencyCanvas.width = latencyCanvas.parentElement.offsetWidth;
  latencyCanvas.height = 80;
}

function drawLatencyChart() {
  if (!latencyCanvas) return;
  const ctx = latencyCanvas.getContext("2d");
  const w = latencyCanvas.width;
  const h = latencyCanvas.height;
  ctx.clearRect(0, 0, w, h);

  if (latencyHistory.length < 2) return;

  const max = Math.max(...latencyHistory, 1);
  const pts = latencyHistory.map((v, i) => ({
    x: (i / (latencyHistory.length - 1)) * w,
    y: h - (v / max) * (h - 10) - 5,
  }));

  // Fill
  const grad = ctx.createLinearGradient(0, 0, 0, h);
  grad.addColorStop(0, "rgba(79,158,255,0.3)");
  grad.addColorStop(1, "rgba(79,158,255,0)");
  ctx.beginPath();
  ctx.moveTo(pts[0].x, h);
  pts.forEach(p => ctx.lineTo(p.x, p.y));
  ctx.lineTo(pts[pts.length - 1].x, h);
  ctx.closePath();
  ctx.fillStyle = grad;
  ctx.fill();

  // Line
  ctx.beginPath();
  ctx.moveTo(pts[0].x, pts[0].y);
  pts.forEach(p => ctx.lineTo(p.x, p.y));
  ctx.strokeStyle = "#4f9eff";
  ctx.lineWidth = 2;
  ctx.stroke();

  // Dots
  pts.forEach(p => {
    ctx.beginPath();
    ctx.arc(p.x, p.y, 3, 0, Math.PI * 2);
    ctx.fillStyle = "#4f9eff";
    ctx.fill();
  });
}

// ─── Payload Vulnerability Matrix ────────────────────────────────────────────
let payloadMatrixData = [];
let matrixActiveCategory = "all";

async function fetchPayloadMatrix() {
  if (!token) return;
  try {
    const res = await fetch(`${API_BASE}/research/payload-success-matrix`, {
      headers: { "Authorization": `Bearer ${token}` },
    });
    if (!res.ok) return;
    payloadMatrixData = await res.json();
    renderPayloadMatrix();
  } catch {}
}

function renderPayloadMatrix() {
  const body = $("matrixBody");
  if (!body) return;

  if (!payloadMatrixData.length) {
    body.innerHTML = '<p class="empty-state">Nenhum dado adversarial encontrado. Execute os experimentos primeiro.</p>';
    return;
  }

  const catLabels = {
    jailbreak: "Jailbreak",
    data_extraction: "Exfiltração de Dados",
    priv_esc: "Escalada de Privilégios",
    prompt_injection: "Injeção de Prompt",
    none: "Nenhuma",
    other: "Outro",
  };

  body.innerHTML = "";

  payloadMatrixData.forEach(modelEntry => {
    // Filtra por categoria selecionada
    const filtered = matrixActiveCategory === "all"
      ? modelEntry.payloads
      : modelEntry.payloads.filter(p => p.category === matrixActiveCategory);

    if (!filtered.length) return;

    const successCount = filtered.filter(p => p.attack_succeeded).length;
    const totalCount = filtered.length;
    const vulnerabilityPct = Math.round((successCount / totalCount) * 100);

    const modelCard = document.createElement("div");
    modelCard.className = "matrix-model-card";

    // Calcula cor do nível de risco
    let riskClass = "risk-low";
    let riskLabel = "Seguro";
    if (vulnerabilityPct >= 75) { riskClass = "risk-critical"; riskLabel = "CRÍTICO"; }
    else if (vulnerabilityPct >= 50) { riskClass = "risk-high"; riskLabel = "ALTO"; }
    else if (vulnerabilityPct >= 25) { riskClass = "risk-medium"; riskLabel = "MÉDIO"; }

    // Header do card do modelo
    const modelHeader = document.createElement("div");
    modelHeader.className = "matrix-model-header";
    modelHeader.innerHTML = `
      <div class="matrix-model-name">
        <span class="matrix-model-icon">🤖</span>
        <span>${escapeHtml(modelEntry.model_name)}</span>
      </div>
      <div class="matrix-model-summary">
        <span class="matrix-risk-badge ${riskClass}">${riskLabel}</span>
        <span class="matrix-stat">${successCount}/${totalCount} payloads</span>
        <span class="matrix-stat-pct">${vulnerabilityPct}% vuln.</span>
      </div>`;

    // Progress bar
    const progressBar = document.createElement("div");
    progressBar.className = "matrix-progress-bar";
    progressBar.innerHTML = `
      <div class="matrix-progress-fill ${riskClass}" style="width: ${vulnerabilityPct}%"></div>`;

    // Lista de payloads
    const payloadList = document.createElement("div");
    payloadList.className = "matrix-payload-list";

    filtered.forEach(payload => {
      const item = document.createElement("div");
      item.className = `matrix-payload-item ${payload.attack_succeeded ? "payload-success" : "payload-blocked"}`;

      const catLabel = catLabels[payload.category] || payload.category;
      const successRatio = `${payload.successful_runs}/${payload.total_runs}`;

      item.innerHTML = `
        <div class="payload-status-icon">${payload.attack_succeeded ? "💀" : "🛡️"}</div>
        <div class="payload-info">
          <div class="payload-preview" title="${escapeHtml(payload.payload_preview)}">${escapeHtml(payload.payload_preview)}</div>
          <div class="payload-meta">
            <span class="payload-cat-badge cat-${payload.category}">${catLabel}</span>
            <span class="payload-runs">${successRatio} exec. com sucesso</span>
          </div>
        </div>
        <div class="payload-result-badge ${payload.attack_succeeded ? "badge-success" : "badge-blocked"}">
          ${payload.attack_succeeded ? `SUCESSO<br><small>${successRatio}</small>` : `BLOQUEADO<br><small>${successRatio}</small>`}
        </div>`;

      payloadList.appendChild(item);
    });

    modelCard.appendChild(modelHeader);
    modelCard.appendChild(progressBar);
    modelCard.appendChild(payloadList);
    body.appendChild(modelCard);
  });

  if (!body.children.length) {
    body.innerHTML = '<p class="empty-state">Nenhum payload encontrado para esta categoria.</p>';
  }
}

// ─── Panel Tab Switcher ───────────────────────────────────────────────────────
function switchPanelTab(tab) {
  const tabAttacks = $("tabAttacks");
  const tabMatrix = $("tabMatrix");
  const contentAttacks = $("tabContentAttacks");
  const contentMatrix = $("tabContentMatrix");

  if (tab === "attacks") {
    tabAttacks.classList.add("active");
    tabMatrix.classList.remove("active");
    contentAttacks.classList.add("active");
    contentAttacks.classList.remove("hidden");
    contentMatrix.classList.add("hidden");
    contentMatrix.classList.remove("active");
    // Aguarda o DOM re-calcular o layout do canvas antes de medir e desenhar
    requestAnimationFrame(() => {
      setupAttacksCanvas();
      if (lastMetricsData) drawAttacksChart(lastMetricsData);
    });
  } else {
    tabMatrix.classList.add("active");
    tabAttacks.classList.remove("active");
    contentMatrix.classList.add("active");
    contentMatrix.classList.remove("hidden");
    contentAttacks.classList.add("hidden");
    contentAttacks.classList.remove("active");
    if (token) fetchPayloadMatrix();
  }
}

// ─── Matrix Category Filter Chips ────────────────────────────────────────────
const matrixFilterChips = $("matrixFilterChips");
if (matrixFilterChips) {
  matrixFilterChips.addEventListener("click", e => {
    const chip = e.target.closest(".chip");
    if (!chip) return;
    matrixFilterChips.querySelectorAll(".chip").forEach(c => c.classList.remove("chip-active"));
    chip.classList.add("chip-active");
    matrixActiveCategory = chip.dataset.cat;
    renderPayloadMatrix();
  });
}

// ─── Refresh All ──────────────────────────────────────────────────────────────
async function refreshAll() {
  await Promise.all([fetchMetrics(), fetchInteractions(), fetchPayloadMatrix()]);
}


// ─── Helpers ──────────────────────────────────────────────────────────────────
function escapeHtml(str) {
  return String(str || "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}

function formatMarkdown(str) {
  return str
    .replace(/\*\*(.+?)\*\*/g, "<strong>$1</strong>")
    .replace(/\*(.+?)\*/g, "<em>$1</em>")
    .replace(/\n/g, "<br>");
}

// ─── Theme Toggle ─────────────────────────────────────────────────────────────
const btnThemeToggle = $("btnThemeToggle");
const themeIcon      = $("themeIcon");
const themeLabel     = $("themeLabel");
const htmlEl         = document.documentElement;

function applyTheme(theme) {
  htmlEl.setAttribute("data-theme", theme);
  localStorage.setItem("finsec_theme", theme);
  if (theme === "dark") {
    themeIcon.textContent = "☀️";
    themeLabel.textContent = "Modo Claro";
  } else {
    themeIcon.textContent = "🌙";
    themeLabel.textContent = "Modo Escuro";
  }
}

btnThemeToggle.addEventListener("click", () => {
  const current = htmlEl.getAttribute("data-theme");
  applyTheme(current === "dark" ? "light" : "dark");
});

// Restore saved theme on load
(function () {
  const saved = localStorage.getItem("finsec_theme") || "light";
  applyTheme(saved);
})();

// ─── Start ────────────────────────────────────────────────────────────────────
init();

// Auto-refresh metrics every 30s
setInterval(() => {
  if (token) refreshAll();
}, 30000);

// Check API health every 10s
setInterval(checkApiHealth, 10000);
