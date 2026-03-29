# Migration Blueprint

## Phase 0 (Current)
- Finalize contracts, schema, and UX direction.
- Preserve current PHP app as production baseline.

## Phase 1: Backend Foundation
- Create FastAPI service with:
  - Auth endpoints.
  - Admin action endpoints.
  - Grader run endpoints.
  - Audit endpoints.
- Add PostgreSQL integration and migrations.
- Add job queue (Celery + Redis or RQ).

Exit criteria:
- `/health` live.
- API endpoints return validated mock payloads.
- DB schema deployed.

## Phase 2: Admin Operation Migration
- Implement command runner with strict allowlist and timeout.
- Map each existing PHP operation to API handlers.
- Add upload endpoint and secure roster storage.
- Persist action request/result + audit event.

Exit criteria:
- All existing actions callable via API.
- No direct shell command interpolation from user input.
- Parity tests pass against current PHP behavior.

## Phase 3: Grader Engine
- Implement crawler (same-domain, BFS, max 30 pages).
- Implement validator client for W3C Nu API.
- Implement rubric scoring engine matching requirements doc.
- Persist section scores, feedback, validator messages.

Exit criteria:
- End-to-end grade run completes and stores full result.
- Score math matches rubric examples.

## Phase 4: New Frontend
- Build UI using selected Balanced design.
- Implement pages: Overview, Admin, Grader, Reports, Audit, Settings.
- Add live job status and actionable feedback presentation.

Exit criteria:
- Core workflows complete with low-click paths.
- Accessibility checks pass for major screens.

## Phase 5: Cutover + Hardening
- Switch traffic from PHP UI to new frontend.
- Keep PHP fallback for one release window.
- Add observability dashboards and alerting.
- Complete integration/e2e test matrix.

Exit criteria:
- Stable production release.
- Rollback path documented and tested.

## Risk Controls
- Command execution timeout + output redaction.
- SSRF guardrails for grader URL fetches.
- Rate limiting per user/IP for grading requests.
- Immutable audit log coverage for privileged operations.
