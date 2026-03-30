"""
Cron router - cron job management endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..deps import get_current_user_id, get_db
from ..services import cron_manager
from ..services.audit import write_audit

router = APIRouter(prefix="/cron", tags=["Cron"])


# ============================================================
# Schemas
# ============================================================

class CronJobResponse(BaseModel):
    id: int
    minute: str
    hour: str
    day: str
    month: str
    weekday: str
    command: str
    schedule: str
    enabled: bool
    comment: Optional[str] = None
    next_run: Optional[str] = None


class CronJobRequest(BaseModel):
    minute: str
    hour: str
    day: str
    month: str
    weekday: str
    command: str
    comment: Optional[str] = None


class ScheduleDescriptionRequest(BaseModel):
    minute: str
    hour: str
    day: str
    month: str
    weekday: str


class ScheduleDescriptionResponse(BaseModel):
    description: str


class CommonSchedulesResponse(BaseModel):
    schedules: dict


class SuccessResponse(BaseModel):
    success: bool
    message: str


# ============================================================
# Endpoints
# ============================================================

@router.get("/{username}", response_model=List[CronJobResponse])
def list_cron_jobs(
    username: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> List[CronJobResponse]:
    """List all cron jobs for a user."""
    try:
        jobs = cron_manager.list_cron_jobs(username)
        return [
            CronJobResponse(
                id=j.id,
                minute=j.minute,
                hour=j.hour,
                day=j.day,
                month=j.month,
                weekday=j.weekday,
                command=j.command,
                schedule=j.schedule,
                enabled=j.enabled,
                comment=j.comment,
                next_run=j.next_run,
            )
            for j in jobs
        ]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{username}/{job_id}", response_model=CronJobResponse)
def get_cron_job(
    username: str,
    job_id: int,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> CronJobResponse:
    """Get a specific cron job."""
    try:
        job = cron_manager.get_cron_job(username, job_id)
        return CronJobResponse(
            id=job.id,
            minute=job.minute,
            hour=job.hour,
            day=job.day,
            month=job.month,
            weekday=job.weekday,
            command=job.command,
            schedule=job.schedule,
            enabled=job.enabled,
            comment=job.comment,
            next_run=job.next_run,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{username}", response_model=CronJobResponse)
def create_cron_job(
    username: str,
    request: CronJobRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> CronJobResponse:
    """Create a new cron job."""
    try:
        job_req = cron_manager.CronJobRequest(
            minute=request.minute,
            hour=request.hour,
            day=request.day,
            month=request.month,
            weekday=request.weekday,
            command=request.command,
            comment=request.comment,
        )
        job = cron_manager.create_cron_job(username, job_req)
        write_audit(db, actor_user_id=current_user_id, event_type="cron.create", entity_type="cron", entity_id=f"{username}/{job.id}", status="success")
        return CronJobResponse(
            id=job.id,
            minute=job.minute,
            hour=job.hour,
            day=job.day,
            month=job.month,
            weekday=job.weekday,
            command=job.command,
            schedule=job.schedule,
            enabled=job.enabled,
            comment=job.comment,
        )
    except ValueError as e:
        write_audit(db, actor_user_id=current_user_id, event_type="cron.create", entity_type="cron", entity_id=username, status="error", metadata={"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{username}/{job_id}", response_model=CronJobResponse)
def update_cron_job(
    username: str,
    job_id: int,
    request: CronJobRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> CronJobResponse:
    """Update an existing cron job."""
    try:
        job_req = cron_manager.CronJobRequest(
            minute=request.minute,
            hour=request.hour,
            day=request.day,
            month=request.month,
            weekday=request.weekday,
            command=request.command,
            comment=request.comment,
        )
        job = cron_manager.update_cron_job(username, job_id, job_req)
        write_audit(db, actor_user_id=current_user_id, event_type="cron.update", entity_type="cron", entity_id=f"{username}/{job_id}", status="success")
        return CronJobResponse(
            id=job.id,
            minute=job.minute,
            hour=job.hour,
            day=job.day,
            month=job.month,
            weekday=job.weekday,
            command=job.command,
            schedule=job.schedule,
            enabled=job.enabled,
            comment=job.comment,
        )
    except ValueError as e:
        write_audit(db, actor_user_id=current_user_id, event_type="cron.update", entity_type="cron", entity_id=f"{username}/{job_id}", status="error", metadata={"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{username}/{job_id}", response_model=SuccessResponse)
def delete_cron_job(
    username: str,
    job_id: int,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """Delete a cron job."""
    try:
        cron_manager.delete_cron_job(username, job_id)
        write_audit(db, actor_user_id=current_user_id, event_type="cron.delete", entity_type="cron", entity_id=f"{username}/{job_id}", status="success")
        return SuccessResponse(success=True, message="Cron job deleted successfully")
    except ValueError as e:
        write_audit(db, actor_user_id=current_user_id, event_type="cron.delete", entity_type="cron", entity_id=f"{username}/{job_id}", status="error", metadata={"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{username}/{job_id}/toggle", response_model=CronJobResponse)
def toggle_cron_job(
    username: str,
    job_id: int,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> CronJobResponse:
    """Enable or disable a cron job."""
    try:
        job = cron_manager.toggle_cron_job(username, job_id)
        write_audit(db, actor_user_id=current_user_id, event_type="cron.toggle", entity_type="cron", entity_id=f"{username}/{job_id}", status="success")
        return CronJobResponse(
            id=job.id,
            minute=job.minute,
            hour=job.hour,
            day=job.day,
            month=job.month,
            weekday=job.weekday,
            command=job.command,
            schedule=job.schedule,
            enabled=job.enabled,
            comment=job.comment,
        )
    except ValueError as e:
        write_audit(db, actor_user_id=current_user_id, event_type="cron.toggle", entity_type="cron", entity_id=f"{username}/{job_id}", status="error", metadata={"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/schedules/common", response_model=CommonSchedulesResponse)
def get_common_schedules(
    current_user_id: str = Depends(get_current_user_id),
) -> CommonSchedulesResponse:
    """Get common cron schedule presets."""
    return CommonSchedulesResponse(schedules=cron_manager.get_common_schedules())


@router.post("/schedules/describe", response_model=ScheduleDescriptionResponse)
def describe_schedule(
    request: ScheduleDescriptionRequest,
    current_user_id: str = Depends(get_current_user_id),
) -> ScheduleDescriptionResponse:
    """Get human-readable description of a cron schedule."""
    description = cron_manager.describe_schedule(
        request.minute,
        request.hour,
        request.day,
        request.month,
        request.weekday,
    )
    return ScheduleDescriptionResponse(description=description)
