# Phase 0 Deliverables

This folder contains concrete planning artifacts for migrating the current PHP admin portal into a full webapp that combines:
- Existing student-hosting admin operations.
- New auto-grader capabilities from `requirmentsForGrader`.
- Updated UI/UX direction from `uiPrompt.yaml`.

## Files
- `01-ux-and-product-strategy.md`: user goals, optimized flows, and UI direction options.
- `02-information-architecture.md`: app layout, nav model, and page ownership.
- `03-api-contract-openapi.yaml`: initial API contract for admin, grader, auth, and audit.
- `04-data-model-and-schema.md`: relational model and key constraints.
- `schema.sql`: starter PostgreSQL schema matching the data model.
- `05-migration-blueprint.md`: phased migration from PHP to FastAPI + modern frontend.

## Out of Scope for Phase 0
- Production implementation of crawler/validator/scoring logic.
- Final visual frontend implementation.
- Infra automation and deployment scripts.

These are intentionally deferred to Phases 1+.
