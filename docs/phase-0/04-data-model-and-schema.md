# Data Model

## Core Entities

### users
- Purpose: authenticated operators (instructor/TA/admin).
- Key fields: `id`, `username`, `password_hash`, `role`, `is_active`, timestamps.

### admin_actions
- Purpose: track each privileged operation request and output.
- Key fields: `id`, `action_type`, `status`, `requested_by`, `params_json`, `exit_code`, `summary`, `output_log`, timestamps.

### file_uploads
- Purpose: uploaded roster metadata and storage refs.
- Key fields: `id`, `uploader_id`, `original_name`, `content_type`, `stored_path`, `sha256`, `size_bytes`.

### grade_runs
- Purpose: one grading execution request.
- Key fields: `id`, `input_url`, `normalized_root`, `student_username`, `term`, `status`, `total_score`, timestamps, `error_message`.

### grade_section_scores
- Purpose: persisted rubric section scores/details.
- Key fields: `id`, `run_id`, `section_key`, `score`, `max_score`, `details_json`.

### grade_feedback_items
- Purpose: student-friendly recommendation bullets.
- Key fields: `id`, `run_id`, `feedback_text`, `order_index`.

### grade_discovered_pages
- Purpose: crawl results per run.
- Key fields: `id`, `run_id`, `url`, `status_code`, `is_html`, `has_form`, `has_table`, `has_list`, `has_media`.

### grade_validator_messages
- Purpose: W3C messages per page.
- Key fields: `id`, `run_id`, `page_url`, `message_type`, `subtype`, `line`, `column`, `message`, `extract`.

### audit_events
- Purpose: immutable operational trace.
- Key fields: `id`, `actor_user_id`, `event_type`, `entity_type`, `entity_id`, `status`, `metadata_json`, `created_at`.

## Relationships
- `users 1..n admin_actions`
- `users 1..n file_uploads`
- `users 1..n grade_runs` (initiator)
- `grade_runs 1..n grade_section_scores`
- `grade_runs 1..n grade_feedback_items`
- `grade_runs 1..n grade_discovered_pages`
- `grade_runs 1..n grade_validator_messages`

## Retention Guidance
- Keep `audit_events` for at least 1 year.
- Keep `grade_runs` and section data per course policy (suggest 1 semester + 1 year).
- Rotate or archive `output_log` fields if large.
