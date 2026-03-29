# UX Strategy

## Primary User Goals
- Run common student admin actions quickly and safely.
- Grade a submitted URL and immediately understand score + fixes.
- Track historical results without digging through logs.
- Recover from mistakes with clear feedback and auditability.

## Key Tasks (Optimized)
1. Student Admin Task (target: <= 3 clicks after data entry)
- Select action card (Add, Reset, Disable, Bulk, Maintenance).
- Enter only required fields (advanced options collapsed by default).
- Confirm and execute; receive immediate status and logs.

2. Auto-Grader Task (target: <= 2 clicks after URL entry)
- Enter URL and submit grade request.
- Watch progress state (queued -> crawling -> validating -> scoring).
- Review total score and per-section feedback in one page.

3. Instructor Review Task
- Filter grading history by student/term/date.
- Open run details and export JSON/CSV when needed.

## Design Principles Applied
- Clarity over cleverness: explicit labels, no hidden jargon.
- Progressive disclosure: show advanced fields only when user asks.
- Recognition over recall: action cards and presets reduce memory load.
- Error prevention first: validation, confirmation for destructive actions.
- Fast feedback: optimistic UI states with live job updates.

# Design Directions (3 Options)

## Option A: Ultra-Minimal
- Single-column layout.
- One prominent primary action area per page.
- Most advanced settings tucked behind "Show advanced".

Best when:
- New users and low-frequency administrative activity.

Tradeoff:
- Slightly slower for power users who need rapid repeated actions.

## Option B: Balanced
- Two-zone layout: primary task area + context/feedback panel.
- More visible controls while preserving whitespace.
- Strong card hierarchy for task groups.

Best when:
- Mixed audience (instructor + TA + occasional admin).

Tradeoff:
- Slightly higher visual density than ultra-minimal.

## Option C: Power-User Optimized
- Dense workspace with keyboard shortcuts and quick action bar.
- Inline batch operations and multi-select for frequent tasks.
- Persisted filters and compact tables.

Best when:
- Heavy daily operations and repeated bulk workflows.

Tradeoff:
- Higher cognitive load for first-time users.

# Selected Direction
Option B (Balanced) is recommended because it best meets:
- Lowest confusion for mixed users.
- Fewest interactions without hiding essential context.
- Strong visual hierarchy while remaining efficient.

## Interaction Rules for Final UI
- Primary CTA appears once per panel and remains visually dominant.
- Each form surfaces required fields first; optional fields are collapsed.
- Destructive actions require explicit confirmation with consequence text.
- Result cards include status, human summary, and expandable raw logs.
