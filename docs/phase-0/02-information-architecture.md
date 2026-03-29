# Information Architecture

## Top-Level Navigation
- Overview
- Student Admin
- Auto-Grader
- Reports
- Audit Log
- Settings

## Layout Outline

### 1) Overview
Purpose:
- Fast health check and launchpad for common tasks.

Sections:
- System status (queue depth, worker status, validator reachability).
- Recent admin operations (latest 10).
- Recent grade runs (latest 10, with score chips).
- Quick actions (Add Student, Bulk Add, Grade URL).

### 2) Student Admin
Purpose:
- Manage student accounts and hosting operations.

Sections:
- Single Student Actions (Add, Reset, Disable).
- Bulk Add (roster upload + dry run).
- Maintenance (fix perms, HTTPS student/admin/wildcard).
- Last operation output panel.

### 3) Auto-Grader
Purpose:
- Submit URL and monitor grading job.

Sections:
- URL submission panel.
- Job status timeline.
- Score summary card (0-100).
- Rubric breakdown cards.
- Actionable feedback list.

### 4) Reports
Purpose:
- Discover historical grading data.

Sections:
- Filters (term, student, date range, score range).
- Results table.
- Run detail drawer (JSON + section details + export).

### 5) Audit Log
Purpose:
- Governance and traceability for privileged operations.

Sections:
- Timeline list with actor, action, args (redacted), outcome.
- Filter by action type/date/user.

### 6) Settings
Purpose:
- Environment-level controls and policy.

Sections:
- Script paths / operation policy.
- Grader limits (max pages, timeouts, validator concurrency).
- Role and access configuration.

## Navigation Behavior
- Global navigation remains persistent.
- Context pane updates in place to avoid full-page context loss.
- Breadcrumbs used only in deep report/detail pages.
- Primary workflows require no more than 2 route transitions.

## Route Map (Proposed)
- `/`
- `/admin`
- `/grader`
- `/reports`
- `/reports/:runId`
- `/audit`
- `/settings`
