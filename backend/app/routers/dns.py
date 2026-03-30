"""
DNS management API endpoints.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Optional

from ..deps import get_current_user_id
from ..services import dns_manager


router = APIRouter(prefix="/dns", tags=["DNS"])


class RecordCreate(BaseModel):
    name: str
    type: str  # A, AAAA, CNAME, TXT, MX
    content: str
    ttl: int = 3600
    priority: Optional[int] = None


class RecordUpdate(BaseModel):
    content: str
    ttl: Optional[int] = None


class RecordResponse(BaseModel):
    id: str
    name: str
    type: str
    content: str
    ttl: int
    priority: Optional[int] = None


class CertificateResponse(BaseModel):
    domain: str
    issuer: str
    valid_from: str
    valid_to: str
    days_remaining: int
    is_wildcard: bool


class DomainInfoResponse(BaseModel):
    domain: str
    subdomains: list[str]
    record_count: int


@router.get("/info")
async def get_domain_info(user_id=Depends(get_current_user_id)) -> DomainInfoResponse:
    """Get domain overview information."""
    domain = dns_manager.get_domain()
    subdomains = dns_manager.get_student_subdomains()
    records = await dns_manager.list_dns_records()
    
    return DomainInfoResponse(
        domain=domain,
        subdomains=subdomains,
        record_count=len(records)
    )


@router.get("/records")
async def list_records(user_id=Depends(get_current_user_id)) -> list[RecordResponse]:
    """List all DNS records."""
    records = await dns_manager.list_dns_records()
    return [
        RecordResponse(
            id=r.id,
            name=r.name,
            type=r.type,
            content=r.content,
            ttl=r.ttl,
            priority=r.priority
        )
        for r in records
    ]


@router.post("/records")
async def create_record(record: RecordCreate, user_id=Depends(get_current_user_id)):
    """Create a new DNS record."""
    # Validate record type
    valid_types = ["A", "AAAA", "CNAME", "TXT", "MX"]
    if record.type.upper() not in valid_types:
        raise HTTPException(400, f"Invalid record type. Must be one of: {valid_types}")
    
    # Validate name (subdomain)
    if not record.name or len(record.name) > 63:
        raise HTTPException(400, "Invalid subdomain name")
    
    success, message = await dns_manager.create_dns_record(
        name=record.name,
        record_type=record.type.upper(),
        content=record.content,
        ttl=record.ttl,
        priority=record.priority
    )
    
    if not success:
        raise HTTPException(500, message)
    
    return {"success": True, "message": message}


@router.patch("/records/{record_id}")
async def update_record(
    record_id: str,
    data: RecordUpdate,
    user_id=Depends(get_current_user_id)
):
    """Update an existing DNS record."""
    success, message = await dns_manager.update_dns_record(
        record_id=record_id,
        content=data.content,
        ttl=data.ttl
    )
    
    if not success:
        raise HTTPException(500, message)
    
    return {"success": True, "message": message}


@router.delete("/records/{record_id}")
async def delete_record(record_id: str, user_id=Depends(get_current_user_id)):
    """Delete a DNS record."""
    success, message = await dns_manager.delete_dns_record(record_id)
    
    if not success:
        raise HTTPException(500, message)
    
    return {"success": True, "message": message}


@router.get("/certificate")
async def get_certificate(user_id=Depends(get_current_user_id)):
    """Get SSL certificate information."""
    cert_info = dns_manager.get_certificate_info()
    
    if not cert_info:
        return {"installed": False}
    
    return {
        "installed": True,
        "domain": cert_info.domain,
        "issuer": cert_info.issuer,
        "valid_from": cert_info.valid_from.isoformat(),
        "valid_to": cert_info.valid_to.isoformat(),
        "days_remaining": cert_info.days_remaining,
        "is_wildcard": cert_info.is_wildcard,
        "status": "valid" if cert_info.days_remaining > 7 else "expiring" if cert_info.days_remaining > 0 else "expired"
    }


@router.get("/subdomains")
async def list_subdomains(user_id=Depends(get_current_user_id)):
    """List student subdomains configured in nginx."""
    subdomains = dns_manager.get_student_subdomains()
    return {"subdomains": subdomains, "count": len(subdomains)}
