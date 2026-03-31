"""
Updates router — package checker and one-click OS/service updates.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from ..deps import get_current_user_id
from ..services import update_manager
from ..services.audit import write_audit

router = APIRouter(prefix="/updates", tags=["Updates"])


# ============================================================
# Schemas
# ============================================================

class PackageUpdateResponse(BaseModel):
    name: str
    current_version: str
    new_version: str
    source: str
    is_security: bool


class UpdateSummaryResponse(BaseModel):
    timestamp: str
    total: int
    security: int
    packages: List[PackageUpdateResponse]
    last_check: Optional[str]
    last_update: Optional[str]
    reboot_required: bool


class ApplyUpdatesRequest(BaseModel):
    package_names: Optional[List[str]] = None
    security_only: bool = False


class UpdateResultResponse(BaseModel):
    success: bool
    message: str
    updated_count: int
    errors: List[str]
    timestamp: str


class ServiceVersionsResponse(BaseModel):
    versions: dict


# ============================================================
# Endpoints
# ============================================================

@router.post("/refresh", response_model=dict)
def refresh_packages(
    current_user_id: str = Depends(get_current_user_id),
) -> dict:
    """Refresh the apt package list (apt-get update)."""
    success, message = update_manager.refresh_package_list()
    write_audit(current_user_id, "updates.refresh", {"success": success})
    if not success:
        raise HTTPException(status_code=500, detail=message)
    return {"status": "ok", "message": message}


@router.get("/check", response_model=UpdateSummaryResponse)
def check_updates(
    current_user_id: str = Depends(get_current_user_id),
) -> UpdateSummaryResponse:
    """Check for available OS/package updates."""
    summary = update_manager.check_updates()
    write_audit(current_user_id, "updates.check", {
        "total": summary.total,
        "security": summary.security,
    })
    return UpdateSummaryResponse(
        timestamp=summary.timestamp,
        total=summary.total,
        security=summary.security,
        packages=[
            PackageUpdateResponse(
                name=p.name,
                current_version=p.current_version,
                new_version=p.new_version,
                source=p.source,
                is_security=p.is_security,
            )
            for p in summary.packages
        ],
        last_check=summary.last_check,
        last_update=summary.last_update,
        reboot_required=summary.reboot_required,
    )


@router.post("/apply", response_model=UpdateResultResponse)
def apply_updates(
    req: ApplyUpdatesRequest,
    current_user_id: str = Depends(get_current_user_id),
) -> UpdateResultResponse:
    """Apply OS/package updates."""
    result = update_manager.apply_updates(
        package_names=req.package_names,
        security_only=req.security_only,
    )
    write_audit(current_user_id, "updates.apply", {
        "success": result.success,
        "updated_count": result.updated_count,
        "security_only": req.security_only,
        "specific_packages": req.package_names,
    })
    return UpdateResultResponse(
        success=result.success,
        message=result.message,
        updated_count=result.updated_count,
        errors=result.errors,
        timestamp=result.timestamp,
    )


@router.get("/versions", response_model=ServiceVersionsResponse)
def get_service_versions(
    current_user_id: str = Depends(get_current_user_id),
) -> ServiceVersionsResponse:
    """Get installed service/software versions."""
    versions = update_manager.get_service_versions()
    return ServiceVersionsResponse(versions=versions)
