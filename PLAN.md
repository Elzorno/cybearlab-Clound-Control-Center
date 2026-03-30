# CybearLab.cloud Control Panel — Project Plan

## Vision
Transform the ISCS1800 student-hosting admin app into a full-featured web hosting control panel (cPanel/CWP-class), branded as **CybearLab.cloud**.

## Tech Stack
- **Backend:** FastAPI + SQLite (SQLAlchemy), Python 3
- **Frontend:** Vanilla JS SPA served via PHP (`index.php` + `app.js` + `styles.css`)
- **DNS:** Hostinger API integration
- **Deployment:** admin.cybearlab.cloud

---

## Phase 0 — Planning & Architecture ✅
- UX strategy, information architecture, OpenAPI contract
- Data model, schema, migration blueprint
- Deliverables in `docs/phase-0/`

## Phase 1 — Backend Foundation ✅
- FastAPI service with auth, health, admin action, grader, and audit endpoints
- SQLite/SQLAlchemy integration
- Grader engine: BFS crawler, W3C Nu validator, rubric scoring (7 categories, 0–100)
- Audit logging service

## Phase 2 — User & Resource Management ✅
- User CRUD: list by term, detail, suspend/unsuspend, quota, delete
- Roster processor: CSV upload, preview/dry-run, bulk import
- Admin action executor with allowlist and timeout
- System monitor: CPU, RAM, disk, network, processes
- Service manager, log viewer/streamer, backup manager

## Phase 3 — DNS Management ✅
- Hostinger API integration (API key auth)
- DNS record listing, create, update, delete
- SSL certificate status
- Subdomain listing

## Phase 4 — Polish & Complete the Core UI ⬅️ CURRENT
- [ ] Audit Log view — dedicated page with timeline, filters (action/user/date)
- [ ] Settings view — grader limits, notification prefs, role/access display
- [ ] Toast/notification system — unified success/error/info feedback
- [ ] Commit staged DNS modal fix
- [ ] Responsive/mobile pass on all views
- [ ] Keyboard shortcuts for power users

## Phase 5 — File Manager & Database Tools
- [ ] File Manager — browse user home dirs, upload/download, edit text files, chmod/chown
- [ ] Database Management — list/create/drop MySQL DBs, user management, privileges
- [ ] FTP Account Management — create/delete accounts, set directories and quotas

## Phase 6 — Email, Cron & Security
- [ ] Email Management — accounts, forwarders, autoresponders, spam filters
- [ ] Cron Job Manager — list/create/edit/delete with expression builder
- [ ] Security Center — SSH keys, IP blocklist (fail2ban), firewall (UFW), ModSecurity
- [ ] SSL/TLS Management — Let's Encrypt install/renew, cert details per domain

## Phase 7 — Multi-User, RBAC & Audit Hardening
- [ ] Role-Based Access Control — roles (admin/reseller/user), permission matrix
- [ ] Multi-tenant support — reseller accounts managing sub-users
- [ ] Audit log hardening — immutable storage, export, retention policies
- [ ] Session management — active sessions, force logout, 2FA/TOTP
- [ ] API key management — generate/revoke tokens for automation

## Phase 8 — Production Hardening & DevOps
- [ ] Observability — Prometheus metrics, health alerting (email/webhook)
- [ ] Backup scheduling — automated policies, remote targets (S3/SFTP)
- [ ] Auto-updates — package checker, one-click OS/service updates
- [ ] E2E test suite — Playwright/Cypress for critical workflows
- [ ] Deployment automation — systemd, Nginx config gen, Docker option
- [ ] Documentation — admin guide, API reference, in-app help

---

## Current Frontend Views
| View | Route | Status |
|------|-------|--------|
| Overview | `#/` | ✅ |
| Auto-Grader | `#/grader` | ✅ |
| Student Admin | `#/admin` | ✅ |
| Users | `#/users` | ✅ |
| DNS | `#/dns` | ✅ |
| System | `#/system` | ✅ |
| Reports | `#/reports` | ✅ |
| Audit Log | `#/audit` | ❌ Not yet built |
| Settings | `#/settings` | ⚠️ Stub only |

## Backend Routers
| Router | Prefix | Endpoints |
|--------|--------|-----------|
| health | `/` | GET /health |
| auth | `/auth` | POST /login |
| admin | `/admin` | POST /actions, GET /actions/{id}, POST /uploads/roster, POST /roster/preview, POST /roster/import |
| grader | `/grader` | POST /runs, GET /runs, GET /runs/{id}, GET /runs/{id}/export |
| audit | `/audit` | GET /events |
| system | `/system` | GET /stats, GET/POST /services, GET /logs, GET /backups, POST /backups, DELETE /backups |
| users | `/users` | GET /terms, GET /, GET /{username}, POST /{username}/suspend, POST /{username}/unsuspend, POST /{username}/quota, DELETE /{username}, GET /{username}/usage |
| dns | `/dns` | GET /info, GET/POST /records, PATCH/DELETE /records/{id}, GET /certificate, GET /subdomains |
