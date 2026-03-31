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
    "/files": "files",
    "/databases": "databases",
    "/ftp": "ftp",
    "/dns": "dns",
    "/cron": "cron",
    "/security": "security",
    "/ssl": "ssl",
    "/updates": "updates",
    "/deploy": "deploy",
    "/reports": "reports",
    "/audit": "audit",
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
    if (route === "files") loadFilesView();
    if (route === "databases") loadDatabasesView();
    if (route === "ftp") loadFtpView();
    if (route === "dns") loadDnsView();
    if (route === "cron") loadCronView();
    if (route === "security") loadSecurityView();
    if (route === "ssl") loadSslView();
    if (route === "updates") loadUpdatesView();
    if (route === "deploy") loadDeployView();
    if (route === "audit") loadAuditView();
    if (route === "settings") loadSettingsView();
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
      showToast("Enter a URL to grade.", "warn");
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
        showToast(`Failed to start grading: ${create.data?.detail || "Unknown error"}`, "error");
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
  // Grader File Picker
  // ============================================================
  const DOMAIN_BASE = "cybearlab.cloud";
  let pickerUser = "";
  let pickerPath = "";
  let pickerSelectedPath = "";

  function openGradeFilePicker() {
    $("#gradeFilePicker").classList.remove("hidden");
    loadPickerUsers();
  }

  window.app = window.app || {};
  window.app.closeGradeFilePicker = closeGradeFilePicker;

  function closeGradeFilePicker() {
    $("#gradeFilePicker").classList.add("hidden");
    pickerUser = "";
    pickerPath = "";
    pickerSelectedPath = "";
    updatePickerPreview();
  }

  async function loadPickerUsers() {
    try {
      const { res, data } = await api("/users?");
      if (!res.ok) return;

      const select = $("#pickerUserSelect");
      select.innerHTML = '<option value="">Select a student...</option>' +
        data.users.map((u) => `<option value="${escapeHtml(u.username)}">${escapeHtml(u.username)}</option>`).join("");
    } catch (err) {
      console.error("Failed to load users:", err);
    }
  }

  function setupGradeFilePicker() {
    $("#pickerUserSelect")?.addEventListener("change", (e) => {
      pickerUser = e.target.value;
      pickerPath = "";
      pickerSelectedPath = "";
      if (pickerUser) {
        loadPickerDirectory();
      } else {
        $("#pickerList").innerHTML = '<p class="muted">Select a student to browse.</p>';
      }
      updatePickerPreview();
    });

    $("#pickerUpBtn")?.addEventListener("click", () => {
      if (pickerPath) {
        const parts = pickerPath.split("/").filter(Boolean);
        parts.pop();
        pickerPath = parts.join("/");
        pickerSelectedPath = pickerPath;
        loadPickerDirectory();
        updatePickerPreview();
      }
    });

    $("#pickerHomeBtn")?.addEventListener("click", () => {
      pickerPath = "";
      pickerSelectedPath = "";
      loadPickerDirectory();
      updatePickerPreview();
    });

    $("#pickerSelectBtn")?.addEventListener("click", () => {
      if (!pickerUser) {
        showToast("Select a student first", "warn");
        return;
      }
      const url = buildPickerUrl();
      $("#gradeUrl").value = url;
      $("#gradeStudent").value = pickerUser;
      closeGradeFilePicker();
      showToast(`Selected: ${url}`, "success");
    });
  }

  async function loadPickerDirectory() {
    if (!pickerUser) return;

    const list = $("#pickerList");
    list.innerHTML = '<p class="muted">Loading...</p>';

    try {
      const path = pickerPath ? `?path=${encodeURIComponent(pickerPath)}` : "";
      const { res, data } = await api(`/files/browse/${encodeURIComponent(pickerUser)}${path}`);

      if (!res.ok) {
        list.innerHTML = `<p class="muted">Error: ${data.detail || "Failed to load"}</p>`;
        return;
      }

      // Update breadcrumb
      updatePickerBreadcrumb(data.path);
      $("#pickerCurrentPath").textContent = "/" + (data.path === "/" ? "" : data.path);

      // Filter to directories only (for picking project folders), but also show files for context
      const items = data.items || [];

      if (!items.length) {
        list.innerHTML = '<p class="muted">Empty directory</p>';
        return;
      }

      list.innerHTML = items.map((item) => {
        const icon = item.type === "directory" ? "📁" : getFileIcon(item.name);
        const isSelected = item.type === "directory" && item.path === pickerSelectedPath;
        return `
          <div class="picker-item ${item.type}${isSelected ? " selected" : ""}" 
               data-path="${escapeHtml(item.path)}" 
               data-type="${item.type}" 
               data-name="${escapeHtml(item.name)}">
            <span class="picker-item-icon">${icon}</span>
            <span class="picker-item-name">${escapeHtml(item.name)}</span>
            <span class="picker-item-meta">${item.type === "directory" ? "folder" : item.size_formatted}</span>
          </div>
        `;
      }).join("");

      // Attach click handlers
      list.querySelectorAll(".picker-item").forEach(el => {
        el.addEventListener("click", () => handlePickerItemClick(el));
        el.addEventListener("dblclick", () => handlePickerItemDblClick(el));
      });

      // Enable select button
      $("#pickerSelectBtn").disabled = false;
    } catch (err) {
      console.error("Picker load error:", err);
      list.innerHTML = '<p class="muted">Error loading files</p>';
    }
  }

  function handlePickerItemClick(el) {
    const type = el.dataset.type;
    const path = el.dataset.path;

    // Remove selection from all items
    $$(".picker-item.selected").forEach(item => item.classList.remove("selected"));

    if (type === "directory") {
      // Select this directory
      el.classList.add("selected");
      pickerSelectedPath = path;
    } else {
      // Files can't be selected, just clear selection
      pickerSelectedPath = pickerPath;
    }
    updatePickerPreview();
  }

  function handlePickerItemDblClick(el) {
    const type = el.dataset.type;
    const path = el.dataset.path;

    if (type === "directory") {
      // Navigate into directory
      pickerPath = path;
      pickerSelectedPath = path;
      loadPickerDirectory();
      updatePickerPreview();
    }
  }

  function updatePickerBreadcrumb(currentPath) {
    const breadcrumb = $("#pickerBreadcrumb");
    if (!currentPath || currentPath === "/") {
      breadcrumb.innerHTML = `<span class="breadcrumb-item">/ (root)</span>`;
      return;
    }

    const parts = currentPath.split("/").filter(Boolean);
    let pathSoFar = "";
    
    breadcrumb.innerHTML = `<span class="breadcrumb-sep">/</span>` + parts.map((part, idx) => {
      pathSoFar += "/" + part;
      const thisPath = pathSoFar.substring(1); // Remove leading /
      return `<span class="breadcrumb-item" data-path="${escapeHtml(thisPath)}">${escapeHtml(part)}</span>`;
    }).join('<span class="breadcrumb-sep">/</span>');
  }

  function buildPickerUrl() {
    let path = pickerSelectedPath || pickerPath || "";
    // Remove leading/trailing slashes
    path = path.replace(/^\/+|\/+$/g, "");
    if (path) {
      return `https://${pickerUser}.${DOMAIN_BASE}/${path}`;
    }
    return `https://${pickerUser}.${DOMAIN_BASE}/`;
  }

  function updatePickerPreview() {
    const preview = $("#pickerPreviewUrl");
    if (!pickerUser) {
      preview.textContent = "—";
      return;
    }
    preview.textContent = buildPickerUrl();
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
      showToast("Username is required for this action.", "warn");
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
  // Toast Notification System
  // ============================================================
  function showToast(message, type = "info", duration = 4000) {
    const container = $("#toastContainer");
    if (!container) return;

    const toast = document.createElement("div");
    toast.className = `toast toast-${type}`;

    const icons = { success: "✓", error: "✗", warn: "⚠", info: "ⓘ" };
    toast.innerHTML = `
      <span class="toast-icon">${icons[type] || icons.info}</span>
      <span class="toast-message">${escapeHtml(message)}</span>
      <button class="toast-close" onclick="this.parentElement.remove()">&times;</button>
    `;

    container.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add("toast-visible"));

    setTimeout(() => {
      toast.classList.remove("toast-visible");
      toast.addEventListener("transitionend", () => toast.remove());
    }, duration);
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
      showToast("Please upload a CSV file.", "warn");
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
        showToast(`${data.detail || "Failed to parse roster"}`, "error");
        return;
      }

      if (data.errors?.length) {
        showToast(`CSV has ${data.errors.length} error(s)`, "error");
        return;
      }

      // Store preview data
      rosterPreviewData = data;
      
      // Show preview
      renderRosterPreview(data);
    } catch (err) {
      showToast(`Upload failed: ${err.message}`, "error");
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
      showToast("No valid entries to import.", "warn");
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
        showToast(`Import failed: ${data.detail || "Unknown error"}`, "error");
        resetRosterUI();
        return;
      }

      // Show results
      renderRosterResults(data);
    } catch (err) {
      showToast(`Import failed: ${err.message}`, "error");
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
        showToast(data.message, "success");
        loadServices();
      } else {
        showToast(`Failed: ${data.detail || data.message || "Unknown error"}`, "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
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
      showToast("Please select a term.", "warn");
      return;
    }
    if (backupType === "student" && (!term || !student)) {
      showToast("Please select a term and student.", "warn");
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
      showToast(`Download error: ${err.message}`, "error");
    }
  }

  async function deleteBackup(filename) {
    if (!confirm(`Delete backup "${filename}"?`)) return;

    try {
      const { res, data } = await api(`/system/backups/${encodeURIComponent(filename)}`, {
        method: "DELETE",
      });

      if (res.ok) {
        showToast("Backup deleted.", "success");
        loadBackups();
      } else {
        showToast(`Failed: ${data.detail || data.message || "Unknown error"}`, "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
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
        showToast("Failed to load user details", "error");
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
      showToast(`Error: ${err.message}`, "error");
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
        showToast(data.message, "success");
        loadUsers();
      } else {
        showToast(`Failed: ${data.detail || "Unknown error"}`, "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function unsuspendUser(username) {
    if (!confirm(`Unsuspend user ${username}?`)) return;

    try {
      const { res, data } = await api(`/users/${encodeURIComponent(username)}/unsuspend`, {
        method: "POST",
      });

      if (res.ok) {
        showToast(data.message, "success");
        loadUsers();
      } else {
        showToast(`Failed: ${data.detail || "Unknown error"}`, "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function setUserQuota(username) {
    const quotaMb = prompt(`Set quota for ${username} (in MB):`, "500");
    if (!quotaMb) return;

    const quota = parseInt(quotaMb, 10);
    if (isNaN(quota) || quota < 0) {
      showToast("Invalid quota value", "warn");
      return;
    }

    try {
      const { res, data } = await api(`/users/${encodeURIComponent(username)}/quota`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ quota_mb: quota }),
      });

      if (res.ok) {
        showToast(data.message, "success");
        loadUsers();
      } else {
        showToast(`Failed: ${data.detail || "Unknown error"}`, "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
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
        showToast(data.message, "success");
        closeUserModal();
        loadUsers();
      } else {
        showToast(`Failed: ${data.detail || "Unknown error"}`, "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
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

    showToast("Bulk suspend complete", "success");
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

    showToast("Bulk unsuspend complete", "success");
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
        showToast("Select a log file first.", "warn");
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
    $("#gradeBrowseBtn")?.addEventListener("click", openGradeFilePicker);
    setupGradeFilePicker();

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

    // Audit filters
    $("#auditFilterBtn")?.addEventListener("click", () => loadAuditEvents());
    $("#auditClearBtn")?.addEventListener("click", () => {
      $("#auditFilterAction").value = "";
      $("#auditFilterActor").value = "";
      loadAuditEvents();
    });

    // Settings - save grader config
    $("#settingsSaveGraderBtn")?.addEventListener("click", saveGraderSettings);

    // Cron Management
    $("#cronLoadBtn")?.addEventListener("click", () => {
      loadCronJobs($("#cronUsername").value.trim());
    });
    $("#addCronBtn")?.addEventListener("click", () => showCronModal());
    $("#cronForm")?.addEventListener("submit", saveCronJob);
    $("#cronModal .modal-close")?.addEventListener("click", closeCronModal);
    $("#cronModal .modal-backdrop")?.addEventListener("click", closeCronModal);

    // Security Management
    $("#sshLoadBtn")?.addEventListener("click", () => {
      loadSshKeys($("#sshUsername").value.trim());
    });
    $("#addSshKeyBtn")?.addEventListener("click", addSshKey);
    $("#banIPBtn")?.addEventListener("click", banIP);
    $("#unbanIPBtn")?.addEventListener("click", unbanIP);
    $("#ufwEnableBtn")?.addEventListener("click", enableUfw);
    $("#ufwDisableBtn")?.addEventListener("click", disableUfw);
    $("#addUfwRuleBtn")?.addEventListener("click", addUfwRule);
    $("#setModsecModeBtn")?.addEventListener("click", setModSecurityMode);

    // SSL Management
    $("#requestCertBtn")?.addEventListener("click", showSslRequestModal);
    $("#renewAllCertsBtn")?.addEventListener("click", renewAllCerts);
    $("#sslRequestForm")?.addEventListener("submit", requestCertificate);
    $("#sslRequestModal .modal-close")?.addEventListener("click", closeSslModal);
    $("#sslRequestModal .modal-backdrop")?.addEventListener("click", closeSslModal);
    $("#sslDetailModal .modal-close")?.addEventListener("click", closeSslDetailModal);
    $("#sslDetailModal .modal-backdrop")?.addEventListener("click", closeSslDetailModal);
  }

  // ============================================================
  // Audit Log View
  // ============================================================
  function loadAuditView() {
    loadAuditEvents();
  }

  async function loadAuditEvents() {
    const timeline = $("#auditTimeline");
    timeline.innerHTML = '<p class="muted">Loading audit events...</p>';

    const actionType = $("#auditFilterAction")?.value || "";
    const actor = $("#auditFilterActor")?.value?.trim() || "";

    let path = "/audit/events?";
    if (actionType) path += `actionType=${encodeURIComponent(actionType)}&`;
    if (actor) path += `actor=${encodeURIComponent(actor)}&`;

    try {
      const { res, data } = await api(path);
      if (!res.ok) {
        timeline.innerHTML = '<p class="muted">Failed to load audit events.</p>';
        return;
      }

      const items = data.items || [];
      if (!items.length) {
        timeline.innerHTML = '<p class="muted">No audit events found.</p>';
        return;
      }

      timeline.innerHTML = items.map((evt) => {
        const date = new Date(evt.created_at);
        const timeStr = date.toLocaleString();
        const statusClass = evt.status === "success" || evt.status === "completed"
          ? "ok" : evt.status === "failed" ? "low" : "neutral";
        const actionLabel = formatActionType(evt.action_type);
        const icon = getAuditIcon(evt.action_type);

        return `
          <div class="audit-event">
            <div class="audit-event-icon">${icon}</div>
            <div class="audit-event-body">
              <div class="audit-event-header">
                <strong>${escapeHtml(actionLabel)}</strong>
                <span class="pill ${statusClass}" style="font-size:0.72rem;padding:3px 8px">${escapeHtml(evt.status)}</span>
              </div>
              <p class="audit-event-meta">
                <span class="audit-actor">${escapeHtml(evt.actor)}</span>
                ${evt.entity_id ? `<span class="muted">\u2192 ${escapeHtml(evt.entity_id)}</span>` : ""}
              </p>
              <span class="audit-event-time">${timeStr}</span>
            </div>
          </div>
        `;
      }).join("");
    } catch (err) {
      console.error("Failed to load audit events:", err);
      timeline.innerHTML = '<p class="muted">Failed to load audit events.</p>';
    }
  }

  function formatActionType(type) {
    return (type || "unknown").replace(/[._]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  }

  function getAuditIcon(type) {
    const icons = {
      "admin.action.create": "\ud83d\udee0\ufe0f",
      "admin.action.read": "\ud83d\udee0\ufe0f",
      "admin.upload.roster": "\ud83d\udccb",
      "grader.run.create": "\ud83d\udcca",
      "grader.run.list": "\ud83d\udcca",
      "grader.run.read": "\ud83d\udcca",
      "auth.login": "\ud83d\udd11",
      "system.backup.create": "\ud83d\udce6",
      "system.backup.delete": "\ud83d\udce6",
      "user.suspend": "\u26d4",
      "user.unsuspend": "\u2705",
      "user.delete": "\ud83d\uddd1\ufe0f",
      "user.quota": "\ud83d\udccf",
      "dns.record.create": "\ud83c\udf10",
      "dns.record.delete": "\ud83c\udf10",
      "service.action": "\u2699\ufe0f",
    };
    return icons[type] || "\ud83d\udcdd";
  }

  // ============================================================
  // Settings View
  // ============================================================
  function loadSettingsView() {
    // Show current API endpoint
    const endpointEl = $("#settingsEndpoint");
    if (endpointEl) endpointEl.textContent = currentApiBase || "auto-detected";

    const versionEl = $("#settingsVersion");
    if (versionEl) versionEl.textContent = "1.0.0";

    // Load saved grader settings from localStorage
    const saved = JSON.parse(localStorage.getItem("graderSettings") || "{}");
    if (saved.maxPages) $("#settingsMaxPages").value = saved.maxPages;
    if (saved.timeout) $("#settingsTimeout").value = saved.timeout;
    if (saved.concurrency) $("#settingsConcurrency").value = saved.concurrency;

    // Check connection status
    checkSettingsStatus();
  }

  async function checkSettingsStatus() {
    const apiPill = $("#settingsApiStatus");
    const dbPill = $("#settingsDbStatus");

    try {
      const { res, data } = await api("/health");
      if (res.ok) {
        apiPill.textContent = "Connected";
        apiPill.className = "pill ok";
        dbPill.textContent = data.database === "ok" ? "Connected" : "Issue";
        dbPill.className = `pill ${data.database === "ok" ? "ok" : "warn"}`;
      } else {
        apiPill.textContent = "Unreachable";
        apiPill.className = "pill warn";
        dbPill.textContent = "Unknown";
        dbPill.className = "pill neutral";
      }
    } catch {
      apiPill.textContent = "Unreachable";
      apiPill.className = "pill warn";
      dbPill.textContent = "Unknown";
      dbPill.className = "pill neutral";
    }
  }

  function saveGraderSettings() {
    const settings = {
      maxPages: parseInt($("#settingsMaxPages").value) || 30,
      timeout: parseInt($("#settingsTimeout").value) || 15,
      concurrency: parseInt($("#settingsConcurrency").value) || 3,
    };
    localStorage.setItem("graderSettings", JSON.stringify(settings));
    showToast("Grader settings saved", "success");
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
    $("#dnsRecordModal")?.classList.remove("hidden");
    $("#dnsRecordForm")?.reset();
  }

  function closeDnsModal() {
    $("#dnsRecordModal")?.classList.add("hidden");
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
      showToast("Name and content are required", "warn");
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
        showToast("DNS record created", "success");
      } else {
        showToast("Failed to create DNS record", "error");
      }
    } catch (err) {
      console.error("Error creating DNS record:", err);
      showToast("Failed to create DNS record", "error");
    }
  }

  async function deleteDnsRecord(recordId) {
    if (!confirm("Delete this DNS record?")) return;

    try {
      const { res } = await api(`/dns/records/${recordId}`, { method: "DELETE" });
      if (res.ok) {
        await loadDnsRecords();
        showToast("DNS record deleted", "success");
      } else {
        showToast("Failed to delete record", "error");
      }
    } catch (err) {
      console.error("Error deleting DNS record:", err);
      showToast("Failed to delete record", "error");
    }
  }

  // ============================================================
  // File Manager
  // ============================================================
  let filesCurrentUser = "";
  let filesCurrentPath = "";
  let filesSelectedItem = null;
  let filesNewType = "file"; // "file" or "folder"

  async function loadFilesView() {
    await loadFilesUsers();
    setupFilesEventListeners();
  }

  async function loadFilesUsers() {
    try {
      const { res, data } = await api("/users?");
      if (!res.ok) return;

      const select = $("#filesUserSelect");
      select.innerHTML = '<option value="">Select a user...</option>' +
        data.users.map((u) => `<option value="${escapeHtml(u.username)}">${escapeHtml(u.username)} (${escapeHtml(u.term)})</option>`).join("");
    } catch (err) {
      console.error("Failed to load users:", err);
    }
  }

  function setupFilesEventListeners() {
    // User selection
    $("#filesUserSelect")?.addEventListener("change", (e) => {
      filesCurrentUser = e.target.value;
      filesCurrentPath = "";
      if (filesCurrentUser) {
        loadFilesDirectory();
      } else {
        $("#filesList").innerHTML = '<p class="muted">Select a user to browse files.</p>';
      }
    });

    // Navigation buttons
    $("#filesUpBtn")?.addEventListener("click", () => {
      if (filesCurrentPath) {
        const parts = filesCurrentPath.split("/").filter(Boolean);
        parts.pop();
        filesCurrentPath = parts.join("/");
        loadFilesDirectory();
      }
    });

    $("#filesHomeBtn")?.addEventListener("click", () => {
      filesCurrentPath = "";
      loadFilesDirectory();
    });

    $("#filesRefreshBtn")?.addEventListener("click", loadFilesDirectory);

    // New file/folder buttons
    $("#filesNewFileBtn")?.addEventListener("click", () => showFilesNewModal("file"));
    $("#filesNewFolderBtn")?.addEventListener("click", () => showFilesNewModal("folder"));
    $("#filesNewCreateBtn")?.addEventListener("click", handleFilesCreate);

    // Upload
    $("#filesUploadBtn")?.addEventListener("click", () => {
      if (!filesCurrentUser) {
        showToast("Select a user first", "warn");
        return;
      }
      $("#filesUploadInput").click();
    });

    $("#filesUploadInput")?.addEventListener("change", handleFilesUpload);

    // Modal actions
    $("#fileEditorSaveBtn")?.addEventListener("click", handleFileSave);
    $("#filesChmodApplyBtn")?.addEventListener("click", handleChmodApply);
    $("#filesRenameApplyBtn")?.addEventListener("click", handleRenameApply);
  }

  async function loadFilesDirectory() {
    if (!filesCurrentUser) return;

    const list = $("#filesList");
    list.innerHTML = '<p class="muted">Loading...</p>';

    try {
      const path = filesCurrentPath ? `?path=${encodeURIComponent(filesCurrentPath)}` : "";
      const { res, data } = await api(`/files/browse/${encodeURIComponent(filesCurrentUser)}${path}`);

      if (!res.ok) {
        list.innerHTML = `<p class="muted">Error: ${data.detail || "Failed to load"}</p>`;
        return;
      }

      // Update breadcrumb
      updateFilesBreadcrumb(data.path);

      // Update stats
      $("#filesStats").textContent = `${data.total_items} items, ${data.total_size_formatted}`;
      $("#filesItemCount").textContent = `${data.total_items} items`;
      $("#filesTotalSize").textContent = data.total_size_formatted;
      $("#filesCurrentPath").textContent = "/" + (data.path === "/" ? "" : data.path);

      // Render files list
      if (!data.items?.length) {
        list.innerHTML = '<p class="muted">Empty directory</p>';
        return;
      }

      list.innerHTML = data.items.map((item) => {
        const icon = item.type === "directory" ? "📁" : getFileIcon(item.name);
        const sizeText = item.type === "directory" ? "-" : item.size_formatted;
        const date = new Date(item.modified).toLocaleDateString();
        const time = new Date(item.modified).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
        
        return `
          <div class="file-item ${item.type}" data-path="${escapeHtml(item.path)}" data-type="${item.type}" data-name="${escapeHtml(item.name)}">
            <div class="file-item-icon">${icon}</div>
            <div class="file-item-name">${escapeHtml(item.name)}</div>
            <div class="file-item-size">${sizeText}</div>
            <div class="file-item-modified">${date} ${time}</div>
            <div class="file-item-perms mono">${item.permissions}</div>
            <div class="file-item-actions">
              ${item.type === "file" && item.is_text ? `<button class="btn-icon" onclick="event.stopPropagation(); app.editFile('${escapeHtml(item.path)}')" title="Edit">✏️</button>` : ""}
              ${item.type === "file" ? `<button class="btn-icon" onclick="event.stopPropagation(); app.downloadFile('${escapeHtml(item.path)}')" title="Download">⬇️</button>` : ""}
              <button class="btn-icon" onclick="event.stopPropagation(); app.showFileProps('${escapeHtml(item.path)}')" title="Properties">ℹ️</button>
              <button class="btn-icon" onclick="event.stopPropagation(); app.renameFile('${escapeHtml(item.path)}', '${escapeHtml(item.name)}')" title="Rename">✏️</button>
              <button class="btn-icon" onclick="event.stopPropagation(); app.chmodFile('${escapeHtml(item.path)}')" title="Permissions">🔒</button>
              <button class="btn-icon danger" onclick="event.stopPropagation(); app.deleteFile('${escapeHtml(item.path)}', '${item.type}')" title="Delete">🗑️</button>
            </div>
          </div>
        `;
      }).join("");

      // Click handlers for navigation
      $$(".file-item").forEach((el) => {
        el.addEventListener("dblclick", () => {
          const type = el.dataset.type;
          const path = el.dataset.path;
          if (type === "directory") {
            filesCurrentPath = path;
            loadFilesDirectory();
          }
        });
      });

    } catch (err) {
      console.error("Failed to load directory:", err);
      list.innerHTML = '<p class="muted">Error loading directory</p>';
    }
  }

  function getFileIcon(name) {
    const ext = name.split(".").pop()?.toLowerCase();
    const icons = {
      html: "🌐", htm: "🌐",
      css: "🎨",
      js: "📜",
      json: "📋",
      php: "🐘",
      py: "🐍",
      txt: "📝", md: "📝",
      jpg: "🖼️", jpeg: "🖼️", png: "🖼️", gif: "🖼️", webp: "🖼️", svg: "🖼️",
      pdf: "📕",
      zip: "📦", tar: "📦", gz: "📦",
      sh: "⚡",
      log: "📋",
    };
    return icons[ext] || "📄";
  }

  function updateFilesBreadcrumb(path) {
    const crumb = $("#filesBreadcrumb");
    const parts = path === "/" ? [] : path.split("/").filter(Boolean);
    
    let html = `<span class="breadcrumb-item" onclick="app.navigateToPath('')">🏠 ${escapeHtml(filesCurrentUser)}</span>`;
    let cumulative = "";
    
    for (const part of parts) {
      cumulative += "/" + part;
      const pathCopy = cumulative.slice(1); // Remove leading slash
      html += ` / <span class="breadcrumb-item" onclick="app.navigateToPath('${escapeHtml(pathCopy)}')">${escapeHtml(part)}</span>`;
    }
    
    crumb.innerHTML = html;
  }

  function navigateToPath(path) {
    filesCurrentPath = path;
    loadFilesDirectory();
  }

  async function editFile(path) {
    try {
      const { res, data } = await api(`/files/read/${encodeURIComponent(filesCurrentUser)}?path=${encodeURIComponent(path)}`);
      
      if (!res.ok) {
        showToast(data.detail || "Failed to read file", "error");
        return;
      }

      $("#fileEditorTitle").textContent = `Edit: ${data.name}`;
      $("#fileEditorContent").value = data.content;
      $("#fileEditorInfo").textContent = `${data.size} bytes | ${data.encoding} | ${data.mime_type}`;
      $("#fileEditorModal").classList.remove("hidden");
      
      // Store current editing file
      $("#fileEditorModal").dataset.path = path;
      
      // Focus editor
      setTimeout(() => $("#fileEditorContent").focus(), 100);
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  function closeFileEditor() {
    $("#fileEditorModal").classList.add("hidden");
    $("#fileEditorContent").value = "";
  }

  async function handleFileSave() {
    const path = $("#fileEditorModal").dataset.path;
    const content = $("#fileEditorContent").value;

    try {
      const { res, data } = await api(`/files/write/${encodeURIComponent(filesCurrentUser)}?path=${encodeURIComponent(path)}`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ content }),
      });

      if (res.ok) {
        showToast("File saved", "success");
        closeFileEditor();
        loadFilesDirectory();
      } else {
        showToast(data.detail || "Failed to save", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function downloadFile(path) {
    try {
      const url = resolveUrl(`/files/download/${encodeURIComponent(filesCurrentUser)}?path=${encodeURIComponent(path)}`);
      const fullUrl = url + (url.includes("?") ? "&" : "") + `token=${token}`;
      window.open(fullUrl, "_blank");
    } catch (err) {
      showToast(`Download error: ${err.message}`, "error");
    }
  }

  async function showFileProps(path) {
    try {
      const { res, data } = await api(`/files/info/${encodeURIComponent(filesCurrentUser)}?path=${encodeURIComponent(path)}`);
      
      if (!res.ok) {
        showToast(data.detail || "Failed to get info", "error");
        return;
      }

      const date = new Date(data.modified).toLocaleString();
      
      $("#filePropsBody").innerHTML = `
        <div class="props-grid">
          <div class="prop-row">
            <span class="prop-label">Name</span>
            <span class="prop-value">${escapeHtml(data.name)}</span>
          </div>
          <div class="prop-row">
            <span class="prop-label">Type</span>
            <span class="prop-value">${data.type === "directory" ? "Directory" : data.mime_type || "File"}</span>
          </div>
          <div class="prop-row">
            <span class="prop-label">Size</span>
            <span class="prop-value">${data.size_formatted} (${data.size} bytes)</span>
          </div>
          <div class="prop-row">
            <span class="prop-label">Path</span>
            <span class="prop-value mono">${escapeHtml(data.path)}</span>
          </div>
          <div class="prop-row">
            <span class="prop-label">Modified</span>
            <span class="prop-value">${date}</span>
          </div>
          <div class="prop-row">
            <span class="prop-label">Permissions</span>
            <span class="prop-value mono">${data.permissions}</span>
          </div>
          <div class="prop-row">
            <span class="prop-label">Owner</span>
            <span class="prop-value">${escapeHtml(data.owner)}</span>
          </div>
          <div class="prop-row">
            <span class="prop-label">Group</span>
            <span class="prop-value">${escapeHtml(data.group)}</span>
          </div>
        </div>
      `;
      
      $("#filePropsModal").classList.remove("hidden");
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  function closeFileProps() {
    $("#filePropsModal").classList.add("hidden");
  }

  function showFilesNewModal(type) {
    if (!filesCurrentUser) {
      showToast("Select a user first", "warn");
      return;
    }
    
    filesNewType = type;
    $("#filesNewModalTitle").textContent = type === "file" ? "New File" : "New Folder";
    $("#filesNewName").value = "";
    $("#filesNewName").placeholder = type === "file" ? "filename.html" : "folder-name";
    $("#filesNewModal").classList.remove("hidden");
    setTimeout(() => $("#filesNewName").focus(), 100);
  }

  function closeFilesNewModal() {
    $("#filesNewModal").classList.add("hidden");
  }

  async function handleFilesCreate() {
    const name = $("#filesNewName").value.trim();
    if (!name) {
      showToast("Enter a name", "warn");
      return;
    }

    const endpoint = filesNewType === "file" ? "create-file" : "create-directory";
    const path = filesCurrentPath ? `?path=${encodeURIComponent(filesCurrentPath)}` : "";

    try {
      const { res, data } = await api(`/files/${endpoint}/${encodeURIComponent(filesCurrentUser)}${path}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ name, content: "" }),
      });

      if (res.ok) {
        showToast(`${filesNewType === "file" ? "File" : "Folder"} created`, "success");
        closeFilesNewModal();
        loadFilesDirectory();
      } else {
        showToast(data.detail || "Failed to create", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function handleFilesUpload() {
    const input = $("#filesUploadInput");
    const files = input.files;
    
    if (!files.length) return;
    if (!filesCurrentUser) {
      showToast("Select a user first", "warn");
      return;
    }

    for (const file of files) {
      const formData = new FormData();
      formData.append("file", file);

      try {
        const path = filesCurrentPath ? `?path=${encodeURIComponent(filesCurrentPath)}` : "";
        const url = resolveUrl(`/files/upload/${encodeURIComponent(filesCurrentUser)}${path}`);
        
        const res = await fetch(url, {
          method: "POST",
          headers: { "Authorization": `Bearer ${token}` },
          body: formData,
        });

        const data = await res.json();

        if (res.ok) {
          showToast(`Uploaded: ${file.name}`, "success");
        } else {
          showToast(`Failed: ${data.detail || file.name}`, "error");
        }
      } catch (err) {
        showToast(`Upload error: ${err.message}`, "error");
      }
    }

    input.value = "";
    loadFilesDirectory();
  }

  function renameFile(path, currentName) {
    filesSelectedItem = path;
    $("#filesRenameName").value = currentName;
    $("#filesRenameModal").classList.remove("hidden");
    setTimeout(() => $("#filesRenameName").focus(), 100);
  }

  function closeRenameModal() {
    $("#filesRenameModal").classList.add("hidden");
  }

  async function handleRenameApply() {
    const newName = $("#filesRenameName").value.trim();
    if (!newName) {
      showToast("Enter a name", "warn");
      return;
    }

    try {
      const { res, data } = await api(`/files/rename/${encodeURIComponent(filesCurrentUser)}?path=${encodeURIComponent(filesSelectedItem)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ new_name: newName }),
      });

      if (res.ok) {
        showToast("Renamed successfully", "success");
        closeRenameModal();
        loadFilesDirectory();
      } else {
        showToast(data.detail || "Failed to rename", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  function chmodFile(path) {
    filesSelectedItem = path;
    $("#filesChmodValue").value = "";
    $("#filesChmodModal").classList.remove("hidden");
    setTimeout(() => $("#filesChmodValue").focus(), 100);
  }

  function closeChmodModal() {
    $("#filesChmodModal").classList.add("hidden");
  }

  async function handleChmodApply() {
    const mode = $("#filesChmodValue").value.trim();
    if (!mode || !/^[0-7]{3,4}$/.test(mode)) {
      showToast("Enter valid octal mode (e.g., 755)", "warn");
      return;
    }

    try {
      const { res, data } = await api(`/files/chmod/${encodeURIComponent(filesCurrentUser)}?path=${encodeURIComponent(filesSelectedItem)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      });

      if (res.ok) {
        showToast("Permissions changed", "success");
        closeChmodModal();
        loadFilesDirectory();
      } else {
        showToast(data.detail || "Failed to chmod", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function deleteFile(path, type) {
    const label = type === "directory" ? "directory" : "file";
    if (!confirm(`Delete this ${label}?`)) return;

    const recursive = type === "directory" && confirm("Delete all contents recursively?");

    try {
      const { res, data } = await api(`/files/delete/${encodeURIComponent(filesCurrentUser)}?path=${encodeURIComponent(path)}&recursive=${recursive}`, {
        method: "DELETE",
      });

      if (res.ok) {
        showToast("Deleted successfully", "success");
        loadFilesDirectory();
      } else {
        showToast(data.detail || "Failed to delete", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  // ============================================================
  // Database Management
  // ============================================================
  let dbCurrentUser = "";
  let dbCurrentDatabase = "";

  async function loadDatabasesView() {
    await loadDatabaseUsers();
    setupDatabaseEventListeners();
  }

  async function loadDatabaseUsers() {
    try {
      const { res, data } = await api("/users?");
      if (!res.ok) return;

      const select = $("#dbUserSelect");
      select.innerHTML = '<option value="">Select a user...</option>' +
        data.users.map((u) => `<option value="${escapeHtml(u.username)}">${escapeHtml(u.username)} (${escapeHtml(u.term)})</option>`).join("");
    } catch (err) {
      console.error("Failed to load users:", err);
    }
  }

  function setupDatabaseEventListeners() {
    // User selection
    $("#dbUserSelect")?.addEventListener("change", (e) => {
      dbCurrentUser = e.target.value;
      if (dbCurrentUser) {
        loadDatabases();
        loadDatabaseUser();
        $("#dbUserInfo").style.display = "block";
      } else {
        $("#dbTableBody").innerHTML = '<tr><td colspan="4" class="muted">Select a user to view databases.</td></tr>';
        $("#dbUserInfo").style.display = "none";
        $("#dbCount").textContent = "—";
        $("#dbTableCount").textContent = "—";
        $("#dbTotalSize").textContent = "—";
      }
    });

    // Refresh
    $("#dbRefreshBtn")?.addEventListener("click", () => {
      if (dbCurrentUser) {
        loadDatabases();
        loadDatabaseUser();
      }
    });

    // Create database
    $("#dbCreateBtn")?.addEventListener("click", () => {
      if (!dbCurrentUser) {
        showToast("Select a user first", "warn");
        return;
      }
      $("#dbNamePrefix").textContent = dbCurrentUser + "_";
      $("#dbFullName").textContent = dbCurrentUser + "_";
      $("#dbCreateName").value = "";
      $("#dbCreateModal").classList.remove("hidden");
    });

    // Create confirmation
    $("#dbCreateConfirmBtn")?.addEventListener("click", handleCreateDatabase);
    $("#dbCreateName")?.addEventListener("input", (e) => {
      $("#dbFullName").textContent = dbCurrentUser + "_" + e.target.value;
    });

    // Password
    $("#dbSetPasswordBtn")?.addEventListener("click", () => {
      if (!dbCurrentUser) {
        showToast("Select a user first", "warn");
        return;
      }
      $("#dbPassword").value = "";
      $("#dbPasswordConfirm").value = "";
      $("#dbPasswordModal").classList.remove("hidden");
    });

    $("#dbSetPasswordConfirmBtn")?.addEventListener("click", handleSetDbPassword);

    // Create MySQL user
    $("#dbCreateUserBtn")?.addEventListener("click", handleCreateDbUser);
  }

  async function loadDatabases() {
    if (!dbCurrentUser) return;

    const tbody = $("#dbTableBody");
    tbody.innerHTML = '<tr><td colspan="4" class="muted">Loading...</td></tr>';

    try {
      const { res, data } = await api(`/databases/${encodeURIComponent(dbCurrentUser)}`);

      if (!res.ok) {
        tbody.innerHTML = `<tr><td colspan="4" class="muted">Error: ${data.detail || "Failed to load"}</td></tr>`;
        return;
      }

      // Update stats
      let totalTables = 0;
      let totalSize = 0;
      data.forEach(db => {
        totalTables += db.tables;
        totalSize += db.size_bytes;
      });

      $("#dbCount").textContent = data.length;
      $("#dbTableCount").textContent = totalTables;
      $("#dbTotalSize").textContent = formatBytes(totalSize);

      if (!data.length) {
        tbody.innerHTML = '<tr><td colspan="4" class="muted">No databases found. Create one to get started.</td></tr>';
        return;
      }

      tbody.innerHTML = data.map(db => `
        <tr>
          <td class="mono">${escapeHtml(db.name)}</td>
          <td>${db.tables}</td>
          <td>${db.size_formatted}</td>
          <td>
            <button class="btn btn-sm" onclick="app.showDbDetail('${escapeHtml(db.name)}')" title="View tables">📊 View</button>
            <button class="btn btn-sm" onclick="app.exportDatabase('${escapeHtml(db.name)}')" title="Export as SQL">⬇️ Export</button>
            <button class="btn btn-sm danger" onclick="app.dropDatabase('${escapeHtml(db.name)}')" title="Drop database">🗑️ Drop</button>
          </td>
        </tr>
      `).join("");
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="4" class="muted">Error: ${err.message}</td></tr>`;
    }
  }

  async function loadDatabaseUser() {
    if (!dbCurrentUser) return;

    const body = $("#dbUserInfoBody");
    body.innerHTML = '<p class="muted">Loading...</p>';

    try {
      const { res, data } = await api(`/databases/${encodeURIComponent(dbCurrentUser)}/user/info`);

      if (!res.ok) {
        body.innerHTML = `<p class="muted">Error: ${data.detail || "Failed to load"}</p>`;
        return;
      }

      if (data.privileges.length === 0) {
        body.innerHTML = `
          <p class="muted">No MySQL user exists for this account.</p>
          <p class="small">Click "Create MySQL User" to set one up.</p>
        `;
        $("#dbSetPasswordBtn").disabled = true;
        $("#dbCreateUserBtn").style.display = "inline-block";
      } else {
        body.innerHTML = `
          <div class="props-grid">
            <div class="prop-row">
              <span class="prop-label">MySQL Username</span>
              <span class="prop-value mono">${escapeHtml(data.username)}</span>
            </div>
            <div class="prop-row">
              <span class="prop-label">Host</span>
              <span class="prop-value mono">${escapeHtml(data.host)}</span>
            </div>
          </div>
        `;
        $("#dbSetPasswordBtn").disabled = false;
        $("#dbCreateUserBtn").style.display = "none";
      }
    } catch (err) {
      body.innerHTML = `<p class="muted">Error: ${err.message}</p>`;
    }
  }

  async function handleCreateDatabase() {
    const name = $("#dbCreateName").value.trim();
    if (!name) {
      showToast("Enter a database name", "warn");
      return;
    }

    try {
      const { res, data } = await api(`/databases/${encodeURIComponent(dbCurrentUser)}`, {
        method: "POST",
        body: JSON.stringify({ name }),
      });

      if (res.ok) {
        showToast(`Database ${data.name} created`, "success");
        closeDbCreateModal();
        loadDatabases();
      } else {
        showToast(data.detail || "Failed to create database", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function handleSetDbPassword() {
    const password = $("#dbPassword").value;
    const confirm = $("#dbPasswordConfirm").value;

    if (!password) {
      showToast("Enter a password", "warn");
      return;
    }

    if (password !== confirm) {
      showToast("Passwords do not match", "error");
      return;
    }

    try {
      const { res, data } = await api(`/databases/${encodeURIComponent(dbCurrentUser)}/user/password`, {
        method: "PUT",
        body: JSON.stringify({ password }),
      });

      if (res.ok) {
        showToast("Password updated", "success");
        closeDbPasswordModal();
      } else {
        showToast(data.detail || "Failed to set password", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function handleCreateDbUser() {
    const password = prompt("Enter password for MySQL user (or leave blank to cancel):");
    if (!password) return;

    try {
      const { res, data } = await api(`/databases/${encodeURIComponent(dbCurrentUser)}/user`, {
        method: "POST",
        body: JSON.stringify({ password }),
      });

      if (res.ok) {
        showToast("MySQL user created", "success");
        loadDatabaseUser();
      } else {
        showToast(data.detail || "Failed to create user", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function showDbDetail(dbName) {
    dbCurrentDatabase = dbName;
    $("#dbDetailTitle").textContent = dbName;
    $("#dbDetailModal").classList.remove("hidden");

    const tbody = $("#dbDetailTableBody");
    tbody.innerHTML = '<tr><td colspan="4" class="muted">Loading...</td></tr>';

    try {
      const { res, data } = await api(`/databases/${encodeURIComponent(dbCurrentUser)}/detail/${encodeURIComponent(dbName)}`);

      if (!res.ok) {
        tbody.innerHTML = `<tr><td colspan="4" class="muted">Error: ${data.detail || "Failed to load"}</td></tr>`;
        return;
      }

      if (!data.tables.length) {
        tbody.innerHTML = '<tr><td colspan="4" class="muted">No tables in this database.</td></tr>';
        return;
      }

      tbody.innerHTML = data.tables.map(t => `
        <tr>
          <td class="mono">${escapeHtml(t.name)}</td>
          <td>${escapeHtml(t.engine)}</td>
          <td>${t.rows.toLocaleString()}</td>
          <td>${t.size_formatted}</td>
        </tr>
      `).join("");
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="4" class="muted">Error: ${err.message}</td></tr>`;
    }
  }

  async function exportDatabase(dbName) {
    if (!dbName) dbName = dbCurrentDatabase;
    try {
      const res = await fetch(`${apiBase}/databases/${encodeURIComponent(dbCurrentUser)}/${encodeURIComponent(dbName)}/export`, {
        headers: { Authorization: `Bearer ${token}` },
      });

      if (res.ok) {
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `${dbName}.sql`;
        a.click();
        URL.revokeObjectURL(url);
        showToast("Database exported", "success");
      } else {
        const data = await res.json();
        showToast(data.detail || "Export failed", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function dropDatabase(dbName) {
    if (!confirm(`Are you sure you want to DROP database "${dbName}"?\n\nThis action cannot be undone!`)) {
      return;
    }

    try {
      const { res, data } = await api(`/databases/${encodeURIComponent(dbCurrentUser)}/${encodeURIComponent(dbName)}`, {
        method: "DELETE",
      });

      if (res.ok) {
        showToast("Database dropped", "success");
        loadDatabases();
      } else {
        showToast(data.detail || "Failed to drop database", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  function closeDbCreateModal() {
    $("#dbCreateModal").classList.add("hidden");
  }

  function closeDbPasswordModal() {
    $("#dbPasswordModal").classList.add("hidden");
  }

  function closeDbDetailModal() {
    $("#dbDetailModal").classList.add("hidden");
  }

  function formatBytes(bytes) {
    if (bytes === 0) return "0 B";
    const k = 1024;
    const sizes = ["B", "KB", "MB", "GB", "TB"];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + " " + sizes[i];
  }

  // ============================================================
  // FTP Management
  // ============================================================
  let ftpCurrentUser = "";

  async function loadFtpView() {
    await loadFtpUsers();
    setupFtpEventListeners();
    loadFtpSessions();
  }

  async function loadFtpUsers() {
    try {
      const { res, data } = await api("/users?");
      if (!res.ok) return;

      const select = $("#ftpUserSelect");
      select.innerHTML = '<option value="">Select a user...</option>' +
        data.users.map((u) => `<option value="${escapeHtml(u.username)}">${escapeHtml(u.username)} (${escapeHtml(u.term)})</option>`).join("");
    } catch (err) {
      console.error("Failed to load users:", err);
    }
  }

  function setupFtpEventListeners() {
    // User selection
    $("#ftpUserSelect")?.addEventListener("change", (e) => {
      ftpCurrentUser = e.target.value;
      if (ftpCurrentUser) {
        loadFtpAccounts();
      } else {
        $("#ftpTableBody").innerHTML = '<tr><td colspan="4" class="muted">Select a user to view FTP accounts.</td></tr>';
        $("#ftpCount").textContent = "—";
      }
    });

    // Refresh
    $("#ftpRefreshBtn")?.addEventListener("click", () => {
      if (ftpCurrentUser) {
        loadFtpAccounts();
      }
      loadFtpSessions();
    });

    // Create FTP account
    $("#ftpCreateBtn")?.addEventListener("click", () => {
      if (!ftpCurrentUser) {
        showToast("Select a user first", "warn");
        return;
      }
      $("#ftpNamePrefix").textContent = ftpCurrentUser + "_";
      $("#ftpCreateName").value = "";
      $("#ftpCreatePassword").value = "";
      $("#ftpCreateModal").classList.remove("hidden");
    });

    // Create confirmation
    $("#ftpCreateConfirmBtn")?.addEventListener("click", handleCreateFtpAccount);

    // Set password confirmation
    $("#ftpSetPasswordConfirmBtn")?.addEventListener("click", handleSetFtpPassword);
  }

  async function loadFtpAccounts() {
    if (!ftpCurrentUser) return;

    const tbody = $("#ftpTableBody");
    tbody.innerHTML = '<tr><td colspan="4" class="muted">Loading...</td></tr>';

    try {
      const { res, data } = await api(`/ftp/accounts/${encodeURIComponent(ftpCurrentUser)}`);

      if (!res.ok) {
        tbody.innerHTML = `<tr><td colspan="4" class="muted">Error: ${data.detail || "Failed to load"}</td></tr>`;
        return;
      }

      $("#ftpCount").textContent = data.length;

      if (!data.length) {
        tbody.innerHTML = '<tr><td colspan="4" class="muted">No FTP accounts found.</td></tr>';
        return;
      }

      tbody.innerHTML = data.map(acc => `
        <tr>
          <td class="mono">${escapeHtml(acc.username)}</td>
          <td class="mono small">${escapeHtml(acc.home_directory)}</td>
          <td><span class="pill ${acc.enabled ? 'ok' : 'warn'}">${acc.enabled ? 'Active' : 'Disabled'}</span></td>
          <td>
            <button class="btn btn-sm" onclick="app.setFtpPassword('${escapeHtml(acc.username)}')" title="Set password">🔑 Password</button>
            ${acc.enabled 
              ? `<button class="btn btn-sm" onclick="app.disableFtpAccount('${escapeHtml(acc.username)}')" title="Disable">⏸️ Disable</button>`
              : `<button class="btn btn-sm" onclick="app.enableFtpAccount('${escapeHtml(acc.username)}')" title="Enable">▶️ Enable</button>`
            }
            ${acc.username !== ftpCurrentUser 
              ? `<button class="btn btn-sm danger" onclick="app.deleteFtpAccount('${escapeHtml(acc.username)}')" title="Delete">🗑️ Delete</button>`
              : ''
            }
          </td>
        </tr>
      `).join("");
    } catch (err) {
      tbody.innerHTML = `<tr><td colspan="4" class="muted">Error: ${err.message}</td></tr>`;
    }
  }

  async function loadFtpSessions() {
    try {
      const { res, data } = await api("/ftp/sessions");

      if (!res.ok) {
        $("#ftpSessions").textContent = "—";
        return;
      }

      $("#ftpSessions").textContent = data.length;

      if (data.length > 0) {
        $("#ftpSessionsCard").style.display = "block";
        $("#ftpSessionsTableBody").innerHTML = data.map(s => `
          <tr>
            <td class="mono">${escapeHtml(s.username)}</td>
            <td>${escapeHtml(s.ip_address)}</td>
            <td>${escapeHtml(s.connected_since)}</td>
            <td class="mono small">${escapeHtml(s.current_dir)}</td>
            <td>
              <button class="btn btn-sm danger" onclick="app.kickFtpSession('${escapeHtml(s.username)}')" title="Disconnect">Kick</button>
            </td>
          </tr>
        `).join("");
      } else {
        $("#ftpSessionsCard").style.display = "none";
      }
    } catch (err) {
      console.error("Failed to load FTP sessions:", err);
      $("#ftpSessions").textContent = "—";
    }
  }

  async function handleCreateFtpAccount() {
    const name = $("#ftpCreateName").value.trim();
    if (!name) {
      showToast("Enter an account name", "warn");
      return;
    }

    const password = $("#ftpCreatePassword").value || null;

    try {
      const { res, data } = await api(`/ftp/accounts/${encodeURIComponent(ftpCurrentUser)}`, {
        method: "POST",
        body: JSON.stringify({ name, password }),
      });

      if (res.ok) {
        closeFtpCreateModal();
        // Show credentials modal
        $("#ftpCreatedUsername").textContent = data.account.username;
        $("#ftpCreatedPassword").textContent = data.password;
        $("#ftpCreatedDirectory").textContent = data.account.home_directory;
        $("#ftpCreatedModal").classList.remove("hidden");
        loadFtpAccounts();
      } else {
        showToast(data.detail || "Failed to create FTP account", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  function setFtpPassword(ftpName) {
    $("#ftpPasswordAccount").value = ftpName;
    $("#ftpNewPassword").value = "";
    $("#ftpPasswordModal").classList.remove("hidden");
  }

  async function handleSetFtpPassword() {
    const ftpName = $("#ftpPasswordAccount").value;
    const password = $("#ftpNewPassword").value;

    if (!password) {
      showToast("Enter a password", "warn");
      return;
    }

    try {
      const { res, data } = await api(`/ftp/accounts/${encodeURIComponent(ftpCurrentUser)}/${encodeURIComponent(ftpName)}/password`, {
        method: "PUT",
        body: JSON.stringify({ password }),
      });

      if (res.ok) {
        showToast("Password updated", "success");
        closeFtpPasswordModal();
      } else {
        showToast(data.detail || "Failed to set password", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function enableFtpAccount(ftpName) {
    try {
      const { res, data } = await api(`/ftp/accounts/${encodeURIComponent(ftpCurrentUser)}/${encodeURIComponent(ftpName)}/enable`, {
        method: "POST",
      });

      if (res.ok) {
        showToast("FTP account enabled", "success");
        loadFtpAccounts();
      } else {
        showToast(data.detail || "Failed to enable account", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function disableFtpAccount(ftpName) {
    try {
      const { res, data } = await api(`/ftp/accounts/${encodeURIComponent(ftpCurrentUser)}/${encodeURIComponent(ftpName)}/disable`, {
        method: "POST",
      });

      if (res.ok) {
        showToast("FTP account disabled", "success");
        loadFtpAccounts();
      } else {
        showToast(data.detail || "Failed to disable account", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function deleteFtpAccount(ftpName) {
    if (!confirm(`Delete FTP account "${ftpName}"?`)) {
      return;
    }

    try {
      const { res, data } = await api(`/ftp/accounts/${encodeURIComponent(ftpCurrentUser)}/${encodeURIComponent(ftpName)}`, {
        method: "DELETE",
      });

      if (res.ok) {
        showToast("FTP account deleted", "success");
        loadFtpAccounts();
      } else {
        showToast(data.detail || "Failed to delete account", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function kickFtpSession(username) {
    try {
      const { res, data } = await api(`/ftp/sessions/${encodeURIComponent(username)}/kick`, {
        method: "POST",
      });

      if (res.ok) {
        showToast("Session disconnected", "success");
        loadFtpSessions();
      } else {
        showToast(data.detail || "Failed to disconnect session", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  function closeFtpCreateModal() {
    $("#ftpCreateModal").classList.add("hidden");
  }

  function closeFtpPasswordModal() {
    $("#ftpPasswordModal").classList.add("hidden");
  }

  function closeFtpCreatedModal() {
    $("#ftpCreatedModal").classList.add("hidden");
  }

  // ============================================================
  // Cron View
  // ============================================================
  let cronCurrentUsername = "";

  async function loadCronView() {
    // View is ready, user needs to select a username
  }

  async function loadCronJobs(username) {
    if (!username) {
      showToast("Enter a username", "warn");
      return;
    }
    cronCurrentUsername = username;
    const container = $("#cronJobsCard");
    const tbody = $("#cronTableBody");

    try {
      const { res, data } = await api(`/cron/${encodeURIComponent(username)}`);
      if (!res.ok) {
        showToast(data.detail || "Failed to load cron jobs", "error");
        return;
      }

      container.style.display = "block";
      $("#cronUserLabel").textContent = username;

      if (!data.length) {
        tbody.innerHTML = '<tr><td colspan="5" class="muted">No cron jobs</td></tr>';
        return;
      }

      tbody.innerHTML = data.map((job) => `
        <tr>
          <td class="mono">${escapeHtml(job.schedule)}</td>
          <td class="mono">${escapeHtml(job.command)}</td>
          <td>${escapeHtml(job.comment || "—")}</td>
          <td><span class="pill ${job.enabled ? 'ok' : 'warn'}">${job.enabled ? "Enabled" : "Disabled"}</span></td>
          <td>
            <button class="btn btn-sm" onclick="app.toggleCronJob(${job.id})">Toggle</button>
            <button class="btn btn-sm" onclick="app.editCronJob(${job.id})">Edit</button>
            <button class="btn btn-sm danger" onclick="app.deleteCronJob(${job.id})">Delete</button>
          </td>
        </tr>
      `).join("");
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  function showCronModal(editId = null) {
    const modal = $("#cronModal");
    const title = $("#cronModalTitle");
    title.textContent = editId ? "Edit Cron Job" : "Add Cron Job";
    $("#cronEditId").value = editId || "";

    // Clear form
    if (!editId) {
      $("#cronMinute").value = "*";
      $("#cronHour").value = "*";
      $("#cronDay").value = "*";
      $("#cronMonth").value = "*";
      $("#cronWeekday").value = "*";
      $("#cronCommand").value = "";
      $("#cronComment").value = "";
    }

    modal.classList.remove("hidden");
  }

  function closeCronModal() {
    $("#cronModal").classList.add("hidden");
  }

  async function saveCronJob(e) {
    e.preventDefault();
    const editId = $("#cronEditId").value;
    const body = {
      minute: $("#cronMinute").value,
      hour: $("#cronHour").value,
      day: $("#cronDay").value,
      month: $("#cronMonth").value,
      weekday: $("#cronWeekday").value,
      command: $("#cronCommand").value,
      comment: $("#cronComment").value || null,
    };

    try {
      const method = editId ? "PUT" : "POST";
      const path = editId
        ? `/cron/${encodeURIComponent(cronCurrentUsername)}/${editId}`
        : `/cron/${encodeURIComponent(cronCurrentUsername)}`;

      const { res, data } = await api(path, {
        method,
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      if (res.ok) {
        showToast(editId ? "Cron job updated" : "Cron job created", "success");
        closeCronModal();
        loadCronJobs(cronCurrentUsername);
      } else {
        showToast(data.detail || "Failed to save cron job", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function toggleCronJob(jobId) {
    try {
      const { res, data } = await api(`/cron/${encodeURIComponent(cronCurrentUsername)}/${jobId}/toggle`, {
        method: "POST",
      });
      if (res.ok) {
        showToast("Cron job toggled", "success");
        loadCronJobs(cronCurrentUsername);
      } else {
        showToast(data.detail || "Failed to toggle", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function editCronJob(jobId) {
    try {
      const { res, data } = await api(`/cron/${encodeURIComponent(cronCurrentUsername)}/${jobId}`);
      if (res.ok) {
        $("#cronMinute").value = data.minute;
        $("#cronHour").value = data.hour;
        $("#cronDay").value = data.day;
        $("#cronMonth").value = data.month;
        $("#cronWeekday").value = data.weekday;
        $("#cronCommand").value = data.command;
        $("#cronComment").value = data.comment || "";
        showCronModal(jobId);
      } else {
        showToast(data.detail || "Failed to load job", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function deleteCronJob(jobId) {
    if (!confirm("Delete this cron job?")) return;
    try {
      const { res, data } = await api(`/cron/${encodeURIComponent(cronCurrentUsername)}/${jobId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        showToast("Cron job deleted", "success");
        loadCronJobs(cronCurrentUsername);
      } else {
        showToast(data.detail || "Failed to delete", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  // ============================================================
  // Security View
  // ============================================================
  let securityCurrentUsername = "";

  async function loadSecurityView() {
    loadFail2Ban();
    loadUfwStatus();
    loadModSecurityStatus();
  }

  // SSH Keys
  async function loadSshKeys(username) {
    if (!username) {
      showToast("Enter a username", "warn");
      return;
    }
    securityCurrentUsername = username;
    const container = $("#sshKeysContainer");
    const list = $("#sshKeysList");

    try {
      const { res, data } = await api(`/security/ssh-keys/${encodeURIComponent(username)}`);
      if (!res.ok) {
        showToast(data.detail || "Failed to load SSH keys", "error");
        return;
      }

      container.style.display = "block";
      $("#sshUserLabel").textContent = username;

      if (!data.length) {
        list.innerHTML = '<p class="muted">No SSH keys</p>';
        return;
      }

      list.innerHTML = data.map((key) => `
        <div class="ssh-key-item">
          <div class="ssh-key-info">
            <span class="pill neutral">${escapeHtml(key.type)}</span>
            <span class="mono">${escapeHtml(key.key.substring(0, 40))}...</span>
            <span class="muted">${escapeHtml(key.comment || "")}</span>
          </div>
          <button class="btn btn-sm danger" onclick="app.deleteSshKey(${key.id})">Remove</button>
        </div>
      `).join("");
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function addSshKey() {
    const key = $("#newSshKey").value.trim();
    if (!key || !securityCurrentUsername) {
      showToast("Enter an SSH key", "warn");
      return;
    }

    try {
      const { res, data } = await api(`/security/ssh-keys/${encodeURIComponent(securityCurrentUsername)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ key }),
      });
      if (res.ok) {
        showToast("SSH key added", "success");
        $("#newSshKey").value = "";
        loadSshKeys(securityCurrentUsername);
      } else {
        showToast(data.detail || "Failed to add key", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function deleteSshKey(keyId) {
    if (!confirm("Remove this SSH key?")) return;
    try {
      const { res, data } = await api(`/security/ssh-keys/${encodeURIComponent(securityCurrentUsername)}/${keyId}`, {
        method: "DELETE",
      });
      if (res.ok) {
        showToast("SSH key removed", "success");
        loadSshKeys(securityCurrentUsername);
      } else {
        showToast(data.detail || "Failed to remove key", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  // Fail2Ban
  async function loadFail2Ban() {
    try {
      const { res, data } = await api("/security/fail2ban/status");
      const statusPill = $("#fail2banStatus");
      const container = $("#fail2banJails");
      const select = $("#fail2banJailSelect");

      if (res.ok) {
        statusPill.textContent = data.running ? "Running" : "Stopped";
        statusPill.className = `pill ${data.running ? "ok" : "warn"}`;

        if (data.jails?.length) {
          container.innerHTML = `<p>Active jails: ${data.jails.map(j => `<span class="pill neutral">${escapeHtml(j)}</span>`).join(" ")}</p>`;
          select.innerHTML = `<option value="">Select jail</option>` + data.jails.map(j => `<option value="${escapeHtml(j)}">${escapeHtml(j)}</option>`).join("");
        } else {
          container.innerHTML = '<p class="muted">No active jails</p>';
        }
      } else {
        statusPill.textContent = "Error";
        statusPill.className = "pill warn";
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function banIP() {
    const jail = $("#fail2banJailSelect").value;
    const ip = $("#fail2banIP").value.trim();
    if (!jail || !ip) {
      showToast("Select a jail and enter an IP", "warn");
      return;
    }

    try {
      const { res, data } = await api(`/security/fail2ban/ban/${encodeURIComponent(jail)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ip }),
      });
      if (res.ok) {
        showToast(`IP ${ip} banned`, "success");
        $("#fail2banIP").value = "";
      } else {
        showToast(data.detail || "Failed to ban IP", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function unbanIP() {
    const jail = $("#fail2banJailSelect").value;
    const ip = $("#fail2banIP").value.trim();
    if (!jail || !ip) {
      showToast("Select a jail and enter an IP", "warn");
      return;
    }

    try {
      const { res, data } = await api(`/security/fail2ban/unban/${encodeURIComponent(jail)}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ip }),
      });
      if (res.ok) {
        showToast(`IP ${ip} unbanned`, "success");
        $("#fail2banIP").value = "";
      } else {
        showToast(data.detail || "Failed to unban IP", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  // UFW
  async function loadUfwStatus() {
    try {
      const { res, data } = await api("/security/ufw/status");
      const statusPill = $("#ufwStatus");
      const tbody = $("#ufwRulesBody");

      if (res.ok) {
        statusPill.textContent = data.enabled ? "Enabled" : "Disabled";
        statusPill.className = `pill ${data.enabled ? "ok" : "warn"}`;

        if (data.rules?.length) {
          tbody.innerHTML = data.rules.map((rule, idx) => `
            <tr>
              <td>${idx + 1}</td>
              <td>${escapeHtml(rule.to || "any")}</td>
              <td>${escapeHtml(rule.action || "")}</td>
              <td>${escapeHtml(rule.from_ip || "any")}</td>
              <td>
                <button class="btn btn-sm danger" onclick="app.deleteUfwRule(${idx + 1})">Delete</button>
              </td>
            </tr>
          `).join("");
        } else {
          tbody.innerHTML = '<tr><td colspan="5" class="muted">No rules configured</td></tr>';
        }
      } else {
        statusPill.textContent = "Error";
        statusPill.className = "pill warn";
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function enableUfw() {
    try {
      const { res, data } = await api("/security/ufw/enable", { method: "POST" });
      if (res.ok) {
        showToast("UFW enabled", "success");
        loadUfwStatus();
      } else {
        showToast(data.detail || "Failed to enable UFW", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function disableUfw() {
    try {
      const { res, data } = await api("/security/ufw/disable", { method: "POST" });
      if (res.ok) {
        showToast("UFW disabled", "success");
        loadUfwStatus();
      } else {
        showToast(data.detail || "Failed to disable UFW", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function addUfwRule() {
    const ruleType = $("#ufwRuleType").value;
    const port = $("#ufwPort").value.trim();
    const protocol = $("#ufwProtocol").value || null;
    const fromIP = $("#ufwFromIP").value.trim() || null;

    if (!port) {
      showToast("Enter a port", "warn");
      return;
    }

    try {
      const { res, data } = await api("/security/ufw/rules", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ rule_type: ruleType, port, protocol, from_ip: fromIP }),
      });
      if (res.ok) {
        showToast("Rule added", "success");
        $("#ufwPort").value = "";
        $("#ufwFromIP").value = "";
        loadUfwStatus();
      } else {
        showToast(data.detail || "Failed to add rule", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function deleteUfwRule(ruleNumber) {
    if (!confirm(`Delete rule #${ruleNumber}?`)) return;
    try {
      const { res, data } = await api(`/security/ufw/rules/${ruleNumber}`, { method: "DELETE" });
      if (res.ok) {
        showToast("Rule deleted", "success");
        loadUfwStatus();
      } else {
        showToast(data.detail || "Failed to delete rule", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  // ModSecurity
  async function loadModSecurityStatus() {
    try {
      const { res, data } = await api("/security/modsecurity/status");
      const statusPill = $("#modsecStatus");
      const modeSelect = $("#modsecMode");

      if (res.ok) {
        statusPill.textContent = data.enabled ? data.mode : "Disabled";
        statusPill.className = `pill ${data.enabled ? "ok" : "warn"}`;
        modeSelect.value = data.mode;
      } else {
        statusPill.textContent = "Error";
        statusPill.className = "pill warn";
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function setModSecurityMode() {
    const mode = $("#modsecMode").value;
    try {
      const { res, data } = await api("/security/modsecurity/mode", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ mode }),
      });
      if (res.ok) {
        showToast(`ModSecurity mode set to ${mode}`, "success");
        loadModSecurityStatus();
      } else {
        showToast(data.detail || "Failed to set mode", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  // ============================================================
  // SSL View
  // ============================================================
  async function loadSslView() {
    loadCertificates();
    loadSslWarnings();
  }

  async function loadCertificates() {
    try {
      const { res, data } = await api("/ssl/certificates");
      const tbody = $("#sslTableBody");

      if (res.ok) {
        const valid = data.filter(c => !c.is_expired).length;
        const expiring = data.filter(c => c.is_expiring_soon && !c.is_expired).length;

        $("#sslTotalCerts").textContent = data.length;
        $("#sslValidCerts").textContent = valid;
        $("#sslExpiringSoon").textContent = expiring;

        if (!data.length) {
          tbody.innerHTML = '<tr><td colspan="5" class="muted">No certificates found</td></tr>';
          return;
        }

        tbody.innerHTML = data.map((cert) => {
          const statusClass = cert.is_expired ? "warn" : cert.is_expiring_soon ? "warn" : "ok";
          const statusText = cert.is_expired ? "Expired" : cert.is_expiring_soon ? "Expiring Soon" : "Valid";
          return `
            <tr>
              <td>${escapeHtml(cert.domain)}</td>
              <td>${escapeHtml(cert.valid_until)}</td>
              <td>${cert.days_remaining}</td>
              <td><span class="pill ${statusClass}">${statusText}</span></td>
              <td>
                <button class="btn btn-sm" onclick="app.showCertDetail('${escapeHtml(cert.domain)}')">Details</button>
                <button class="btn btn-sm" onclick="app.renewCert('${escapeHtml(cert.domain)}')">Renew</button>
                <button class="btn btn-sm danger" onclick="app.deleteCert('${escapeHtml(cert.domain)}')">Delete</button>
              </td>
            </tr>
          `;
        }).join("");
      } else {
        tbody.innerHTML = '<tr><td colspan="5" class="muted">Failed to load certificates</td></tr>';
      }
    } catch (err) {
      console.error(err);
    }
  }

  async function loadSslWarnings() {
    try {
      const { res, data } = await api("/ssl/warnings?days_threshold=30");
      const card = $("#sslWarningsCard");
      const container = $("#sslWarnings");

      if (res.ok && data.warnings?.length) {
        card.style.display = "block";
        container.innerHTML = data.warnings.map((w) => `
          <div class="warning-item">
            <span class="pill warn">⚠️</span>
            <span><strong>${escapeHtml(w.domain)}</strong> expires in ${w.days_remaining} days (${escapeHtml(w.valid_until)})</span>
          </div>
        `).join("");
      } else {
        card.style.display = "none";
      }
    } catch (err) {
      console.error(err);
    }
  }

  function showSslRequestModal() {
    $("#sslRequestModal").classList.remove("hidden");
    $("#sslDomains").value = "";
    $("#sslEmail").value = "";
    $("#sslWebroot").value = "";
    $("#sslStaging").checked = false;
  }

  function closeSslModal() {
    $("#sslRequestModal").classList.add("hidden");
  }

  function closeSslDetailModal() {
    $("#sslDetailModal").classList.add("hidden");
  }

  async function requestCertificate(e) {
    e.preventDefault();
    const domains = $("#sslDomains").value.split(",").map(d => d.trim()).filter(Boolean);
    const email = $("#sslEmail").value.trim() || null;
    const webroot = $("#sslWebroot").value.trim() || null;
    const staging = $("#sslStaging").checked;

    if (!domains.length) {
      showToast("Enter at least one domain", "warn");
      return;
    }

    try {
      const { res, data } = await api("/ssl/certificates", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ domains, email, webroot, staging }),
      });
      if (res.ok) {
        showToast("Certificate requested", "success");
        closeSslModal();
        loadCertificates();
      } else {
        showToast(data.detail || "Failed to request certificate", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function showCertDetail(domain) {
    try {
      const { res, data } = await api(`/ssl/certificates/${encodeURIComponent(domain)}`);
      const modal = $("#sslDetailModal");
      const body = $("#sslDetailBody");

      if (res.ok) {
        const statusClass = data.is_expired ? 'warn' : data.is_expiring_soon ? 'warn' : 'ok';
        const statusText = data.is_expired ? 'Expired' : data.is_expiring_soon ? 'Expiring Soon' : 'Valid';
        body.innerHTML = `
          <div class="cert-detail">
            <div class="detail-row"><strong>Domain:</strong> ${escapeHtml(data.domain)}</div>
            <div class="detail-row"><strong>Issuer:</strong> ${escapeHtml(data.issuer)}</div>
            <div class="detail-row"><strong>Valid From:</strong> ${escapeHtml(data.valid_from)}</div>
            <div class="detail-row"><strong>Valid Until:</strong> ${escapeHtml(data.valid_until)}</div>
            <div class="detail-row"><strong>Serial:</strong> <code>${escapeHtml(data.serial)}</code></div>
            <div class="detail-row"><strong>Days Remaining:</strong> ${data.days_remaining}</div>
            <div class="detail-row"><strong>Status:</strong> <span class="pill ${statusClass}">${statusText}</span></div>
            <div class="detail-row"><strong>Auto-Renew:</strong> ${data.auto_renew ? 'Yes' : 'No'}</div>
            ${data.domains?.length > 1 ? `<div class="detail-row"><strong>All Domains:</strong> ${data.domains.map(s => escapeHtml(s)).join(", ")}</div>` : ""}
          </div>
        `;
        modal.classList.remove("hidden");
      } else {
        showToast(data.detail || "Failed to load certificate details", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function renewCert(domain) {
    try {
      const { res, data } = await api(`/ssl/certificates/${encodeURIComponent(domain)}/renew?force=true`, {
        method: "POST",
      });
      if (res.ok) {
        showToast(`Certificate for ${domain} renewed`, "success");
        loadCertificates();
      } else {
        showToast(data.detail || "Failed to renew certificate", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function renewAllCerts() {
    try {
      const { res, data } = await api("/ssl/certificates/renew-all", { method: "POST" });
      if (res.ok) {
        showToast("All certificates renewed", "success");
        loadCertificates();
      } else {
        showToast(data.detail || "Failed to renew certificates", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function deleteCert(domain) {
    if (!confirm(`Delete certificate for ${domain}?`)) return;
    try {
      const { res, data } = await api(`/ssl/certificates/${encodeURIComponent(domain)}`, {
        method: "DELETE",
      });
      if (res.ok) {
        showToast("Certificate deleted", "success");
        loadCertificates();
      } else {
        showToast(data.detail || "Failed to delete certificate", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  // ============================================================
  // Updates View
  // ============================================================
  let updatesData = null;

  async function loadUpdatesView() {
    loadServiceVersions();
    setupUpdatesEvents();
  }

  function setupUpdatesEvents() {
    const checkBtn = $("#updCheckBtn");
    const refreshBtn = $("#updRefreshBtn");
    const applySecBtn = $("#updApplySecurityBtn");
    const applyAllBtn = $("#updApplyAllBtn");
    const selectAll = $("#updSelectAll");

    if (checkBtn) checkBtn.onclick = checkForUpdates;
    if (refreshBtn) refreshBtn.onclick = refreshApt;
    if (applySecBtn) applySecBtn.onclick = () => applyUpdates(true);
    if (applyAllBtn) applyAllBtn.onclick = () => applyUpdates(false);
    if (selectAll) selectAll.onchange = (e) => {
      $$("#updPackagesBody input[type=checkbox]").forEach((cb) => {
        cb.checked = e.target.checked;
      });
    };
  }

  async function loadServiceVersions() {
    try {
      const { res, data } = await api("/updates/versions");
      if (res.ok && data.versions) {
        const grid = $("#updVersionsGrid");
        grid.innerHTML = Object.entries(data.versions)
          .map(
            ([name, ver]) => `
          <div class="settings-status-row">
            <span>${name}</span>
            <span class="mono small">${escHtml(ver)}</span>
          </div>`
          )
          .join("");
      }
    } catch (err) {
      showToast(`Error loading versions: ${err.message}`, "error");
    }
  }

  async function refreshApt() {
    $("#updRefreshBtn").disabled = true;
    try {
      const { res, data } = await api("/updates/refresh", { method: "POST" });
      if (res.ok) {
        showToast("APT package list refreshed", "success");
      } else {
        showToast(data.detail || "Failed to refresh", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    } finally {
      $("#updRefreshBtn").disabled = false;
    }
  }

  async function checkForUpdates() {
    $("#updCheckBtn").disabled = true;
    $("#updCheckBtn").textContent = "Checking...";
    try {
      const { res, data } = await api("/updates/check");
      if (res.ok) {
        updatesData = data;
        renderUpdateStatus(data);
        renderUpdatePackages(data.packages);
      } else {
        showToast(data.detail || "Failed to check updates", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    } finally {
      $("#updCheckBtn").disabled = false;
      $("#updCheckBtn").textContent = "Check for Updates";
    }
  }

  function renderUpdateStatus(data) {
    const totalPill = $("#updTotalPill");
    totalPill.textContent = data.total;
    totalPill.className = `pill ${data.total > 0 ? "warn" : "ok"}`;

    const secPill = $("#updSecurityPill");
    secPill.textContent = data.security;
    secPill.className = `pill ${data.security > 0 ? "danger" : "ok"}`;

    const rebootPill = $("#updRebootPill");
    rebootPill.textContent = data.reboot_required ? "Yes" : "No";
    rebootPill.className = `pill ${data.reboot_required ? "warn" : "ok"}`;

    if (data.last_check) {
      $("#updLastCheck").textContent = new Date(data.last_check).toLocaleString();
    }

    $("#updApplySecurityBtn").disabled = data.security === 0;
    $("#updApplyAllBtn").disabled = data.total === 0;
  }

  function renderUpdatePackages(packages) {
    const tbody = $("#updPackagesBody");
    if (!packages || packages.length === 0) {
      tbody.innerHTML = '<tr><td colspan="6" class="muted">System is up to date.</td></tr>';
      return;
    }
    tbody.innerHTML = packages
      .map(
        (p) => `
      <tr>
        <td><input type="checkbox" value="${escHtml(p.name)}" checked /></td>
        <td class="mono">${escHtml(p.name)}</td>
        <td class="mono small">${escHtml(p.current_version)}</td>
        <td class="mono small">${escHtml(p.new_version)}</td>
        <td>${escHtml(p.source)}</td>
        <td>${p.is_security ? '<span class="pill danger">Security</span>' : '<span class="pill neutral">Standard</span>'}</td>
      </tr>`
      )
      .join("");
  }

  async function applyUpdates(securityOnly) {
    const selectedPkgs = [];
    $$("#updPackagesBody input[type=checkbox]:checked").forEach((cb) => {
      selectedPkgs.push(cb.value);
    });

    const label = securityOnly ? "security updates" : `${selectedPkgs.length} package(s)`;
    if (!confirm(`Apply ${label}? This may take several minutes.`)) return;

    $("#updProgress").classList.remove("hidden");
    $("#updProgressFill").style.width = "0%";
    $("#updProgressText").textContent = "Applying updates...";
    $("#updApplyAllBtn").disabled = true;
    $("#updApplySecurityBtn").disabled = true;

    // Animate progress
    let pct = 0;
    const progressTimer = setInterval(() => {
      pct = Math.min(pct + 2, 90);
      $("#updProgressFill").style.width = `${pct}%`;
    }, 1000);

    try {
      const body = securityOnly
        ? { security_only: true }
        : { package_names: selectedPkgs.length > 0 ? selectedPkgs : null };
      const { res, data } = await api("/updates/apply", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body),
      });

      clearInterval(progressTimer);
      $("#updProgressFill").style.width = "100%";

      if (res.ok && data.success) {
        $("#updProgressText").textContent = data.message;
        showToast(data.message, "success");
        // Re-check updates
        setTimeout(checkForUpdates, 2000);
      } else {
        $("#updProgressText").textContent = data.message || "Update failed";
        showToast(data.message || data.detail || "Update failed", "error");
      }
    } catch (err) {
      clearInterval(progressTimer);
      $("#updProgressText").textContent = `Error: ${err.message}`;
      showToast(`Error: ${err.message}`, "error");
    } finally {
      setTimeout(() => $("#updProgress").classList.add("hidden"), 5000);
      $("#updApplyAllBtn").disabled = false;
      $("#updApplySecurityBtn").disabled = false;
    }
  }

  // ============================================================
  // Deployment View
  // ============================================================

  async function loadDeployView() {
    await loadDeploymentStatus();
    setupDeployEvents();
  }

  function setupDeployEvents() {
    // Tab switching
    $$("#view-deploy .tab-btn").forEach((btn) => {
      btn.addEventListener("click", () => {
        const tab = btn.dataset.deployTab;
        $$("#view-deploy .tab-btn").forEach((b) => b.classList.remove("active"));
        btn.classList.add("active");
        $$(".deploy-panel").forEach((p) => p.classList.add("hidden"));
        $(`#deploy${tab.charAt(0).toUpperCase() + tab.slice(1)}Panel`)?.classList.remove("hidden");
      });
    });

    const previewSys = $("#deployPreviewSystemdBtn");
    const installSys = $("#deployInstallSystemdBtn");
    const previewNgx = $("#deployPreviewNginxBtn");
    const installNgx = $("#deployInstallNginxBtn");
    const refreshLogs = $("#deployRefreshLogsBtn");

    if (previewSys) previewSys.onclick = previewSystemd;
    if (installSys) installSys.onclick = installSystemd;
    if (previewNgx) previewNgx.onclick = previewNginx;
    if (installNgx) installNgx.onclick = installNginx;
    if (refreshLogs) refreshLogs.onclick = loadDeployLogs;
  }

  async function loadDeploymentStatus() {
    try {
      const { res, data } = await api("/deployment/status");
      if (res.ok) {
        const statusPill = $("#deployServiceStatus");
        statusPill.textContent = data.service_status;
        statusPill.className = `pill ${data.service_active ? "ok" : "warn"}`;

        const enabledPill = $("#deployServiceEnabled");
        enabledPill.textContent = data.service_enabled ? "Yes" : "No";
        enabledPill.className = `pill ${data.service_enabled ? "ok" : "neutral"}`;

        $("#deployPython").textContent = data.python_version;
        $("#deployAppDir").textContent = data.app_dir;

        const ngxConfig = $("#deployNginxConfig");
        ngxConfig.textContent = data.nginx_config_exists ? "Yes" : "No";
        ngxConfig.className = `pill ${data.nginx_config_exists ? "ok" : "neutral"}`;

        const ngxEnabled = $("#deployNginxEnabled");
        ngxEnabled.textContent = data.nginx_config_enabled ? "Yes" : "No";
        ngxEnabled.className = `pill ${data.nginx_config_enabled ? "ok" : "neutral"}`;
      }
    } catch (err) {
      showToast(`Error loading status: ${err.message}`, "error");
    }
  }

  async function deployServiceAction(action) {
    try {
      const { res, data } = await api("/deployment/systemd/control", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ action }),
      });
      if (res.ok && data.success) {
        showToast(data.message, "success");
        setTimeout(loadDeploymentStatus, 1000);
      } else {
        showToast(data.message || data.detail || `Failed to ${action} service`, "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function reloadNginx() {
    try {
      const { res, data } = await api("/deployment/nginx/reload", { method: "POST" });
      if (res.ok && data.success) {
        showToast("Nginx reloaded", "success");
      } else {
        showToast(data.message || data.detail || "Nginx reload failed", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function previewSystemd() {
    try {
      const port = parseInt($("#deployPort").value) || 8000;
      const { res, data } = await api("/deployment/systemd/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ port }),
      });
      if (res.ok) {
        $("#deploySystemdPreview").textContent = data.content;
      } else {
        showToast(data.detail || "Preview failed", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function installSystemd() {
    if (!confirm("Install/overwrite the systemd service unit?")) return;
    try {
      const port = parseInt($("#deployPort").value) || 8000;
      const { res, data } = await api("/deployment/systemd/install", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ port }),
      });
      if (res.ok && data.success) {
        showToast(data.message, "success");
        loadDeploymentStatus();
      } else {
        showToast(data.message || data.detail || "Install failed", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  function getNginxConfigFromForm() {
    return {
      server_name: $("#deployServerName").value.trim(),
      proxy_port: parseInt($("#deployProxyPort").value) || 8000,
      root_dir: $("#deployWebRoot").value.trim(),
      ssl_enabled: $("#deploySslEnabled").checked,
      ssl_cert_path: $("#deploySslCert").value.trim(),
      ssl_key_path: $("#deploySslKey").value.trim(),
      php_enabled: $("#deployPhpEnabled").checked,
    };
  }

  async function previewNginx() {
    try {
      const config = getNginxConfigFromForm();
      const { res, data } = await api("/deployment/nginx/preview", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      if (res.ok) {
        $("#deployNginxPreview").textContent = data.content;
      } else {
        showToast(data.detail || "Preview failed", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function installNginx() {
    if (!confirm("Install/overwrite the nginx site config and reload?")) return;
    try {
      const config = getNginxConfigFromForm();
      const { res, data } = await api("/deployment/nginx/install", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(config),
      });
      if (res.ok && data.success) {
        showToast(data.message, "success");
        loadDeploymentStatus();
      } else {
        showToast(data.message || data.detail || "Install failed", "error");
      }
    } catch (err) {
      showToast(`Error: ${err.message}`, "error");
    }
  }

  async function loadDeployLogs() {
    const lines = parseInt($("#deployLogLines").value) || 100;
    $("#deployLogsOutput").textContent = "Loading...";
    try {
      const { res, data } = await api(`/deployment/logs?lines=${lines}`);
      if (res.ok) {
        $("#deployLogsOutput").textContent = data.logs || "No logs available.";
        $("#deployLogsOutput").scrollTop = $("#deployLogsOutput").scrollHeight;
      } else {
        $("#deployLogsOutput").textContent = data.detail || "Failed to load logs.";
      }
    } catch (err) {
      $("#deployLogsOutput").textContent = `Error: ${err.message}`;
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
    showToast,
    // File Manager
    editFile,
    closeFileEditor,
    downloadFile,
    showFileProps,
    closeFileProps,
    navigateToPath,
    renameFile,
    closeRenameModal,
    chmodFile,
    closeChmodModal,
    deleteFile,
    closeFilesNewModal,
    // Database Management
    showDbDetail,
    exportDatabase,
    dropDatabase,
    closeDbCreateModal,
    closeDbPasswordModal,
    closeDbDetailModal,
    // FTP Management
    setFtpPassword,
    enableFtpAccount,
    disableFtpAccount,
    deleteFtpAccount,
    kickFtpSession,
    closeFtpCreateModal,
    closeFtpPasswordModal,
    closeFtpCreatedModal,
    // Cron Management
    loadCronJobs,
    showCronModal,
    closeCronModal,
    toggleCronJob,
    editCronJob,
    deleteCronJob,
    // Security Management
    loadSshKeys,
    addSshKey,
    deleteSshKey,
    banIP,
    unbanIP,
    enableUfw,
    disableUfw,
    addUfwRule,
    deleteUfwRule,
    setModSecurityMode,
    // SSL Management
    showSslRequestModal,
    closeSslModal,
    closeSslDetailModal,
    showCertDetail,
    renewCert,
    renewAllCerts,
    deleteCert,
    // Updates & Deployment
    deployServiceAction,
    reloadNginx,
    // Grader File Picker
    closeGradeFilePicker,
  };

  // Start
  init();
})();
