"""
Deployment manager service — systemd service management, nginx config generation.
"""

import os
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional


SYSTEMD_UNIT_DIR = "/etc/systemd/system"
NGINX_SITES_AVAILABLE = "/etc/nginx/sites-available"
NGINX_SITES_ENABLED = "/etc/nginx/sites-enabled"
APP_DIR = "/var/www/iscs1800-admin"


@dataclass
class DeploymentStatus:
    service_active: bool
    service_enabled: bool
    service_status: str
    nginx_config_exists: bool
    nginx_config_enabled: bool
    app_dir: str
    python_version: str
    last_deploy: Optional[str] = None


@dataclass
class NginxConfig:
    server_name: str
    proxy_port: int = 8000
    ssl_enabled: bool = True
    ssl_cert_path: str = ""
    ssl_key_path: str = ""
    root_dir: str = "/var/www/iscs1800-admin/public"
    php_enabled: bool = True


SYSTEMD_TEMPLATE = """[Unit]
Description=CybearLab.cloud Control Panel API
After=network.target

[Service]
Type=exec
User=root
Group=root
WorkingDirectory={app_dir}/backend
ExecStart={python_path} -m uvicorn app.main:app --host 127.0.0.1 --port {port}
Restart=always
RestartSec=5
Environment=EXECUTION_MODE=live
Environment=PATH=/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin

[Install]
WantedBy=multi-user.target
"""

NGINX_TEMPLATE = """server {{
    listen 80;
    server_name {server_name};
{ssl_redirect}}}

{ssl_block}server {{
{listen_directive}
    server_name {server_name};
{ssl_directives}
    root {root_dir};
    index index.php index.html;

    # Frontend SPA
    location / {{
        try_files $uri $uri/ /index.php?$query_string;
    }}

{php_block}
    # API reverse proxy
    location /api/ {{
        proxy_pass http://127.0.0.1:{proxy_port}/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300s;
        proxy_connect_timeout 60s;
    }}

    # WebSocket support (for log streaming)
    location /api/system/logs/stream {{
        proxy_pass http://127.0.0.1:{proxy_port}/system/logs/stream;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }}

    # Deny access to dotfiles
    location ~ /\\. {{
        deny all;
    }}
}}
"""

PHP_BLOCK = """    # PHP processing
    location ~ \\.php$ {{
        include snippets/fastcgi-php.conf;
        fastcgi_pass unix:/run/php/{php_sock};
        fastcgi_param SCRIPT_FILENAME $document_root$fastcgi_script_name;
        include fastcgi_params;
    }}
"""


def _run(cmd: List[str], timeout: int = 30) -> subprocess.CompletedProcess:
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def _find_python() -> str:
    for candidate in ["python3.12", "python3.11", "python3.10", "python3"]:
        try:
            result = _run(["which", candidate], timeout=5)
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            continue
    return "/usr/bin/python3"


def _find_php_sock() -> str:
    import glob
    socks = glob.glob("/run/php/php*-fpm.sock")
    if socks:
        socks.sort(reverse=True)
        return os.path.basename(socks[0])
    return "php-fpm.sock"


def get_deployment_status() -> DeploymentStatus:
    # Check systemd service
    service_active = False
    service_enabled = False
    service_status = "not installed"
    try:
        result = _run(["systemctl", "is-active", "cybearlab-api"], timeout=10)
        service_active = result.stdout.strip() == "active"
        service_status = result.stdout.strip()
    except Exception:
        pass

    try:
        result = _run(["systemctl", "is-enabled", "cybearlab-api"], timeout=10)
        service_enabled = result.stdout.strip() == "enabled"
    except Exception:
        pass

    # Check nginx config
    nginx_config_exists = os.path.exists(f"{NGINX_SITES_AVAILABLE}/cybearlab-admin")
    nginx_config_enabled = os.path.exists(f"{NGINX_SITES_ENABLED}/cybearlab-admin")

    # Python version
    python_version = "unknown"
    try:
        result = _run(["python3", "--version"], timeout=5)
        python_version = result.stdout.strip()
    except Exception:
        pass

    return DeploymentStatus(
        service_active=service_active,
        service_enabled=service_enabled,
        service_status=service_status,
        nginx_config_exists=nginx_config_exists,
        nginx_config_enabled=nginx_config_enabled,
        app_dir=APP_DIR,
        python_version=python_version,
    )


def generate_systemd_unit(port: int = 8000) -> str:
    python_path = _find_python()
    return SYSTEMD_TEMPLATE.format(
        app_dir=APP_DIR,
        python_path=python_path,
        port=port,
    )


def install_systemd_unit(port: int = 8000) -> tuple[bool, str]:
    unit_content = generate_systemd_unit(port)
    unit_path = f"{SYSTEMD_UNIT_DIR}/cybearlab-api.service"

    try:
        with open(unit_path, "w") as f:
            f.write(unit_content)

        _run(["systemctl", "daemon-reload"], timeout=30)
        _run(["systemctl", "enable", "cybearlab-api"], timeout=30)
        return True, f"Service installed at {unit_path}"
    except Exception as e:
        return False, str(e)


def control_api_service(action: str) -> tuple[bool, str]:
    if action not in ("start", "stop", "restart", "enable", "disable"):
        return False, f"Invalid action: {action}"

    try:
        result = _run(["systemctl", action, "cybearlab-api"], timeout=30)
        if result.returncode == 0:
            return True, f"Service {action} succeeded"
        return False, result.stderr.strip() or f"systemctl {action} failed"
    except subprocess.TimeoutExpired:
        return False, f"Timed out running systemctl {action}"
    except Exception as e:
        return False, str(e)


def generate_nginx_config(config: NginxConfig) -> str:
    php_sock = _find_php_sock()

    if config.ssl_enabled and config.ssl_cert_path:
        ssl_redirect = "    return 301 https://$host$request_uri;\n"
        ssl_block = ""
        listen_directive = "    listen 443 ssl http2;"
        ssl_directives = f"""    ssl_certificate {config.ssl_cert_path};
    ssl_certificate_key {config.ssl_key_path};
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;
"""
    else:
        ssl_redirect = ""
        ssl_block = ""
        listen_directive = "    listen 80;"
        ssl_directives = ""

    php_block = PHP_BLOCK.format(php_sock=php_sock) if config.php_enabled else ""

    return NGINX_TEMPLATE.format(
        server_name=config.server_name,
        proxy_port=config.proxy_port,
        root_dir=config.root_dir,
        ssl_redirect=ssl_redirect,
        ssl_block=ssl_block,
        listen_directive=listen_directive,
        ssl_directives=ssl_directives,
        php_block=php_block,
    )


def install_nginx_config(config: NginxConfig) -> tuple[bool, str]:
    content = generate_nginx_config(config)
    config_path = f"{NGINX_SITES_AVAILABLE}/cybearlab-admin"
    enabled_path = f"{NGINX_SITES_ENABLED}/cybearlab-admin"

    try:
        with open(config_path, "w") as f:
            f.write(content)

        # Test nginx config
        result = _run(["nginx", "-t"], timeout=10)
        if result.returncode != 0:
            os.unlink(config_path)
            return False, f"Nginx config test failed: {result.stderr.strip()}"

        # Enable site
        if not os.path.exists(enabled_path):
            os.symlink(config_path, enabled_path)

        return True, f"Nginx config installed at {config_path}"
    except Exception as e:
        return False, str(e)


def reload_nginx() -> tuple[bool, str]:
    try:
        result = _run(["systemctl", "reload", "nginx"], timeout=15)
        if result.returncode == 0:
            return True, "Nginx reloaded"
        return False, result.stderr.strip() or "Nginx reload failed"
    except Exception as e:
        return False, str(e)


def get_api_service_logs(lines: int = 100) -> str:
    try:
        result = _run(
            ["journalctl", "-u", "cybearlab-api", "-n", str(lines), "--no-pager"],
            timeout=15,
        )
        return result.stdout
    except Exception as e:
        return f"Error reading logs: {e}"
