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
        <a href="#/users" class="nav-link" data-route="users">Users</a>
        <a href="#/system" class="nav-link" data-route="system">System</a>
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

      <!-- Roster Import Section -->
      <article class="card glass roster-import-card">
        <h3>Import Students from CSV Roster</h3>
        <p class="muted">Upload a CSV with columns: FirstName, LastName, StudentID</p>
        
        <div id="rosterUploadArea" class="file-upload-area">
          <div class="upload-icon">📄</div>
          <p class="upload-text">Drop CSV file here or <label class="upload-link">browse<input type="file" id="rosterFileInput" accept=".csv" hidden /></label></p>
          <p class="upload-hint">Usernames: lastnamefirstinitial • Passwords: 6-digit StudentID</p>
        </div>

        <div id="rosterTermRow" class="roster-term-row hidden">
          <label>Term <span class="optional">(optional)</span>
            <input id="rosterTerm" class="input" placeholder="2026sp" />
          </label>
        </div>

        <!-- Preview Table -->
        <div id="rosterPreview" class="roster-preview hidden">
          <div class="roster-preview-header">
            <h4>Preview <span id="rosterPreviewCount"></span></h4>
            <button id="rosterImportBtn" class="btn primary">Import All</button>
          </div>
          <div class="roster-table-wrap">
            <table class="roster-table">
              <thead>
                <tr>
                  <th>First Name</th>
                  <th>Last Name</th>
                  <th>Student ID</th>
                  <th>→</th>
                  <th>Username</th>
                  <th>Password</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody id="rosterPreviewBody"></tbody>
            </table>
          </div>
        </div>

        <!-- Import Progress -->
        <div id="rosterProgress" class="roster-progress hidden">
          <div class="progress-bar">
            <div class="progress-fill" id="rosterProgressFill"></div>
          </div>
          <p id="rosterProgressText" class="muted">Importing...</p>
        </div>

        <!-- Import Results -->
        <div id="rosterResults" class="roster-results hidden">
          <div class="roster-results-summary">
            <span class="result-stat ok"><span id="rosterCreatedCount">0</span> created</span>
            <span class="result-stat warn"><span id="rosterSkippedCount">0</span> skipped</span>
            <span class="result-stat error"><span id="rosterFailedCount">0</span> failed</span>
          </div>
          <details>
            <summary>View Details</summary>
            <div class="roster-table-wrap">
              <table class="roster-table">
                <thead>
                  <tr>
                    <th>Username</th>
                    <th>Status</th>
                    <th>Message</th>
                  </tr>
                </thead>
                <tbody id="rosterResultsBody"></tbody>
              </table>
            </div>
          </details>
          <button id="rosterResetBtn" class="btn">Upload Another Roster</button>
        </div>
      </article>

      <article class="card glass">
        <h3>Operation Result</h3>
        <pre id="adminOutput" class="output">No operation run yet.</pre>
      </article>
    </section>

    <!-- View: System Monitoring -->
    <section id="view-system" class="view hidden">
      <div class="view-header">
        <h2>System</h2>
        <p class="muted">Server health, services, logs, and backups</p>
      </div>
      
      <!-- System Stats Cards - matches Overview pattern -->
      <div class="grid-2">
        <article class="card glass">
          <h3>Server Health</h3>
          <div class="health-stats">
            <div class="health-stat">
              <div class="health-stat-header">
                <span class="health-stat-label">CPU</span>
                <span id="sysCpu" class="health-stat-value">—</span>
              </div>
              <div class="health-bar"><div id="sysCpuBar" class="health-bar-fill"></div></div>
            </div>
            <div class="health-stat">
              <div class="health-stat-header">
                <span class="health-stat-label">Memory</span>
                <span id="sysMemory" class="health-stat-value">—</span>
              </div>
              <div class="health-bar"><div id="sysMemoryBar" class="health-bar-fill"></div></div>
            </div>
            <div class="health-stat">
              <div class="health-stat-header">
                <span class="health-stat-label">Disk</span>
                <span id="sysDisk" class="health-stat-value">—</span>
              </div>
              <div class="health-bar"><div id="sysDiskBar" class="health-bar-fill"></div></div>
            </div>
          </div>
        </article>
        <article class="card glass stat-card">
          <p class="stat-label">Uptime</p>
          <p id="sysUptime" class="stat-value">—</p>
          <p id="sysLoadAvg" class="muted small"></p>
        </article>
      </div>

      <!-- System Sub-tabs - matches Admin view pattern -->
      <article class="card glass">
        <div class="action-tabs">
          <button class="tab-btn active" data-sys-tab="services">Services</button>
          <button class="tab-btn" data-sys-tab="logs">Logs</button>
          <button class="tab-btn" data-sys-tab="processes">Processes</button>
          <button class="tab-btn" data-sys-tab="backups">Backups</button>
        </div>

        <!-- Services Panel -->
        <div id="sysServicesPanel" class="sys-panel">
          <div class="panel-actions">
            <button id="refreshServicesBtn" class="btn btn-sm btn-ghost">↻ Refresh</button>
          </div>
          <div class="services-grid" id="servicesGrid">
            <p class="muted">Loading services...</p>
          </div>
        </div>

        <!-- Logs Panel -->
        <div id="sysLogsPanel" class="sys-panel hidden">
          <div class="panel-form">
            <label>Log File
              <select id="logSelect" class="input">
                <option value="">Select a log file...</option>
              </select>
            </label>
            <label>Search <span class="optional">(optional)</span>
              <input id="logSearch" class="input" placeholder="Pattern to search..." />
            </label>
            <div class="btn-group">
              <button id="logViewBtn" class="btn">View Log</button>
              <button id="logSearchBtn" class="btn">Search</button>
              <button id="logStreamBtn" class="btn primary">Live Stream</button>
            </div>
          </div>
          <pre id="logOutput" class="output">Select a log file to view its contents.</pre>
        </div>

        <!-- Processes Panel -->
        <div id="sysProcessesPanel" class="sys-panel hidden">
          <div class="panel-actions">
            <button id="refreshProcessesBtn" class="btn btn-sm btn-ghost">↻ Refresh</button>
          </div>
          <div class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>PID</th>
                  <th>Process</th>
                  <th>User</th>
                  <th>CPU</th>
                  <th>Memory</th>
                  <th>Status</th>
                </tr>
              </thead>
              <tbody id="processesBody">
                <tr><td colspan="6" class="muted">Loading...</td></tr>
              </tbody>
            </table>
          </div>
        </div>

        <!-- Backups Panel -->
        <div id="sysBackupsPanel" class="sys-panel hidden">
          <div class="panel-form panel-form-inline">
            <label>Backup Type
              <select id="backupType" class="input">
                <option value="full">Full Backup</option>
                <option value="term">Term Only</option>
                <option value="student">Single Student</option>
              </select>
            </label>
            <label id="backupTermLabel" class="hidden">Term
              <select id="backupTerm" class="input">
                <option value="">Select term...</option>
              </select>
            </label>
            <label id="backupStudentLabel" class="hidden">Student
              <select id="backupStudent" class="input">
                <option value="">Select student...</option>
              </select>
            </label>
            <button id="createBackupBtn" class="btn primary">Create Backup</button>
          </div>
          <div id="backupProgress" class="progress-container hidden">
            <div class="progress-bar"><div id="backupProgressFill" class="progress-fill"></div></div>
            <p id="backupProgressText" class="muted small">Creating backup...</p>
          </div>
          <div class="table-wrap">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Backup</th>
                  <th>Type</th>
                  <th>Size</th>
                  <th>Created</th>
                  <th></th>
                </tr>
              </thead>
              <tbody id="backupsBody">
                <tr><td colspan="5" class="muted">Loading...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </article>
    </section>

    <!-- View: Users -->
    <section id="view-users" class="view hidden">
      <div class="view-header">
        <h2>User Management</h2>
        <p class="muted">Manage student accounts, quotas, and access</p>
      </div>

      <!-- Filters Bar -->
      <div class="filters-bar card glass">
        <div class="filter-group">
          <label>Term
            <select id="usersTermFilter" class="input">
              <option value="">All Terms</option>
            </select>
          </label>
          <label>Status
            <select id="usersStatusFilter" class="input">
              <option value="">All</option>
              <option value="active">Active</option>
              <option value="suspended">Suspended</option>
            </select>
          </label>
          <label>Search
            <input type="text" id="usersSearchInput" class="input" placeholder="Username...">
          </label>
        </div>
        <div class="filter-actions">
          <button id="refreshUsersBtn" class="btn btn-ghost">↻ Refresh</button>
          <span id="usersCount" class="muted"></span>
        </div>
      </div>

      <!-- Users Table -->
      <article class="card glass">
        <div class="table-container">
          <table class="data-table">
            <thead>
              <tr>
                <th><input type="checkbox" id="selectAllUsers"></th>
                <th>Username</th>
                <th>Term</th>
                <th>Status</th>
                <th>Disk Usage</th>
                <th>Files</th>
                <th>Website</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody id="usersTableBody">
              <tr><td colspan="8" class="muted">Loading users...</td></tr>
            </tbody>
          </table>
        </div>

        <!-- Bulk Actions -->
        <div id="usersBulkActions" class="bulk-actions hidden">
          <span id="selectedUsersCount">0 selected</span>
          <button class="btn btn-sm btn-danger" onclick="app.bulkSuspendUsers()">Suspend Selected</button>
          <button class="btn btn-sm" onclick="app.bulkUnsuspendUsers()">Unsuspend Selected</button>
        </div>
      </article>

      <!-- User Detail Modal -->
      <div id="userDetailModal" class="modal hidden">
        <div class="modal-backdrop"></div>
        <div class="modal-content card">
          <div class="modal-header">
            <h3 id="userDetailTitle">User Details</h3>
            <button class="btn-close" onclick="app.closeUserModal()">&times;</button>
          </div>
          <div class="modal-body" id="userDetailBody">
            <!-- Populated dynamically -->
          </div>
          <div class="modal-footer">
            <button class="btn" onclick="app.closeUserModal()">Close</button>
          </div>
        </div>
      </div>
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
