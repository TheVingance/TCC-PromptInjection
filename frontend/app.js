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
btnRefreshMetrics.addEventListener("click", refreshAll);

async function fetchMetrics() {
  if (!token) return;
  try {
    const res = await fetch(`${API_BASE}/research/metrics`, {
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
    const url = `${API_BASE}/ai/interactions?limit=30${showOnlyAdversarial ? "&adversarial_only=true" : ""}`;
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

// ─── Latency Chart (Canvas) ───────────────────────────────────────────────────
function setupLatencyCanvas() {
  latencyCanvas.width = latencyCanvas.parentElement.offsetWidth;
  latencyCanvas.height = 80;
}

function drawLatencyChart() {
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

// ─── Refresh All ──────────────────────────────────────────────────────────────
async function refreshAll() {
  await Promise.all([fetchMetrics(), fetchInteractions()]);
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
