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

## Phase 4 — Polish & Complete the Core UI ✅
- [x] Audit Log view — dedicated page with timeline, filters (action/user/date)
- [x] Settings view — grader limits, notification prefs, role/access display
- [x] Toast/notification system — unified success/error/info feedback
- [x] Commit staged DNS modal fix
- [x] Responsive/mobile pass on all views
- [x] Keyboard shortcuts for power users

## Phase 5 — File Manager & Database Tools ✅
- [x] File Manager — browse user home dirs, upload/download, edit text files, chmod/chown
- [x] Database Management — list/create/drop MySQL DBs, user management, privileges
- [x] FTP Account Management — create/delete accounts, set directories and quotas

## Phase 6 — Cron, Security & SSL ✅
- [x] Cron Job Manager — list/create/edit/delete per-user cron jobs, schedule helpers
- [x] Security Center — SSH keys, Fail2Ban management, UFW firewall, ModSecurity WAF
- [x] SSL/TLS Management — Let's Encrypt certificates, list/request/renew/revoke/delete

## Phase 7 — Multi-User, RBAC & Audit Hardening ⬅️ NEXT
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
| Files | `#/files` | ✅ |
| Databases | `#/databases` | ✅ |
| FTP | `#/ftp` | ✅ |
| DNS | `#/dns` | ✅ |
| Cron Jobs | `#/cron` | ✅ |
| Security | `#/security` | ✅ |
| SSL Certificates | `#/ssl` | ✅ |
| System | `#/system` | ✅ |
| Reports | `#/reports` | ✅ |
| Audit Log | `#/audit` | ✅ |
| Settings | `#/settings` | ✅ |

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
| files | `/files` | GET /browse/{user}, GET /read/{user}, PUT /write/{user}, POST /create-file/{user}, POST /create-directory/{user}, DELETE /delete/{user}, POST /rename/{user}, POST /move/{user}, POST /copy/{user}, POST /chmod/{user}, POST /chown/{user}, POST /upload/{user}, GET /download/{user}, GET /info/{user} |
| databases | `/databases` | GET /{user}, GET /{user}/detail/{db}, POST /{user}, DELETE /{user}/{db}, GET /{user}/user/info, POST /{user}/user, PUT /{user}/user/password, DELETE /{user}/user, POST /{user}/{db}/sql, GET /{user}/{db}/export, POST /{user}/{db}/import |
| ftp | `/ftp` | GET /accounts/{user}, GET /accounts/{user}/{name}, POST /accounts/{user}, DELETE /accounts/{user}/{name}, PUT /accounts/{user}/{name}/password, POST /accounts/{user}/{name}/enable, POST /accounts/{user}/{name}/disable, PUT /accounts/{user}/{name}/directory, GET /sessions, POST /sessions/{user}/kick |
| cron | `/cron` | GET /{user}, GET /{user}/{id}, POST /{user}, PUT /{user}/{id}, DELETE /{user}/{id}, POST /{user}/{id}/toggle, GET /schedules/common, POST /schedules/describe |
| security | `/security` | GET/POST/DELETE /ssh-keys/{user}, GET /fail2ban/status, GET /fail2ban/banned/{jail}, POST /fail2ban/ban/{jail}, POST /fail2ban/unban/{jail}, GET /ufw/status, POST /ufw/enable, POST /ufw/disable, POST/DELETE /ufw/rules, GET /modsecurity/status, POST /modsecurity/mode |
| ssl | `/ssl` | GET /certificates, GET /certificates/{domain}, POST /certificates, POST /certificates/{domain}/renew, POST /certificates/renew-all, POST /certificates/{domain}/revoke, DELETE /certificates/{domain}, GET /warnings |
