"""
Security router - SSH keys, Fail2Ban, UFW, ModSecurity endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..deps import get_current_user_id, get_db
from ..services import security_manager
from ..services.audit import write_audit

router = APIRouter(prefix="/security", tags=["Security"])


# ============================================================
# Schemas
# ============================================================

class SSHKeyResponse(BaseModel):
    id: int
    type: str
    key: str
    comment: str
    fingerprint: str


class SSHKeyRequest(BaseModel):
    key: str


class SSHKeyDeleteRequest(BaseModel):
    key_id: int


class Fail2BanStatusResponse(BaseModel):
    running: bool
    jails: List[str]


class BannedIPsResponse(BaseModel):
    jail: str
    ips: List[str]


class IPActionRequest(BaseModel):
    ip: str


class UFWStatusResponse(BaseModel):
    enabled: bool
    default_incoming: str
    default_outgoing: str
    rules: List[dict]


class UFWRuleRequest(BaseModel):
    action: str  # allow, deny, limit
    port: str
    protocol: Optional[str] = "tcp"
    from_ip: Optional[str] = "any"
    direction: Optional[str] = "in"


class ModSecurityStatusResponse(BaseModel):
    enabled: bool
    mode: str
    rules_count: int


class ModSecurityModeRequest(BaseModel):
    mode: str  # On, Off, DetectionOnly


class SuccessResponse(BaseModel):
    success: bool
    message: str


# ============================================================
# SSH Keys Endpoints
# ============================================================

@router.get("/ssh-keys/{username}", response_model=List[SSHKeyResponse])
def list_ssh_keys(
    username: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> List[SSHKeyResponse]:
    """List SSH keys for a user."""
    try:
        keys = security_manager.list_ssh_keys(username)
        return [
            SSHKeyResponse(
                id=k.id,
                type=k.type,
                key=k.key,
                comment=k.comment,
                fingerprint=k.fingerprint,
            )
            for k in keys
        ]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ssh-keys/{username}", response_model=SuccessResponse)
def add_ssh_key(
    username: str,
    request: SSHKeyRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """Add an SSH key for a user."""
    try:
        security_manager.add_ssh_key(username, request.key)
        write_audit(db, actor_user_id=current_user_id, event_type="security.ssh_key.add", entity_type="ssh_key", entity_id=username, status="success")
        return SuccessResponse(success=True, message="SSH key added successfully")
    except ValueError as e:
        write_audit(db, actor_user_id=current_user_id, event_type="security.ssh_key.add", entity_type="ssh_key", entity_id=username, status="error", metadata={"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/ssh-keys/{username}/{key_id}", response_model=SuccessResponse)
def delete_ssh_key(
    username: str,
    key_id: int,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """Remove an SSH key for a user by key ID."""
    try:
        security_manager.delete_ssh_key(username, key_id)
        write_audit(db, actor_user_id=current_user_id, event_type="security.ssh_key.delete", entity_type="ssh_key", entity_id=f"{username}/{key_id}", status="success")
        return SuccessResponse(success=True, message="SSH key removed successfully")
    except ValueError as e:
        write_audit(db, actor_user_id=current_user_id, event_type="security.ssh_key.delete", entity_type="ssh_key", entity_id=f"{username}/{key_id}", status="error", metadata={"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# Fail2Ban Endpoints
# ============================================================

@router.get("/fail2ban/status", response_model=Fail2BanStatusResponse)
def get_fail2ban_status(
    current_user_id: str = Depends(get_current_user_id),
) -> Fail2BanStatusResponse:
    """Get Fail2Ban service status."""
    try:
        jails = security_manager.get_fail2ban_status()
        return Fail2BanStatusResponse(
            running=len(jails) > 0,
            jails=[j.name for j in jails],
        )
    except ValueError:
        return Fail2BanStatusResponse(running=False, jails=[])


@router.get("/fail2ban/banned/{jail}", response_model=BannedIPsResponse)
def get_banned_ips(
    jail: str,
    current_user_id: str = Depends(get_current_user_id),
) -> BannedIPsResponse:
    """Get list of banned IPs for a jail."""
    try:
        bans = security_manager.get_fail2ban_banned_ips(jail)
        return BannedIPsResponse(jail=jail, ips=[b.ip for b in bans])
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/fail2ban/ban/{jail}", response_model=SuccessResponse)
def ban_ip(
    jail: str,
    request: IPActionRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """Ban an IP address."""
    try:
        security_manager.ban_ip(request.ip, jail)
        write_audit(db, actor_user_id=current_user_id, event_type="security.fail2ban.ban", entity_type="fail2ban", entity_id=f"{jail}/{request.ip}", status="success")
        return SuccessResponse(success=True, message=f"IP {request.ip} banned in {jail}")
    except ValueError as e:
        write_audit(db, actor_user_id=current_user_id, event_type="security.fail2ban.ban", entity_type="fail2ban", entity_id=f"{jail}/{request.ip}", status="error", metadata={"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/fail2ban/unban/{jail}", response_model=SuccessResponse)
def unban_ip(
    jail: str,
    request: IPActionRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """Unban an IP address."""
    try:
        security_manager.unban_ip(request.ip, jail)
        write_audit(db, actor_user_id=current_user_id, event_type="security.fail2ban.unban", entity_type="fail2ban", entity_id=f"{jail}/{request.ip}", status="success")
        return SuccessResponse(success=True, message=f"IP {request.ip} unbanned from {jail}")
    except ValueError as e:
        write_audit(db, actor_user_id=current_user_id, event_type="security.fail2ban.unban", entity_type="fail2ban", entity_id=f"{jail}/{request.ip}", status="error", metadata={"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# UFW (Firewall) Endpoints
# ============================================================

@router.get("/ufw/status", response_model=UFWStatusResponse)
def get_ufw_status(
    current_user_id: str = Depends(get_current_user_id),
) -> UFWStatusResponse:
    """Get UFW firewall status."""
    try:
        status = security_manager.get_ufw_status()
        return UFWStatusResponse(
            enabled=status.enabled,
            default_incoming=status.default_incoming,
            default_outgoing=status.default_outgoing,
            rules=[{
                "id": r.id,
                "action": r.action,
                "direction": r.direction,
                "protocol": r.protocol,
                "port": r.port,
                "from_ip": r.from_ip,
                "to_ip": r.to_ip,
            } for r in status.rules],
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ufw/enable", response_model=SuccessResponse)
def enable_ufw(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """Enable UFW firewall."""
    try:
        security_manager.enable_ufw()
        write_audit(db, actor_user_id=current_user_id, event_type="security.ufw.enable", entity_type="ufw", entity_id="ufw", status="success")
        return SuccessResponse(success=True, message="UFW enabled")
    except ValueError as e:
        write_audit(db, actor_user_id=current_user_id, event_type="security.ufw.enable", entity_type="ufw", entity_id="ufw", status="error", metadata={"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ufw/disable", response_model=SuccessResponse)
def disable_ufw(
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """Disable UFW firewall."""
    try:
        security_manager.disable_ufw()
        write_audit(db, actor_user_id=current_user_id, event_type="security.ufw.disable", entity_type="ufw", entity_id="ufw", status="success")
        return SuccessResponse(success=True, message="UFW disabled")
    except ValueError as e:
        write_audit(db, actor_user_id=current_user_id, event_type="security.ufw.disable", entity_type="ufw", entity_id="ufw", status="error", metadata={"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/ufw/rules", response_model=SuccessResponse)
def add_ufw_rule(
    request: UFWRuleRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """Add a UFW firewall rule."""
    try:
        security_manager.add_ufw_rule(
            action=request.action,
            port=request.port,
            protocol=request.protocol or "tcp",
            from_ip=request.from_ip or "any",
            direction=request.direction or "in",
        )
        write_audit(db, actor_user_id=current_user_id, event_type="security.ufw.add_rule", entity_type="ufw", entity_id=f"{request.action}/{request.port}", status="success")
        return SuccessResponse(success=True, message="UFW rule added")
    except ValueError as e:
        write_audit(db, actor_user_id=current_user_id, event_type="security.ufw.add_rule", entity_type="ufw", entity_id=f"{request.action}/{request.port}", status="error", metadata={"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/ufw/rules/{rule_number}", response_model=SuccessResponse)
def delete_ufw_rule(
    rule_number: int,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """Delete a UFW firewall rule by number."""
    try:
        security_manager.delete_ufw_rule(rule_number)
        write_audit(db, actor_user_id=current_user_id, event_type="security.ufw.delete_rule", entity_type="ufw", entity_id=str(rule_number), status="success")
        return SuccessResponse(success=True, message=f"UFW rule {rule_number} deleted")
    except ValueError as e:
        write_audit(db, actor_user_id=current_user_id, event_type="security.ufw.delete_rule", entity_type="ufw", entity_id=str(rule_number), status="error", metadata={"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# ModSecurity Endpoints
# ============================================================

@router.get("/modsecurity/status", response_model=ModSecurityStatusResponse)
def get_modsecurity_status(
    current_user_id: str = Depends(get_current_user_id),
) -> ModSecurityStatusResponse:
    """Get ModSecurity status."""
    try:
        status = security_manager.get_modsecurity_status()
        return ModSecurityStatusResponse(
            enabled=status.enabled,
            mode=status.mode,
            rules_count=status.rules_count,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/modsecurity/mode", response_model=SuccessResponse)
def set_modsecurity_mode(
    request: ModSecurityModeRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """Set ModSecurity mode (On, Off, DetectionOnly)."""
    try:
        security_manager.set_modsecurity_mode(request.mode)
        write_audit(db, actor_user_id=current_user_id, event_type="security.modsecurity.mode", entity_type="modsecurity", entity_id=request.mode, status="success")
        return SuccessResponse(success=True, message=f"ModSecurity mode set to {request.mode}")
    except ValueError as e:
        write_audit(db, actor_user_id=current_user_id, event_type="security.modsecurity.mode", entity_type="modsecurity", entity_id=request.mode, status="error", metadata={"error": str(e)})
        raise HTTPException(status_code=400, detail=str(e))
