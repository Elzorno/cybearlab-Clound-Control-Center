from datetime import datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, EmailStr, Field, HttpUrl, model_validator


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


RubricScope = Literal["index", "all_pages", "any_page"] | dict[str, str]
RubricCheckType = Literal[
    "html_element",
    "html_attribute",
    "css_property",
    "css_selector",
    "js_file",
    "js_function",
    "js_dom_event",
    "link_crawl",
    "page_count",
    "w3c_html",
    "w3c_css",
    "meta_tag",
    "file_exists",
    "custom_regex",
]


class RubricCheck(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    type: str = Field(min_length=1, max_length=64)
    description: str = Field(min_length=1)
    points: float = Field(gt=0)
    required: bool = False
    scope: RubricScope = "index"
    params: dict[str, Any] = Field(default_factory=dict)


class RubricSection(BaseModel):
    id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    checks: list[RubricCheck] = Field(default_factory=list)


class RubricDefinition(BaseModel):
    version: str = "1.0"
    title: str = Field(min_length=1, max_length=200)
    description: str | None = None
    totalPoints: float = Field(gt=0)
    passingScore: float = Field(default=70, ge=0, le=100)
    requiresJavaScript: bool = False
    minPages: int | None = Field(default=None, ge=1)
    maxPages: int = Field(default=20, ge=1, le=100)
    sections: list[RubricSection] = Field(default_factory=list)

    @model_validator(mode="after")
    def validate_rubric(self) -> "RubricDefinition":
        if self.version != "1.0":
            raise ValueError("Only rubric schema version 1.0 is supported")

        section_ids = [section.id for section in self.sections]
        if len(section_ids) != len(set(section_ids)):
            raise ValueError("Rubric section IDs must be unique")

        check_ids: list[str] = []
        for section in self.sections:
            check_ids.extend(check.id for check in section.checks)
        if len(check_ids) != len(set(check_ids)):
            raise ValueError("Rubric check IDs must be unique")

        check_total = round(sum(check.points for section in self.sections for check in section.checks), 2)
        if round(self.totalPoints, 2) != check_total:
            raise ValueError(f"Rubric totalPoints must equal the sum of check points ({check_total:g})")
        return self


class AssignmentBase(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None
    rubricJson: RubricDefinition
    isActive: bool = True


class AssignmentCreate(AssignmentBase):
    pass


class AssignmentUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    description: str | None = None
    rubricJson: RubricDefinition | None = None
    isActive: bool | None = None


class AssignmentResponse(BaseModel):
    id: str
    name: str
    description: str | None = None
    rubricJson: dict[str, Any]
    isActive: bool
    createdAt: datetime
    totalPoints: float
    sectionCount: int
    checkCount: int


class SubmissionCreate(BaseModel):
    assignmentId: str
    studentName: str = Field(min_length=1, max_length=200)
    studentEmail: EmailStr
    projectUrl: HttpUrl


class SubmissionAccepted(BaseModel):
    id: str
    assignmentId: str
    studentName: str
    studentEmail: EmailStr
    projectUrl: str
    status: str
    ticketCode: str
    submittedAt: datetime


class CheckResult(BaseModel):
    checkId: str
    type: str
    description: str
    passed: bool
    required: bool = False
    pointsEarned: float
    pointsPossible: float
    message: str
    details: dict[str, Any] | None = None


class SectionResult(BaseModel):
    sectionId: str
    title: str
    description: str | None = None
    pointsEarned: float
    pointsPossible: float
    checks: list[CheckResult]


class GradingResult(BaseModel):
    submissionId: str
    assignmentName: str
    studentName: str
    projectUrl: str
    pagesFound: list[str]
    totalPointsEarned: float
    totalPointsPossible: float
    percentScore: float
    passed: bool
    incomplete: bool = False
    gradedAt: datetime
    sections: list[SectionResult]
    errors: list[str] = Field(default_factory=list)


class SubmissionResponse(BaseModel):
    id: str
    assignmentId: str
    assignmentName: str | None = None
    studentName: str
    studentEmail: str
    projectUrl: str
    submittedAt: datetime
    status: str
    score: float | None = None
    maxScore: float | None = None
    percentScore: float | None = None
    resultJson: dict[str, Any] | None = None
    ticketCode: str
    gradedAt: datetime | None = None
    errorMessage: str | None = None


class SubmissionListResponse(BaseModel):
    items: list[SubmissionResponse]


class RubricTemplateResponse(BaseModel):
    name: str
    rubric: dict[str, Any]


class AuditEventResponse(BaseModel):
    id: str
    actor: str
    action_type: str
    entity_id: str | None = None
    status: str
    created_at: datetime


class AuditListResponse(BaseModel):
    items: list[AuditEventResponse]


# ============================================================
# Roster Import Schemas
# ============================================================

class RosterEntryPreview(BaseModel):
    first_name: str
    last_name: str
    student_id: str
    username: str
    password: str
    status: str  # "pending", "skip"
    message: str


class RosterPreviewResponse(BaseModel):
    entries: list[RosterEntryPreview]
    errors: list[str]
    valid_count: int
    skip_count: int


class RosterImportRequest(BaseModel):
    entries: list[RosterEntryPreview]
    term: str | None = Field(default=None, pattern=r"^[A-Za-z0-9._-]{2,20}$")


class RosterImportResultItem(BaseModel):
    username: str
    status: str  # "created", "failed", "skipped"
    message: str


class RosterImportResponse(BaseModel):
    results: list[RosterImportResultItem]
    created_count: int
    failed_count: int
    skipped_count: int
