from datetime import datetime
from uuid import uuid4

from sqlalchemy import JSON, Boolean, DateTime, ForeignKey, Integer, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)


class User(Base, TimestampMixin):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    username: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="admin")
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class FileUpload(Base, TimestampMixin):
    __tablename__ = "file_uploads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    uploader_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    original_name: Mapped[str] = mapped_column(Text, nullable=False)
    content_type: Mapped[str | None] = mapped_column(Text)
    stored_path: Mapped[str] = mapped_column(Text, nullable=False)
    sha256: Mapped[str | None] = mapped_column(String(64))
    size_bytes: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class AdminAction(Base, TimestampMixin):
    __tablename__ = "admin_actions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    action_type: Mapped[str] = mapped_column(String(64), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    requested_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    upload_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("file_uploads.id"))
    params_json: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=dict, nullable=False)
    exit_code: Mapped[int | None] = mapped_column(Integer)
    summary: Mapped[str | None] = mapped_column(Text)
    output_log: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class Assignment(Base, TimestampMixin):
    __tablename__ = "assignments"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    rubric_json: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)


class Submission(Base):
    __tablename__ = "submissions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    assignment_id: Mapped[str] = mapped_column(String(36), ForeignKey("assignments.id"), nullable=False)
    student_name: Mapped[str] = mapped_column(String(200), nullable=False)
    student_email: Mapped[str] = mapped_column(String(254), nullable=False)
    project_url: Mapped[str] = mapped_column(Text, nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=datetime.utcnow, nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
    score: Mapped[float | None] = mapped_column(Numeric(7, 2))
    max_score: Mapped[float | None] = mapped_column(Numeric(7, 2))
    result_json: Mapped[dict | None] = mapped_column(JSON().with_variant(JSONB, "postgresql"))
    ticket_code: Mapped[str] = mapped_column(String(8), unique=True, nullable=False)
    graded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    error_message: Mapped[str | None] = mapped_column(Text)


class GradeRun(Base, TimestampMixin):
    __tablename__ = "grade_runs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    requested_by: Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False)
    input_url: Mapped[str] = mapped_column(Text, nullable=False)
    normalized_root: Mapped[str | None] = mapped_column(Text)
    student_username: Mapped[str | None] = mapped_column(String(32))
    term: Mapped[str | None] = mapped_column(String(20))
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="queued")
    total_score: Mapped[float | None] = mapped_column(Numeric(5, 2))
    error_message: Mapped[str | None] = mapped_column(Text)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class GradeSectionScore(Base):
    __tablename__ = "grade_section_scores"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("grade_runs.id"), nullable=False)
    section_key: Mapped[str] = mapped_column(String(64), nullable=False)
    score: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    max_score: Mapped[float] = mapped_column(Numeric(6, 2), nullable=False)
    details_json: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=dict, nullable=False)


class GradeFeedbackItem(Base):
    __tablename__ = "grade_feedback_items"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("grade_runs.id"), nullable=False)
    order_index: Mapped[int] = mapped_column(Integer, nullable=False)
    feedback_text: Mapped[str] = mapped_column(Text, nullable=False)


class GradeDiscoveredPage(Base):
    __tablename__ = "grade_discovered_pages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("grade_runs.id"), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    status_code: Mapped[int | None] = mapped_column(Integer)
    is_html: Mapped[bool | None] = mapped_column(Boolean)
    has_form: Mapped[bool | None] = mapped_column(Boolean)
    has_table: Mapped[bool | None] = mapped_column(Boolean)
    has_list: Mapped[bool | None] = mapped_column(Boolean)
    has_media: Mapped[bool | None] = mapped_column(Boolean)


class GradeValidatorMessage(Base):
    __tablename__ = "grade_validator_messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    run_id: Mapped[str] = mapped_column(String(36), ForeignKey("grade_runs.id"), nullable=False)
    page_url: Mapped[str] = mapped_column(Text, nullable=False)
    message_type: Mapped[str] = mapped_column(String(32), nullable=False)
    subtype: Mapped[str | None] = mapped_column(String(32))
    line: Mapped[int | None] = mapped_column(Integer)
    column_num: Mapped[int | None] = mapped_column(Integer)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    extract: Mapped[str | None] = mapped_column(Text)


class AuditEvent(Base, TimestampMixin):
    __tablename__ = "audit_events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    actor_user_id: Mapped[str | None] = mapped_column(String(36), ForeignKey("users.id"))
    event_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_type: Mapped[str] = mapped_column(String(64), nullable=False)
    entity_id: Mapped[str | None] = mapped_column(String(36))
    status: Mapped[str] = mapped_column(String(16), nullable=False)
    metadata_json: Mapped[dict] = mapped_column(JSON().with_variant(JSONB, "postgresql"), default=dict, nullable=False)
