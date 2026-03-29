let token = "";

const statusPill = document.getElementById("statusPill");
const apiBaseInput = document.getElementById("apiBase");
const loginOutput = document.getElementById("loginOutput");
const PROXY_BASE = `${window.location.origin}/api-proxy.php`;

function inferApiBase() {
  // Prefer same-origin proxy first; it forwards to backend on localhost.
  return PROXY_BASE;
}

function inferFallbackApiBase() {
  const host = window.location.hostname;
  if (host === "localhost" || host === "127.0.0.1") {
    return "http://127.0.0.1:8000";
  }
  return `${window.location.origin}/api`;
}

function normalizedBase(value) {
  return value.trim().replace(/\/$/, "");
}

function apiBase() {
  const fromInput = normalizedBase(apiBaseInput.value || "");
  if (fromInput) {
    return fromInput;
  }
  const inferred = inferApiBase();
  apiBaseInput.value = inferred;
  return inferred;
}

function candidateApiBases() {
  const origin = window.location.origin;
  const host = window.location.hostname;
  const proto = window.location.protocol;
  const current = normalizedBase(apiBaseInput.value || "");
  const candidates = [
    current,
    PROXY_BASE,
    `${origin}/api`,
    `${proto}//${host}:8000`,
    origin,
  ].filter(Boolean);

  const unique = [];
  const seen = new Set();
  for (const c of candidates) {
    const n = normalizedBase(c);
    if (!seen.has(n)) {
      seen.add(n);
      unique.push(n);
    }
  }
  return unique;
}

async function probeApiBase(base) {
  try {
    const url = base === PROXY_BASE
      ? `${PROXY_BASE}?path=${encodeURIComponent("/health")}`
      : `${base.replace(/\/$/, "")}/health`;
    const res = await fetch(url, { method: "GET" });
    if (!res.ok) return false;
    const text = await res.text();
    let data = {};
    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      return false;
    }
    return typeof data === "object" && data !== null && typeof data.status === "string";
  } catch {
    return false;
  }
}

async function autoConfigureApiBase() {
  const current = normalizedBase(apiBaseInput.value || "");
  if (current) return;
  apiBaseInput.value = inferApiBase();

  const origin = window.location.origin;
  const host = window.location.hostname;
  const proto = window.location.protocol;
  const candidates = [
    PROXY_BASE,
    `${origin}/api`,
    `${proto}//${host}:8000`,
    origin,
  ];

  for (const candidate of candidates) {
    if (await probeApiBase(candidate)) {
      apiBaseInput.value = candidate;
      return;
    }
  }
  apiBaseInput.value = inferFallbackApiBase();
}

function setStatus(text, kind = "neutral") {
  statusPill.textContent = text;
  statusPill.className = `pill ${kind}`;
}

async function fetchJson(url, options) {
  const timeoutMs = 12000;
  const controller = new AbortController();
  const timer = setTimeout(() => controller.abort(), timeoutMs);
  try {
    const res = await fetch(url, { ...options, signal: controller.signal });
    const text = await res.text();
    let data;
    try {
      data = text ? JSON.parse(text) : {};
    } catch {
      data = { raw: text };
    }
    return { res, data };
  } finally {
    clearTimeout(timer);
  }
}

function resolveUrl(base, path) {
  if (normalizedBase(base) === normalizedBase(PROXY_BASE)) {
    return `${PROXY_BASE}?path=${encodeURIComponent(path)}`;
  }
  return `${normalizedBase(base)}${path}`;
}

async function authedRequest(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("Authorization", `Bearer ${token}`);
  return fetchJson(resolveUrl(apiBase(), path), { ...options, headers });
}

document.getElementById("loginBtn").addEventListener("click", async () => {
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;
  const attempts = [];
  loginOutput.textContent = "Signing in...";

  for (const base of candidateApiBases()) {
    try {
      const { res, data } = await fetchJson(resolveUrl(base, "/auth/login"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ username, password }),
      });

      if (res.ok && data && typeof data.access_token === "string" && data.access_token.length > 0) {
        token = data.access_token;
        apiBaseInput.value = base;
        setStatus("Signed in", "ok");
        loginOutput.textContent = `Signed in successfully.\nAPI base: ${base}\nToken length: ${token.length}`;
        return;
      }

      const snippet =
        typeof data === "object" && data !== null
          ? JSON.stringify(data).slice(0, 180)
          : String(data).slice(0, 180);
      attempts.push(`${base} -> ${res.status} ${snippet}`);
    } catch (err) {
      const errText = err && typeof err === "object" && "name" in err ? `${err.name}: ${err.message || ""}` : String(err);
      attempts.push(`${base} -> network error: ${errText}`);
    }
  }

  token = "";
  setStatus("Login failed", "warn");
  loginOutput.textContent =
    "Login failed on all detected API bases.\n\n" +
    `API base input: ${apiBaseInput.value || "(empty)"}\n` +
    attempts.join("\n");
});

document.getElementById("gradeBtn").addEventListener("click", async () => {
  if (!token) {
    alert("Sign in first");
    return;
  }

  const url = document.getElementById("gradeUrl").value.trim();
  const out = document.getElementById("gradeOutput");
  out.textContent = "Running grade...";

  try {
    const create = await authedRequest("/grader/runs", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ url }),
    });

    if (!create.res.ok) {
      out.textContent = JSON.stringify(create.data, null, 2);
      return;
    }

    const details = await authedRequest(`/grader/runs/${create.data.run_id}`);
    out.textContent = JSON.stringify(details.data, null, 2);
  } catch (err) {
    out.textContent = `Failed to run grade: ${err}`;
  }
});

document.getElementById("runActionBtn").addEventListener("click", async () => {
  if (!token) {
    alert("Sign in first");
    return;
  }

  const action = document.getElementById("actionType").value;
  const username = document.getElementById("actionUsername").value.trim();
  const term = document.getElementById("actionTerm").value.trim();
  const out = document.getElementById("adminOutput");
  out.textContent = "Running admin action...";

  const body = { action };
  if (username) body.username = username;
  if (term) body.term = term;

  try {
    const create = await authedRequest("/admin/actions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });

    if (!create.res.ok) {
      out.textContent = JSON.stringify(create.data, null, 2);
      return;
    }

    const details = await authedRequest(`/admin/actions/${create.data.action_id}`);
    out.textContent = JSON.stringify(details.data, null, 2);
  } catch (err) {
    out.textContent = `Failed to run action: ${err}`;
  }
});

setStatus("Not signed in", "neutral");
autoConfigureApiBase();
