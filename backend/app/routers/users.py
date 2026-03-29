"""
Users management router - list, view, and manage user accounts.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..deps import get_current_user_id, get_db
from ..services import user_manager
from ..services.audit import write_audit

router = APIRouter(prefix="/users", tags=["Users"])


# ============================================================
# Schemas
# ============================================================

class UserInfoResponse(BaseModel):
    username: str
    term: str
    uid: int
    gid: int
    home_dir: str
    shell: str
    disk_used_bytes: int
    disk_used_formatted: str
    disk_quota_bytes: Optional[int]
    disk_quota_formatted: Optional[str]
    disk_percent: float
    is_suspended: bool
    public_html_exists: bool
    file_count: int


class UserDetailResponse(UserInfoResponse):
    groups: List[str]
    last_login: Optional[str]
    created_at: Optional[str]
    public_html_files: int
    index_exists: bool


class UserListResponse(BaseModel):
    users: List[UserInfoResponse]
    total: int
    terms: List[str]


class TermsResponse(BaseModel):
    terms: List[str]


class UserActionRequest(BaseModel):
    action: str  # suspend, unsuspend, set_quota, delete


class QuotaRequest(BaseModel):
    quota_mb: int


class DeleteRequest(BaseModel):
    remove_home: bool = False


class ActionResponse(BaseModel):
    success: bool
    message: str


# ============================================================
# Endpoints
# ============================================================

@router.get("/terms", response_model=TermsResponse)
def get_terms(
    current_user_id: str = Depends(get_current_user_id),
) -> TermsResponse:
    """Get list of available terms."""
    terms = user_manager.get_terms()
    return TermsResponse(terms=terms)


@router.get("", response_model=UserListResponse)
def list_users(
    term: Optional[str] = Query(None, description="Filter by term"),
    suspended: Optional[bool] = Query(None, description="Filter by suspended status"),
    search: Optional[str] = Query(None, description="Search username"),
    current_user_id: str = Depends(get_current_user_id),
) -> UserListResponse:
    """List all users with optional filters."""
    users = user_manager.list_users(term=term)
    
    # Apply filters
    if suspended is not None:
        users = [u for u in users if u.is_suspended == suspended]
    
    if search:
        search_lower = search.lower()
        users = [u for u in users if search_lower in u.username.lower()]
    
    # Convert to response format
    user_responses = []
    for u in users:
        user_responses.append(UserInfoResponse(
            username=u.username,
            term=u.term,
            uid=u.uid,
            gid=u.gid,
            home_dir=u.home_dir,
            shell=u.shell,
            disk_used_bytes=u.disk_used_bytes,
            disk_used_formatted=user_manager.format_bytes(u.disk_used_bytes),
            disk_quota_bytes=u.disk_quota_bytes,
            disk_quota_formatted=user_manager.format_bytes(u.disk_quota_bytes) if u.disk_quota_bytes else None,
            disk_percent=u.disk_percent,
            is_suspended=u.is_suspended,
            public_html_exists=u.public_html_exists,
            file_count=u.file_count,
        ))
    
    terms = user_manager.get_terms()
    
    return UserListResponse(
        users=user_responses,
        total=len(user_responses),
        terms=terms,
    )


@router.get("/{username}", response_model=UserDetailResponse)
def get_user_detail(
    username: str,
    current_user_id: str = Depends(get_current_user_id),
) -> UserDetailResponse:
    """Get detailed information about a specific user."""
    detail = user_manager.get_user_detail(username)
    
    if not detail:
        raise HTTPException(status_code=404, detail="User not found")
    
    return UserDetailResponse(
        username=detail.username,
        term=detail.term,
        uid=detail.uid,
        gid=detail.gid,
        home_dir=detail.home_dir,
        shell=detail.shell,
        disk_used_bytes=detail.disk_used_bytes,
        disk_used_formatted=user_manager.format_bytes(detail.disk_used_bytes),
        disk_quota_bytes=detail.disk_quota_bytes,
        disk_quota_formatted=user_manager.format_bytes(detail.disk_quota_bytes) if detail.disk_quota_bytes else None,
        disk_percent=detail.disk_percent,
        is_suspended=detail.is_suspended,
        public_html_exists=detail.public_html_exists,
        file_count=detail.file_count,
        groups=detail.groups,
        last_login=detail.last_login,
        created_at=detail.created_at,
        public_html_files=detail.public_html_files,
        index_exists=detail.index_exists,
    )


@router.post("/{username}/suspend", response_model=ActionResponse)
def suspend_user(
    username: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> ActionResponse:
    """Suspend a user account."""
    success, message = user_manager.suspend_user(username)
    
    write_audit(
        db,
        actor_user_id=current_user_id,
        event_type="user.suspend",
        entity_type="user",
        entity_id=username,
        status="success" if success else "failed",
        metadata={"message": message},
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return ActionResponse(success=True, message=message)


@router.post("/{username}/unsuspend", response_model=ActionResponse)
def unsuspend_user(
    username: str,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> ActionResponse:
    """Unsuspend a user account."""
    success, message = user_manager.unsuspend_user(username)
    
    write_audit(
        db,
        actor_user_id=current_user_id,
        event_type="user.unsuspend",
        entity_type="user",
        entity_id=username,
        status="success" if success else "failed",
        metadata={"message": message},
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return ActionResponse(success=True, message=message)


@router.post("/{username}/quota", response_model=ActionResponse)
def set_user_quota(
    username: str,
    request: QuotaRequest,
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> ActionResponse:
    """Set disk quota for a user."""
    success, message = user_manager.set_quota(username, request.quota_mb)
    
    write_audit(
        db,
        actor_user_id=current_user_id,
        event_type="user.set_quota",
        entity_type="user",
        entity_id=username,
        status="success" if success else "failed",
        metadata={"quota_mb": request.quota_mb, "message": message},
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return ActionResponse(success=True, message=message)


@router.delete("/{username}", response_model=ActionResponse)
def delete_user(
    username: str,
    remove_home: bool = Query(False, description="Also remove home directory"),
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id),
) -> ActionResponse:
    """Delete a user account."""
    success, message = user_manager.delete_user(username, remove_home=remove_home)
    
    write_audit(
        db,
        actor_user_id=current_user_id,
        event_type="user.delete",
        entity_type="user",
        entity_id=username,
        status="success" if success else "failed",
        metadata={"remove_home": remove_home, "message": message},
    )
    
    if not success:
        raise HTTPException(status_code=400, detail=message)
    
    return ActionResponse(success=True, message=message)


@router.get("/{username}/usage")
def get_user_disk_usage(
    username: str,
    current_user_id: str = Depends(get_current_user_id),
):
    """Get detailed disk usage breakdown for a user."""
    detail = user_manager.get_user_detail(username)
    
    if not detail:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "username": username,
        "home_dir": detail.home_dir,
        "total_bytes": detail.disk_used_bytes,
        "total_formatted": user_manager.format_bytes(detail.disk_used_bytes),
        "file_count": detail.file_count,
        "public_html_files": detail.public_html_files,
        "quota_bytes": detail.disk_quota_bytes,
        "quota_formatted": user_manager.format_bytes(detail.disk_quota_bytes) if detail.disk_quota_bytes else None,
        "percent_used": detail.disk_percent,
    }
