"""
SSL router - SSL/TLS certificate management endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..deps import get_current_user_id, get_db
from ..services import ssl_manager
from ..services.audit import write_audit

router = APIRouter(prefix="/ssl", tags=["SSL"])


# ============================================================
# Schemas
# ============================================================

class CertificateResponse(BaseModel):
    domain: str
    domains: List[str]
    issuer: str
    valid_from: str
    valid_until: str
    serial: str
    days_remaining: int
    is_expired: bool
    is_expiring_soon: bool
    auto_renew: bool


class CertificateSummaryResponse(BaseModel):
    domain: str
    valid_until: str
    days_remaining: int
    is_expired: bool
    is_expiring_soon: bool


class CertificateRequestBody(BaseModel):
    domains: List[str]
    email: str
    webroot_path: Optional[str] = None
    standalone: bool = False
    dry_run: bool = False


class ExpiryWarning(BaseModel):
    domain: str
    days_remaining: int
    valid_until: str


class ExpiryWarningsResponse(BaseModel):
    warnings: List[ExpiryWarning]


class SuccessResponse(BaseModel):
    success: bool
    message: str


# ============================================================
# Endpoints
# ============================================================

@router.get("/certificates", response_model=List[CertificateSummaryResponse])
def list_certificates(
    current_user_id: str = Depends(get_current_user_id),
) -> List[CertificateSummaryResponse]:
    """List all SSL certificates."""
    certs = ssl_manager.list_certificates()
    return [
        CertificateSummaryResponse(
            domain=c.domain,
            valid_until=c.valid_until,
            days_remaining=c.days_remaining,
            is_expired=c.is_expired,
            is_expiring_soon=c.is_expiring_soon,
        )
        for c in certs
    ]


@router.get("/certificates/{domain}", response_model=CertificateResponse)
def get_certificate(
    domain: str,
    current_user_id: str = Depends(get_current_user_id),
) -> CertificateResponse:
    """Get details of a specific certificate."""
    try:
        cert = ssl_manager.get_certificate(domain)
        return CertificateResponse(
            domain=cert.domain,
            domains=cert.domains,
            issuer=cert.issuer,
            valid_from=cert.valid_from,
            valid_until=cert.valid_until,
            serial=cert.serial,
            days_remaining=cert.days_remaining,
            is_expired=cert.is_expired,
            is_expiring_soon=cert.is_expiring_soon,
            auto_renew=cert.auto_renew,
        )
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/certificates", response_model=SuccessResponse)
def request_certificate(
    request: CertificateRequestBody,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """Request a new SSL certificate."""
    try:
        req = ssl_manager.CertificateRequest(
            domains=request.domains,
            email=request.email,
            webroot_path=request.webroot_path,
            standalone=request.standalone,
            dry_run=request.dry_run,
        )
        ssl_manager.request_certificate(req)
        write_audit(
            db, actor_user_id=current_user_id, event_type="ssl.request",
            entity_type="ssl", entity_id=",".join(request.domains), status="success"
        )
        return SuccessResponse(
            success=True,
            message=f"Certificate requested for {', '.join(request.domains)}"
        )
    except ValueError as e:
        write_audit(
            db, actor_user_id=current_user_id, event_type="ssl.request",
            entity_type="ssl", entity_id=",".join(request.domains), status="error",
            metadata={"error": str(e)}
        )
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/certificates/{domain}/renew", response_model=SuccessResponse)
def renew_certificate(
    domain: str,
    force: bool = Query(False, description="Force renewal even if certificate is not expiring"),
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """Renew a specific certificate."""
    try:
        ssl_manager.renew_certificate(domain, force=force)
        write_audit(db, actor_user_id=current_user_id, event_type="ssl.renew", entity_type="ssl", entity_id=domain, status="success", metadata={"force": force})
        return SuccessResponse(success=True, message=f"Certificate renewed for {domain}" + (" (forced)" if force else ""))
    except ValueError as e:
        write_audit(db, actor_user_id=current_user_id, event_type="ssl.renew", entity_type="ssl", entity_id=domain, status="error", metadata={"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/certificates/renew-all", response_model=SuccessResponse)
def renew_all_certificates(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """Renew all certificates that need renewal."""
    try:
        ssl_manager.renew_all_certificates()
        write_audit(db, actor_user_id=current_user_id, event_type="ssl.renew_all", entity_type="ssl", entity_id="all", status="success")
        return SuccessResponse(success=True, message="All certificates renewed")
    except ValueError as e:
        write_audit(db, actor_user_id=current_user_id, event_type="ssl.renew_all", entity_type="ssl", entity_id="all", status="error", metadata={"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/certificates/{domain}/revoke", response_model=SuccessResponse)
def revoke_certificate(
    domain: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """Revoke a certificate."""
    try:
        ssl_manager.revoke_certificate(domain)
        write_audit(db, actor_user_id=current_user_id, event_type="ssl.revoke", entity_type="ssl", entity_id=domain, status="success")
        return SuccessResponse(success=True, message=f"Certificate revoked for {domain}")
    except ValueError as e:
        write_audit(db, actor_user_id=current_user_id, event_type="ssl.revoke", entity_type="ssl", entity_id=domain, status="error", metadata={"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/certificates/{domain}", response_model=SuccessResponse)
def delete_certificate(
    domain: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """Delete a certificate."""
    try:
        ssl_manager.delete_certificate(domain)
        write_audit(db, actor_user_id=current_user_id, event_type="ssl.delete", entity_type="ssl", entity_id=domain, status="success")
        return SuccessResponse(success=True, message=f"Certificate deleted for {domain}")
    except ValueError as e:
        write_audit(db, actor_user_id=current_user_id, event_type="ssl.delete", entity_type="ssl", entity_id=domain, status="error", metadata={"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/warnings", response_model=ExpiryWarningsResponse)
def check_expiry_warnings(
    days_threshold: int = 30,
    current_user_id: str = Depends(get_current_user_id),
) -> ExpiryWarningsResponse:
    """Check for certificates expiring soon."""
    certs = ssl_manager.list_certificates()
    warnings = [
        ExpiryWarning(
            domain=c.domain,
            days_remaining=c.days_remaining,
            valid_until=c.valid_until,
        )
        for c in certs
        if c.days_remaining <= days_threshold and not c.is_expired
    ]
    return ExpiryWarningsResponse(warnings=warnings)
