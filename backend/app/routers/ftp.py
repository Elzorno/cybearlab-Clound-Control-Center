"""
FTP router - FTP account management endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..deps import get_current_user_id, get_db
from ..services import ftp_manager
from ..services.audit import write_audit

router = APIRouter(prefix="/ftp", tags=["FTP"])


# ============================================================
# Schemas
# ============================================================

class FTPAccountResponse(BaseModel):
    username: str
    parent_user: str
    home_directory: str
    enabled: bool
    uid: int
    gid: int
    quota_mb: Optional[int] = None
    last_login: Optional[str] = None
    created: Optional[str] = None


class FTPSessionResponse(BaseModel):
    username: str
    ip_address: str
    connected_since: str
    idle_time: str
    current_dir: str


class CreateFTPAccountRequest(BaseModel):
    name: str
    password: Optional[str] = None
    directory: Optional[str] = None


class CreateFTPAccountResponse(BaseModel):
    account: FTPAccountResponse
    password: str  # Return generated password to admin


class SetPasswordRequest(BaseModel):
    password: str


class SetDirectoryRequest(BaseModel):
    directory: str


class SuccessResponse(BaseModel):
    success: bool
    message: str


# ============================================================
# Endpoints
# ============================================================

@router.get("/accounts/{username}", response_model=List[FTPAccountResponse])
def list_ftp_accounts(
    username: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> List[FTPAccountResponse]:
    """List all FTP accounts for a parent user."""
    try:
        accounts = ftp_manager.list_ftp_accounts(username)
        return [
            FTPAccountResponse(
                username=a.username,
                parent_user=a.parent_user,
                home_directory=a.home_directory,
                enabled=a.enabled,
                uid=a.uid,
                gid=a.gid,
                quota_mb=a.quota_mb,
                last_login=a.last_login,
                created=a.created
            )
            for a in accounts
        ]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/accounts/{username}/{ftp_name}", response_model=FTPAccountResponse)
def get_ftp_account(
    username: str,
    ftp_name: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> FTPAccountResponse:
    """Get details of a specific FTP account."""
    # Validate ownership
    prefix = f"{username}_"
    if ftp_name != username and not ftp_name.startswith(prefix):
        raise HTTPException(status_code=403, detail="FTP account does not belong to this user")
    
    try:
        account = ftp_manager.get_ftp_account(ftp_name)
        return FTPAccountResponse(
            username=account.username,
            parent_user=account.parent_user,
            home_directory=account.home_directory,
            enabled=account.enabled,
            uid=account.uid,
            gid=account.gid,
            quota_mb=account.quota_mb,
            last_login=account.last_login,
            created=account.created
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/accounts/{username}", response_model=CreateFTPAccountResponse)
def create_ftp_account(
    username: str,
    request: CreateFTPAccountRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> CreateFTPAccountResponse:
    """Create a new FTP account for a user."""
    try:
        account, password = ftp_manager.create_ftp_account(
            username,
            request.name,
            request.password,
            request.directory
        )
        write_audit(db, current_user_id, "ftp.create", f"{username}/{account.username}", "success")
        return CreateFTPAccountResponse(
            account=FTPAccountResponse(
                username=account.username,
                parent_user=account.parent_user,
                home_directory=account.home_directory,
                enabled=account.enabled,
                uid=account.uid,
                gid=account.gid,
                quota_mb=account.quota_mb,
                last_login=account.last_login,
                created=account.created
            ),
            password=password
        )
    except ValueError as e:
        write_audit(db, current_user_id, "ftp.create", f"{username}/{request.name}", "error", str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/accounts/{username}/{ftp_name}", response_model=SuccessResponse)
def delete_ftp_account(
    username: str,
    ftp_name: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """Delete an FTP account."""
    # Validate ownership  
    prefix = f"{username}_"
    if not ftp_name.startswith(prefix):
        raise HTTPException(status_code=403, detail="FTP account does not belong to this user")
    
    try:
        ftp_manager.delete_ftp_account(username, ftp_name)
        write_audit(db, current_user_id, "ftp.delete", f"{username}/{ftp_name}", "success")
        return SuccessResponse(success=True, message=f"FTP account {ftp_name} deleted successfully")
    except ValueError as e:
        write_audit(db, current_user_id, "ftp.delete", f"{username}/{ftp_name}", "error", str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/accounts/{username}/{ftp_name}/password", response_model=SuccessResponse)
def set_ftp_password(
    username: str,
    ftp_name: str,
    request: SetPasswordRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """Set/reset password for an FTP account."""
    try:
        ftp_manager.set_ftp_password(username, ftp_name, request.password)
        write_audit(db, current_user_id, "ftp.password", f"{username}/{ftp_name}", "success")
        return SuccessResponse(success=True, message="Password updated successfully")
    except ValueError as e:
        write_audit(db, current_user_id, "ftp.password", f"{username}/{ftp_name}", "error", str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/accounts/{username}/{ftp_name}/enable", response_model=SuccessResponse)
def enable_ftp_account(
    username: str,
    ftp_name: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """Enable a disabled FTP account."""
    try:
        ftp_manager.enable_ftp_account(username, ftp_name)
        write_audit(db, current_user_id, "ftp.enable", f"{username}/{ftp_name}", "success")
        return SuccessResponse(success=True, message=f"FTP account {ftp_name} enabled")
    except ValueError as e:
        write_audit(db, current_user_id, "ftp.enable", f"{username}/{ftp_name}", "error", str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/accounts/{username}/{ftp_name}/disable", response_model=SuccessResponse)
def disable_ftp_account(
    username: str,
    ftp_name: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """Disable an FTP account."""
    try:
        ftp_manager.disable_ftp_account(username, ftp_name)
        write_audit(db, current_user_id, "ftp.disable", f"{username}/{ftp_name}", "success")
        return SuccessResponse(success=True, message=f"FTP account {ftp_name} disabled")
    except ValueError as e:
        write_audit(db, current_user_id, "ftp.disable", f"{username}/{ftp_name}", "error", str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/accounts/{username}/{ftp_name}/directory", response_model=SuccessResponse)
def set_ftp_directory(
    username: str,
    ftp_name: str,
    request: SetDirectoryRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """Set the home directory for an FTP account."""
    try:
        ftp_manager.set_ftp_directory(username, ftp_name, request.directory)
        write_audit(db, current_user_id, "ftp.directory", f"{username}/{ftp_name}", "success")
        return SuccessResponse(success=True, message="Home directory updated successfully")
    except ValueError as e:
        write_audit(db, current_user_id, "ftp.directory", f"{username}/{ftp_name}", "error", str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/sessions", response_model=List[FTPSessionResponse])
def get_active_sessions(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> List[FTPSessionResponse]:
    """Get list of active FTP sessions."""
    try:
        sessions = ftp_manager.get_active_ftp_sessions()
        return [
            FTPSessionResponse(
                username=s.username,
                ip_address=s.ip_address,
                connected_since=s.connected_since,
                idle_time=s.idle_time,
                current_dir=s.current_dir
            )
            for s in sessions
        ]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/sessions/{username}/kick", response_model=SuccessResponse)
def kick_session(
    username: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """Disconnect an active FTP session."""
    try:
        ftp_manager.kick_ftp_session(username)
        write_audit(db, current_user_id, "ftp.kick", username, "success")
        return SuccessResponse(success=True, message=f"Session for {username} disconnected")
    except ValueError as e:
        write_audit(db, current_user_id, "ftp.kick", username, "error", str(e))
        raise HTTPException(status_code=400, detail=str(e))
