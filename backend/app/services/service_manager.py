"""
Service status management - check and control system services.
"""

import subprocess
from dataclasses import dataclass
from typing import List, Optional
from enum import Enum


class ServiceStatus(str, Enum):
    RUNNING = "running"
    STOPPED = "stopped"
    FAILED = "failed"
    UNKNOWN = "unknown"


@dataclass
class ServiceInfo:
    name: str
    display_name: str
    status: ServiceStatus
    enabled: bool
    description: str
    pid: Optional[int] = None
    memory_mb: Optional[float] = None
    uptime: Optional[str] = None


# Services to monitor - maps internal name to systemd service name
MONITORED_SERVICES = {
    "nginx": ("nginx", "Web Server (Nginx)"),
    "apache": ("apache2", "Web Server (Apache)"),
    "mysql": ("mysql", "Database (MySQL)"),
    "mariadb": ("mariadb", "Database (MariaDB)"),
    "postgresql": ("postgresql", "Database (PostgreSQL)"),
    "postfix": ("postfix", "Mail Server (SMTP)"),
    "dovecot": ("dovecot", "Mail Server (IMAP/POP3)"),
    "ssh": ("sshd", "SSH Server"),
    "vsftpd": ("vsftpd", "FTP Server"),
    "proftpd": ("proftpd", "FTP Server (ProFTPD)"),
    "redis": ("redis-server", "Redis Cache"),
    "fail2ban": ("fail2ban", "Fail2Ban (Intrusion Prevention)"),
    "ufw": ("ufw", "Firewall (UFW)"),
    "cron": ("cron", "Task Scheduler"),
    "rsyslog": ("rsyslog", "System Logging"),
    "php-fpm": ("php8.3-fpm", "PHP-FPM"),
}


def _run_systemctl(cmd: List[str], check: bool = False) -> subprocess.CompletedProcess:
    """Run a systemctl command."""
    try:
        return subprocess.run(
            ["systemctl"] + cmd,
            capture_output=True,
            text=True,
            timeout=10,
            check=check,
        )
    except subprocess.TimeoutExpired:
        return subprocess.CompletedProcess(cmd, returncode=-1, stdout="", stderr="timeout")
    except subprocess.CalledProcessError as e:
        return subprocess.CompletedProcess(cmd, returncode=e.returncode, stdout=e.stdout, stderr=e.stderr)


def _get_service_status(service_name: str) -> ServiceStatus:
    """Get the status of a systemd service."""
    result = _run_systemctl(["is-active", service_name])
    status_str = result.stdout.strip()
    
    if status_str == "active":
        return ServiceStatus.RUNNING
    elif status_str == "inactive":
        return ServiceStatus.STOPPED
    elif status_str == "failed":
        return ServiceStatus.FAILED
    else:
        return ServiceStatus.UNKNOWN


def _is_service_enabled(service_name: str) -> bool:
    """Check if a service is enabled at boot."""
    result = _run_systemctl(["is-enabled", service_name])
    return result.stdout.strip() == "enabled"


def _get_service_pid(service_name: str) -> Optional[int]:
    """Get the main PID of a service."""
    result = _run_systemctl(["show", service_name, "--property=MainPID", "--value"])
    try:
        pid = int(result.stdout.strip())
        return pid if pid > 0 else None
    except ValueError:
        return None


def _get_service_memory(service_name: str) -> Optional[float]:
    """Get memory usage of a service in MB."""
    result = _run_systemctl(["show", service_name, "--property=MemoryCurrent", "--value"])
    try:
        memory_bytes = int(result.stdout.strip())
        return round(memory_bytes / (1024 * 1024), 1) if memory_bytes > 0 else None
    except ValueError:
        return None


def _get_service_uptime(service_name: str) -> Optional[str]:
    """Get how long a service has been running."""
    result = _run_systemctl(["show", service_name, "--property=ActiveEnterTimestamp", "--value"])
    timestamp = result.stdout.strip()
    if not timestamp or timestamp == "n/a":
        return None
    
    # Parse and format as relative time
    try:
        from datetime import datetime
        import time
        
        # Parse systemd timestamp format
        dt = datetime.strptime(timestamp.split('.')[0], "%a %Y-%m-%d %H:%M:%S")
        elapsed = int(time.time() - dt.timestamp())
        
        if elapsed < 60:
            return f"{elapsed}s"
        elif elapsed < 3600:
            return f"{elapsed // 60}m"
        elif elapsed < 86400:
            return f"{elapsed // 3600}h {(elapsed % 3600) // 60}m"
        else:
            return f"{elapsed // 86400}d {(elapsed % 86400) // 3600}h"
    except Exception:
        return None


def _service_exists(service_name: str) -> bool:
    """Check if a service unit exists."""
    result = _run_systemctl(["list-unit-files", f"{service_name}.service", "--no-legend"])
    return bool(result.stdout.strip())


def get_service_info(service_key: str) -> Optional[ServiceInfo]:
    """Get detailed info for a specific service."""
    if service_key not in MONITORED_SERVICES:
        return None
    
    service_name, display_name = MONITORED_SERVICES[service_key]
    
    if not _service_exists(service_name):
        return None
    
    status = _get_service_status(service_name)
    
    return ServiceInfo(
        name=service_key,
        display_name=display_name,
        status=status,
        enabled=_is_service_enabled(service_name),
        description=display_name,
        pid=_get_service_pid(service_name) if status == ServiceStatus.RUNNING else None,
        memory_mb=_get_service_memory(service_name) if status == ServiceStatus.RUNNING else None,
        uptime=_get_service_uptime(service_name) if status == ServiceStatus.RUNNING else None,
    )


def get_all_services() -> List[ServiceInfo]:
    """Get info for all monitored services that exist on the system."""
    services = []
    
    for service_key in MONITORED_SERVICES:
        info = get_service_info(service_key)
        if info:
            services.append(info)
    
    # Sort: running first, then by name
    services.sort(key=lambda s: (s.status != ServiceStatus.RUNNING, s.display_name))
    return services


def control_service(service_key: str, action: str) -> tuple[bool, str]:
    """
    Control a service (start, stop, restart, enable, disable).
    Returns (success, message).
    """
    if service_key not in MONITORED_SERVICES:
        return False, f"Unknown service: {service_key}"
    
    if action not in ("start", "stop", "restart", "enable", "disable"):
        return False, f"Invalid action: {action}"
    
    service_name, display_name = MONITORED_SERVICES[service_key]
    
    if not _service_exists(service_name):
        return False, f"Service {display_name} is not installed"
    
    result = _run_systemctl([action, service_name])
    
    if result.returncode == 0:
        return True, f"Successfully executed {action} on {display_name}"
    else:
        error = result.stderr.strip() or result.stdout.strip() or "Unknown error"
        return False, f"Failed to {action} {display_name}: {error}"
