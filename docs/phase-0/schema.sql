CREATE EXTENSION IF NOT EXISTS pgcrypto;

CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  username VARCHAR(64) UNIQUE NOT NULL,
  password_hash TEXT NOT NULL,
  role VARCHAR(32) NOT NULL CHECK (role IN ('admin', 'instructor', 'ta', 'viewer')),
  is_active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS file_uploads (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  uploader_id UUID NOT NULL REFERENCES users(id),
  original_name TEXT NOT NULL,
  content_type TEXT,
  stored_path TEXT NOT NULL,
  sha256 CHAR(64),
  size_bytes BIGINT NOT NULL CHECK (size_bytes >= 0),
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS admin_actions (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  action_type VARCHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL CHECK (status IN ('queued', 'running', 'success', 'failed', 'timed_out')),
  requested_by UUID NOT NULL REFERENCES users(id),
  upload_id UUID REFERENCES file_uploads(id),
  params_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  exit_code INTEGER,
  summary TEXT,
  output_log TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS grade_runs (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  requested_by UUID NOT NULL REFERENCES users(id),
  input_url TEXT NOT NULL,
  normalized_root TEXT,
  student_username VARCHAR(32),
  term VARCHAR(20),
  status VARCHAR(32) NOT NULL CHECK (status IN ('queued', 'running', 'completed', 'failed')),
  total_score NUMERIC(5,2),
  error_message TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  started_at TIMESTAMPTZ,
  finished_at TIMESTAMPTZ
);

CREATE TABLE IF NOT EXISTS grade_section_scores (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES grade_runs(id) ON DELETE CASCADE,
  section_key VARCHAR(64) NOT NULL,
  score NUMERIC(6,2) NOT NULL,
  max_score NUMERIC(6,2) NOT NULL,
  details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  UNIQUE (run_id, section_key)
);

CREATE TABLE IF NOT EXISTS grade_feedback_items (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES grade_runs(id) ON DELETE CASCADE,
  order_index INTEGER NOT NULL,
  feedback_text TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS grade_discovered_pages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES grade_runs(id) ON DELETE CASCADE,
  url TEXT NOT NULL,
  status_code INTEGER,
  is_html BOOLEAN,
  has_form BOOLEAN,
  has_table BOOLEAN,
  has_list BOOLEAN,
  has_media BOOLEAN,
  UNIQUE (run_id, url)
);

CREATE TABLE IF NOT EXISTS grade_validator_messages (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  run_id UUID NOT NULL REFERENCES grade_runs(id) ON DELETE CASCADE,
  page_url TEXT NOT NULL,
  message_type VARCHAR(32) NOT NULL,
  subtype VARCHAR(32),
  line INTEGER,
  column_num INTEGER,
  message TEXT NOT NULL,
  extract TEXT
);

CREATE TABLE IF NOT EXISTS audit_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  actor_user_id UUID REFERENCES users(id),
  event_type VARCHAR(64) NOT NULL,
  entity_type VARCHAR(64) NOT NULL,
  entity_id UUID,
  status VARCHAR(16) NOT NULL CHECK (status IN ('success', 'failed', 'denied')),
  metadata_json JSONB NOT NULL DEFAULT '{}'::jsonb,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_admin_actions_status_created
  ON admin_actions (status, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_grade_runs_created
  ON grade_runs (created_at DESC);

CREATE INDEX IF NOT EXISTS idx_grade_runs_term_student
  ON grade_runs (term, student_username);

CREATE INDEX IF NOT EXISTS idx_audit_events_created
  ON audit_events (created_at DESC);
