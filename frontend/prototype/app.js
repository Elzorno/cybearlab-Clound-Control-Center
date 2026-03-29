let token = "";

const statusPill = document.getElementById("statusPill");
const apiBaseInput = document.getElementById("apiBase");

function inferApiBase() {
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

function setStatus(text, kind = "neutral") {
  statusPill.textContent = text;
  statusPill.className = `pill ${kind}`;
}

async function fetchJson(url, options) {
  const res = await fetch(url, options);
  const text = await res.text();
  let data;
  try {
    data = text ? JSON.parse(text) : {};
  } catch {
    data = { raw: text };
  }
  return { res, data };
}

async function authedRequest(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("Authorization", `Bearer ${token}`);
  return fetchJson(`${apiBase()}${path}`, { ...options, headers });
}

document.getElementById("loginBtn").addEventListener("click", async () => {
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;

  try {
    const { res, data } = await fetchJson(`${apiBase()}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    });

    if (!res.ok) {
      token = "";
      setStatus("Login failed", "warn");
      alert(`Login failed (${res.status}). ${data.detail || "Check API base URL and credentials."}`);
      return;
    }

    token = data.access_token || "";
    if (!token) {
      setStatus("Login failed", "warn");
      alert("Login response did not include a token.");
      return;
    }

    setStatus("Signed in", "ok");
  } catch (err) {
    token = "";
    setStatus("API unreachable", "warn");
    alert(`Could not reach API at ${apiBase()}. Update API Base URL.\n\n${err}`);
  }
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
apiBase();
