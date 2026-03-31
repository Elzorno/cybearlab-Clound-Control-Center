# CybearLab.cloud Control Center — User Guide

> **Version:** 1.0 &nbsp;|&nbsp; **Last updated:** March 31, 2026

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Overview Dashboard](#2-overview-dashboard)
3. [Auto-Grader](#3-auto-grader)
4. [Student Admin](#4-student-admin)
5. [Grading Reports](#5-grading-reports)
6. [User Management](#6-user-management)
7. [File Manager](#7-file-manager)
8. [Database Management](#8-database-management)
9. [FTP Account Management](#9-ftp-account-management)
10. [DNS Management](#10-dns-management)
11. [Cron Job Manager](#11-cron-job-manager)
12. [Security Center](#12-security-center)
13. [SSL/TLS Certificates](#13-ssltls-certificates)
14. [System Monitoring](#14-system-monitoring)
15. [System Updates](#15-system-updates)
16. [Deployment](#16-deployment)
17. [Audit Log](#17-audit-log)
18. [Settings](#18-settings)
19. [Configuration Reference](#19-configuration-reference)
20. [Troubleshooting](#20-troubleshooting)

---

## 1. Getting Started

### 1.1 Accessing the Panel

Open your browser and navigate to:

```
https://admin.cybearlab.cloud
```

### 1.2 Signing In

| Field    | Default Value    |
|----------|------------------|
| Username | `admin`          |
| Password | `change-me-now`  |

Enter your credentials and click **Sign In** (or press **Enter** in the password field). On success you are taken to the Overview dashboard and a green "Signed in" pill appears in the top bar.

> **Important:** Change the default password immediately after your first login by setting the `BOOTSTRAP_ADMIN_PASSWORD` environment variable and restarting the API service.

### 1.3 Signing Out

Click **Sign Out** in the top-right corner. You will be returned to the login screen and your session token is discarded.

### 1.4 Navigation

The top navigation bar organizes all views into four dropdown groups:

| Group     | Views                                           |
|-----------|--------------------------------------------------|
| **Grading**  | Auto-Grader, Student Admin, Reports            |
| **Server**   | System, DNS, Cron Jobs, Security, SSL/TLS, Updates, Deployment |
| **Storage**  | Files, Databases, FTP Accounts                  |
| **Admin**    | Users, Audit Log, Settings                      |

The **Overview** link is always visible at the top level.

### 1.5 Help Tooltips

Every major view includes a **?** icon next to its heading. Hover over (or tap on mobile) the icon to see a brief description of what the view does.

---

## 2. Overview Dashboard

**Route:** `#/`

The dashboard shows an at-a-glance summary of the server and recent activity:

| Card              | Description                            |
|-------------------|----------------------------------------|
| System Status     | `Healthy`, `Degraded`, or `Unavailable` based on the `/health` endpoint |
| Recent Grades     | Count of grading runs in the database  |
| API Endpoint      | The currently connected backend URL    |
| Recent Grade Runs | Table of the last 5 grading runs with student, URL, score, and date |

The dashboard loads automatically each time you navigate to the home view.

---

## 3. Auto-Grader

**Route:** `#/grader`

The auto-grader crawls a student website, validates every page against the W3C HTML validator, and scores the site on a 0–100 rubric.

### 3.1 Running a Grade

1. Enter the **Site URL** (e.g. `https://jsmith.cybearlab.cloud/project`).
2. Optionally fill in the **Student Username**.
3. Click **Grade**.

You can also click **Browse…** to open the file picker, select a student, navigate into their `public_html` directory, and the URL will be auto-constructed for you.

### 3.2 Grading Pipeline

Once submitted, the run moves through these stages (shown visually as a step timeline):

1. **Queued** — Waiting for processing
2. **Crawling** — BFS traversal of pages starting from the submitted URL
3. **Validating** — Each discovered page is sent to the W3C Nu HTML validator
4. **Scoring** — The rubric engine evaluates seven categories
5. **Completed** — Final score and details are ready

### 3.3 Scoring Rubric

| Category | Max Points | How It Is Scored |
|----------|:----------:|------------------|
| **Page Count** | 10 | ≥ 5 pages → 10 · 4 → 7 · 3 → 4 · 2 → 2 · fewer → 0 |
| **External Stylesheet** | 15 | Points based on how consistently a single external `.css` file is referenced across pages |
| **HTML Structures** | 30 | Sub-scored for forms, tables, lists, and media elements (7.5 pts each) |
| **Responsiveness** | 10 | `@media` queries in external CSS → 10 · inline only → 6 · none → 0 |
| **Theme Consistency** | 15 | Measures how uniform the stylesheet usage is across pages |
| **Navigation** | 10 | Perfect internal links → 10 · 1–2 broken → 7 · 3–5 broken → 4 · > 5 → 0 |
| **W3C Validity** | 20 | 20 − (errors × 1.0) − (warnings × 0.25), minimum 0 |
| **Total** | **100** | |

### 3.4 Viewing Results

After the run completes, a results card appears showing:

- **Total score** (with color: green ≥ 70 · yellow 50–69 · red < 50)
- **Category breakdown** — each rubric section with score / max
- **Summary feedback** — up to 6 human-readable notes
- **Validator messages** — individual HTML errors and warnings per page
- **Page list** — every crawled URL with HTTP status, size, and content type

You can also view past results from the **Reports** view.

---

## 4. Student Admin

**Route:** `#/admin`

This view provides admin operations and bulk student import.

### 4.1 Admin Actions

Switch between actions using the tab bar:

| Action | Fields | Description |
|--------|--------|-------------|
| **Add Student** | Username | Create a single Linux user account |
| **Reset Password** | Username | Reset a student's password to a generated value |
| **Disable Student** | Username | Lock a student's SSH/FTP access |
| **Fix Permissions** | *(none)* | Run global permission-fix script across all student dirs |
| **HTTPS All** | *(none)* | Enable HTTPS (Let's Encrypt) for every student site |

Click **Run Action** to execute. The result (stdout/stderr) appears in the output area below.

### 4.2 Roster Import (Bulk)

Upload a CSV file to create many student accounts at once.

#### CSV Format

The file must contain columns (header names are case-insensitive):

| Column | Accepted Names | Required |
|--------|---------------|:--------:|
| First name | `FirstName`, `First` | ✔ |
| Last name | `LastName`, `Last` | ✔ |
| Student ID | `StudentID`, `ID`, `Student_ID` | ✔ |

Example CSV:

```csv
FirstName,LastName,StudentID
John,Smith,123456
Patricia,O'Brien,987654
```

#### Username Generation

Usernames are auto-derived from the name fields:

- Format: `{lastname}{firstinitial}` — all lowercase, non-alpha characters stripped
- Max length: 15 characters
- Duplicates appended with a number: `smithj`, `smithj2`, `smithj3`

#### Password Generation

Passwords are derived from the StudentID:

- Only numeric digits are extracted
- Zero-padded to 6 digits if fewer than 6 numbers
- Last 6 digits used if more than 6 numbers
- Example: `12345` → `012345`, `1234567890` → `567890`

#### Import Workflow

1. Click **Upload Roster CSV** and select your file.
2. A **preview table** appears showing each student's derived username, password, and validation status.
3. Review the preview for any errors (highlighted in red).
4. Click **Import** to create the accounts.
5. A results summary shows created / failed / skipped counts.

---

## 5. Grading Reports

**Route:** `#/reports`

Browse all historical grading runs.

### 5.1 Filtering

| Filter | Description |
|--------|-------------|
| Term | Academic term string (e.g. `2026sp`) |
| Student | Username substring match |

Click **Filter** to apply, or **Clear** to reset.

### 5.2 Table Columns

| Column | Description |
|--------|-------------|
| Date | When the grading run started |
| Student | Username (if provided) |
| URL | The graded site URL |
| Score | Numeric score with color coding |
| Status | `completed`, `failed`, `in_progress`, etc. |
| Actions | **View** button to see full results |

### 5.3 Pagination

Displays 15 runs per page. Use **← Prev** and **Next →** to navigate.

### 5.4 Exporting

From the detail view of any completed run, click **Export** to download the results as a JSON file.

---

## 6. User Management

**Route:** `#/users`

Manage individual Linux user accounts on the server.

### 6.1 User List

The table shows all student users with:

- Username, status (Active / Suspended), disk usage, file count

Actions on each row:

| Button | Action |
|--------|--------|
| **View** | Open detail modal with full user info |
| **Suspend** | Lock the account (shell set to `/usr/sbin/nologin`) |
| **Unsuspend** | Re-enable the account |
| **Quota** | Set disk quota (prompted for MB value, default 500) |
| **Delete** | Permanently delete the user and their home directory |

### 6.2 Bulk Actions

Select multiple users via checkboxes, then:

- **Suspend Selected** — Suspend all checked users
- **Unsuspend Selected** — Unsuspend all checked users

### 6.3 User Detail Modal

Shows comprehensive information:

- **Account:** UID, GID, home directory, shell, group memberships
- **Disk Usage:** Visual progress bar, formatted used / total
- **Website:** File counts inside `public_html`, whether `index.html` exists
- **Last Login:** Timestamp of most recent login, or "Never"

---

## 7. File Manager

**Route:** `#/files`

Browse and manage files in student home directories.

### 7.1 Browsing

1. Select a student from the **Username** dropdown.
2. The file browser loads their home directory (`/home/{user}`).
3. Navigate into subdirectories by clicking folder names.
4. Use **⬆ Up** / **🏠 Home** / the breadcrumb trail to navigate back.

### 7.2 File Operations

| Operation | How |
|-----------|-----|
| **Upload** | Click **Upload**, choose a file. Uploaded to the current directory. |
| **New File** | Click **New File**, enter a filename. Creates an empty file. |
| **New Folder** | Click **New Folder**, enter a name. Creates a directory. |
| **Edit** | Click the ✏ icon on a text file. Opens an in-browser editor with **Save** button. |
| **Download** | Click the ⬇ icon. Downloads the file to your computer. |
| **Rename** | Click the ✎ icon. Enter the new name in the modal. |
| **Delete** | Click the 🗑 icon. Confirms before deleting. |
| **Properties** | Click the ℹ icon. Shows size, permissions, owner, modified date. |
| **Chmod** | From properties, change file permissions (numeric or rwx). |

### 7.3 File Display

Each entry shows:

- Icon (📁 folder, 📄 file, specific icons for images / code / archives)
- Name, size (formatted), last modified date, permissions string

---

## 8. Database Management

**Route:** `#/databases`

Create and manage MySQL databases and users for each student.

### 8.1 Selecting a Student

Choose a student from the **Username** dropdown. Their databases and MySQL user info load automatically.

### 8.2 Database List

Shows all databases owned by the selected student, with size and table count.

| Action | Description |
|--------|-------------|
| **View Detail** | Opens a modal with tables, row counts, and sizes |
| **Export** | Downloads a `.sql` dump of the database |
| **Drop** | Permanently deletes the database (with confirmation) |

### 8.3 Creating a Database

1. Click **Create Database**.
2. Enter the database name (will be prefixed with the student's username, e.g. `jsmith_mydb`).
3. Click **Create**.

### 8.4 MySQL User Management

Each student has one MySQL user. You can:

- **View** — See current username, host, and privileges
- **Create** — If no user exists, create one with a generated password
- **Change Password** — Set a new password for the MySQL user
- **Delete** — Remove the MySQL user

### 8.5 Running SQL

From the database detail modal, enter a SQL query and click **Execute**. Results are displayed in a table below. Use this for quick data inspection or fixes.

### 8.6 Import

Upload a `.sql` file to import into a database from the detail modal.

---

## 9. FTP Account Management

**Route:** `#/ftp`

Manage vsftpd FTP accounts for student file access.

### 9.1 Account List

Select a student to see their FTP accounts. Each account shows:

- Account name, home directory, status (enabled/disabled)

### 9.2 Creating an FTP Account

1. Click **Create Account**.
2. Enter: account name, password, home directory.
3. Click **Create**.

The password is shown once in a confirmation dialog — copy it before closing.

### 9.3 Account Operations

| Action | Description |
|--------|-------------|
| **Set Password** | Change the FTP password |
| **Enable** | Re-enable a disabled account |
| **Disable** | Disable without deleting |
| **Delete** | Permanently remove the account |

### 9.4 Active Sessions

The **Sessions** section at the bottom shows currently connected FTP users. Click **Kick** to forcibly disconnect a session.

---

## 10. DNS Management

**Route:** `#/dns`

Manage DNS records via the Hostinger API.

### 10.1 Domain Info

At the top, the view shows:

- Domain name, nameservers, and current SSL certificate status

### 10.2 Records Table

All DNS records are listed with: Type, Name, Value, TTL.

### 10.3 Adding a Record

1. Click **Add Record**.
2. Fill in the modal form:
   - **Type:** A, AAAA, CNAME, MX, TXT, SRV, NS
   - **Name:** Use `@` for the root domain, `*` for wildcard
   - **Value:** IP address, hostname, or text value depending on type
   - **TTL:** Time to live in seconds (default: 3600)
   - **Priority:** Required for MX records
3. Click **Save**.

### 10.4 Editing a Record

Click the ✏ icon next to any record. The modal pre-fills with existing values.

### 10.5 Deleting a Record

Click the 🗑 icon. Confirms before deleting.

### 10.6 Subdomains

The **Subdomains** section lists all subdomains pointing to the server.

---

## 11. Cron Job Manager

**Route:** `#/cron`

Schedule recurring tasks for individual users.

### 11.1 Loading Jobs

Enter a **Username** and click **Load**. All cron jobs for that user are displayed.

### 11.2 Creating a Cron Job

1. Click **Add Job**.
2. Fill in the modal:
   - **Command:** The shell command to run
   - **Schedule:** Pick from common presets or enter a custom cron expression
   - **Description:** Optional note about what this job does
3. Click **Save**.

#### Common Schedule Presets

| Preset | Expression |
|--------|------------|
| Every minute | `* * * * *` |
| Every 5 minutes | `*/5 * * * *` |
| Every hour | `0 * * * *` |
| Every day at midnight | `0 0 * * *` |
| Every Monday at 3 AM | `0 3 * * 1` |
| First of month at noon | `0 12 1 * *` |

### 11.3 Managing Jobs

| Action | Description |
|--------|-------------|
| **Edit** | Modify the command, schedule, or description |
| **Toggle** | Enable or disable without deleting |
| **Delete** | Permanently remove the cron entry |

The **Describe** feature converts a cron expression into human-readable text (e.g. `0 3 * * 1` → "At 03:00 on Monday").

---

## 12. Security Center

**Route:** `#/security`

Manage SSH keys, intrusion prevention, firewall, and web application firewall.

### 12.1 SSH Keys

1. Enter a **Username** and click **Load Keys**.
2. View all authorized SSH public keys for that user.
3. **Add Key:** Paste a public key (e.g. `ssh-ed25519 AAAA...`) and click Add.
4. **Delete Key:** Click the 🗑 icon next to any key.

### 12.2 Fail2Ban

Monitors and manages the Fail2Ban intrusion prevention system.

- **Status:** Shows active jails and currently banned IP count
- **Ban IP:** Enter an IP address, select a jail (e.g. `sshd`), click **Ban**
- **Unban IP:** Enter the IP, select jail, click **Unban**

### 12.3 UFW Firewall

- **Status:** Shows whether UFW is active and lists all current rules
- **Enable / Disable:** Toggle the firewall
- **Add Rule:** Specify port, protocol (TCP/UDP), and action (allow/deny)
- **Delete Rule:** Click 🗑 next to any rule to remove it

### 12.4 ModSecurity WAF

- **Status:** Shows current mode
- **Set Mode:**
  - `on` — Active blocking mode (blocks malicious requests)
  - `detection` — Logs threats but does not block
  - `off` — Disabled

---

## 13. SSL/TLS Certificates

**Route:** `#/ssl`

Manage Let's Encrypt SSL certificates.

### 13.1 Certificate List

Shows all installed certificates with: domain, issuer, expiry date, status.

Certificates nearing expiry are highlighted with warning colors.

### 13.2 Requesting a New Certificate

1. Click **Request Certificate**.
2. Enter comma-separated domain names (e.g. `example.com, www.example.com`).
3. Click **Request**. Certbot runs in the background.
4. On success, the certificate appears in the list.

### 13.3 Certificate Operations

| Action | Description |
|--------|-------------|
| **View Detail** | See full cert info: issuer, serial, SANs, dates |
| **Renew** | Force-renew a single certificate |
| **Renew All** | Renew all certificates nearing expiry |
| **Delete** | Remove certificate files from the server |

### 13.4 Warnings

The **Warnings** panel at the top shows any certificates expiring within 30 days, or certificates with configuration issues.

---

## 14. System Monitoring

**Route:** `#/system`

Real-time server health monitoring, service control, log viewing, and backups.

### 14.1 Health Overview

Displays at the top of the view and auto-refreshes every 10 seconds:

| Metric | Description |
|--------|-------------|
| **CPU** | Current usage percentage with progress bar |
| **Memory** | Used / Total with progress bar |
| **Disk** | Used / Total with progress bar |
| **Uptime** | Formatted uptime (e.g. "5 days, 3 hours") |
| **Load Average** | 1-min, 5-min, 15-min load averages |

Color coding: green (< 50%) · yellow (50–80%) · red (> 80%).

### 14.2 Services Tab

Lists monitored system services:

| Service | systemd Unit |
|---------|-------------|
| Nginx | `nginx` |
| MySQL | `mysql` |
| SSH | `sshd` |
| PHP-FPM | `php*-fpm` |
| Fail2Ban | `fail2ban` |
| vsftpd | `vsftpd` |
| Redis | `redis-server` |
| Certbot timer | `certbot.timer` |

Each service shows: status (active/inactive), memory usage, PID.

**Controls:** Click **Start**, **Stop**, or **Restart** for any service. A confirmation dialog appears for stop/restart.

### 14.3 Logs Tab

1. Select a **log file** from the dropdown (e.g. `/var/log/nginx/access.log`).
2. Click **View Log** to see the last 100 lines.
3. Enter a search pattern and click **Search** to filter.
4. Click **Live Stream** to open a WebSocket connection that tails the log in real time. Click again to stop streaming.

### 14.4 Processes Tab

Displays the top processes sorted by CPU usage: PID, name, user, CPU %, memory %, status. Click **↻ Refresh** to update.

### 14.5 Backups Tab

Create and manage server backups.

**Creating a Backup:**

1. Select backup type:
   - **Full Backup** — Entire server configuration and student data
   - **Student** — Single student's home directory
2. For student backups, select the student from the dropdown.
3. Click **Create Backup**. A progress bar shows while the backup runs.

**Managing Backups:**

| Column | Description |
|--------|-------------|
| Backup | Filename |
| Type | full / student |
| Size | Formatted file size |
| Created | Date and time |
| Actions | **Download** or **Delete** |

---

## 15. System Updates

**Route:** `#/updates`

Check for and apply OS and package updates.

### 15.1 Checking for Updates

1. Click **Check for Updates** to scan for available apt packages.
2. The status panel shows:
   - **Available Updates** — Total count (yellow if > 0)
   - **Security Updates** — Security-specific count (red if > 0)
   - **Reboot Required** — Whether the kernel needs a reboot
   - **Last Checked** — Timestamp of the last scan

### 15.2 Refreshing the Package List

Click **↻ Refresh APT** to run `apt-get update` and refresh the repository cache. Do this before checking for updates if your data is stale.

### 15.3 Package Table

After checking, available updates appear in a table:

| Column | Description |
|--------|-------------|
| ☑ | Select checkbox for targeted updates |
| Package | Package name |
| Current Version | Installed version |
| New Version | Available version |
| Source | Repository source |
| Type | `Security` (red) or `Standard` (gray) |

Use the **Select All** checkbox in the header to toggle all packages.

### 15.4 Applying Updates

- **Apply Security Only** — Updates only packages flagged as security patches
- **Apply All Updates** — Updates all selected packages (or all if none deselected)

A progress bar appears during the update process. Results are shown via toast notification, and the package list re-scans automatically after a successful update.

### 15.5 Software Versions

The right-side card shows installed versions of key software: Nginx, MySQL, Python, PHP, Node.js, OpenSSL.

---

## 16. Deployment

**Route:** `#/deploy`

Generate and manage the systemd service unit and nginx site configuration for the control panel itself.

### 16.1 Status Cards

| Indicator | Description |
|-----------|-------------|
| **API Service Status** | `active`, `inactive`, or `not installed` |
| **Enabled at Boot** | Whether the service starts on reboot |
| **Python** | Python version running the API |
| **App Directory** | Filesystem path of the application |
| **Nginx Config Installed** | Whether the site config exists |
| **Nginx Site Enabled** | Whether the symlink in `sites-enabled` exists |

### 16.2 Service Control

Quick-action buttons for the API service:

| Button | Action |
|--------|--------|
| **Restart** | Restart the API (graceful) |
| **Stop** | Stop the API service |
| **Start** | Start the API service |
| **Reload Nginx** | Reload nginx configuration without downtime |

### 16.3 Systemd Unit Tab

Generate and install a systemd service unit file.

1. Set the **API Port** (default: 8000).
2. Click **Preview** to see the generated unit file.
3. Click **Install Service** to write it to `/etc/systemd/system/cybearlab-api.service` and enable it.

The generated unit:
- Runs uvicorn with the FastAPI app
- Auto-restarts on failure (5-second delay)
- Sets `EXECUTION_MODE=live`
- Binds to `127.0.0.1` (reverse-proxied by nginx)

### 16.4 Nginx Config Tab

Generate and install an nginx site configuration.

| Field | Default | Description |
|-------|---------|-------------|
| Server Name | `admin.cybearlab.cloud` | The domain name |
| Proxy Port | `8000` | Port the API listens on |
| Web Root | `/var/www/iscs1800-admin/public` | Document root for PHP/static |
| SSL Certificate Path | *(empty)* | Path to fullchain.pem |
| SSL Key Path | *(empty)* | Path to privkey.pem |
| Enable SSL | ✔ | Add SSL directives and HTTP→HTTPS redirect |
| Enable PHP | ✔ | Add PHP-FPM processing block |

1. Fill in the fields.
2. Click **Preview** to see the generated config.
3. Click **Install & Reload** to write to `/etc/nginx/sites-available/cybearlab-admin`, enable it, and reload nginx.

The generated config includes:
- HTTP → HTTPS redirect (when SSL enabled)
- Reverse proxy from `/api/` to the backend
- WebSocket upgrade support for log streaming
- PHP-FPM passthrough for `.php` files
- Security: dotfile access denied

### 16.5 Service Logs Tab

View recent API service logs from `journalctl`.

1. Select the number of lines (50, 100, 250, or 500).
2. Click **↻ Refresh** to load.

The output area auto-scrolls to the bottom.

---

## 17. Audit Log

**Route:** `#/audit`

View a chronological timeline of all administrative actions performed through the panel.

### 17.1 Filtering

| Filter | Description |
|--------|-------------|
| Action | Filter by action type (e.g. `updates.apply`, `user.suspend`) |
| Actor | Filter by the user who performed the action |

Click **Filter** to apply, or **Clear** to reset.

### 17.2 Timeline

Each audit event shows:

- **Timestamp** — When the action occurred
- **Action** — The operation performed (e.g. `deployment.nginx_install`)
- **Actor** — Who performed it
- **Details** — JSON payload with parameters and results

Actions are color-coded by category (grading, system, user, security, etc.).

---

## 18. Settings

**Route:** `#/settings`

### 18.1 API Configuration

- **API Base URL:** Override the auto-detected backend URL. Leave empty for automatic detection. Changes apply immediately.

### 18.2 Connection Status

| Indicator | Description |
|-----------|-------------|
| Backend API | `Connected` or `Unreachable` — tests the `/health` endpoint |
| Database | `Connected` or `Issue` — reported by the health check |

### 18.3 Grader Configuration

Tune the auto-grader behavior (saved to browser `localStorage`):

| Setting | Default | Range | Description |
|---------|---------|-------|-------------|
| Max Pages per Crawl | 30 | 1–100 | Maximum pages the BFS crawler visits |
| Request Timeout (seconds) | 15 | 5–60 | Timeout per HTTP request |
| Validator Concurrency | 3 | 1–10 | Parallel W3C validation requests |

Click **Save Grader Settings** to persist.

### 18.4 About

Displays the application version number and current API endpoint.

---

## 19. Configuration Reference

All settings are controlled via environment variables. Create a `/var/www/iscs1800-admin/backend/.env` file or set them in your systemd unit.

### 19.1 Core Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `APP_NAME` | `ISCS1800 Unified Admin + Grader API` | Display name |
| `APP_VERSION` | `0.2.0` | API version |
| `DATABASE_URL` | `sqlite:///./iscs1800.db` | Database connection string |
| `TOKEN_TTL_SECONDS` | `28800` | Auth token lifetime (8 hours) |
| `EXECUTION_MODE` | `mock` | Set to `live` for real command execution |
| `COMMAND_TIMEOUT_SECONDS` | `120` | Max seconds for shell commands |

### 19.2 Authentication

| Variable | Default | Description |
|----------|---------|-------------|
| `BOOTSTRAP_ADMIN_USERNAME` | `admin` | Admin username (created on first startup) |
| `BOOTSTRAP_ADMIN_PASSWORD` | `change-me-now` | Admin password |

### 19.3 Grader Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `GRADER_MAX_PAGES` | `30` | Max pages crawled per run |
| `GRADER_HTTP_TIMEOUT_SECONDS` | `20` | Per-request timeout |
| `GRADER_VALIDATOR_ENDPOINT` | `https://validator.w3.org/nu/` | W3C validator URL |

### 19.4 File & Upload Limits

| Variable | Default | Description |
|----------|---------|-------------|
| `UPLOAD_ROOT_DIR` | `/tmp/iscs1800/uploads` | Temp directory for uploads |
| `MAX_ROSTER_UPLOAD_BYTES` | `20971520` | Max roster CSV size (20 MB) |

### 19.5 System Script Paths

| Variable | Default |
|----------|---------|
| `SCRIPT_ADD_STUDENT` | `/usr/local/sbin/iscs1800-add-student` |
| `SCRIPT_RESET_PASSWORD` | `/usr/local/sbin/iscs1800-reset-password` |
| `SCRIPT_DISABLE_STUDENT` | `/usr/local/sbin/iscs1800-disable-student` |
| `SCRIPT_BULK_ADD` | `/usr/local/sbin/iscs1800-bulk-add` |
| `SCRIPT_FIX_PERMS` | `/usr/local/sbin/iscs1800-fix-perms` |
| `SCRIPT_HTTPS_STUDENTS` | `/usr/local/sbin/iscs1800-enable-https-students` |
| `SCRIPT_HTTPS_ADMIN` | `/usr/local/sbin/iscs1800-enable-https-admin` |
| `SCRIPT_HTTPS_WILDCARD` | `/usr/local/sbin/iscs1800-enable-https-wildcard` |

---

## 20. Troubleshooting

### "Invalid credentials or backend unavailable"

- Verify the API service is running: `systemctl status cybearlab-api`
- Confirm the API is reachable: `curl http://127.0.0.1:8000/health`
- Check credentials match `BOOTSTRAP_ADMIN_USERNAME` / `BOOTSTRAP_ADMIN_PASSWORD`

### Views show "Loading…" indefinitely

- Open browser DevTools → Console for JavaScript errors
- Check the **Settings** page for connection status
- Hard-refresh with **Ctrl+Shift+R** to clear cached assets

### Commands fail with "mock mode"

- The API defaults to `EXECUTION_MODE=mock` which simulates commands
- Set `EXECUTION_MODE=live` in `.env` or the systemd unit to run real commands

### Grader returns score of 0

- Ensure the student URL is publicly accessible (not just from localhost)
- Check that the W3C validator endpoint is reachable
- Increase `GRADER_HTTP_TIMEOUT_SECONDS` if the student server is slow

### DNS changes not appearing

- DNS propagation can take up to 48 hours
- Verify the Hostinger API key is set (check the backend `.env` for `HOSTINGER_API_TOKEN`)
- Use `dig` or `nslookup` to verify records at the authoritative nameserver

### SSL certificate request fails

- Ensure port 80 is open and reachable from the internet (Let's Encrypt HTTP-01 challenge)
- Check that nginx is running and the domain resolves to the server IP
- Review certbot logs: `journalctl -u certbot`

### Updates fail to apply

- Run `apt-get update` manually to check for repository errors
- Check available disk space: `df -h`
- Review the error output in the toast notification for specifics

### Service won't start after systemd install

- Check the service log: `journalctl -u cybearlab-api -n 50`
- Verify the Python virtual environment exists: `ls /var/www/iscs1800-admin/backend/.venv/bin/python`
- Ensure all dependencies are installed: `.venv/bin/pip install -r requirements.txt`

---

## Appendix A: Backend API Endpoints

Full list of API routes (all require `Authorization: Bearer {token}` except `/health` and `/auth/login`):

| Method | Path | Description |
|--------|------|-------------|
| GET | `/health` | Health check |
| POST | `/auth/login` | Authenticate and get token |
| POST | `/admin/actions` | Run an admin action |
| GET | `/admin/actions/{id}` | Get action result |
| POST | `/admin/uploads/roster` | Upload roster CSV |
| POST | `/admin/roster/preview` | Preview roster import |
| POST | `/admin/roster/import` | Execute roster import |
| POST | `/grader/runs` | Start a grading run |
| GET | `/grader/runs` | List grading runs |
| GET | `/grader/runs/{id}` | Get grading run detail |
| GET | `/grader/runs/{id}/export` | Export run as JSON |
| GET | `/audit/events` | List audit events |
| GET | `/system/stats` | System health metrics |
| GET | `/system/services` | List monitored services |
| POST | `/system/services/{name}` | Control a service |
| GET | `/system/logs` | List available log files |
| GET | `/system/backups` | List backups |
| POST | `/system/backups` | Create a backup |
| DELETE | `/system/backups` | Delete a backup |
| GET | `/users/` | List users |
| GET | `/users/{username}` | User detail |
| POST | `/users/{username}/suspend` | Suspend user |
| POST | `/users/{username}/unsuspend` | Unsuspend user |
| POST | `/users/{username}/quota` | Set disk quota |
| DELETE | `/users/{username}` | Delete user |
| GET | `/users/{username}/usage` | Disk usage info |
| GET | `/dns/info` | Domain info |
| GET | `/dns/records` | List DNS records |
| POST | `/dns/records` | Create DNS record |
| PATCH | `/dns/records/{id}` | Update DNS record |
| DELETE | `/dns/records/{id}` | Delete DNS record |
| GET | `/dns/certificate` | SSL certificate info |
| GET | `/dns/subdomains` | List subdomains |
| GET | `/files/browse/{user}` | List directory contents |
| GET | `/files/read/{user}` | Read file content |
| PUT | `/files/write/{user}` | Write file content |
| POST | `/files/create-file/{user}` | Create empty file |
| POST | `/files/create-directory/{user}` | Create directory |
| DELETE | `/files/delete/{user}` | Delete file or directory |
| POST | `/files/rename/{user}` | Rename file |
| POST | `/files/move/{user}` | Move file |
| POST | `/files/copy/{user}` | Copy file |
| POST | `/files/chmod/{user}` | Change permissions |
| POST | `/files/chown/{user}` | Change ownership |
| POST | `/files/upload/{user}` | Upload file |
| GET | `/files/download/{user}` | Download file |
| GET | `/files/info/{user}` | File metadata |
| GET | `/databases/{user}` | List databases |
| GET | `/databases/{user}/detail/{db}` | Database detail |
| POST | `/databases/{user}` | Create database |
| DELETE | `/databases/{user}/{db}` | Drop database |
| GET | `/databases/{user}/user/info` | MySQL user info |
| POST | `/databases/{user}/user` | Create MySQL user |
| PUT | `/databases/{user}/user/password` | Change MySQL password |
| DELETE | `/databases/{user}/user` | Delete MySQL user |
| POST | `/databases/{user}/{db}/sql` | Execute SQL query |
| GET | `/databases/{user}/{db}/export` | Export database |
| POST | `/databases/{user}/{db}/import` | Import SQL file |
| GET | `/ftp/accounts/{user}` | List FTP accounts |
| GET | `/ftp/accounts/{user}/{name}` | FTP account detail |
| POST | `/ftp/accounts/{user}` | Create FTP account |
| DELETE | `/ftp/accounts/{user}/{name}` | Delete FTP account |
| PUT | `/ftp/accounts/{user}/{name}/password` | Set FTP password |
| POST | `/ftp/accounts/{user}/{name}/enable` | Enable FTP account |
| POST | `/ftp/accounts/{user}/{name}/disable` | Disable FTP account |
| PUT | `/ftp/accounts/{user}/{name}/directory` | Set FTP directory |
| GET | `/ftp/sessions` | List active FTP sessions |
| POST | `/ftp/sessions/{user}/kick` | Disconnect FTP session |
| GET | `/cron/{user}` | List cron jobs |
| GET | `/cron/{user}/{id}` | Cron job detail |
| POST | `/cron/{user}` | Create cron job |
| PUT | `/cron/{user}/{id}` | Update cron job |
| DELETE | `/cron/{user}/{id}` | Delete cron job |
| POST | `/cron/{user}/{id}/toggle` | Enable/disable job |
| GET | `/cron/schedules/common` | Common schedule presets |
| POST | `/cron/schedules/describe` | Describe a cron expression |
| GET | `/security/ssh-keys/{user}` | List SSH keys |
| POST | `/security/ssh-keys/{user}` | Add SSH key |
| DELETE | `/security/ssh-keys/{user}` | Delete SSH key |
| GET | `/security/fail2ban/status` | Fail2Ban status |
| GET | `/security/fail2ban/banned/{jail}` | Banned IPs for jail |
| POST | `/security/fail2ban/ban/{jail}` | Ban an IP |
| POST | `/security/fail2ban/unban/{jail}` | Unban an IP |
| GET | `/security/ufw/status` | UFW firewall status |
| POST | `/security/ufw/enable` | Enable firewall |
| POST | `/security/ufw/disable` | Disable firewall |
| POST | `/security/ufw/rules` | Add firewall rule |
| DELETE | `/security/ufw/rules` | Delete firewall rule |
| GET | `/security/modsecurity/status` | ModSecurity status |
| POST | `/security/modsecurity/mode` | Set WAF mode |
| GET | `/ssl/certificates` | List certificates |
| GET | `/ssl/certificates/{domain}` | Certificate detail |
| POST | `/ssl/certificates` | Request certificate |
| POST | `/ssl/certificates/{domain}/renew` | Renew certificate |
| POST | `/ssl/certificates/renew-all` | Renew all expiring |
| POST | `/ssl/certificates/{domain}/revoke` | Revoke certificate |
| DELETE | `/ssl/certificates/{domain}` | Delete certificate |
| GET | `/ssl/warnings` | Expiry warnings |
| POST | `/updates/refresh` | Refresh apt cache |
| GET | `/updates/check` | Check for updates |
| POST | `/updates/apply` | Apply updates |
| GET | `/updates/versions` | Software versions |
| GET | `/deployment/status` | Deployment status |
| POST | `/deployment/systemd/install` | Install systemd unit |
| POST | `/deployment/systemd/control` | Control API service |
| POST | `/deployment/systemd/preview` | Preview systemd unit |
| POST | `/deployment/nginx/install` | Install nginx config |
| POST | `/deployment/nginx/preview` | Preview nginx config |
| POST | `/deployment/nginx/reload` | Reload nginx |
| GET | `/deployment/logs` | API service logs |

---

## Appendix B: Tech Stack

| Component | Technology |
|-----------|-----------|
| Backend Framework | FastAPI 0.117 |
| ASGI Server | Uvicorn 0.37 |
| Database | SQLite (SQLAlchemy 2.0) |
| Frontend | Vanilla JavaScript SPA |
| Served via | PHP (index.php) + nginx |
| CSS | Custom CSS (no framework) |
| DNS Integration | Hostinger API |
| SSL | Let's Encrypt / Certbot |
| System Monitoring | psutil |
| HTML Validation | W3C Nu Validator |
| HTML Parsing | BeautifulSoup 4 |
