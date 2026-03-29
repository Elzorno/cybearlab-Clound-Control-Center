/**
 * ISCS1800 Control Center
 * Frontend Application with Hash Router
 */

(function () {
  "use strict";

  // ============================================================
  // State
  // ============================================================
  let token = "";
  let currentApiBase = "";
  let currentRoute = "overview";
  let reportsPage = 1;
  let reportsPageSize = 15;
  let currentAdminAction = "add_student";

  const PROXY_BASE = `${window.location.origin}/api-proxy.php`;
  const REVERSE_PROXY_BASE = `${window.location.origin}/api`;

  // ============================================================
  // DOM Elements
  // ============================================================
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  // ============================================================
  // API Utilities
  // ============================================================
  function normalizedBase(value) {
    return (value || "").trim().replace(/\/$/, "");
  }

  function candidateApiBases() {
    const host = window.location.hostname;
    const proto = window.location.protocol;
    const current = normalizedBase($("#apiBase")?.value || "");
    const candidates = [
      current,
      REVERSE_PROXY_BASE,
      PROXY_BASE,
      `${proto}//${host}:8000`,
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
        : `${normalizedBase(base)}/health`;
      const res = await fetch(url, { method: "GET" });
      if (!res.ok) return false;
      const text = await res.text();
      const data = text ? JSON.parse(text) : {};
      return typeof data === "object" && data !== null && typeof data.status === "string";
    } catch {
      return false;
    }
  }

  async function autoConfigureApiBase() {
    for (const base of candidateApiBases()) {
      if (await probeApiBase(base)) {
        currentApiBase = base;
        const input = $("#apiBase");
        if (input) input.value = base;
        return base;
      }
    }
    currentApiBase = REVERSE_PROXY_BASE;
    return currentApiBase;
  }

  function resolveUrl(path) {
    const base = currentApiBase || REVERSE_PROXY_BASE;
    if (normalizedBase(base) === normalizedBase(PROXY_BASE)) {
      return `${PROXY_BASE}?path=${encodeURIComponent(path)}`;
    }
    return `${normalizedBase(base)}${path}`;
  }

  async function fetchJson(url, options = {}) {
    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15000);
    try {
      const res = await fetch(url, { ...options, signal: controller.signal, cache: "no-store" });
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

  async function api(path, options = {}) {
    const headers = new Headers(options.headers || {});
    if (token) headers.set("Authorization", `Bearer ${token}`);
    return fetchJson(resolveUrl(path), { ...options, headers });
  }

  function sleep(ms) {
    return new Promise((r) => setTimeout(r, ms));
  }

  // ============================================================
  // Router
  // ============================================================
  const routes = {
    "/": "overview",
    "/grader": "grader",
    "/admin": "admin",
    "/reports": "reports",
    "/settings": "settings",
  };

  function getRouteFromHash() {
    const hash = window.location.hash.replace(/^#/, "") || "/";
    return routes[hash] || "overview";
  }

  function navigateTo(route) {
    const path = Object.keys(routes).find((k) => routes[k] === route) || "/";
    window.location.hash = path;
  }

  function updateActiveNav() {
    $$(".nav-link").forEach((link) => {
      const route = link.dataset.route;
      link.classList.toggle("active", route === currentRoute);
    });
  }

  function showView(route) {
    currentRoute = route;
    $$(".view").forEach((v) => v.classList.add("hidden"));
    const viewEl = $(`#view-${route}`);
    if (viewEl) viewEl.classList.remove("hidden");
    updateActiveNav();

    // Fire view-specific init
    if (route === "overview") loadOverview();
    if (route === "reports") loadReports();
  }

  function handleRouteChange() {
    const route = getRouteFromHash();
    showView(route);
  }

  // ============================================================
  // Authentication
  // ============================================================
  function showApp() {
    $("#loginGate").classList.add("hidden");
    $("#appShell").classList.remove("hidden");
    handleRouteChange();
  }

  function showLogin() {
    $("#loginGate").classList.remove("hidden");
    $("#appShell").classList.add("hidden");
    token = "";
  }

  async function handleLogin() {
    const username = $("#username").value.trim();
    const password = $("#password").value;
    const errorEl = $("#loginError");
    errorEl.textContent = "";

    if (!username || !password) {
      errorEl.textContent = "Username and password required.";
      return;
    }

    $("#loginBtn").disabled = true;
    $("#loginBtn").textContent = "Signing in...";

    try {
      await autoConfigureApiBase();

      for (const base of candidateApiBases()) {
        try {
          const url = base === PROXY_BASE
            ? `${PROXY_BASE}?path=${encodeURIComponent("/auth/login")}`
            : `${normalizedBase(base)}/auth/login`;

          const { res, data } = await fetchJson(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ username, password }),
          });

          if (res.ok && data?.access_token) {
            token = data.access_token;
            currentApiBase = base;
            if ($("#apiBase")) $("#apiBase").value = base;
            showApp();
            return;
          }
        } catch {}
      }

      errorEl.textContent = "Invalid credentials or backend unavailable.";
    } finally {
      $("#loginBtn").disabled = false;
      $("#loginBtn").textContent = "Sign In";
    }
  }

  function handleLogout() {
    showLogin();
  }

  // ============================================================
  // Overview View
  // ============================================================
  async function loadOverview() {
    // System status
    try {
      const { res, data } = await api("/health");
      $("#systemStatus").textContent = res.ok ? "Healthy" : "Degraded";
      $("#systemStatus").className = `stat-value ${res.ok ? "ok" : "warn"}`;
    } catch {
      $("#systemStatus").textContent = "Unavailable";
      $("#systemStatus").className = "stat-value warn";
    }

    // API endpoint
    $("#apiEndpoint").textContent = currentApiBase || "—";

    // Recent grades
    try {
      const { res, data } = await api("/grader/runs?pageSize=5");
      if (res.ok && data.items) {
        $("#recentGradesCount").textContent = data.total ?? data.items.length;
        renderRecentGrades(data.items);
      }
    } catch {
      $("#recentGrades").innerHTML = '<p class="muted">Failed to load.</p>';
    }
  }

  function renderRecentGrades(items) {
    const container = $("#recentGrades");
    if (!items.length) {
      container.innerHTML = '<p class="muted">No grade runs yet.</p>';
      return;
    }

    container.innerHTML = items
      .map((item) => {
        const score = item.total_score != null ? Math.round(item.total_score) : "—";
        const scoreClass = item.total_score >= 70 ? "ok" : item.total_score >= 50 ? "warn" : "low";
        const date = new Date(item.created_at).toLocaleDateString();
        const urlShort = item.url?.replace(/^https?:\/\//, "").slice(0, 30) || "—";
        return `
          <div class="recent-item">
            <span class="recent-score ${scoreClass}">${score}</span>
            <span class="recent-url">${escapeHtml(urlShort)}</span>
            <span class="recent-date">${date}</span>
          </div>
        `;
      })
      .join("");
  }

  // ============================================================
  // Grader View
  // ============================================================
  async function handleGrade() {
    const url = $("#gradeUrl").value.trim();
    if (!url) {
      alert("Enter a URL to grade.");
      return;
    }

    const student = $("#gradeStudent")?.value.trim() || null;
    const term = $("#gradeTerm")?.value.trim() || null;

    // Reset UI
    $("#gradeStatus").classList.remove("hidden");
    $("#gradeScore").classList.add("hidden");
    $("#gradeRubric").classList.add("hidden");
    $("#gradeFeedback").classList.add("hidden");
    $("#gradeRaw").classList.add("hidden");
    setGradeStep("queued");

    $("#gradeBtn").disabled = true;
    $("#gradeBtn").textContent = "Running...";

    try {
      const body = { url };
      if (student) body.student_username = student;
      if (term) body.term = term;

      const create = await api("/grader/runs", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!create.res.ok) {
        alert(`Failed to start grading: ${create.data?.detail || "Unknown error"}`);
        return;
      }

      const runId = create.data.run_id;
      await pollGradeRun(runId);
    } finally {
      $("#gradeBtn").disabled = false;
      $("#gradeBtn").textContent = "Run Grader";
    }
  }

  async function pollGradeRun(runId) {
    const timeout = Date.now() + 120000;
    let lastStatus = "queued";

    while (Date.now() < timeout) {
      const { res, data } = await api(`/grader/runs/${runId}`);

      if (!res.ok) {
        setGradeStep("failed");
        return;
      }

      lastStatus = data.status || lastStatus;

      // Map backend status to our steps
      if (lastStatus === "queued") setGradeStep("queued");
      else if (lastStatus === "in_progress" || lastStatus === "crawling") setGradeStep("crawling");
      else if (lastStatus === "validating") setGradeStep("validating");
      else if (lastStatus === "scoring") setGradeStep("scoring");
      else if (lastStatus === "completed") {
        setGradeStep("completed");
        renderGradeResult(data);
        return;
      } else if (lastStatus === "failed") {
        setGradeStep("failed");
        $("#gradeRaw").classList.remove("hidden");
        $("#gradeRawJson").textContent = JSON.stringify(data, null, 2);
        return;
      }

      await sleep(1500);
    }
  }

  function setGradeStep(step) {
    const steps = ["queued", "crawling", "validating", "scoring", "completed"];
    const idx = steps.indexOf(step);

    $$(".status-step").forEach((el, i) => {
      el.classList.remove("active", "done");
      if (i < idx) el.classList.add("done");
      else if (i === idx) el.classList.add("active");
    });
  }

  function renderGradeResult(data) {
    // Score gauge
    const score = data.total_score ?? 0;
    $("#gradeScore").classList.remove("hidden");
    $("#totalScore").textContent = Math.round(score);
    $("#scoredUrl").textContent = data.input_url || "—";

    // Gauge animation
    const gauge = $("#gaugeCircle");
    const circumference = 2 * Math.PI * 45;
    gauge.style.strokeDasharray = circumference;
    gauge.style.strokeDashoffset = circumference - (score / 100) * circumference;
    gauge.classList.remove("low", "mid", "high");
    gauge.classList.add(score >= 70 ? "high" : score >= 50 ? "mid" : "low");

    // Rubric breakdown
    if (data.sections) {
      $("#gradeRubric").classList.remove("hidden");
      renderRubricSections(data.sections);
    }

    // Feedback
    if (data.summary_feedback?.length) {
      $("#gradeFeedback").classList.remove("hidden");
      $("#feedbackList").innerHTML = data.summary_feedback
        .map((f) => `<li>${escapeHtml(f)}</li>`)
        .join("");
    }

    // Raw JSON
    $("#gradeRaw").classList.remove("hidden");
    $("#gradeRawJson").textContent = JSON.stringify(data, null, 2);
  }

  function renderRubricSections(sections) {
    const container = $("#rubricSections");
    const labels = {
      page_count: "Page Count",
      external_stylesheet: "External Stylesheet",
      structures: "HTML Structures",
      responsiveness: "Responsiveness",
      theme: "Theme Consistency",
      navigation: "Navigation",
      validity: "W3C Validity",
    };

    container.innerHTML = Object.entries(sections)
      .map(([key, sec]) => {
        const score = sec.score ?? 0;
        const max = sec.max_score ?? 10;
        const pct = max > 0 ? (score / max) * 100 : 0;
        const label = labels[key] || key;
        const cls = pct >= 70 ? "high" : pct >= 50 ? "mid" : "low";
        return `
          <div class="rubric-item">
            <div class="rubric-header">
              <span class="rubric-label">${escapeHtml(label)}</span>
              <span class="rubric-score">${score}/${max}</span>
            </div>
            <div class="rubric-bar">
              <div class="rubric-fill ${cls}" style="width: ${pct}%"></div>
            </div>
          </div>
        `;
      })
      .join("");
  }

  // ============================================================
  // Admin View
  // ============================================================
  function setupAdminTabs() {
    $$(".tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        $$(".tab-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        currentAdminAction = btn.dataset.action;
        updateAdminButtonLabel();
      });
    });

    // Bulk actions
    $$("[data-bulk]").forEach((btn) => {
      btn.addEventListener("click", () => runBulkAction(btn.dataset.bulk));
    });
  }

  function updateAdminButtonLabel() {
    const labels = {
      add_student: "Add Student",
      reset_password: "Reset Password",
      disable_student: "Disable Student",
    };
    $("#adminSubmitBtn").textContent = labels[currentAdminAction] || "Run Action";
  }

  async function handleAdminAction() {
    const username = $("#adminUsername").value.trim();
    const term = $("#adminTerm").value.trim();
    const out = $("#adminOutput");

    if (!username && currentAdminAction !== "fix_perms_all" && currentAdminAction !== "https_students_all") {
      alert("Username is required for this action.");
      return;
    }

    out.textContent = "Running...";
    $("#adminSubmitBtn").disabled = true;

    try {
      const body = { action: currentAdminAction };
      if (username) body.username = username;
      if (term) body.term = term;

      const create = await api("/admin/actions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (!create.res.ok) {
        out.textContent = `Error: ${JSON.stringify(create.data, null, 2)}`;
        return;
      }

      // Poll for result
      const actionId = create.data.action_id;
      const details = await api(`/admin/actions/${actionId}`);
      out.textContent = JSON.stringify(details.data, null, 2);
    } catch (err) {
      out.textContent = `Failed: ${err}`;
    } finally {
      $("#adminSubmitBtn").disabled = false;
    }
  }

  async function runBulkAction(action) {
    const out = $("#adminOutput");
    out.textContent = `Running ${action}...`;

    try {
      const create = await api("/admin/actions", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });

      if (!create.res.ok) {
        out.textContent = `Error: ${JSON.stringify(create.data, null, 2)}`;
        return;
      }

      const actionId = create.data.action_id;
      const details = await api(`/admin/actions/${actionId}`);
      out.textContent = JSON.stringify(details.data, null, 2);
    } catch (err) {
      out.textContent = `Failed: ${err}`;
    }
  }

  // ============================================================
  // Reports View
  // ============================================================
  async function loadReports() {
    const term = $("#filterTerm")?.value.trim() || "";
    const student = $("#filterStudent")?.value.trim() || "";

    const params = new URLSearchParams();
    params.set("page", reportsPage);
    params.set("pageSize", reportsPageSize);
    if (term) params.set("term", term);
    if (student) params.set("student", student);

    const tbody = $("#reportsBody");
    tbody.innerHTML = '<tr><td colspan="6" class="muted">Loading...</td></tr>';

    try {
      const { res, data } = await api(`/grader/runs?${params}`);

      if (!res.ok) {
        tbody.innerHTML = '<tr><td colspan="6" class="muted">Failed to load.</td></tr>';
        return;
      }

      if (!data.items?.length) {
        tbody.innerHTML = '<tr><td colspan="6" class="muted">No results found.</td></tr>';
        updatePagination(1, 0);
        return;
      }

      tbody.innerHTML = data.items
        .map((item) => {
          const date = new Date(item.created_at).toLocaleString();
          const score = item.total_score != null ? Math.round(item.total_score) : "—";
          const scoreClass = item.total_score >= 70 ? "ok" : item.total_score >= 50 ? "warn" : "low";
          const urlShort = item.url?.replace(/^https?:\/\//, "").slice(0, 35) || "—";
          return `
            <tr>
              <td>${escapeHtml(date)}</td>
              <td>${escapeHtml(item.student_username || "—")}</td>
              <td class="url-cell" title="${escapeHtml(item.url || "")}">${escapeHtml(urlShort)}</td>
              <td><span class="score-badge ${scoreClass}">${score}</span></td>
              <td><span class="status-badge ${item.status}">${item.status}</span></td>
              <td><button class="btn btn-sm" onclick="app.showRunDetail('${item.run_id}')">View</button></td>
            </tr>
          `;
        })
        .join("");

      updatePagination(data.page, data.total);
    } catch {
      tbody.innerHTML = '<tr><td colspan="6" class="muted">Error loading reports.</td></tr>';
    }
  }

  function updatePagination(page, total) {
    const totalPages = Math.ceil(total / reportsPageSize) || 1;
    $("#pageInfo").textContent = `Page ${page} of ${totalPages}`;
    $("#prevPageBtn").disabled = page <= 1;
    $("#nextPageBtn").disabled = page >= totalPages;
  }

  async function showRunDetail(runId) {
    const modal = $("#runDetailModal");
    const body = $("#runDetailBody");
    modal.classList.remove("hidden");
    body.innerHTML = '<p class="muted">Loading...</p>';

    try {
      const { res, data } = await api(`/grader/runs/${runId}`);
      if (!res.ok) {
        body.innerHTML = `<p class="error-text">Failed to load run details.</p>`;
        return;
      }

      const score = data.total_score ?? "—";
      body.innerHTML = `
        <div class="detail-header">
          <div class="detail-score ${score >= 70 ? "high" : score >= 50 ? "mid" : "low"}">${Math.round(score)}</div>
          <div class="detail-meta">
            <p><strong>URL:</strong> ${escapeHtml(data.input_url || "—")}</p>
            <p><strong>Status:</strong> ${data.status}</p>
            <p><strong>Student:</strong> ${escapeHtml(data.student_username || "—")}</p>
          </div>
        </div>
        <h4>Rubric Breakdown</h4>
        ${data.sections ? renderDetailSections(data.sections) : "<p>No section data.</p>"}
        <h4>Feedback</h4>
        ${data.summary_feedback?.length ? `<ul>${data.summary_feedback.map((f) => `<li>${escapeHtml(f)}</li>`).join("")}</ul>` : "<p>No feedback.</p>"}
        <details>
          <summary>Raw JSON</summary>
          <pre class="output">${escapeHtml(JSON.stringify(data, null, 2))}</pre>
        </details>
      `;
    } catch {
      body.innerHTML = `<p class="error-text">Error loading details.</p>`;
    }
  }

  function renderDetailSections(sections) {
    return Object.entries(sections)
      .map(([key, sec]) => {
        const score = sec.score ?? 0;
        const max = sec.max_score ?? 10;
        return `<p><strong>${escapeHtml(key)}:</strong> ${score}/${max}</p>`;
      })
      .join("");
  }

  function closeModal() {
    $("#runDetailModal").classList.add("hidden");
  }

  // ============================================================
  // Utilities
  // ============================================================
  function escapeHtml(str) {
    const div = document.createElement("div");
    div.textContent = str;
    return div.innerHTML;
  }

  // ============================================================
  // Event Bindings
  // ============================================================
  function bindEvents() {
    // Login
    $("#loginBtn").addEventListener("click", handleLogin);
    $("#password").addEventListener("keydown", (e) => {
      if (e.key === "Enter") handleLogin();
    });

    // Logout
    $("#logoutBtn").addEventListener("click", handleLogout);

    // Router
    window.addEventListener("hashchange", handleRouteChange);

    // Grader
    $("#gradeBtn").addEventListener("click", handleGrade);

    // Admin
    setupAdminTabs();
    $("#adminSubmitBtn").addEventListener("click", handleAdminAction);

    // Reports
    $("#filterBtn").addEventListener("click", () => {
      reportsPage = 1;
      loadReports();
    });
    $("#clearFiltersBtn").addEventListener("click", () => {
      $("#filterTerm").value = "";
      $("#filterStudent").value = "";
      reportsPage = 1;
      loadReports();
    });
    $("#prevPageBtn").addEventListener("click", () => {
      reportsPage = Math.max(1, reportsPage - 1);
      loadReports();
    });
    $("#nextPageBtn").addEventListener("click", () => {
      reportsPage++;
      loadReports();
    });

    // Modal
    $(".modal-close")?.addEventListener("click", closeModal);
    $(".modal-backdrop")?.addEventListener("click", closeModal);

    // Settings - API base changes
    $("#apiBase")?.addEventListener("change", (e) => {
      currentApiBase = normalizedBase(e.target.value);
    });
  }

  // ============================================================
  // Init
  // ============================================================
  async function init() {
    bindEvents();
    await autoConfigureApiBase();
    showLogin();
  }

  // Expose needed functions globally
  window.app = {
    showRunDetail,
  };

  // Start
  init();
})();
