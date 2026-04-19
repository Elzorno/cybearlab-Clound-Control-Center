from __future__ import annotations

import csv
import io
from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..deps import get_current_user_id, get_db
from ..models import Assignment, Submission
from ..schemas import (
    AssignmentCreate,
    AssignmentResponse,
    AssignmentUpdate,
    RubricTemplateResponse,
    SubmissionAccepted,
    SubmissionCreate,
    SubmissionListResponse,
    SubmissionResponse,
)
from ..services.rubric_templates import get_rubric_templates
from ..services.webgrader_engine import generate_ticket_code, grade_submission_with_rubric

router = APIRouter(tags=["WebGrader"])


def _assignment_response(assignment: Assignment) -> AssignmentResponse:
    rubric = assignment.rubric_json or {}
    sections = rubric.get("sections") or []
    check_count = sum(len(section.get("checks") or []) for section in sections)
    return AssignmentResponse(
        id=assignment.id,
        name=assignment.name,
        description=assignment.description,
        rubricJson=rubric,
        isActive=assignment.is_active,
        createdAt=assignment.created_at,
        totalPoints=float(rubric.get("totalPoints") or 0),
        sectionCount=len(sections),
        checkCount=check_count,
    )


def _submission_response(submission: Submission, assignment: Assignment | None = None) -> SubmissionResponse:
    percent = None
    if submission.score is not None and submission.max_score:
        percent = round((float(submission.score) / float(submission.max_score)) * 100, 2)
    return SubmissionResponse(
        id=submission.id,
        assignmentId=submission.assignment_id,
        assignmentName=assignment.name if assignment else None,
        studentName=submission.student_name,
        studentEmail=submission.student_email,
        projectUrl=submission.project_url,
        submittedAt=submission.submitted_at,
        status=submission.status,
        score=float(submission.score) if submission.score is not None else None,
        maxScore=float(submission.max_score) if submission.max_score is not None else None,
        percentScore=percent,
        resultJson=submission.result_json,
        ticketCode=submission.ticket_code,
        gradedAt=submission.graded_at,
        errorMessage=submission.error_message,
    )


def _run_submission_grading(submission_id: str) -> None:
    db = SessionLocal()
    try:
        submission = db.query(Submission).filter(Submission.id == submission_id).first()
        if not submission:
            return
        assignment = db.query(Assignment).filter(Assignment.id == submission.assignment_id).first()
        if not assignment:
            submission.status = "error"
            submission.error_message = "Assignment not found"
            db.commit()
            return

        submission.status = "running"
        submission.error_message = None
        db.commit()

        try:
            result = grade_submission_with_rubric(submission, assignment)
            submission.status = "complete"
            submission.score = result["totalPointsEarned"]
            submission.max_score = result["totalPointsPossible"]
            submission.result_json = result
            submission.graded_at = datetime.now(timezone.utc)
            submission.error_message = None
        except Exception as exc:
            submission.status = "error"
            submission.error_message = str(exc)
        db.commit()
    finally:
        db.close()


@router.get("/assignments", response_model=list[AssignmentResponse])
def list_assignments(
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user_id),
) -> list[AssignmentResponse]:
    assignments = db.query(Assignment).order_by(Assignment.created_at.desc()).all()
    return [_assignment_response(assignment) for assignment in assignments]


@router.get("/assignments/active", response_model=list[AssignmentResponse])
def list_active_assignments(db: Session = Depends(get_db)) -> list[AssignmentResponse]:
    assignments = db.query(Assignment).filter(Assignment.is_active.is_(True)).order_by(Assignment.name.asc()).all()
    return [_assignment_response(assignment) for assignment in assignments]


@router.get("/assignments/{assignment_id}", response_model=AssignmentResponse)
def get_assignment(
    assignment_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user_id),
) -> AssignmentResponse:
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    return _assignment_response(assignment)


@router.post("/assignments", response_model=AssignmentResponse, status_code=201)
def create_assignment(
    payload: AssignmentCreate,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user_id),
) -> AssignmentResponse:
    assignment = Assignment(
        name=payload.name,
        description=payload.description,
        rubric_json=payload.rubricJson.model_dump(mode="json"),
        is_active=payload.isActive,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return _assignment_response(assignment)


@router.patch("/assignments/{assignment_id}", response_model=AssignmentResponse)
def update_assignment(
    assignment_id: str,
    payload: AssignmentUpdate,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user_id),
) -> AssignmentResponse:
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")

    if payload.name is not None:
        assignment.name = payload.name
    if payload.description is not None:
        assignment.description = payload.description
    if payload.rubricJson is not None:
        assignment.rubric_json = payload.rubricJson.model_dump(mode="json")
    if payload.isActive is not None:
        assignment.is_active = payload.isActive

    db.commit()
    db.refresh(assignment)
    return _assignment_response(assignment)


@router.delete("/assignments/{assignment_id}", status_code=204)
def delete_assignment(
    assignment_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user_id),
) -> None:
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    if not assignment:
        raise HTTPException(status_code=404, detail="Assignment not found")
    db.query(Submission).filter(Submission.assignment_id == assignment_id).delete()
    db.delete(assignment)
    db.commit()


@router.get("/rubric-templates", response_model=list[RubricTemplateResponse])
def rubric_templates(_: str = Depends(get_current_user_id)) -> list[dict[str, Any]]:
    return get_rubric_templates()


@router.post("/submissions", response_model=SubmissionAccepted, status_code=202)
def create_submission(
    payload: SubmissionCreate,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
) -> SubmissionAccepted:
    assignment = (
        db.query(Assignment)
        .filter(Assignment.id == payload.assignmentId)
        .filter(Assignment.is_active.is_(True))
        .first()
    )
    if not assignment:
        raise HTTPException(status_code=404, detail="Active assignment not found")

    submission = Submission(
        assignment_id=assignment.id,
        student_name=payload.studentName,
        student_email=str(payload.studentEmail),
        project_url=str(payload.projectUrl),
        status="pending",
        ticket_code=generate_ticket_code(db),
    )
    db.add(submission)
    db.commit()
    db.refresh(submission)

    background_tasks.add_task(_run_submission_grading, submission.id)
    return SubmissionAccepted(
        id=submission.id,
        assignmentId=submission.assignment_id,
        studentName=submission.student_name,
        studentEmail=submission.student_email,
        projectUrl=submission.project_url,
        status=submission.status,
        ticketCode=submission.ticket_code,
        submittedAt=submission.submitted_at,
    )


@router.get("/submissions", response_model=SubmissionListResponse)
def list_submissions(
    assignmentId: str | None = None,
    status: str | None = None,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user_id),
) -> SubmissionListResponse:
    query = db.query(Submission)
    if assignmentId:
        query = query.filter(Submission.assignment_id == assignmentId)
    if status:
        query = query.filter(Submission.status == status)
    submissions = query.order_by(Submission.submitted_at.desc()).all()
    assignment_ids = {submission.assignment_id for submission in submissions}
    assignments = {
        assignment.id: assignment
        for assignment in db.query(Assignment).filter(Assignment.id.in_(assignment_ids)).all()
    } if assignment_ids else {}
    return SubmissionListResponse(items=[_submission_response(s, assignments.get(s.assignment_id)) for s in submissions])


@router.get("/submissions/{submission_id}", response_model=SubmissionResponse)
def get_submission(
    submission_id: str,
    db: Session = Depends(get_db),
) -> SubmissionResponse:
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    assignment = db.query(Assignment).filter(Assignment.id == submission.assignment_id).first()
    return _submission_response(submission, assignment)


@router.get("/submissions/ticket/{code}", response_model=SubmissionResponse)
def get_submission_by_ticket(code: str, db: Session = Depends(get_db)) -> SubmissionResponse:
    submission = db.query(Submission).filter(Submission.ticket_code == code.upper()).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    assignment = db.query(Assignment).filter(Assignment.id == submission.assignment_id).first()
    return _submission_response(submission, assignment)


@router.get("/submissions/by-assignment/{assignment_id}", response_model=SubmissionListResponse)
def get_submissions_by_assignment(
    assignment_id: str,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user_id),
) -> SubmissionListResponse:
    submissions = (
        db.query(Submission)
        .filter(Submission.assignment_id == assignment_id)
        .order_by(Submission.submitted_at.desc())
        .all()
    )
    assignment = db.query(Assignment).filter(Assignment.id == assignment_id).first()
    return SubmissionListResponse(items=[_submission_response(submission, assignment) for submission in submissions])


@router.post("/submissions/{submission_id}/regrade", response_model=SubmissionResponse)
def regrade_submission(
    submission_id: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user_id),
) -> SubmissionResponse:
    submission = db.query(Submission).filter(Submission.id == submission_id).first()
    if not submission:
        raise HTTPException(status_code=404, detail="Submission not found")
    submission.status = "pending"
    submission.error_message = None
    db.commit()
    db.refresh(submission)
    background_tasks.add_task(_run_submission_grading, submission.id)
    assignment = db.query(Assignment).filter(Assignment.id == submission.assignment_id).first()
    return _submission_response(submission, assignment)


@router.get("/export/csv")
def export_submissions_csv(
    assignmentId: str | None = Query(default=None),
    db: Session = Depends(get_db),
    _: str = Depends(get_current_user_id),
) -> PlainTextResponse:
    query = db.query(Submission)
    if assignmentId:
        query = query.filter(Submission.assignment_id == assignmentId)
    submissions = query.order_by(Submission.submitted_at.desc()).all()
    assignment_ids = {submission.assignment_id for submission in submissions}
    assignments = {
        assignment.id: assignment
        for assignment in db.query(Assignment).filter(Assignment.id.in_(assignment_ids)).all()
    } if assignment_ids else {}

    out = io.StringIO()
    writer = csv.writer(out)
    writer.writerow(["Ticket", "Student Name", "Email", "Assignment", "URL", "Score", "Max Score", "Percent", "Status", "Submitted At"])
    for submission in submissions:
        assignment = assignments.get(submission.assignment_id)
        percent = ""
        if submission.score is not None and submission.max_score:
            percent = round((float(submission.score) / float(submission.max_score)) * 100, 2)
        writer.writerow(
            [
                submission.ticket_code,
                submission.student_name,
                submission.student_email,
                assignment.name if assignment else "",
                submission.project_url,
                "" if submission.score is None else float(submission.score),
                "" if submission.max_score is None else float(submission.max_score),
                percent,
                submission.status,
                submission.submitted_at.isoformat(),
            ]
        )
    return PlainTextResponse(
        out.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=webgrader-submissions.csv"},
    )
