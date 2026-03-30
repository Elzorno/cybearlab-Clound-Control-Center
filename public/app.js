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
    "/users": "users",
    "/dns": "dns",
    "/reports": "reports",
    "/settings": "settings",
    "/system": "system",
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
    if (route === "system") loadSystemView();
    if (route === "users") loadUsersView();
    if (route === "dns") loadDnsView();
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
  // Roster Import
  // ============================================================
  let rosterPreviewData = null;

  function setupRosterUpload() {
    const uploadArea = $("#rosterUploadArea");
    const fileInput = $("#rosterFileInput");

    // Drag and drop
    uploadArea.addEventListener("dragover", (e) => {
      e.preventDefault();
      uploadArea.classList.add("dragover");
    });

    uploadArea.addEventListener("dragleave", () => {
      uploadArea.classList.remove("dragover");
    });

    uploadArea.addEventListener("drop", (e) => {
      e.preventDefault();
      uploadArea.classList.remove("dragover");
      const files = e.dataTransfer.files;
      if (files.length > 0) {
        handleRosterFile(files[0]);
      }
    });

    // File input change
    fileInput.addEventListener("change", () => {
      if (fileInput.files.length > 0) {
        handleRosterFile(fileInput.files[0]);
      }
    });

    // Import button
    $("#rosterImportBtn").addEventListener("click", handleRosterImport);

    // Reset button
    $("#rosterResetBtn").addEventListener("click", resetRosterUI);
  }

  async function handleRosterFile(file) {
    if (!file.name.toLowerCase().endsWith(".csv")) {
      alert("Please upload a CSV file.");
      return;
    }

    // Show loading state
    $("#rosterUploadArea").classList.add("loading");
    
    try {
      const formData = new FormData();
      formData.append("file", file);

      const res = await fetch(resolveUrl("/admin/roster/preview"), {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${token}`,
        },
        body: formData,
      });

      const data = await res.json();

      if (!res.ok) {
        alert(`Error: ${data.detail || "Failed to parse roster"}`);
        return;
      }

      if (data.errors?.length) {
        alert(`CSV Errors:\n${data.errors.join("\n")}`);
        return;
      }

      // Store preview data
      rosterPreviewData = data;
      
      // Show preview
      renderRosterPreview(data);
    } catch (err) {
      alert(`Upload failed: ${err.message}`);
    } finally {
      $("#rosterUploadArea").classList.remove("loading");
    }
  }

  function renderRosterPreview(data) {
    // Hide upload, show preview
    $("#rosterUploadArea").classList.add("hidden");
    $("#rosterTermRow").classList.remove("hidden");
    $("#rosterPreview").classList.remove("hidden");

    // Update count
    $("#rosterPreviewCount").textContent = `(${data.valid_count} valid, ${data.skip_count} skipped)`;

    // Render table
    const tbody = $("#rosterPreviewBody");
    tbody.innerHTML = data.entries
      .map((e) => {
        const statusClass = e.status === "pending" ? "ok" : "warn";
        return `
          <tr class="${e.status === "skip" ? "row-skip" : ""}">
            <td>${escapeHtml(e.first_name)}</td>
            <td>${escapeHtml(e.last_name)}</td>
            <td>${escapeHtml(e.student_id)}</td>
            <td class="arrow-cell">→</td>
            <td><code>${escapeHtml(e.username || "—")}</code></td>
            <td><code>${escapeHtml(e.password || "—")}</code></td>
            <td><span class="status-badge ${statusClass}">${e.status}</span>${e.message ? ` <span class="muted small">${escapeHtml(e.message)}</span>` : ""}</td>
          </tr>
        `;
      })
      .join("");

    // Enable/disable import button
    $("#rosterImportBtn").disabled = data.valid_count === 0;
  }

  async function handleRosterImport() {
    if (!rosterPreviewData || rosterPreviewData.valid_count === 0) {
      alert("No valid entries to import.");
      return;
    }

    const term = $("#rosterTerm").value.trim() || null;
    
    // Hide preview, show progress
    $("#rosterPreview").classList.add("hidden");
    $("#rosterTermRow").classList.add("hidden");
    $("#rosterProgress").classList.remove("hidden");
    $("#rosterProgressFill").style.width = "0%";
    $("#rosterProgressText").textContent = "Starting import...";

    try {
      const payload = {
        entries: rosterPreviewData.entries,
        term: term,
      };

      // Simulate progress (backend doesn't stream, so we fake it)
      let progress = 0;
      const progressInterval = setInterval(() => {
        progress = Math.min(progress + 5, 90);
        $("#rosterProgressFill").style.width = `${progress}%`;
        $("#rosterProgressText").textContent = `Importing... ${progress}%`;
      }, 200);

      const { res, data } = await api("/admin/roster/import", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      clearInterval(progressInterval);
      $("#rosterProgressFill").style.width = "100%";

      if (!res.ok) {
        alert(`Import failed: ${data.detail || "Unknown error"}`);
        resetRosterUI();
        return;
      }

      // Show results
      renderRosterResults(data);
    } catch (err) {
      alert(`Import failed: ${err.message}`);
      resetRosterUI();
    }
  }

  function renderRosterResults(data) {
    // Hide progress, show results
    $("#rosterProgress").classList.add("hidden");
    $("#rosterResults").classList.remove("hidden");

    // Update summary
    $("#rosterCreatedCount").textContent = data.created_count;
    $("#rosterSkippedCount").textContent = data.skipped_count;
    $("#rosterFailedCount").textContent = data.failed_count;

    // Render details table
    const tbody = $("#rosterResultsBody");
    tbody.innerHTML = data.results
      .map((r) => {
        const statusClass = r.status === "created" ? "ok" : r.status === "skipped" ? "warn" : "error";
        return `
          <tr>
            <td><code>${escapeHtml(r.username)}</code></td>
            <td><span class="status-badge ${statusClass}">${r.status}</span></td>
            <td class="muted">${escapeHtml(r.message)}</td>
          </tr>
        `;
      })
      .join("");
  }

  function resetRosterUI() {
    rosterPreviewData = null;
    
    // Reset file input
    $("#rosterFileInput").value = "";
    
    // Reset visibility
    $("#rosterUploadArea").classList.remove("hidden", "loading");
    $("#rosterTermRow").classList.add("hidden");
    $("#rosterPreview").classList.add("hidden");
    $("#rosterProgress").classList.add("hidden");
    $("#rosterResults").classList.add("hidden");
    
    // Clear tables
    $("#rosterPreviewBody").innerHTML = "";
    $("#rosterResultsBody").innerHTML = "";
    $("#rosterTerm").value = "";
  }

  // ============================================================
  // System Monitoring
  // ============================================================
  let logWebSocket = null;
  let systemRefreshInterval = null;

  async function loadSystemView() {
    // Stop any existing refresh
    if (systemRefreshInterval) {
      clearInterval(systemRefreshInterval);
    }

    // Initial load
    await refreshSystemStats();
    await loadServices();
    await loadLogs();
    await loadBackups();
    await loadBackupTerms();

    // Auto-refresh every 10 seconds
    systemRefreshInterval = setInterval(refreshSystemStats, 10000);

    // Setup sub-tabs (within the system view)
    setupSystemTabs();
  }

  function setupSystemTabs() {
    // Use tabs within #view-system to avoid conflict with admin tabs
    $$("#view-system .tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const tab = btn.dataset.sysTab;
        
        // Update active tab
        $$("#view-system .tab-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        
        // Show correct panel
        $$(".sys-panel").forEach((p) => p.classList.add("hidden"));
        $(`#sys${tab.charAt(0).toUpperCase() + tab.slice(1)}Panel`)?.classList.remove("hidden");
        
        // Stop log streaming if switching away
        if (tab !== "logs" && logWebSocket) {
          logWebSocket.close();
          logWebSocket = null;
        }
      });
    });
  }

  async function refreshSystemStats() {
    try {
      const { res, data } = await api("/system/stats");
      if (!res.ok) return;

      // Uptime + load average
      $("#sysUptime").textContent = data.uptime_formatted;
      const loadEl = $("#sysLoadAvg");
      if (loadEl && data.cpu.load_avg) {
        loadEl.textContent = `Load: ${data.cpu.load_avg.map(l => l.toFixed(2)).join(", ")}`;
      }

      // CPU
      const cpuPct = Math.round(data.cpu.percent);
      $("#sysCpu").textContent = `${cpuPct}%`;
      $("#sysCpuBar").style.width = `${cpuPct}%`;
      $("#sysCpuBar").className = `health-bar-fill ${cpuPct > 80 ? 'high' : cpuPct > 50 ? 'mid' : 'low'}`;

      // Memory
      const memPct = Math.round(data.memory.percent);
      $("#sysMemory").textContent = `${data.memory.used_formatted} / ${data.memory.total_formatted}`;
      $("#sysMemoryBar").style.width = `${memPct}%`;
      $("#sysMemoryBar").className = `health-bar-fill ${memPct > 80 ? 'high' : memPct > 50 ? 'mid' : 'low'}`;

      // Disk (first/main disk)
      if (data.disks.length > 0) {
        const disk = data.disks[0];
        const diskPct = Math.round(disk.percent);
        $("#sysDisk").textContent = `${disk.used_formatted} / ${disk.total_formatted}`;
        $("#sysDiskBar").style.width = `${diskPct}%`;
        $("#sysDiskBar").className = `health-bar-fill ${diskPct > 80 ? 'high' : diskPct > 50 ? 'mid' : 'low'}`;
      }

      // Processes
      renderProcesses(data.top_processes);
    } catch (err) {
      console.error("Failed to load system stats:", err);
    }
  }

  function renderProcesses(processes) {
    const tbody = $("#processesBody");
    if (!processes?.length) {
      tbody.innerHTML = '<tr><td colspan="6" class="muted">No process data.</td></tr>';
      return;
    }

    tbody.innerHTML = processes
      .map((p) => `
        <tr>
          <td>${p.pid}</td>
          <td>${escapeHtml(p.name)}</td>
          <td>${escapeHtml(p.username)}</td>
          <td>${p.cpu_percent.toFixed(1)}%</td>
          <td>${p.memory_percent.toFixed(1)}%</td>
          <td><span class="status-badge ${p.status === 'running' ? 'ok' : 'warn'}">${p.status}</span></td>
        </tr>
      `)
      .join("");
  }

  async function loadServices() {
    try {
      const { res, data } = await api("/system/services");
      if (!res.ok) return;

      const grid = $("#servicesGrid");
      if (!data?.length) {
        grid.innerHTML = '<p class="muted">No services found.</p>';
        return;
      }

      grid.innerHTML = data
        .map((s) => `
          <div class="service-card ${s.status === 'running' ? 'running' : 'stopped'}">
            <div class="service-header">
              <span class="service-status-dot"></span>
              <span class="service-name">${escapeHtml(s.display_name)}</span>
            </div>
            <div class="service-meta">
              ${s.memory_mb ? `<span>💾 ${s.memory_mb} MB</span>` : ''}
              ${s.uptime ? `<span>⏱ ${s.uptime}</span>` : ''}
            </div>
            <div class="service-actions">
              ${s.status === 'running' 
                ? `<button class="btn btn-xs" onclick="app.controlService('${s.name}', 'restart')">Restart</button>
                   <button class="btn btn-xs btn-danger" onclick="app.controlService('${s.name}', 'stop')">Stop</button>`
                : `<button class="btn btn-xs primary" onclick="app.controlService('${s.name}', 'start')">Start</button>`
              }
            </div>
          </div>
        `)
        .join("");
    } catch (err) {
      console.error("Failed to load services:", err);
    }
  }

  async function controlService(serviceName, action) {
    if (!confirm(`${action.charAt(0).toUpperCase() + action.slice(1)} ${serviceName}?`)) return;

    try {
      const { res, data } = await api(`/system/services/${serviceName}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });

      if (res.ok) {
        alert(data.message);
        loadServices();
      } else {
        alert(`Failed: ${data.detail || data.message || "Unknown error"}`);
      }
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  }

  async function loadLogs() {
    try {
      const { res, data } = await api("/system/logs");
      if (!res.ok) return;

      const select = $("#logSelect");
      select.innerHTML = '<option value="">Select a log file...</option>' +
        data
          .filter((l) => l.exists)
          .map((l) => `<option value="${l.key}">${escapeHtml(l.name)} (${l.size_formatted})</option>`)
          .join("");
    } catch (err) {
      console.error("Failed to load logs:", err);
    }
  }

  async function viewLog(logKey, lines = 100) {
    if (!logKey) return;

    try {
      const { res, data } = await api(`/system/logs/${logKey}?lines=${lines}`);
      if (!res.ok) {
        $("#logOutput").textContent = `Error: ${data.detail || "Failed to load log"}`;
        return;
      }

      $("#logOutput").textContent = data.content || "(empty)";
      // Scroll to bottom
      $("#logOutput").scrollTop = $("#logOutput").scrollHeight;
    } catch (err) {
      $("#logOutput").textContent = `Error: ${err.message}`;
    }
  }

  async function searchLog(logKey, pattern) {
    if (!logKey || !pattern) return;

    try {
      const { res, data } = await api(`/system/logs/${logKey}/search?pattern=${encodeURIComponent(pattern)}`);
      if (!res.ok) {
        $("#logOutput").textContent = `Error: ${data.detail || "Search failed"}`;
        return;
      }

      $("#logOutput").textContent = data.content || "(no matches)";
    } catch (err) {
      $("#logOutput").textContent = `Error: ${err.message}`;
    }
  }

  function startLogStream(logKey) {
    if (logWebSocket) {
      logWebSocket.close();
    }

    const wsBase = currentApiBase.replace(/^http/, "ws");
    const wsUrl = `${wsBase}/system/logs/${logKey}/stream`;

    try {
      logWebSocket = new WebSocket(wsUrl);
      $("#logOutput").textContent = "Connecting to live stream...\\n";
      $("#logStreamBtn").textContent = "Stop Stream";
      $("#logStreamBtn").classList.add("streaming");

      logWebSocket.onmessage = (event) => {
        const output = $("#logOutput");
        output.textContent += event.data;
        // Auto-scroll
        output.scrollTop = output.scrollHeight;
        // Limit buffer
        if (output.textContent.length > 500000) {
          output.textContent = output.textContent.slice(-400000);
        }
      };

      logWebSocket.onclose = () => {
        $("#logStreamBtn").textContent = "Live Stream";
        $("#logStreamBtn").classList.remove("streaming");
        logWebSocket = null;
      };

      logWebSocket.onerror = () => {
        $("#logOutput").textContent += "\\n[WebSocket error - stream ended]\\n";
      };
    } catch (err) {
      $("#logOutput").textContent = `WebSocket error: ${err.message}`;
    }
  }

  function stopLogStream() {
    if (logWebSocket) {
      logWebSocket.close();
      logWebSocket = null;
    }
  }

  async function loadBackups() {
    try {
      const { res, data } = await api("/system/backups");
      if (!res.ok) return;

      const tbody = $("#backupsBody");
      if (!data?.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="muted">No backups found.</td></tr>';
        return;
      }

      tbody.innerHTML = data
        .map((b) => `
          <tr>
            <td><code>${escapeHtml(b.filename)}</code></td>
            <td><span class="badge">${b.backup_type}</span></td>
            <td>${b.size_formatted}</td>
            <td>${new Date(b.created_at).toLocaleString()}</td>
            <td>
              <button class="btn btn-xs" onclick="app.downloadBackup('${escapeHtml(b.filename)}')">Download</button>
              <button class="btn btn-xs btn-danger" onclick="app.deleteBackup('${escapeHtml(b.filename)}')">Delete</button>
            </td>
          </tr>
        `)
        .join("");
    } catch (err) {
      console.error("Failed to load backups:", err);
    }
  }

  async function loadBackupTerms() {
    try {
      const { res, data } = await api("/system/backups/terms");
      if (!res.ok) return;

      const select = $("#backupTerm");
      select.innerHTML = '<option value="">Select term...</option>' +
        data.terms.map((t) => `<option value="${t}">${t}</option>`).join("");
    } catch (err) {
      console.error("Failed to load terms:", err);
    }
  }

  async function loadBackupStudents(term) {
    try {
      const { res, data } = await api(`/system/backups/terms/${term}/students`);
      if (!res.ok) return;

      const select = $("#backupStudent");
      select.innerHTML = '<option value="">Select student...</option>' +
        data.students.map((s) => `<option value="${s}">${s}</option>`).join("");
    } catch (err) {
      console.error("Failed to load students:", err);
    }
  }

  async function createBackup() {
    const backupType = $("#backupType").value;
    const term = $("#backupTerm").value;
    const student = $("#backupStudent").value;

    if (backupType === "term" && !term) {
      alert("Please select a term.");
      return;
    }
    if (backupType === "student" && (!term || !student)) {
      alert("Please select a term and student.");
      return;
    }

    // Show progress
    $("#backupProgress").classList.remove("hidden");
    $("#backupProgressFill").style.width = "0%";
    $("#backupProgressText").textContent = "Creating backup...";
    $("#createBackupBtn").disabled = true;

    // Fake progress since backend doesn't stream
    let progress = 0;
    const progressInterval = setInterval(() => {
      progress = Math.min(progress + 3, 90);
      $("#backupProgressFill").style.width = `${progress}%`;
    }, 500);

    try {
      const { res, data } = await api("/system/backups", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ backup_type: backupType, term, student }),
      });

      clearInterval(progressInterval);
      $("#backupProgressFill").style.width = "100%";

      if (res.ok) {
        $("#backupProgressText").textContent = `Backup created: ${data.filename} (${data.size_formatted})`;
        await loadBackups();
      } else {
        $("#backupProgressText").textContent = `Failed: ${data.detail || "Unknown error"}`;
      }
    } catch (err) {
      clearInterval(progressInterval);
      $("#backupProgressText").textContent = `Error: ${err.message}`;
    } finally {
      $("#createBackupBtn").disabled = false;
      setTimeout(() => {
        $("#backupProgress").classList.add("hidden");
      }, 3000);
    }
  }

  async function downloadBackup(filename) {
    try {
      const url = resolveUrl(`/system/backups/${encodeURIComponent(filename)}/download`);
      const fullUrl = url + (url.includes("?") ? "&" : "?") + `token=${token}`;
      window.open(fullUrl, "_blank");
    } catch (err) {
      alert(`Download error: ${err.message}`);
    }
  }

  async function deleteBackup(filename) {
    if (!confirm(`Delete backup "${filename}"?`)) return;

    try {
      const { res, data } = await api(`/system/backups/${encodeURIComponent(filename)}`, {
        method: "DELETE",
      });

      if (res.ok) {
        alert("Backup deleted.");
        loadBackups();
      } else {
        alert(`Failed: ${data.detail || data.message || "Unknown error"}`);
      }
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  }

  // ============================================================
  // Users Management
  // ============================================================
  let usersData = [];
  let selectedUsers = new Set();

  async function loadUsersView() {
    await loadUsersTerms();
    await loadUsers();
    setupUsersEventListeners();
  }

  async function loadUsersTerms() {
    try {
      const { res, data } = await api("/users/terms");
      if (!res.ok) return;

      const select = $("#usersTermFilter");
      select.innerHTML = '<option value="">All Terms</option>' +
        data.terms.map((t) => `<option value="${escapeHtml(t)}">${escapeHtml(t)}</option>`).join("");
    } catch (err) {
      console.error("Failed to load user terms:", err);
    }
  }

  async function loadUsers() {
    const term = $("#usersTermFilter")?.value || "";
    const status = $("#usersStatusFilter")?.value || "";
    const search = $("#usersSearchInput")?.value || "";

    let url = "/users?";
    if (term) url += `term=${encodeURIComponent(term)}&`;
    if (status === "suspended") url += "suspended=true&";
    if (status === "active") url += "suspended=false&";
    if (search) url += `search=${encodeURIComponent(search)}&`;

    try {
      const { res, data } = await api(url);
      if (!res.ok) return;

      usersData = data.users;
      renderUsersTable(usersData);
      $("#usersCount").textContent = `${data.total} user${data.total !== 1 ? 's' : ''}`;
    } catch (err) {
      console.error("Failed to load users:", err);
      $("#usersTableBody").innerHTML = '<tr><td colspan="8" class="muted">Failed to load users</td></tr>';
    }
  }

  function renderUsersTable(users) {
    const tbody = $("#usersTableBody");
    
    if (!users?.length) {
      tbody.innerHTML = '<tr><td colspan="8" class="muted">No users found</td></tr>';
      return;
    }

    tbody.innerHTML = users.map((u) => {
      const statusClass = u.is_suspended ? "warn" : "ok";
      const statusText = u.is_suspended ? "Suspended" : "Active";
      const diskPct = Math.round(u.disk_percent);
      const diskClass = diskPct > 80 ? "high" : diskPct > 50 ? "mid" : "low";
      const websiteIcon = u.public_html_exists ? "✓" : "—";
      const websiteClass = u.public_html_exists ? "ok" : "muted";

      return `
        <tr data-username="${escapeHtml(u.username)}">
          <td><input type="checkbox" class="user-checkbox" data-username="${escapeHtml(u.username)}"></td>
          <td>
            <a href="#" class="user-link" onclick="event.preventDefault(); app.showUserDetail('${escapeHtml(u.username)}')">${escapeHtml(u.username)}</a>
          </td>
          <td><span class="badge">${escapeHtml(u.term)}</span></td>
          <td><span class="status-badge ${statusClass}">${statusText}</span></td>
          <td>
            <div class="disk-bar">
              <div class="disk-bar-track">
                <div class="disk-bar-fill ${diskClass}" style="width: ${diskPct}%"></div>
              </div>
              <span class="disk-bar-text">${u.disk_used_formatted}</span>
            </div>
          </td>
          <td>${u.file_count}</td>
          <td><span class="${websiteClass}">${websiteIcon}</span></td>
          <td>
            <div class="action-btns">
              ${u.is_suspended
                ? `<button class="btn btn-xs" onclick="app.unsuspendUser('${escapeHtml(u.username)}')">Unsuspend</button>`
                : `<button class="btn btn-xs btn-danger" onclick="app.suspendUser('${escapeHtml(u.username)}')">Suspend</button>`
              }
            </div>
          </td>
        </tr>
      `;
    }).join("");

    // Reset selection
    selectedUsers.clear();
    updateBulkActions();
  }

  function setupUsersEventListeners() {
    // Filters
    $("#usersTermFilter")?.addEventListener("change", loadUsers);
    $("#usersStatusFilter")?.addEventListener("change", loadUsers);
    
    let searchTimeout;
    $("#usersSearchInput")?.addEventListener("input", () => {
      clearTimeout(searchTimeout);
      searchTimeout = setTimeout(loadUsers, 300);
    });

    // Refresh
    $("#refreshUsersBtn")?.addEventListener("click", loadUsers);

    // Select all checkbox
    $("#selectAllUsers")?.addEventListener("change", (e) => {
      const checked = e.target.checked;
      $$(".user-checkbox").forEach((cb) => {
        cb.checked = checked;
        const username = cb.dataset.username;
        if (checked) {
          selectedUsers.add(username);
        } else {
          selectedUsers.delete(username);
        }
      });
      updateBulkActions();
    });

    // Individual checkboxes (delegate)
    $("#usersTableBody")?.addEventListener("change", (e) => {
      if (e.target.classList.contains("user-checkbox")) {
        const username = e.target.dataset.username;
        if (e.target.checked) {
          selectedUsers.add(username);
        } else {
          selectedUsers.delete(username);
        }
        updateBulkActions();
      }
    });

    // Modal backdrop click
    $("#userDetailModal .modal-backdrop")?.addEventListener("click", closeUserModal);
  }

  function updateBulkActions() {
    const count = selectedUsers.size;
    const bulkEl = $("#usersBulkActions");
    const countEl = $("#selectedUsersCount");

    if (count > 0) {
      bulkEl?.classList.remove("hidden");
      if (countEl) countEl.textContent = `${count} selected`;
    } else {
      bulkEl?.classList.add("hidden");
    }
  }

  async function showUserDetail(username) {
    try {
      const { res, data } = await api(`/users/${encodeURIComponent(username)}`);
      if (!res.ok) {
        alert("Failed to load user details");
        return;
      }

      const diskPct = Math.round(data.disk_percent);
      const diskClass = diskPct > 80 ? "high" : diskPct > 50 ? "mid" : "low";

      $("#userDetailTitle").textContent = data.username;
      $("#userDetailBody").innerHTML = `
        <div class="user-detail-grid">
          <div class="user-detail-item">
            <span class="label">Term</span>
            <span class="value">${escapeHtml(data.term)}</span>
          </div>
          <div class="user-detail-item">
            <span class="label">Status</span>
            <span class="value">
              <span class="status-badge ${data.is_suspended ? 'warn' : 'ok'}">${data.is_suspended ? 'Suspended' : 'Active'}</span>
            </span>
          </div>
          <div class="user-detail-item">
            <span class="label">UID / GID</span>
            <span class="value">${data.uid} / ${data.gid}</span>
          </div>
          <div class="user-detail-item">
            <span class="label">Shell</span>
            <span class="value">${escapeHtml(data.shell)}</span>
          </div>
          <div class="user-detail-item full-width">
            <span class="label">Home Directory</span>
            <span class="value">${escapeHtml(data.home_dir)}</span>
          </div>
          <div class="user-detail-item">
            <span class="label">Disk Usage</span>
            <span class="value">
              <div class="disk-bar">
                <div class="disk-bar-track">
                  <div class="disk-bar-fill ${diskClass}" style="width: ${diskPct}%"></div>
                </div>
                <span class="disk-bar-text">${data.disk_used_formatted}${data.disk_quota_formatted ? ' / ' + data.disk_quota_formatted : ''}</span>
              </div>
            </span>
          </div>
          <div class="user-detail-item">
            <span class="label">Total Files</span>
            <span class="value">${data.file_count}</span>
          </div>
          <div class="user-detail-item">
            <span class="label">Website Files</span>
            <span class="value">${data.public_html_files} ${data.index_exists ? '(has index.html)' : ''}</span>
          </div>
          <div class="user-detail-item">
            <span class="label">Last Login</span>
            <span class="value">${data.last_login || 'Never'}</span>
          </div>
          <div class="user-detail-item full-width">
            <span class="label">Groups</span>
            <span class="value">${data.groups?.join(', ') || 'None'}</span>
          </div>
        </div>
        <div class="user-actions-row">
          ${data.is_suspended
            ? `<button class="btn" onclick="app.unsuspendUser('${escapeHtml(data.username)}'); app.closeUserModal();">Unsuspend</button>`
            : `<button class="btn btn-danger" onclick="app.suspendUser('${escapeHtml(data.username)}'); app.closeUserModal();">Suspend</button>`
          }
          <button class="btn" onclick="app.setUserQuota('${escapeHtml(data.username)}')">Set Quota</button>
          <button class="btn btn-danger" onclick="app.deleteUser('${escapeHtml(data.username)}')">Delete</button>
        </div>
      `;

      $("#userDetailModal").classList.remove("hidden");
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  }

  function closeUserModal() {
    $("#userDetailModal").classList.add("hidden");
  }

  async function suspendUser(username) {
    if (!confirm(`Suspend user ${username}?`)) return;

    try {
      const { res, data } = await api(`/users/${encodeURIComponent(username)}/suspend`, {
        method: "POST",
      });

      if (res.ok) {
        alert(data.message);
        loadUsers();
      } else {
        alert(`Failed: ${data.detail || "Unknown error"}`);
      }
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  }

  async function unsuspendUser(username) {
    if (!confirm(`Unsuspend user ${username}?`)) return;

    try {
      const { res, data } = await api(`/users/${encodeURIComponent(username)}/unsuspend`, {
        method: "POST",
      });

      if (res.ok) {
        alert(data.message);
        loadUsers();
      } else {
        alert(`Failed: ${data.detail || "Unknown error"}`);
      }
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  }

  async function setUserQuota(username) {
    const quotaMb = prompt(`Set quota for ${username} (in MB):`, "500");
    if (!quotaMb) return;

    const quota = parseInt(quotaMb, 10);
    if (isNaN(quota) || quota < 0) {
      alert("Invalid quota value");
      return;
    }

    try {
      const { res, data } = await api(`/users/${encodeURIComponent(username)}/quota`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ quota_mb: quota }),
      });

      if (res.ok) {
        alert(data.message);
        loadUsers();
      } else {
        alert(`Failed: ${data.detail || "Unknown error"}`);
      }
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  }

  async function deleteUser(username) {
    if (!confirm(`Are you sure you want to DELETE user ${username}? This cannot be undone.`)) return;
    
    const removeHome = confirm("Also remove home directory and all files?");

    try {
      const { res, data } = await api(`/users/${encodeURIComponent(username)}?remove_home=${removeHome}`, {
        method: "DELETE",
      });

      if (res.ok) {
        alert(data.message);
        closeUserModal();
        loadUsers();
      } else {
        alert(`Failed: ${data.detail || "Unknown error"}`);
      }
    } catch (err) {
      alert(`Error: ${err.message}`);
    }
  }

  async function bulkSuspendUsers() {
    if (selectedUsers.size === 0) return;
    if (!confirm(`Suspend ${selectedUsers.size} user(s)?`)) return;

    for (const username of selectedUsers) {
      try {
        await api(`/users/${encodeURIComponent(username)}/suspend`, { method: "POST" });
      } catch (err) {
        console.error(`Failed to suspend ${username}:`, err);
      }
    }

    alert("Bulk suspend complete");
    selectedUsers.clear();
    loadUsers();
  }

  async function bulkUnsuspendUsers() {
    if (selectedUsers.size === 0) return;
    if (!confirm(`Unsuspend ${selectedUsers.size} user(s)?`)) return;

    for (const username of selectedUsers) {
      try {
        await api(`/users/${encodeURIComponent(username)}/unsuspend`, { method: "POST" });
      } catch (err) {
        console.error(`Failed to unsuspend ${username}:`, err);
      }
    }

    alert("Bulk unsuspend complete");
    selectedUsers.clear();
    loadUsers();
  }

  function setupSystemEventListeners() {
    // Refresh buttons
    $("#refreshServicesBtn")?.addEventListener("click", loadServices);
    $("#refreshProcessesBtn")?.addEventListener("click", refreshSystemStats);

    // Log controls
    $("#logSelect")?.addEventListener("change", (e) => {
      const logKey = e.target.value;
      if (logKey) {
        viewLog(logKey);
      }
    });

    $("#logSearchBtn")?.addEventListener("click", () => {
      const logKey = $("#logSelect").value;
      const pattern = $("#logSearch").value.trim();
      if (logKey && pattern) {
        searchLog(logKey, pattern);
      }
    });

    $("#logStreamBtn")?.addEventListener("click", () => {
      const logKey = $("#logSelect").value;
      if (!logKey) {
        alert("Select a log file first.");
        return;
      }
      if (logWebSocket) {
        stopLogStream();
      } else {
        startLogStream(logKey);
      }
    });

    // View Log button (similar to logSelect change but explicit)
    $("#logViewBtn")?.addEventListener("click", () => {
      const logKey = $("#logSelect").value;
      if (logKey) {
        viewLog(logKey);
      }
    });

    // Backup controls - toggle label wrappers
    $("#backupType")?.addEventListener("change", (e) => {
      const type = e.target.value;
      $("#backupTermLabel")?.classList.toggle("hidden", type === "full");
      $("#backupStudentLabel")?.classList.toggle("hidden", type !== "student");
    });

    $("#backupTerm")?.addEventListener("change", (e) => {
      const term = e.target.value;
      if (term && $("#backupType").value === "student") {
        loadBackupStudents(term);
      }
    });

    $("#createBackupBtn")?.addEventListener("click", createBackup);
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

    // Roster Import
    setupRosterUpload();

    // System Monitoring
    setupSystemEventListeners();

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
  // DNS Management View
  // ============================================================
  let dnsRecords = [];

  async function loadDnsView() {
    await Promise.all([loadDnsInfo(), loadDnsRecords(), loadCertInfo()]);
    setupDnsEventListeners();
  }

  async function loadDnsInfo() {
    try {
      const { res, data } = await api("/dns/info");
      if (!res.ok) return;

      $("#dnsDomain").textContent = data.domain;
      $("#dnsRecordCount").textContent = data.record_count;
      $("#dnsSubdomainCount").textContent = data.subdomains.length;
    } catch (err) {
      console.error("Failed to load DNS info:", err);
    }
  }

  async function loadDnsRecords() {
    try {
      const { res, data } = await api("/dns/records");
      if (!res.ok) return;

      dnsRecords = data;
      renderDnsTable(dnsRecords);
    } catch (err) {
      console.error("Failed to load DNS records:", err);
      $("#dnsTableBody").innerHTML = '<tr><td colspan="5" class="muted">Failed to load records</td></tr>';
    }
  }

  async function loadCertInfo() {
    try {
      const { res, data } = await api("/dns/certificate");
      if (!res.ok) return;

      const certCard = $("#certStatus");
      if (!certCard) return;

      if (!data.installed) {
        certCard.innerHTML = '<p class="muted">No SSL certificate installed</p>';
        return;
      }

      const statusClass = data.status === "valid" ? "ok" : data.status === "expiring" ? "warn" : "crit";
      const statusIcon = data.status === "valid" ? "✓" : data.status === "expiring" ? "⚠" : "✗";

      certCard.innerHTML = `
        <div class="cert-info">
          <div class="cert-domain">
            <span class="status-chip ${statusClass}">${statusIcon} ${data.domain}</span>
          </div>
          <p class="muted">Issued by: ${escapeHtml(data.issuer)}</p>
          <p>Expires: ${new Date(data.valid_to).toLocaleDateString()} (${data.days_remaining} days)</p>
          ${data.is_wildcard ? '<span class="badge">Wildcard</span>' : ''}
        </div>
      `;
    } catch (err) {
      console.error("Failed to load certificate info:", err);
    }
  }

  function renderDnsTable(records) {
    const tbody = $("#dnsTableBody");
    const filter = $("#dnsTypeFilter")?.value || "";
    const search = $("#dnsSearchInput")?.value?.toLowerCase() || "";

    let filtered = records;
    if (filter) filtered = filtered.filter((r) => r.type === filter);
    if (search) filtered = filtered.filter((r) => 
      r.name.toLowerCase().includes(search) || r.content.toLowerCase().includes(search)
    );

    if (!filtered?.length) {
      tbody.innerHTML = '<tr><td colspan="5" class="muted">No DNS records found</td></tr>';
      return;
    }

    tbody.innerHTML = filtered.map((r) => {
      const typeClass = getRecordTypeClass(r.type);
      const fqdn = r.name === "@" ? "cybearlab.cloud" : r.name === "*" ? "*.cybearlab.cloud" : `${r.name}.cybearlab.cloud`;

      return `
        <tr data-id="${escapeHtml(r.id)}">
          <td><span class="dns-type ${typeClass}">${escapeHtml(r.type)}</span></td>
          <td><code>${escapeHtml(fqdn)}</code></td>
          <td><code>${escapeHtml(r.content)}</code></td>
          <td>${r.ttl}s</td>
          <td>
            <button class="btn-icon" onclick="app.deleteDnsRecord('${escapeHtml(r.id)}')" title="Delete">🗑️</button>
          </td>
        </tr>
      `;
    }).join("");
  }

  function getRecordTypeClass(type) {
    switch (type) {
      case "A": return "type-a";
      case "AAAA": return "type-aaaa";
      case "CNAME": return "type-cname";
      case "TXT": return "type-txt";
      case "MX": return "type-mx";
      default: return "";
    }
  }

  function setupDnsEventListeners() {
    // Filter changes
    $("#dnsTypeFilter")?.addEventListener("change", () => renderDnsTable(dnsRecords));
    $("#dnsSearchInput")?.addEventListener("input", () => renderDnsTable(dnsRecords));

    // Add record form
    $("#addDnsRecordBtn")?.addEventListener("click", showAddRecordModal);
    $("#dnsRecordForm")?.addEventListener("submit", handleAddDnsRecord);
    $("#closeDnsModal")?.addEventListener("click", closeDnsModal);
  }

  function showAddRecordModal() {
    $("#dnsRecordModal")?.classList.add("active");
    $("#dnsRecordForm")?.reset();
  }

  function closeDnsModal() {
    $("#dnsRecordModal")?.classList.remove("active");
  }

  async function handleAddDnsRecord(e) {
    e.preventDefault();
    const form = e.target;
    const data = {
      name: form.elements.name.value.trim(),
      type: form.elements.type.value,
      content: form.elements.content.value.trim(),
      ttl: parseInt(form.elements.ttl?.value) || 3600,
    };

    if (!data.name || !data.content) {
      alert("Name and content are required");
      return;
    }

    try {
      const { res } = await api("/dns/records", {
        method: "POST",
        body: JSON.stringify(data),
      });

      if (res.ok) {
        closeDnsModal();
        await loadDnsRecords();
      } else {
        alert("Failed to create DNS record");
      }
    } catch (err) {
      console.error("Error creating DNS record:", err);
      alert("Failed to create DNS record");
    }
  }

  async function deleteDnsRecord(recordId) {
    if (!confirm("Delete this DNS record?")) return;

    try {
      const { res } = await api(`/dns/records/${recordId}`, { method: "DELETE" });
      if (res.ok) {
        await loadDnsRecords();
      } else {
        alert("Failed to delete record");
      }
    } catch (err) {
      console.error("Error deleting DNS record:", err);
      alert("Failed to delete record");
    }
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
    controlService,
    downloadBackup,
    deleteBackup,
    showUserDetail,
    closeUserModal,
    suspendUser,
    unsuspendUser,
    setUserQuota,
    deleteUser,
    bulkSuspendUsers,
    bulkUnsuspendUsers,
    deleteDnsRecord,
    closeDnsModal,
  };

  // Start
  init();
})();
