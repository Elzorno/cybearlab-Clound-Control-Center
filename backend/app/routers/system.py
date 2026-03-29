"""
System management router - monitoring, services, logs, backups.
"""

from typing import List, Optional
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, Query
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..deps import get_current_user_id, get_db
from ..services import system_monitor, service_manager, log_streamer, backup_manager
from ..services.audit import write_audit

router = APIRouter(prefix="/system", tags=["System"])


# ============================================================
# Schemas
# ============================================================

class CpuStatsResponse(BaseModel):
    percent: float
    count: int
    per_cpu: List[float]
    load_avg: List[float]


class MemoryStatsResponse(BaseModel):
    total: int
    available: int
    used: int
    percent: float
    swap_total: int
    swap_used: int
    swap_percent: float
    total_formatted: str
    used_formatted: str
    available_formatted: str


class DiskStatsResponse(BaseModel):
    mount: str
    device: str
    total: int
    used: int
    free: int
    percent: float
    total_formatted: str
    used_formatted: str
    free_formatted: str


class NetworkStatsResponse(BaseModel):
    bytes_sent: int
    bytes_recv: int
    packets_sent: int
    packets_recv: int
    sent_formatted: str
    recv_formatted: str


class ProcessInfoResponse(BaseModel):
    pid: int
    name: str
    username: str
    cpu_percent: float
    memory_percent: float
    status: str


class SystemStatsResponse(BaseModel):
    timestamp: str
    uptime: int
    uptime_formatted: str
    cpu: CpuStatsResponse
    memory: MemoryStatsResponse
    disks: List[DiskStatsResponse]
    network: NetworkStatsResponse
    top_processes: List[ProcessInfoResponse]


class ServiceInfoResponse(BaseModel):
    name: str
    display_name: str
    status: str
    enabled: bool
    description: str
    pid: Optional[int]
    memory_mb: Optional[float]
    uptime: Optional[str]


class ServiceActionRequest(BaseModel):
    action: str  # start, stop, restart, enable, disable


class ServiceActionResponse(BaseModel):
    success: bool
    message: str


class LogFileResponse(BaseModel):
    key: str
    name: str
    path: str
    description: str
    exists: bool
    size_bytes: int
    size_formatted: str


class LogContentResponse(BaseModel):
    key: str
    content: str
    lines: int


class BackupInfoResponse(BaseModel):
    filename: str
    path: str
    size_bytes: int
    size_formatted: str
    created_at: str
    term: Optional[str]
    student: Optional[str]
    backup_type: str


class BackupResultResponse(BaseModel):
    success: bool
    message: str
    filename: Optional[str]
    size_bytes: int
    size_formatted: str
    duration_seconds: float


class CreateBackupRequest(BaseModel):
    backup_type: str  # full, term, student
    term: Optional[str] = None
    student: Optional[str] = None


class TermsResponse(BaseModel):
    terms: List[str]


class StudentsResponse(BaseModel):
    students: List[str]


# ============================================================
# Monitoring Endpoints
# ============================================================

@router.get("/stats", response_model=SystemStatsResponse)
def get_system_stats(
    current_user_id: str = Depends(get_current_user_id),
) -> SystemStatsResponse:
    """Get current system statistics (CPU, memory, disk, network)."""
    stats = system_monitor.get_system_stats(include_processes=True)
    
    return SystemStatsResponse(
        timestamp=stats.timestamp,
        uptime=stats.uptime,
        uptime_formatted=system_monitor.format_uptime(stats.uptime),
        cpu=CpuStatsResponse(
            percent=stats.cpu.percent,
            count=stats.cpu.count,
            per_cpu=stats.cpu.per_cpu,
            load_avg=list(stats.cpu.load_avg),
        ),
        memory=MemoryStatsResponse(
            total=stats.memory.total,
            available=stats.memory.available,
            used=stats.memory.used,
            percent=stats.memory.percent,
            swap_total=stats.memory.swap_total,
            swap_used=stats.memory.swap_used,
            swap_percent=stats.memory.swap_percent,
            total_formatted=system_monitor.format_bytes(stats.memory.total),
            used_formatted=system_monitor.format_bytes(stats.memory.used),
            available_formatted=system_monitor.format_bytes(stats.memory.available),
        ),
        disks=[
            DiskStatsResponse(
                mount=d.mount,
                device=d.device,
                total=d.total,
                used=d.used,
                free=d.free,
                percent=d.percent,
                total_formatted=system_monitor.format_bytes(d.total),
                used_formatted=system_monitor.format_bytes(d.used),
                free_formatted=system_monitor.format_bytes(d.free),
            )
            for d in stats.disks
        ],
        network=NetworkStatsResponse(
            bytes_sent=stats.network.bytes_sent,
            bytes_recv=stats.network.bytes_recv,
            packets_sent=stats.network.packets_sent,
            packets_recv=stats.network.packets_recv,
            sent_formatted=system_monitor.format_bytes(stats.network.bytes_sent),
            recv_formatted=system_monitor.format_bytes(stats.network.bytes_recv),
        ),
        top_processes=[
            ProcessInfoResponse(
                pid=p.pid,
                name=p.name,
                username=p.username,
                cpu_percent=p.cpu_percent,
                memory_percent=p.memory_percent,
                status=p.status,
            )
            for p in stats.top_processes
        ],
    )


# ============================================================
# Service Management Endpoints
# ============================================================

@router.get("/services", response_model=List[ServiceInfoResponse])
def get_services(
    current_user_id: str = Depends(get_current_user_id),
) -> List[ServiceInfoResponse]:
    """Get status of all monitored services."""
    services = service_manager.get_all_services()
    
    return [
        ServiceInfoResponse(
            name=s.name,
            display_name=s.display_name,
            status=s.status.value,
            enabled=s.enabled,
            description=s.description,
            pid=s.pid,
            memory_mb=s.memory_mb,
            uptime=s.uptime,
        )
        for s in services
    ]


@router.post("/services/{service_name}", response_model=ServiceActionResponse)
def control_service(
    service_name: str,
    request: ServiceActionRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> ServiceActionResponse:
    """Control a service (start, stop, restart, enable, disable)."""
    success, message = service_manager.control_service(service_name, request.action)
    
    write_audit(
        db,
        actor_user_id=current_user_id,
        event_type=f"system.service.{request.action}",
        entity_type="service",
        entity_id=service_name,
        status="success" if success else "failed",
        metadata={"action": request.action, "message": message},
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return ServiceActionResponse(success=success, message=message)


# ============================================================
# Log Endpoints
# ============================================================

@router.get("/logs", response_model=List[LogFileResponse])
def get_logs(
    current_user_id: str = Depends(get_current_user_id),
) -> List[LogFileResponse]:
    """Get list of available log files."""
    logs = log_streamer.get_available_logs()
    
    return [
        LogFileResponse(
            key=l.key,
            name=l.name,
            path=l.path,
            description=l.description,
            exists=l.exists,
            size_bytes=l.size_bytes,
            size_formatted=log_streamer.format_log_size(l.size_bytes),
        )
        for l in logs
    ]


@router.get("/logs/{log_key}", response_model=LogContentResponse)
def get_log_content(
    log_key: str,
    lines: int = Query(default=100, ge=1, le=1000),
    current_user_id: str = Depends(get_current_user_id),
) -> LogContentResponse:
    """Get the last N lines of a log file."""
    content = log_streamer.read_log_tail(log_key, lines)
    
    if content is None:
        raise HTTPException(status_code=404, detail=f"Log not found: {log_key}")
    
    return LogContentResponse(
        key=log_key,
        content=content,
        lines=content.count('\n'),
    )


@router.get("/logs/{log_key}/search")
def search_log(
    log_key: str,
    pattern: str = Query(..., min_length=1),
    lines: int = Query(default=100, ge=1, le=500),
    current_user_id: str = Depends(get_current_user_id),
) -> LogContentResponse:
    """Search a log file for a pattern."""
    content = log_streamer.search_log(log_key, pattern, lines)
    
    if content is None:
        raise HTTPException(status_code=404, detail=f"Log not found: {log_key}")
    
    return LogContentResponse(
        key=log_key,
        content=content,
        lines=content.count('\n'),
    )


@router.websocket("/logs/{log_key}/stream")
async def stream_log(
    websocket: WebSocket,
    log_key: str,
):
    """WebSocket endpoint to stream log file updates in real-time."""
    await websocket.accept()
    
    try:
        async for line in log_streamer.tail_log_stream(log_key):
            if line:
                await websocket.send_text(line)
            else:
                # Keepalive ping
                await websocket.send_text("")
    except WebSocketDisconnect:
        pass
    except Exception as e:
        try:
            await websocket.send_text(f"Error: {str(e)}\n")
        except:
            pass


# ============================================================
# Backup Endpoints
# ============================================================

@router.get("/backups", response_model=List[BackupInfoResponse])
def get_backups(
    current_user_id: str = Depends(get_current_user_id),
) -> List[BackupInfoResponse]:
    """Get list of existing backups."""
    backups = backup_manager.get_backup_list()
    
    return [
        BackupInfoResponse(
            filename=b.filename,
            path=b.path,
            size_bytes=b.size_bytes,
            size_formatted=backup_manager.format_backup_size(b.size_bytes),
            created_at=b.created_at,
            term=b.term,
            student=b.student,
            backup_type=b.backup_type,
        )
        for b in backups
    ]


@router.post("/backups", response_model=BackupResultResponse)
def create_backup(
    request: CreateBackupRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> BackupResultResponse:
    """Create a new backup."""
    if request.backup_type == "full":
        result = backup_manager.create_full_backup()
    elif request.backup_type == "term":
        if not request.term:
            raise HTTPException(status_code=400, detail="Term is required for term backup")
        result = backup_manager.create_term_backup(request.term)
    elif request.backup_type == "student":
        if not request.term or not request.student:
            raise HTTPException(status_code=400, detail="Term and student are required for student backup")
        result = backup_manager.create_student_backup(request.term, request.student)
    else:
        raise HTTPException(status_code=400, detail=f"Invalid backup type: {request.backup_type}")
    
    write_audit(
        db,
        actor_user_id=current_user_id,
        event_type="system.backup.create",
        entity_type="backup",
        entity_id=result.filename,
        status="success" if result.success else "failed",
        metadata={
            "backup_type": request.backup_type,
            "term": request.term,
            "student": request.student,
            "size_bytes": result.size_bytes,
            "duration_seconds": result.duration_seconds,
        },
    )
    
    if not result.success:
        raise HTTPException(status_code=500, detail=result.message)
    
    return BackupResultResponse(
        success=result.success,
        message=result.message,
        filename=result.filename,
        size_bytes=result.size_bytes,
        size_formatted=backup_manager.format_backup_size(result.size_bytes),
        duration_seconds=result.duration_seconds,
    )


@router.get("/backups/{filename}/download")
def download_backup(
    filename: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
):
    """Download a backup file."""
    filepath = backup_manager.get_backup_download_path(filename)
    
    if not filepath:
        raise HTTPException(status_code=404, detail="Backup not found")
    
    write_audit(
        db,
        actor_user_id=current_user_id,
        event_type="system.backup.download",
        entity_type="backup",
        entity_id=filename,
        status="success",
    )
    
    return FileResponse(
        filepath,
        filename=filename,
        media_type="application/gzip",
    )


@router.delete("/backups/{filename}")
def delete_backup(
    filename: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> ServiceActionResponse:
    """Delete a backup file."""
    success, message = backup_manager.delete_backup(filename)
    
    write_audit(
        db,
        actor_user_id=current_user_id,
        event_type="system.backup.delete",
        entity_type="backup",
        entity_id=filename,
        status="success" if success else "failed",
        metadata={"message": message},
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return ServiceActionResponse(success=success, message=message)


@router.get("/backups/terms", response_model=TermsResponse)
def get_terms(
    current_user_id: str = Depends(get_current_user_id),
) -> TermsResponse:
    """Get list of available terms for backup."""
    return TermsResponse(terms=backup_manager.get_available_terms())


@router.get("/backups/terms/{term}/students", response_model=StudentsResponse)
def get_students_in_term(
    term: str,
    current_user_id: str = Depends(get_current_user_id),
) -> StudentsResponse:
    """Get list of students in a term for backup."""
    return StudentsResponse(students=backup_manager.get_students_in_term(term))
