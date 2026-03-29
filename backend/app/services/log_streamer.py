"""
Log streaming service - tail and stream log files via WebSocket.
"""

import asyncio
import os
from dataclasses import dataclass
from typing import List, Dict, Optional, AsyncGenerator
from pathlib import Path


@dataclass
class LogFile:
    key: str
    name: str
    path: str
    description: str
    exists: bool
    size_bytes: int = 0


# Available log files
LOG_FILES: Dict[str, tuple] = {
    "syslog": ("/var/log/syslog", "System Log", "Main system log"),
    "auth": ("/var/log/auth.log", "Authentication Log", "SSH and authentication events"),
    "nginx_access": ("/var/log/nginx/access.log", "Nginx Access", "Web server access log"),
    "nginx_error": ("/var/log/nginx/error.log", "Nginx Errors", "Web server error log"),
    "apache_access": ("/var/log/apache2/access.log", "Apache Access", "Apache access log"),
    "apache_error": ("/var/log/apache2/error.log", "Apache Errors", "Apache error log"),
    "mysql": ("/var/log/mysql/error.log", "MySQL Log", "Database error log"),
    "mail": ("/var/log/mail.log", "Mail Log", "Email server log"),
    "fail2ban": ("/var/log/fail2ban.log", "Fail2Ban Log", "Intrusion prevention log"),
    "ufw": ("/var/log/ufw.log", "Firewall Log", "UFW firewall log"),
    "php_fpm": ("/var/log/php8.3-fpm.log", "PHP-FPM Log", "PHP FastCGI process manager"),
    "cron": ("/var/log/cron.log", "Cron Log", "Scheduled task log"),
}


def get_available_logs() -> List[LogFile]:
    """Get list of available log files."""
    logs = []
    
    for key, (path, name, description) in LOG_FILES.items():
        exists = os.path.isfile(path)
        size = 0
        if exists:
            try:
                size = os.path.getsize(path)
            except OSError:
                pass
        
        logs.append(LogFile(
            key=key,
            name=name,
            path=path,
            description=description,
            exists=exists,
            size_bytes=size,
        ))
    
    # Sort by existence (existing first), then by name
    logs.sort(key=lambda l: (not l.exists, l.name))
    return logs


def read_log_tail(log_key: str, lines: int = 100) -> Optional[str]:
    """Read the last N lines of a log file."""
    if log_key not in LOG_FILES:
        return None
    
    path = LOG_FILES[log_key][0]
    
    if not os.path.isfile(path):
        return None
    
    try:
        # Use tail for efficiency
        import subprocess
        result = subprocess.run(
            ["tail", "-n", str(lines), path],
            capture_output=True,
            text=True,
            timeout=5,
        )
        return result.stdout
    except Exception:
        # Fallback to pure Python
        try:
            with open(path, 'r', errors='replace') as f:
                all_lines = f.readlines()
                return ''.join(all_lines[-lines:])
        except Exception:
            return None


def search_log(log_key: str, pattern: str, lines: int = 100) -> Optional[str]:
    """Search a log file for a pattern (grep)."""
    if log_key not in LOG_FILES:
        return None
    
    path = LOG_FILES[log_key][0]
    
    if not os.path.isfile(path):
        return None
    
    try:
        import subprocess
        result = subprocess.run(
            ["grep", "-i", "-m", str(lines), pattern, path],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.stdout
    except Exception:
        return None


async def tail_log_stream(log_key: str) -> AsyncGenerator[str, None]:
    """
    Async generator that yields new lines from a log file (like tail -f).
    """
    if log_key not in LOG_FILES:
        yield f"Error: Unknown log key: {log_key}\n"
        return
    
    path = LOG_FILES[log_key][0]
    
    if not os.path.isfile(path):
        yield f"Error: Log file does not exist: {path}\n"
        return
    
    try:
        # Start tail -f process
        process = await asyncio.create_subprocess_exec(
            "tail", "-f", "-n", "50", path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        
        try:
            while True:
                line = await asyncio.wait_for(
                    process.stdout.readline(),
                    timeout=30.0  # Send keepalive if no data
                )
                if line:
                    yield line.decode('utf-8', errors='replace')
                else:
                    break
        except asyncio.TimeoutError:
            # Send keepalive
            yield ""
        finally:
            process.terminate()
            try:
                await asyncio.wait_for(process.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                process.kill()
                
    except Exception as e:
        yield f"Error: {str(e)}\n"


def format_log_size(size_bytes: int) -> str:
    """Format log file size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"
