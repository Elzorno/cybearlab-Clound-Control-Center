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
        <div class="nav-dropdown">
          <button class="nav-link nav-dropdown-trigger">Grading <span class="caret">▾</span></button>
          <div class="nav-dropdown-menu">
            <a href="#/grader" class="nav-link" data-route="grader">Auto-Grader</a>
            <a href="#/admin" class="nav-link" data-route="admin">Student Admin</a>
            <a href="#/reports" class="nav-link" data-route="reports">Reports</a>
          </div>
        </div>
        <div class="nav-dropdown">
          <button class="nav-link nav-dropdown-trigger">Server <span class="caret">▾</span></button>
          <div class="nav-dropdown-menu">
            <a href="#/system" class="nav-link" data-route="system">System</a>
            <a href="#/dns" class="nav-link" data-route="dns">DNS</a>
            <a href="#/cron" class="nav-link" data-route="cron">Cron Jobs</a>
            <a href="#/security" class="nav-link" data-route="security">Security</a>
            <a href="#/ssl" class="nav-link" data-route="ssl">SSL/TLS</a>
          </div>
        </div>
        <div class="nav-dropdown">
          <button class="nav-link nav-dropdown-trigger">Storage <span class="caret">▾</span></button>
          <div class="nav-dropdown-menu">
            <a href="#/files" class="nav-link" data-route="files">Files</a>
            <a href="#/databases" class="nav-link" data-route="databases">Databases</a>
            <a href="#/ftp" class="nav-link" data-route="ftp">FTP Accounts</a>
          </div>
        </div>
        <div class="nav-dropdown">
          <button class="nav-link nav-dropdown-trigger">Admin <span class="caret">▾</span></button>
          <div class="nav-dropdown-menu">
            <a href="#/users" class="nav-link" data-route="users">Users</a>
            <a href="#/audit" class="nav-link" data-route="audit">Audit Log</a>
            <a href="#/settings" class="nav-link" data-route="settings">Settings</a>
          </div>
        </div>
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

    <!-- View: File Manager -->
    <section id="view-files" class="view hidden">
      <div class="view-header">
        <h2>File Manager</h2>
        <p class="muted">Browse and manage user files</p>
      </div>

      <!-- User Selection -->
      <div class="filters-bar card glass">
        <div class="filter-group">
          <label>User
            <select id="filesUserSelect" class="input">
              <option value="">Select a user...</option>
            </select>
          </label>
          <span id="filesCurrentPath" class="files-path mono"></span>
        </div>
        <div class="filter-actions">
          <button id="filesRefreshBtn" class="btn btn-ghost">↻ Refresh</button>
          <span id="filesStats" class="muted"></span>
        </div>
      </div>

      <!-- File Browser -->
      <article class="card glass files-browser">
        <!-- Toolbar -->
        <div class="files-toolbar">
          <div class="files-toolbar-left">
            <button id="filesUpBtn" class="btn btn-sm" title="Go up">↑ Up</button>
            <button id="filesHomeBtn" class="btn btn-sm" title="Go to root">🏠 Home</button>
          </div>
          <div class="breadcrumb" id="filesBreadcrumb"></div>
          <div class="files-toolbar-right">
            <button id="filesNewFileBtn" class="btn btn-sm">+ New File</button>
            <button id="filesNewFolderBtn" class="btn btn-sm">+ New Folder</button>
            <button id="filesUploadBtn" class="btn btn-sm primary">↑ Upload</button>
            <input type="file" id="filesUploadInput" hidden multiple />
          </div>
        </div>

        <!-- Files List/Grid -->
        <div class="files-list" id="filesList">
          <p class="muted">Select a user to browse files.</p>
        </div>

        <!-- Status Bar -->
        <div class="files-statusbar">
          <span id="filesItemCount">0 items</span>
          <span id="filesTotalSize"></span>
        </div>
      </article>

      <!-- File Editor Modal -->
      <div id="fileEditorModal" class="modal hidden">
        <div class="modal-backdrop" onclick="app.closeFileEditor()"></div>
        <div class="modal-content card file-editor-modal">
          <div class="modal-header">
            <h3 id="fileEditorTitle">Edit File</h3>
            <button class="btn-close" onclick="app.closeFileEditor()">&times;</button>
          </div>
          <div class="modal-body file-editor-body">
            <textarea id="fileEditorContent" class="file-editor-textarea" spellcheck="false"></textarea>
          </div>
          <div class="modal-footer">
            <span id="fileEditorInfo" class="muted"></span>
            <div class="modal-footer-actions">
              <button class="btn" onclick="app.closeFileEditor()">Cancel</button>
              <button id="fileEditorSaveBtn" class="btn primary">Save</button>
            </div>
          </div>
        </div>
      </div>

      <!-- File Properties Modal -->
      <div id="filePropsModal" class="modal hidden">
        <div class="modal-backdrop" onclick="app.closeFileProps()"></div>
        <div class="modal-content card">
          <div class="modal-header">
            <h3>File Properties</h3>
            <button class="btn-close" onclick="app.closeFileProps()">&times;</button>
          </div>
          <div class="modal-body" id="filePropsBody">
            <!-- Populated dynamically -->
          </div>
          <div class="modal-footer">
            <button class="btn" onclick="app.closeFileProps()">Close</button>
          </div>
        </div>
      </div>

      <!-- New File/Folder Modal -->
      <div id="filesNewModal" class="modal hidden">
        <div class="modal-backdrop" onclick="app.closeFilesNewModal()"></div>
        <div class="modal-content card">
          <div class="modal-header">
            <h3 id="filesNewModalTitle">New File</h3>
            <button class="btn-close" onclick="app.closeFilesNewModal()">&times;</button>
          </div>
          <div class="modal-body">
            <label>Name
              <input id="filesNewName" class="input" placeholder="filename.html" />
            </label>
          </div>
          <div class="modal-footer">
            <button class="btn" onclick="app.closeFilesNewModal()">Cancel</button>
            <button id="filesNewCreateBtn" class="btn primary">Create</button>
          </div>
        </div>
      </div>

      <!-- Chmod Modal -->
      <div id="filesChmodModal" class="modal hidden">
        <div class="modal-backdrop" onclick="app.closeChmodModal()"></div>
        <div class="modal-content card">
          <div class="modal-header">
            <h3>Change Permissions</h3>
            <button class="btn-close" onclick="app.closeChmodModal()">&times;</button>
          </div>
          <div class="modal-body">
            <label>Permissions (octal)
              <input id="filesChmodValue" class="input mono" placeholder="755" maxlength="4" />
            </label>
            <p class="muted small">Enter octal mode like 755, 644, etc.</p>
            <div class="chmod-presets">
              <button class="btn btn-sm" onclick="document.getElementById('filesChmodValue').value='755'">755</button>
              <button class="btn btn-sm" onclick="document.getElementById('filesChmodValue').value='644'">644</button>
              <button class="btn btn-sm" onclick="document.getElementById('filesChmodValue').value='600'">600</button>
              <button class="btn btn-sm" onclick="document.getElementById('filesChmodValue').value='777'">777</button>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn" onclick="app.closeChmodModal()">Cancel</button>
            <button id="filesChmodApplyBtn" class="btn primary">Apply</button>
          </div>
        </div>
      </div>

      <!-- Rename Modal -->
      <div id="filesRenameModal" class="modal hidden">
        <div class="modal-backdrop" onclick="app.closeRenameModal()"></div>
        <div class="modal-content card">
          <div class="modal-header">
            <h3>Rename</h3>
            <button class="btn-close" onclick="app.closeRenameModal()">&times;</button>
          </div>
          <div class="modal-body">
            <label>New Name
              <input id="filesRenameName" class="input" />
            </label>
          </div>
          <div class="modal-footer">
            <button class="btn" onclick="app.closeRenameModal()">Cancel</button>
            <button id="filesRenameApplyBtn" class="btn primary">Rename</button>
          </div>
        </div>
      </div>

    </section>

    <!-- View: Database Management -->
    <section id="view-databases" class="view hidden">
      <div class="view-header">
        <h2>Database Management</h2>
        <p class="muted">Manage MySQL databases and users</p>
      </div>

      <!-- User Selection -->
      <div class="filters-bar card glass">
        <div class="filter-group">
          <label>User
            <select id="dbUserSelect" class="input">
              <option value="">Select a user...</option>
            </select>
          </label>
        </div>
        <div class="filter-actions">
          <button id="dbRefreshBtn" class="btn btn-ghost">↻ Refresh</button>
          <button id="dbCreateBtn" class="btn primary">+ Create Database</button>
        </div>
      </div>

      <!-- Stats Cards -->
      <div class="card-grid cols-3" id="dbStats">
        <article class="card glass stat-card">
          <p class="stat-label">Databases</p>
          <p id="dbCount" class="stat-value">—</p>
        </article>
        <article class="card glass stat-card">
          <p class="stat-label">Total Tables</p>
          <p id="dbTableCount" class="stat-value">—</p>
        </article>
        <article class="card glass stat-card">
          <p class="stat-label">Total Size</p>
          <p id="dbTotalSize" class="stat-value">—</p>
        </article>
      </div>

      <!-- Database List -->
      <article class="card glass">
        <div class="card-header">
          <h3>Databases</h3>
        </div>
        <div class="card-body">
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Database Name</th>
                  <th>Tables</th>
                  <th>Size</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody id="dbTableBody">
                <tr><td colspan="4" class="muted">Select a user to view databases.</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </article>

      <!-- MySQL User Info -->
      <article class="card glass" id="dbUserInfo" style="display: none;">
        <div class="card-header">
          <h3>MySQL User</h3>
          <div class="card-actions">
            <button id="dbSetPasswordBtn" class="btn btn-sm">Set Password</button>
            <button id="dbCreateUserBtn" class="btn btn-sm primary">Create MySQL User</button>
          </div>
        </div>
        <div class="card-body" id="dbUserInfoBody">
          <p class="muted">Loading...</p>
        </div>
      </article>

      <!-- Create Database Modal -->
      <div id="dbCreateModal" class="modal hidden">
        <div class="modal-backdrop" onclick="app.closeDbCreateModal()"></div>
        <div class="modal-content card">
          <div class="modal-header">
            <h3>Create Database</h3>
            <button class="btn-close" onclick="app.closeDbCreateModal()">&times;</button>
          </div>
          <div class="modal-body">
            <label>Database Name
              <div class="input-group">
                <span class="input-prefix" id="dbNamePrefix"></span>
                <input id="dbCreateName" class="input" placeholder="myapp" />
              </div>
            </label>
            <p class="muted small">Database will be created as <span id="dbFullName"></span></p>
          </div>
          <div class="modal-footer">
            <button class="btn" onclick="app.closeDbCreateModal()">Cancel</button>
            <button id="dbCreateConfirmBtn" class="btn primary">Create</button>
          </div>
        </div>
      </div>

      <!-- Set Password Modal -->
      <div id="dbPasswordModal" class="modal hidden">
        <div class="modal-backdrop" onclick="app.closeDbPasswordModal()"></div>
        <div class="modal-content card">
          <div class="modal-header">
            <h3>Set MySQL Password</h3>
            <button class="btn-close" onclick="app.closeDbPasswordModal()">&times;</button>
          </div>
          <div class="modal-body">
            <label>New Password
              <input id="dbPassword" type="password" class="input" placeholder="Enter new password" />
            </label>
            <label>Confirm Password
              <input id="dbPasswordConfirm" type="password" class="input" placeholder="Confirm password" />
            </label>
          </div>
          <div class="modal-footer">
            <button class="btn" onclick="app.closeDbPasswordModal()">Cancel</button>
            <button id="dbSetPasswordConfirmBtn" class="btn primary">Set Password</button>
          </div>
        </div>
      </div>

      <!-- Database Detail Modal -->
      <div id="dbDetailModal" class="modal hidden">
        <div class="modal-backdrop" onclick="app.closeDbDetailModal()"></div>
        <div class="modal-content card modal-wide">
          <div class="modal-header">
            <h3 id="dbDetailTitle">Database Details</h3>
            <button class="btn-close" onclick="app.closeDbDetailModal()">&times;</button>
          </div>
          <div class="modal-body">
            <div class="table-container">
              <table class="data-table">
                <thead>
                  <tr>
                    <th>Table</th>
                    <th>Engine</th>
                    <th>Rows</th>
                    <th>Size</th>
                  </tr>
                </thead>
                <tbody id="dbDetailTableBody">
                  <tr><td colspan="4" class="muted">Loading...</td></tr>
                </tbody>
              </table>
            </div>
          </div>
          <div class="modal-footer">
            <button class="btn" onclick="app.closeDbDetailModal()">Close</button>
            <button class="btn" onclick="app.exportDatabase()">Export SQL</button>
          </div>
        </div>
      </div>
    </section>

    <!-- View: FTP Management -->
    <section id="view-ftp" class="view hidden">
      <div class="view-header">
        <h2>FTP Account Management</h2>
        <p class="muted">Create and manage FTP accounts for file access</p>
      </div>

      <!-- User Selection -->
      <div class="filters-bar card glass">
        <div class="filter-group">
          <label>User
            <select id="ftpUserSelect" class="input">
              <option value="">Select a user...</option>
            </select>
          </label>
        </div>
        <div class="filter-actions">
          <button id="ftpRefreshBtn" class="btn btn-ghost">↻ Refresh</button>
          <button id="ftpCreateBtn" class="btn primary">+ Create FTP Account</button>
        </div>
      </div>

      <!-- FTP Info -->
      <div class="card-grid cols-3">
        <article class="card glass stat-card">
          <p class="stat-label">FTP Accounts</p>
          <p id="ftpCount" class="stat-value">—</p>
        </article>
        <article class="card glass stat-card">
          <p class="stat-label">Active Sessions</p>
          <p id="ftpSessions" class="stat-value">—</p>
        </article>
        <article class="card glass stat-card">
          <p class="stat-label">FTP Server</p>
          <p id="ftpServer" class="stat-value">ftp.cybearlab.cloud</p>
        </article>
      </div>

      <!-- FTP Accounts List -->
      <article class="card glass">
        <div class="card-header">
          <h3>FTP Accounts</h3>
        </div>
        <div class="card-body">
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>Home Directory</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody id="ftpTableBody">
                <tr><td colspan="4" class="muted">Select a user to view FTP accounts.</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </article>

      <!-- Active Sessions -->
      <article class="card glass" id="ftpSessionsCard" style="display: none;">
        <div class="card-header">
          <h3>Active FTP Sessions</h3>
        </div>
        <div class="card-body">
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Username</th>
                  <th>IP Address</th>
                  <th>Connected</th>
                  <th>Current Dir</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody id="ftpSessionsTableBody">
                <tr><td colspan="5" class="muted">No active sessions.</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </article>

      <!-- Create FTP Account Modal -->
      <div id="ftpCreateModal" class="modal hidden">
        <div class="modal-backdrop" onclick="app.closeFtpCreateModal()"></div>
        <div class="modal-content card">
          <div class="modal-header">
            <h3>Create FTP Account</h3>
            <button class="btn-close" onclick="app.closeFtpCreateModal()">&times;</button>
          </div>
          <div class="modal-body">
            <label>Account Name
              <div class="input-group">
                <span class="input-prefix" id="ftpNamePrefix"></span>
                <input id="ftpCreateName" class="input" placeholder="webmaster" />
              </div>
            </label>
            <label>Password (leave blank to generate)
              <input id="ftpCreatePassword" type="password" class="input" placeholder="Auto-generate" />
            </label>
          </div>
          <div class="modal-footer">
            <button class="btn" onclick="app.closeFtpCreateModal()">Cancel</button>
            <button id="ftpCreateConfirmBtn" class="btn primary">Create</button>
          </div>
        </div>
      </div>

      <!-- FTP Password Modal -->
      <div id="ftpPasswordModal" class="modal hidden">
        <div class="modal-backdrop" onclick="app.closeFtpPasswordModal()"></div>
        <div class="modal-content card">
          <div class="modal-header">
            <h3>Set FTP Password</h3>
            <button class="btn-close" onclick="app.closeFtpPasswordModal()">&times;</button>
          </div>
          <div class="modal-body">
            <input id="ftpPasswordAccount" type="hidden" />
            <label>New Password
              <input id="ftpNewPassword" type="password" class="input" placeholder="Enter new password" />
            </label>
          </div>
          <div class="modal-footer">
            <button class="btn" onclick="app.closeFtpPasswordModal()">Cancel</button>
            <button id="ftpSetPasswordConfirmBtn" class="btn primary">Set Password</button>
          </div>
        </div>
      </div>

      <!-- Created Account Modal (shows credentials) -->
      <div id="ftpCreatedModal" class="modal hidden">
        <div class="modal-backdrop" onclick="app.closeFtpCreatedModal()"></div>
        <div class="modal-content card">
          <div class="modal-header">
            <h3>FTP Account Created</h3>
            <button class="btn-close" onclick="app.closeFtpCreatedModal()">&times;</button>
          </div>
          <div class="modal-body">
            <div class="alert alert-success">FTP account created successfully!</div>
            <div class="props-grid">
              <div class="prop-row">
                <span class="prop-label">FTP Host</span>
                <span class="prop-value mono">ftp.cybearlab.cloud</span>
              </div>
              <div class="prop-row">
                <span class="prop-label">Username</span>
                <span class="prop-value mono" id="ftpCreatedUsername"></span>
              </div>
              <div class="prop-row">
                <span class="prop-label">Password</span>
                <span class="prop-value mono" id="ftpCreatedPassword"></span>
              </div>
              <div class="prop-row">
                <span class="prop-label">Directory</span>
                <span class="prop-value mono" id="ftpCreatedDirectory"></span>
              </div>
            </div>
            <p class="muted small">Save these credentials securely. The password won't be shown again.</p>
          </div>
          <div class="modal-footer">
            <button class="btn primary" onclick="app.closeFtpCreatedModal()">Done</button>
          </div>
        </div>
      </div>
    </section>

    <!-- View: DNS Management -->
    <section id="view-dns" class="view hidden">
      <div class="view-header">
        <h2>DNS Management</h2>
        <p class="muted">Manage domain records and SSL certificates</p>
      </div>

      <!-- Domain Info Cards -->
      <div class="card-grid cols-3">
        <article class="card glass">
          <div class="card-header">
            <h3>Domain</h3>
          </div>
          <div class="card-body">
            <div class="stat-value" id="dnsDomain">—</div>
            <p class="muted">Primary domain</p>
          </div>
        </article>

        <article class="card glass">
          <div class="card-header">
            <h3>DNS Records</h3>
          </div>
          <div class="card-body">
            <div class="stat-value" id="dnsRecordCount">—</div>
            <p class="muted">Total records</p>
          </div>
        </article>

        <article class="card glass">
          <div class="card-header">
            <h3>Subdomains</h3>
          </div>
          <div class="card-body">
            <div class="stat-value" id="dnsSubdomainCount">—</div>
            <p class="muted">Student sites</p>
          </div>
        </article>
      </div>

      <!-- SSL Certificate Status -->
      <article class="card glass">
        <div class="card-header">
          <h3>SSL Certificate</h3>
        </div>
        <div class="card-body" id="certStatus">
          <p class="muted">Loading certificate info...</p>
        </div>
      </article>

      <!-- DNS Records Table -->
      <article class="card glass">
        <div class="card-header">
          <h3>DNS Records</h3>
          <div class="card-actions">
            <select id="dnsTypeFilter" class="input input-sm">
              <option value="">All Types</option>
              <option value="A">A</option>
              <option value="AAAA">AAAA</option>
              <option value="CNAME">CNAME</option>
              <option value="TXT">TXT</option>
              <option value="MX">MX</option>
            </select>
            <input type="text" id="dnsSearchInput" class="input input-sm" placeholder="Search...">
            <button id="addDnsRecordBtn" class="btn btn-primary btn-sm">+ Add Record</button>
          </div>
        </div>
        <div class="card-body">
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Name</th>
                  <th>Content</th>
                  <th>TTL</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody id="dnsTableBody">
                <tr><td colspan="5" class="muted">Loading DNS records...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </article>

      <!-- Add DNS Record Modal -->
      <div id="dnsRecordModal" class="modal hidden">
        <div class="modal-backdrop" onclick="app.closeDnsModal && app.closeDnsModal()"></div>
        <div class="modal-content card">
          <div class="modal-header">
            <h3>Add DNS Record</h3>
            <button id="closeDnsModal" class="btn-close">&times;</button>
          </div>
          <form id="dnsRecordForm" class="modal-body">
            <div class="form-group">
              <label for="dnsRecordName">Name (subdomain)</label>
              <input type="text" id="dnsRecordName" name="name" class="input" placeholder="e.g., www, student1, @" required>
              <span class="hint">Use @ for root domain, * for wildcard</span>
            </div>
            <div class="form-group">
              <label for="dnsRecordType">Type</label>
              <select id="dnsRecordType" name="type" class="input" required>
                <option value="A">A (IPv4 Address)</option>
                <option value="AAAA">AAAA (IPv6 Address)</option>
                <option value="CNAME">CNAME (Alias)</option>
                <option value="TXT">TXT (Text Record)</option>
                <option value="MX">MX (Mail Server)</option>
              </select>
            </div>
            <div class="form-group">
              <label for="dnsRecordContent">Content</label>
              <input type="text" id="dnsRecordContent" name="content" class="input" placeholder="e.g., 72.61.7.180" required>
              <span class="hint">IP address, hostname, or text value</span>
            </div>
            <div class="form-group">
              <label for="dnsRecordTTL">TTL (seconds)</label>
              <select name="ttl" class="input">
                <option value="300">5 minutes</option>
                <option value="3600" selected>1 hour</option>
                <option value="14400">4 hours</option>
                <option value="86400">1 day</option>
              </select>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn" onclick="document.getElementById('dnsRecordModal').classList.add('hidden')">Cancel</button>
              <button type="submit" class="btn btn-primary">Create Record</button>
            </div>
          </form>
        </div>
      </div>
    </section>

    <!-- View: Audit Log -->
    <section id="view-audit" class="view hidden">
      <div class="view-header">
        <h2>Audit Log</h2>
        <p class="muted">Track all privileged operations and system events</p>
      </div>
      <article class="card glass">
        <div class="audit-filters">
          <label>Action Type
            <select id="auditFilterAction" class="input">
              <option value="">All Actions</option>
              <option value="auth.login">Login</option>
              <option value="admin.action.create">Admin Action</option>
              <option value="admin.action.read">Admin Action Read</option>
              <option value="admin.upload.roster">Roster Upload</option>
              <option value="grader.run.create">Grade Run</option>
              <option value="grader.run.list">Grade Run List</option>
              <option value="grader.run.read">Grade Run Read</option>
              <option value="system.backup.create">Backup Create</option>
            </select>
          </label>
          <label>Actor
            <input id="auditFilterActor" class="input" placeholder="username" />
          </label>
          <button id="auditFilterBtn" class="btn">Apply</button>
          <button id="auditClearBtn" class="btn btn-ghost">Clear</button>
        </div>
      </article>
      <article class="card glass">
        <div id="auditTimeline" class="audit-timeline">
          <p class="muted">Loading audit events...</p>
        </div>
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

    <!-- View: Cron Jobs -->
    <section id="view-cron" class="view hidden">
      <div class="view-header">
        <h2>Cron Jobs</h2>
        <p class="muted">Scheduled task management for users</p>
      </div>

      <!-- User Selection -->
      <article class="card glass">
        <div class="card-header">
          <h3>Select User</h3>
        </div>
        <div class="card-body">
          <div class="form-row">
            <input type="text" id="cronUsername" class="input" placeholder="Enter username" />
            <button id="cronLoadBtn" class="btn primary">Load Cron Jobs</button>
          </div>
        </div>
      </article>

      <!-- Cron Jobs Table -->
      <article class="card glass" id="cronJobsCard" style="display:none">
        <div class="card-header">
          <h3>Cron Jobs for <span id="cronUserLabel">—</span></h3>
          <button id="addCronBtn" class="btn btn-primary btn-sm">+ Add Cron Job</button>
        </div>
        <div class="card-body">
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Schedule</th>
                  <th>Command</th>
                  <th>Comment</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody id="cronTableBody">
                <tr><td colspan="5" class="muted">No cron jobs</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </article>

      <!-- Common Schedules Reference -->
      <article class="card glass">
        <div class="card-header">
          <h3>Common Schedules</h3>
        </div>
        <div class="card-body">
          <div id="commonSchedules" class="common-schedules-grid">
            <div class="schedule-item"><code>* * * * *</code> <span>Every minute</span></div>
            <div class="schedule-item"><code>0 * * * *</code> <span>Every hour</span></div>
            <div class="schedule-item"><code>0 0 * * *</code> <span>Daily at midnight</span></div>
            <div class="schedule-item"><code>0 0 * * 0</code> <span>Weekly (Sundays)</span></div>
            <div class="schedule-item"><code>0 0 1 * *</code> <span>Monthly</span></div>
            <div class="schedule-item"><code>*/5 * * * *</code> <span>Every 5 minutes</span></div>
          </div>
        </div>
      </article>

      <!-- Add/Edit Cron Job Modal -->
      <div id="cronModal" class="modal hidden">
        <div class="modal-backdrop"></div>
        <div class="modal-content card">
          <div class="modal-header">
            <h3 id="cronModalTitle">Add Cron Job</h3>
            <button class="modal-close">&times;</button>
          </div>
          <form id="cronForm" class="modal-body">
            <div class="form-group">
              <label>Minute (0-59)</label>
              <input type="text" id="cronMinute" class="input" placeholder="*" required>
            </div>
            <div class="form-group">
              <label>Hour (0-23)</label>
              <input type="text" id="cronHour" class="input" placeholder="*" required>
            </div>
            <div class="form-group">
              <label>Day of Month (1-31)</label>
              <input type="text" id="cronDay" class="input" placeholder="*" required>
            </div>
            <div class="form-group">
              <label>Month (1-12)</label>
              <input type="text" id="cronMonth" class="input" placeholder="*" required>
            </div>
            <div class="form-group">
              <label>Day of Week (0-6, Sun=0)</label>
              <input type="text" id="cronWeekday" class="input" placeholder="*" required>
            </div>
            <div class="form-group">
              <label>Command</label>
              <input type="text" id="cronCommand" class="input" placeholder="/path/to/script.sh" required>
            </div>
            <div class="form-group">
              <label>Comment (optional)</label>
              <input type="text" id="cronComment" class="input" placeholder="Backup script">
            </div>
            <input type="hidden" id="cronEditId" value="">
            <div class="modal-footer">
              <button type="button" class="btn" onclick="app.closeCronModal()">Cancel</button>
              <button type="submit" class="btn primary">Save</button>
            </div>
          </form>
        </div>
      </div>
    </section>

    <!-- View: Security -->
    <section id="view-security" class="view hidden">
      <div class="view-header">
        <h2>Security Center</h2>
        <p class="muted">SSH keys, firewall, and intrusion prevention</p>
      </div>

      <!-- SSH Keys Section -->
      <article class="card glass">
        <div class="card-header">
          <h3>SSH Keys</h3>
        </div>
        <div class="card-body">
          <div class="form-row">
            <input type="text" id="sshUsername" class="input" placeholder="Enter username" />
            <button id="sshLoadBtn" class="btn primary">Load SSH Keys</button>
          </div>
          <div id="sshKeysContainer" style="display:none; margin-top: 16px;">
            <h4>SSH Keys for <span id="sshUserLabel">—</span></h4>
            <div id="sshKeysList" class="ssh-keys-list">
              <p class="muted">No SSH keys</p>
            </div>
            <div class="form-group" style="margin-top: 12px;">
              <label>Add SSH Key</label>
              <textarea id="newSshKey" class="input" rows="3" placeholder="ssh-rsa AAAA... user@host"></textarea>
              <button id="addSshKeyBtn" class="btn primary btn-sm" style="margin-top: 8px;">Add Key</button>
            </div>
          </div>
        </div>
      </article>

      <!-- Fail2Ban Section -->
      <article class="card glass">
        <div class="card-header">
          <h3>Fail2Ban</h3>
          <span id="fail2banStatus" class="pill neutral">Unknown</span>
        </div>
        <div class="card-body">
          <div id="fail2banJails" class="jail-list">
            <p class="muted">Loading Fail2Ban status...</p>
          </div>
          <div class="form-row" style="margin-top: 12px;">
            <select id="fail2banJailSelect" class="input">
              <option value="">Select jail</option>
            </select>
            <input type="text" id="fail2banIP" class="input" placeholder="IP address" />
            <button id="banIPBtn" class="btn btn-sm">Ban IP</button>
            <button id="unbanIPBtn" class="btn btn-sm">Unban IP</button>
          </div>
        </div>
      </article>

      <!-- UFW Firewall Section -->
      <article class="card glass">
        <div class="card-header">
          <h3>UFW Firewall</h3>
          <span id="ufwStatus" class="pill neutral">Unknown</span>
        </div>
        <div class="card-body">
          <div class="form-row" style="margin-bottom: 12px;">
            <button id="ufwEnableBtn" class="btn primary btn-sm">Enable UFW</button>
            <button id="ufwDisableBtn" class="btn btn-sm">Disable UFW</button>
          </div>
          <h4>Firewall Rules</h4>
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>#</th>
                  <th>To</th>
                  <th>Action</th>
                  <th>From</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody id="ufwRulesBody">
                <tr><td colspan="5" class="muted">Loading rules...</td></tr>
              </tbody>
            </table>
          </div>
          <div class="form-row" style="margin-top: 12px;">
            <select id="ufwRuleType" class="input">
              <option value="allow">Allow</option>
              <option value="deny">Deny</option>
              <option value="limit">Limit</option>
            </select>
            <input type="text" id="ufwPort" class="input input-sm" placeholder="Port (e.g., 22)" />
            <select id="ufwProtocol" class="input">
              <option value="">Any</option>
              <option value="tcp">TCP</option>
              <option value="udp">UDP</option>
            </select>
            <input type="text" id="ufwFromIP" class="input input-sm" placeholder="From IP (optional)" />
            <button id="addUfwRuleBtn" class="btn primary btn-sm">Add Rule</button>
          </div>
        </div>
      </article>

      <!-- ModSecurity Section -->
      <article class="card glass">
        <div class="card-header">
          <h3>ModSecurity WAF</h3>
          <span id="modsecStatus" class="pill neutral">Unknown</span>
        </div>
        <div class="card-body">
          <div class="form-row">
            <select id="modsecMode" class="input">
              <option value="On">On (Block)</option>
              <option value="DetectionOnly">Detection Only</option>
              <option value="Off">Off</option>
            </select>
            <button id="setModsecModeBtn" class="btn primary btn-sm">Set Mode</button>
          </div>
          <p class="muted small" style="margin-top: 8px;">ModSecurity provides web application firewall protection.</p>
        </div>
      </article>
    </section>

    <!-- View: SSL Certificates -->
    <section id="view-ssl" class="view hidden">
      <div class="view-header">
        <h2>SSL/TLS Certificates</h2>
        <p class="muted">Let's Encrypt certificate management</p>
      </div>

      <!-- Certificate Stats -->
      <div class="card-grid cols-3">
        <article class="card glass">
          <div class="card-body">
            <div class="stat-value" id="sslTotalCerts">—</div>
            <p class="stat-label">Total Certificates</p>
          </div>
        </article>
        <article class="card glass">
          <div class="card-body">
            <div class="stat-value" id="sslValidCerts">—</div>
            <p class="stat-label">Valid</p>
          </div>
        </article>
        <article class="card glass">
          <div class="card-body">
            <div class="stat-value warn" id="sslExpiringSoon">—</div>
            <p class="stat-label">Expiring Soon</p>
          </div>
        </article>
      </div>

      <!-- Certificates Table -->
      <article class="card glass">
        <div class="card-header">
          <h3>SSL Certificates</h3>
          <div class="card-actions">
            <button id="renewAllCertsBtn" class="btn btn-sm">Renew All</button>
            <button id="requestCertBtn" class="btn btn-primary btn-sm">+ Request Certificate</button>
          </div>
        </div>
        <div class="card-body">
          <div class="table-container">
            <table class="data-table">
              <thead>
                <tr>
                  <th>Domain</th>
                  <th>Valid Until</th>
                  <th>Days Left</th>
                  <th>Status</th>
                  <th>Actions</th>
                </tr>
              </thead>
              <tbody id="sslTableBody">
                <tr><td colspan="5" class="muted">Loading certificates...</td></tr>
              </tbody>
            </table>
          </div>
        </div>
      </article>

      <!-- Expiry Warnings -->
      <article class="card glass" id="sslWarningsCard" style="display:none">
        <div class="card-header">
          <h3>Expiry Warnings</h3>
        </div>
        <div class="card-body">
          <div id="sslWarnings" class="warnings-list"></div>
        </div>
      </article>

      <!-- Request Certificate Modal -->
      <div id="sslRequestModal" class="modal hidden">
        <div class="modal-backdrop"></div>
        <div class="modal-content card">
          <div class="modal-header">
            <h3>Request SSL Certificate</h3>
            <button class="modal-close">&times;</button>
          </div>
          <form id="sslRequestForm" class="modal-body">
            <div class="form-group">
              <label>Domain(s)</label>
              <input type="text" id="sslDomains" class="input" placeholder="example.com, www.example.com" required>
              <span class="hint">Comma-separated list of domains</span>
            </div>
            <div class="form-group">
              <label>Email (optional)</label>
              <input type="email" id="sslEmail" class="input" placeholder="admin@example.com">
            </div>
            <div class="form-group">
              <label>Webroot Path (optional)</label>
              <input type="text" id="sslWebroot" class="input" placeholder="/var/www/html">
            </div>
            <div class="form-group">
              <label class="checkbox-label">
                <input type="checkbox" id="sslStaging">
                Use staging environment (for testing)
              </label>
            </div>
            <div class="modal-footer">
              <button type="button" class="btn" onclick="app.closeSslModal()">Cancel</button>
              <button type="submit" class="btn primary">Request Certificate</button>
            </div>
          </form>
        </div>
      </div>

      <!-- Certificate Details Modal -->
      <div id="sslDetailModal" class="modal hidden">
        <div class="modal-backdrop"></div>
        <div class="modal-content card">
          <div class="modal-header">
            <h3>Certificate Details</h3>
            <button class="modal-close">&times;</button>
          </div>
          <div id="sslDetailBody" class="modal-body">
            <p class="muted">Loading...</p>
          </div>
        </div>
      </div>
    </section>

    <!-- View: Settings -->
    <section id="view-settings" class="view hidden">
      <div class="view-header">
        <h2>Settings</h2>
        <p class="muted">Configuration and preferences</p>
      </div>

      <div class="grid-2">
        <!-- API Configuration -->
        <article class="card glass">
          <h3>API Configuration</h3>
          <label>API Base URL
            <input id="apiBase" class="input mono" placeholder="auto-detected" />
          </label>
          <p class="muted small">Leave empty for auto-detection. Changes apply immediately.</p>
        </article>

        <!-- Connection Status -->
        <article class="card glass">
          <h3>Connection Status</h3>
          <div class="settings-status-grid">
            <div class="settings-status-row">
              <span>Backend API</span>
              <span id="settingsApiStatus" class="pill neutral">Checking...</span>
            </div>
            <div class="settings-status-row">
              <span>Database</span>
              <span id="settingsDbStatus" class="pill neutral">Checking...</span>
            </div>
          </div>
        </article>
      </div>

      <!-- Grader Configuration -->
      <article class="card glass">
        <h3>Grader Configuration</h3>
        <div class="grid-3">
          <label>Max Pages per Crawl
            <input id="settingsMaxPages" class="input" type="number" value="30" min="1" max="100" />
          </label>
          <label>Request Timeout (seconds)
            <input id="settingsTimeout" class="input" type="number" value="15" min="5" max="60" />
          </label>
          <label>Validator Concurrency
            <input id="settingsConcurrency" class="input" type="number" value="3" min="1" max="10" />
          </label>
        </div>
        <p class="muted small">These settings affect all future grading runs. Changes are saved to your browser.</p>
        <button id="settingsSaveGraderBtn" class="btn primary" style="margin-top:12px">Save Grader Settings</button>
      </article>

      <!-- About -->
      <article class="card glass">
        <h3>About</h3>
        <div class="settings-about">
          <p><strong>CybearLab.cloud Control Center</strong></p>
          <p class="muted">Student hosting administration and auto-grading platform.</p>
          <div class="settings-status-grid" style="margin-top:12px">
            <div class="settings-status-row">
              <span>Version</span>
              <span class="mono" id="settingsVersion">—</span>
            </div>
            <div class="settings-status-row">
              <span>API Endpoint</span>
              <span class="mono" id="settingsEndpoint">—</span>
            </div>
          </div>
        </div>
      </article>
    </section>

  </main>

  <div id="toastContainer" class="toast-container"></div>

  <script src="./app.js" defer></script>
</body>
</html>
