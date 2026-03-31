"""
Deployment router — systemd service management, nginx config generation.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from ..deps import get_current_user_id
from ..services import deployment_manager
from ..services.deployment_manager import NginxConfig
from ..services.audit import write_audit

router = APIRouter(prefix="/deployment", tags=["Deployment"])


# ============================================================
# Schemas
# ============================================================

class DeploymentStatusResponse(BaseModel):
    service_active: bool
    service_enabled: bool
    service_status: str
    nginx_config_exists: bool
    nginx_config_enabled: bool
    app_dir: str
    python_version: str
    last_deploy: Optional[str] = None


class ServiceActionRequest(BaseModel):
    action: str  # start, stop, restart, enable, disable


class SystemdInstallRequest(BaseModel):
    port: int = 8000


class NginxConfigRequest(BaseModel):
    server_name: str
    proxy_port: int = 8000
    ssl_enabled: bool = True
    ssl_cert_path: str = ""
    ssl_key_path: str = ""
    root_dir: str = "/var/www/iscs1800-admin/public"
    php_enabled: bool = True


class ActionResultResponse(BaseModel):
    success: bool
    message: str


class GeneratedConfigResponse(BaseModel):
    content: str


class ServiceLogsResponse(BaseModel):
    logs: str


# ============================================================
# Endpoints
# ============================================================

@router.get("/status", response_model=DeploymentStatusResponse)
def get_status(
    current_user_id: str = Depends(get_current_user_id),
) -> DeploymentStatusResponse:
    """Get current deployment status."""
    status = deployment_manager.get_deployment_status()
    return DeploymentStatusResponse(
        service_active=status.service_active,
        service_enabled=status.service_enabled,
        service_status=status.service_status,
        nginx_config_exists=status.nginx_config_exists,
        nginx_config_enabled=status.nginx_config_enabled,
        app_dir=status.app_dir,
        python_version=status.python_version,
        last_deploy=status.last_deploy,
    )


@router.post("/systemd/install", response_model=ActionResultResponse)
def install_systemd(
    req: SystemdInstallRequest,
    current_user_id: str = Depends(get_current_user_id),
) -> ActionResultResponse:
    """Install/update the systemd service unit."""
    success, message = deployment_manager.install_systemd_unit(port=req.port)
    write_audit(current_user_id, "deployment.systemd_install", {
        "success": success, "port": req.port,
    })
    return ActionResultResponse(success=success, message=message)


@router.post("/systemd/control", response_model=ActionResultResponse)
def control_service(
    req: ServiceActionRequest,
    current_user_id: str = Depends(get_current_user_id),
) -> ActionResultResponse:
    """Control the API service (start/stop/restart/enable/disable)."""
    if req.action not in ("start", "stop", "restart", "enable", "disable"):
        raise HTTPException(status_code=400, detail=f"Invalid action: {req.action}")

    success, message = deployment_manager.control_api_service(req.action)
    write_audit(current_user_id, "deployment.service_control", {
        "action": req.action, "success": success,
    })
    return ActionResultResponse(success=success, message=message)


@router.post("/systemd/preview", response_model=GeneratedConfigResponse)
def preview_systemd(
    req: SystemdInstallRequest,
    current_user_id: str = Depends(get_current_user_id),
) -> GeneratedConfigResponse:
    """Preview the systemd unit file content."""
    content = deployment_manager.generate_systemd_unit(port=req.port)
    return GeneratedConfigResponse(content=content)


@router.post("/nginx/install", response_model=ActionResultResponse)
def install_nginx(
    req: NginxConfigRequest,
    current_user_id: str = Depends(get_current_user_id),
) -> ActionResultResponse:
    """Install/update the nginx site config."""
    config = NginxConfig(
        server_name=req.server_name,
        proxy_port=req.proxy_port,
        ssl_enabled=req.ssl_enabled,
        ssl_cert_path=req.ssl_cert_path,
        ssl_key_path=req.ssl_key_path,
        root_dir=req.root_dir,
        php_enabled=req.php_enabled,
    )
    success, message = deployment_manager.install_nginx_config(config)
    write_audit(current_user_id, "deployment.nginx_install", {
        "success": success, "server_name": req.server_name,
    })
    if success:
        deployment_manager.reload_nginx()
    return ActionResultResponse(success=success, message=message)


@router.post("/nginx/preview", response_model=GeneratedConfigResponse)
def preview_nginx(
    req: NginxConfigRequest,
    current_user_id: str = Depends(get_current_user_id),
) -> GeneratedConfigResponse:
    """Preview the nginx config content."""
    config = NginxConfig(
        server_name=req.server_name,
        proxy_port=req.proxy_port,
        ssl_enabled=req.ssl_enabled,
        ssl_cert_path=req.ssl_cert_path,
        ssl_key_path=req.ssl_key_path,
        root_dir=req.root_dir,
        php_enabled=req.php_enabled,
    )
    content = deployment_manager.generate_nginx_config(config)
    return GeneratedConfigResponse(content=content)


@router.post("/nginx/reload", response_model=ActionResultResponse)
def reload_nginx(
    current_user_id: str = Depends(get_current_user_id),
) -> ActionResultResponse:
    """Reload nginx configuration."""
    success, message = deployment_manager.reload_nginx()
    write_audit(current_user_id, "deployment.nginx_reload", {"success": success})
    return ActionResultResponse(success=success, message=message)


@router.get("/logs", response_model=ServiceLogsResponse)
def get_service_logs(
    lines: int = Query(default=100, ge=10, le=1000),
    current_user_id: str = Depends(get_current_user_id),
) -> ServiceLogsResponse:
    """Get recent API service logs from journalctl."""
    logs = deployment_manager.get_api_service_logs(lines=lines)
    return ServiceLogsResponse(logs=logs)
