let token = "";

const statusPill = document.getElementById("statusPill");
const apiBaseInput = document.getElementById("apiBase");

function apiBase() {
  return apiBaseInput.value.trim().replace(/\/$/, "");
}

function setSignedIn(ok) {
  if (ok) {
    statusPill.textContent = "Signed in";
    statusPill.className = "pill ok";
  } else {
    statusPill.textContent = "Not signed in";
    statusPill.className = "pill neutral";
  }
}

async function authedRequest(path, options = {}) {
  const headers = new Headers(options.headers || {});
  headers.set("Authorization", `Bearer ${token}`);
  return fetch(`${apiBase()}${path}`, { ...options, headers });
}

document.getElementById("loginBtn").addEventListener("click", async () => {
  const username = document.getElementById("username").value.trim();
  const password = document.getElementById("password").value;
  const res = await fetch(`${apiBase()}/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ username, password }),
  });

  if (!res.ok) {
    setSignedIn(false);
    alert("Login failed");
    return;
  }

  const data = await res.json();
  token = data.access_token;
  setSignedIn(true);
});

document.getElementById("gradeBtn").addEventListener("click", async () => {
  if (!token) return alert("Sign in first");
  const url = document.getElementById("gradeUrl").value.trim();
  const out = document.getElementById("gradeOutput");
  out.textContent = "Running grade...";

  const create = await authedRequest("/grader/runs", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ url }),
  });

  const created = await create.json();
  if (!create.ok) {
    out.textContent = JSON.stringify(created, null, 2);
    return;
  }

  const details = await authedRequest(`/grader/runs/${created.run_id}`);
  const payload = await details.json();
  out.textContent = JSON.stringify(payload, null, 2);
});

document.getElementById("runActionBtn").addEventListener("click", async () => {
  if (!token) return alert("Sign in first");

  const action = document.getElementById("actionType").value;
  const username = document.getElementById("actionUsername").value.trim();
  const term = document.getElementById("actionTerm").value.trim();
  const out = document.getElementById("adminOutput");
  out.textContent = "Running admin action...";

  const body = { action };
  if (username) body.username = username;
  if (term) body.term = term;

  const create = await authedRequest("/admin/actions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });

  const created = await create.json();
  if (!create.ok) {
    out.textContent = JSON.stringify(created, null, 2);
    return;
  }

  const details = await authedRequest(`/admin/actions/${created.action_id}`);
  const payload = await details.json();
  out.textContent = JSON.stringify(payload, null, 2);
});
