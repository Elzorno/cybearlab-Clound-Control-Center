from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy.orm import Session

from ..db import SessionLocal
from ..deps import get_current_user_id, get_db
from ..models import GradeFeedbackItem, GradeRun, GradeSectionScore
from ..schemas import GradeRequest, GradeResponse, GradeRunAccepted, GradeRunListItem, GradeRunListResponse
from ..services.audit import write_audit
from ..services.grader_engine import run_grading

router = APIRouter(prefix="/grader", tags=["Grader"])


def _run_grading_task(run_id: str, actor_user_id: str) -> None:
    db = SessionLocal()
    try:
        run = db.query(GradeRun).filter(GradeRun.id == run_id).first()
        if not run:
            return

        try:
            run_grading(db, run)
            result_status = "success"
        except Exception:
            result_status = "failed"

        db.refresh(run)
        write_audit(
            db,
            actor_user_id=actor_user_id,
            event_type="grader.run.create",
            entity_type="grade_run",
            entity_id=run.id,
            status=result_status,
            metadata={"url": run.input_url, "run_status": run.status},
        )
    finally:
        db.close()


@router.post("/runs", response_model=GradeRunAccepted, status_code=202)
def create_grade_run(
    payload: GradeRequest,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> GradeRunAccepted:
    run = GradeRun(
        requested_by=current_user_id,
        input_url=str(payload.url),
        normalized_root=str(payload.url),
        student_username=payload.student_username,
        term=payload.term,
        status="queued",
    )
    db.add(run)
    db.commit()
    db.refresh(run)

    background_tasks.add_task(_run_grading_task, run.id, current_user_id)
    write_audit(
        db,
        actor_user_id=current_user_id,
        event_type="grader.run.create",
        entity_type="grade_run",
        entity_id=run.id,
        status="accepted",
        metadata={"url": run.input_url, "run_status": run.status},
    )
    return GradeRunAccepted(run_id=run.id, status=run.status)


@router.get("/runs", response_model=GradeRunListResponse)
def list_grade_runs(
    term: str | None = None,
    student: str | None = None,
    page: int = Query(default=1, ge=1),
    pageSize: int = Query(default=20, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> GradeRunListResponse:
    query = db.query(GradeRun)
    if term:
        query = query.filter(GradeRun.term == term)
    if student:
        query = query.filter(GradeRun.student_username == student)

    total = query.count()
    runs = (
        query.order_by(GradeRun.created_at.desc())
        .offset((page - 1) * pageSize)
        .limit(pageSize)
        .all()
    )

    items = [
        GradeRunListItem(
            run_id=r.id,
            url=r.input_url,
            status=r.status,
            total_score=float(r.total_score) if r.total_score is not None else None,
            created_at=r.created_at,
        )
        for r in runs
    ]

    write_audit(
        db,
        actor_user_id=current_user_id,
        event_type="grader.run.list",
        entity_type="grade_run",
        entity_id=None,
        status="success",
        metadata={"page": page, "pageSize": pageSize},
    )
    return GradeRunListResponse(page=page, page_size=pageSize, total=total, items=items)


@router.get("/runs/{run_id}", response_model=GradeResponse)
def get_grade_run(
    run_id: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> GradeResponse:
    run = db.query(GradeRun).filter(GradeRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    feedback = (
        db.query(GradeFeedbackItem)
        .filter(GradeFeedbackItem.run_id == run_id)
        .order_by(GradeFeedbackItem.order_index.asc())
        .all()
    )
    sections = db.query(GradeSectionScore).filter(GradeSectionScore.run_id == run_id).all()
    sections_payload = {
        s.section_key: {
            "score": float(s.score),
            "max_score": float(s.max_score),
            "details": s.details_json,
        }
        for s in sections
    }

    write_audit(
        db,
        actor_user_id=current_user_id,
        event_type="grader.run.read",
        entity_type="grade_run",
        entity_id=run.id,
        status="success",
    )
    return GradeResponse(
        run_id=run.id,
        status=run.status,
        input_url=run.input_url,
        normalized_root=run.normalized_root,
        total_score=float(run.total_score) if run.total_score is not None else None,
        sections=sections_payload,
        summary_feedback=[x.feedback_text for x in feedback],
        started_at=run.started_at,
        finished_at=run.finished_at,
    )


@router.get("/runs/{run_id}/export")
def export_grade_run(
    run_id: str,
    format: str = Query(default="json", pattern="^(json|csv)$"),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    run = db.query(GradeRun).filter(GradeRun.id == run_id).first()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    write_audit(
        db,
        actor_user_id=current_user_id,
        event_type="grader.run.export",
        entity_type="grade_run",
        entity_id=run.id,
        status="success",
        metadata={"format": format},
    )

    payload = {
        "run_id": run.id,
        "status": run.status,
        "input_url": run.input_url,
        "normalized_root": run.normalized_root,
        "total_score": float(run.total_score) if run.total_score is not None else None,
        "error_message": run.error_message,
    }

    if format == "csv":
        csv_text = "run_id,status,input_url,normalized_root,total_score\n"
        csv_text += (
            f"{run.id},{run.status},{run.input_url},{run.normalized_root or ''},"
            f"{'' if run.total_score is None else float(run.total_score)}\n"
        )
        return PlainTextResponse(content=csv_text, media_type="text/csv")

    return JSONResponse(content=payload)
