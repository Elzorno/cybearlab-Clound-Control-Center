from datetime import datetime
from enum import StrEnum
from typing import Any

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class AdminActionType(StrEnum):
    ADD_STUDENT = "add_student"
    RESET_PASSWORD = "reset_password"
    DISABLE_STUDENT = "disable_student"
    BULK_ADD = "bulk_add"
    FIX_PERMS_ONE = "fix_perms_one"
    FIX_PERMS_ALL = "fix_perms_all"
    HTTPS_STUDENTS_ONE = "https_students_one"
    HTTPS_STUDENTS_ALL = "https_students_all"
    HTTPS_ADMIN = "https_admin"
    HTTPS_WILDCARD = "https_wildcard"


class AdminActionRequest(BaseModel):
    action: AdminActionType
    term: str | None = Field(default=None, pattern=r"^[A-Za-z0-9._-]{2,20}$")
    username: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_-]{2,15}$")
    password_mode: str | None = Field(default=None, pattern=r"^(random|manual|id)$")
    password: str | None = Field(default=None, min_length=10)
    admin_email: EmailStr | None = None
    propagation_seconds: int | None = Field(default=None, ge=30, le=900)
    dry_run: bool = False
    roster_file_ref: str | None = None


class AdminActionAccepted(BaseModel):
    action_id: str
    status: str


class AdminActionResult(BaseModel):
    action_id: str
    action: str
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    exit_code: int | None = None
    summary: str | None = None
    output: str | None = None


class UploadRosterResponse(BaseModel):
    file_ref: str
    original_name: str
    size_bytes: int
    sha256: str
    content_type: str | None = None


class GradeRequest(BaseModel):
    url: HttpUrl
    student_username: str | None = Field(default=None, pattern=r"^[a-z][a-z0-9_-]{2,15}$")
    term: str | None = Field(default=None, pattern=r"^[A-Za-z0-9._-]{2,20}$")


class GradeRunAccepted(BaseModel):
    run_id: str
    status: str


class ScoreSection(BaseModel):
    score: float
    max_score: float
    details: dict[str, Any]


class GradeResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    run_id: str
    status: str
    input_url: str
    normalized_root: str | None = None
    total_score: float | None = None
    sections: dict[str, ScoreSection] | None = None
    summary_feedback: list[str] = []
    started_at: datetime | None = None
    finished_at: datetime | None = None


class GradeRunListItem(BaseModel):
    run_id: str
    url: str
    status: str
    total_score: float | None = None
    created_at: datetime


class GradeRunListResponse(BaseModel):
    page: int
    page_size: int
    total: int
    items: list[GradeRunListItem]


class AuditEventResponse(BaseModel):
    id: str
    actor: str
    action_type: str
    entity_id: str | None = None
    status: str
    created_at: datetime


class AuditListResponse(BaseModel):
    items: list[AuditEventResponse]
