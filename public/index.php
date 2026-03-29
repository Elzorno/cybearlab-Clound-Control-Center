<?php
declare(strict_types=1);
?>
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>CybearLab.cloud Control Center</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=Manrope:wght@500;600;700;800&family=IBM+Plex+Mono:wght@500&display=swap" rel="stylesheet">
  <link rel="stylesheet" href="./styles.css" />
</head>
<body>
  <div class="bg-layer"></div>

  <!-- Login Gate -->
  <div id="loginGate" class="login-gate">
    <div class="login-card glass">
      <p class="eyebrow">CybearLab.cloud</p>
      <h1>Control Center</h1>
      <p class="muted">Sign in to access admin and grading tools.</p>
      <label>Username
        <input id="username" class="input" value="admin" autocomplete="username" />
      </label>
      <label>Password
        <input id="password" class="input" type="password" value="change-me-now" autocomplete="current-password" />
      </label>
      <button id="loginBtn" class="btn primary full-width">Sign In</button>
      <p id="loginError" class="error-text"></p>
    </div>
  </div>

  <!-- Main App (hidden until authenticated) -->
  <main id="appShell" class="app-shell hidden">
    <header class="topbar glass">
      <div class="topbar-brand">
        <p class="eyebrow">CybearLab.cloud</p>
        <h1>Control Center</h1>
      </div>
      <nav class="topbar-nav">
        <a href="#/" class="nav-link" data-route="overview">Overview</a>
        <a href="#/grader" class="nav-link" data-route="grader">Auto-Grader</a>
        <a href="#/admin" class="nav-link" data-route="admin">Student Admin</a>
        <a href="#/reports" class="nav-link" data-route="reports">Reports</a>
        <a href="#/settings" class="nav-link" data-route="settings">Settings</a>
      </nav>
      <div class="topbar-actions">
        <span id="statusPill" class="pill ok">Signed in</span>
        <button id="logoutBtn" class="btn btn-sm">Sign Out</button>
      </div>
    </header>

    <!-- View: Overview -->
    <section id="view-overview" class="view">
      <div class="view-header">
        <h2>Overview</h2>
        <p class="muted">System status and quick actions</p>
      </div>
      <div class="grid-3">
        <article class="card glass stat-card">
          <p class="stat-label">System Status</p>
          <p id="systemStatus" class="stat-value ok">Healthy</p>
        </article>
        <article class="card glass stat-card">
          <p class="stat-label">Recent Grades</p>
          <p id="recentGradesCount" class="stat-value">—</p>
        </article>
        <article class="card glass stat-card">
          <p class="stat-label">API Endpoint</p>
          <p id="apiEndpoint" class="stat-value mono small">—</p>
        </article>
      </div>
      <div class="grid-2">
        <article class="card glass">
          <h3>Quick Actions</h3>
          <div class="quick-actions">
            <a href="#/grader" class="action-card">
              <span class="action-icon">📊</span>
              <span class="action-label">Grade a URL</span>
            </a>
            <a href="#/admin" class="action-card">
              <span class="action-icon">👤</span>
              <span class="action-label">Add Student</span>
            </a>
            <a href="#/reports" class="action-card">
              <span class="action-icon">📋</span>
              <span class="action-label">View Reports</span>
            </a>
          </div>
        </article>
        <article class="card glass">
          <h3>Recent Grade Runs</h3>
          <div id="recentGrades" class="recent-list">
            <p class="muted">Loading...</p>
          </div>
        </article>
      </div>
    </section>

    <!-- View: Auto-Grader -->
    <section id="view-grader" class="view hidden">
      <div class="view-header">
        <h2>Auto-Grader</h2>
        <p class="muted">Submit a URL for automated rubric-based grading</p>
      </div>
      <div class="grader-layout">
        <article class="card glass grader-input-card">
          <h3>Grade a Website</h3>
          <label>Site URL
            <input id="gradeUrl" class="input" placeholder="https://student.example.com/project" />
          </label>
          <label>Student Username <span class="optional">(optional)</span>
            <input id="gradeStudent" class="input" placeholder="jsmith" />
          </label>
          <label>Term <span class="optional">(optional)</span>
            <input id="gradeTerm" class="input" placeholder="2026sp" />
          </label>
          <button id="gradeBtn" class="btn primary full-width">Run Grader</button>
        </article>

        <div class="grader-results">
          <!-- Status Timeline -->
          <article id="gradeStatus" class="card glass hidden">
            <div class="status-timeline">
              <div class="status-step" data-step="queued">
                <span class="step-dot"></span>
                <span class="step-label">Queued</span>
              </div>
              <div class="status-step" data-step="crawling">
                <span class="step-dot"></span>
                <span class="step-label">Crawling</span>
              </div>
              <div class="status-step" data-step="validating">
                <span class="step-dot"></span>
                <span class="step-label">Validating</span>
              </div>
              <div class="status-step" data-step="scoring">
                <span class="step-dot"></span>
                <span class="step-label">Scoring</span>
              </div>
              <div class="status-step" data-step="completed">
                <span class="step-dot"></span>
                <span class="step-label">Done</span>
              </div>
            </div>
          </article>

          <!-- Score Summary -->
          <article id="gradeScore" class="card glass hidden">
            <div class="score-header">
              <div class="score-gauge">
                <svg viewBox="0 0 100 100" class="gauge-svg">
                  <circle cx="50" cy="50" r="45" class="gauge-bg" />
                  <circle cx="50" cy="50" r="45" class="gauge-fill" id="gaugeCircle" />
                </svg>
                <span class="gauge-value" id="totalScore">—</span>
              </div>
              <div class="score-meta">
                <p class="score-title">Total Score</p>
                <p class="score-url" id="scoredUrl">—</p>
              </div>
            </div>
          </article>

          <!-- Rubric Breakdown -->
          <article id="gradeRubric" class="card glass hidden">
            <h3>Rubric Breakdown</h3>
            <div id="rubricSections" class="rubric-grid"></div>
          </article>

          <!-- Feedback -->
          <article id="gradeFeedback" class="card glass hidden">
            <h3>Feedback &amp; Recommendations</h3>
            <ul id="feedbackList" class="feedback-list"></ul>
          </article>

          <!-- Raw JSON (collapsible) -->
          <details id="gradeRaw" class="card glass hidden">
            <summary>Raw JSON Response</summary>
            <pre id="gradeRawJson" class="output"></pre>
          </details>
        </div>
      </div>
    </section>

    <!-- View: Student Admin -->
    <section id="view-admin" class="view hidden">
      <div class="view-header">
        <h2>Student Admin</h2>
        <p class="muted">Manage student accounts and server operations</p>
      </div>
      <div class="grid-2">
        <article class="card glass">
          <h3>Single Student Actions</h3>
          <div class="action-tabs">
            <button class="tab-btn active" data-action="add_student">Add</button>
            <button class="tab-btn" data-action="reset_password">Reset Password</button>
            <button class="tab-btn" data-action="disable_student">Disable</button>
          </div>
          <div class="admin-form">
            <label>Username
              <input id="adminUsername" class="input" placeholder="jsmith" required />
            </label>
            <label>Term
              <input id="adminTerm" class="input" placeholder="2026sp" />
            </label>
            <div id="adminExtraFields"></div>
            <button id="adminSubmitBtn" class="btn primary">Add Student</button>
          </div>
        </article>

        <article class="card glass">
          <h3>Bulk Operations</h3>
          <div class="bulk-actions">
            <button class="btn" data-bulk="fix_perms_all">Fix Permissions (All)</button>
            <button class="btn" data-bulk="https_students_all">Enable HTTPS (All Students)</button>
          </div>
          <p class="muted small">These operations run across all student accounts.</p>
        </article>
      </div>

      <article class="card glass">
        <h3>Operation Result</h3>
        <pre id="adminOutput" class="output">No operation run yet.</pre>
      </article>
    </section>

    <!-- View: Reports -->
    <section id="view-reports" class="view hidden">
      <div class="view-header">
        <h2>Grading Reports</h2>
        <p class="muted">Browse and filter historical grading runs</p>
      </div>
      <article class="card glass">
        <div class="reports-filters">
          <label>Term
            <input id="filterTerm" class="input" placeholder="2026sp" />
          </label>
          <label>Student
            <input id="filterStudent" class="input" placeholder="jsmith" />
          </label>
          <button id="filterBtn" class="btn">Apply Filters</button>
          <button id="clearFiltersBtn" class="btn btn-ghost">Clear</button>
        </div>
      </article>
      <article class="card glass">
        <div class="reports-table-wrap">
          <table class="reports-table">
            <thead>
              <tr>
                <th>Date</th>
                <th>Student</th>
                <th>URL</th>
                <th>Score</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody id="reportsBody">
              <tr><td colspan="6" class="muted">Loading...</td></tr>
            </tbody>
          </table>
        </div>
        <div class="reports-pagination">
          <button id="prevPageBtn" class="btn btn-sm" disabled>Previous</button>
          <span id="pageInfo" class="page-info">Page 1</span>
          <button id="nextPageBtn" class="btn btn-sm">Next</button>
        </div>
      </article>

      <!-- Run Detail Modal -->
      <div id="runDetailModal" class="modal hidden">
        <div class="modal-backdrop"></div>
        <div class="modal-content card glass">
          <div class="modal-header">
            <h3>Run Details</h3>
            <button class="modal-close">&times;</button>
          </div>
          <div id="runDetailBody" class="modal-body"></div>
        </div>
      </div>
    </section>

    <!-- View: Settings -->
    <section id="view-settings" class="view hidden">
      <div class="view-header">
        <h2>Settings</h2>
        <p class="muted">API configuration and preferences</p>
      </div>
      <article class="card glass">
        <h3>API Configuration</h3>
        <label>API Base URL
          <input id="apiBase" class="input mono" placeholder="auto-detected" />
        </label>
        <p class="muted small">Leave empty for auto-detection. Changes apply immediately.</p>
      </article>
    </section>

  </main>

  <script src="./app.js" defer></script>
</body>
</html>
