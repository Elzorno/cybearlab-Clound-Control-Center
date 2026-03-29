"""
User management service - list users, get details, manage quotas.
"""

import grp
import os
import pwd
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from ..config import settings


@dataclass
class UserInfo:
    username: str
    term: str
    uid: int
    gid: int
    home_dir: str
    shell: str
    disk_used_bytes: int
    disk_quota_bytes: Optional[int]
    disk_percent: float
    is_suspended: bool
    public_html_exists: bool
    file_count: int


@dataclass
class UserDetail(UserInfo):
    groups: list[str]
    last_login: Optional[str]
    created_at: Optional[str]
    public_html_files: int
    index_exists: bool


def _format_bytes(b: int) -> str:
    """Format bytes to human readable."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


def _get_dir_size(path: str) -> tuple[int, int]:
    """Get directory size and file count."""
    total_size = 0
    file_count = 0
    try:
        for dirpath, dirnames, filenames in os.walk(path):
            for f in filenames:
                fp = os.path.join(dirpath, f)
                try:
                    total_size += os.path.getsize(fp)
                    file_count += 1
                except (OSError, FileNotFoundError):
                    pass
    except (OSError, PermissionError):
        pass
    return total_size, file_count


def _get_quota(username: str) -> Optional[int]:
    """Get user's disk quota in bytes (if quotas are enabled)."""
    try:
        result = subprocess.run(
            ["quota", "-u", username, "-w"],
            capture_output=True,
            text=True,
            timeout=5
        )
        # Parse quota output - format varies by system
        # Typically: Filesystem blocks quota limit grace files quota limit grace
        for line in result.stdout.split('\n'):
            if '/home' in line or '/dev' in line:
                parts = line.split()
                if len(parts) >= 3:
                    # Block limit (typically in KB)
                    limit = parts[2].replace('*', '')
                    if limit.isdigit():
                        return int(limit) * 1024  # Convert KB to bytes
    except (subprocess.TimeoutExpired, FileNotFoundError, Exception):
        pass
    return None


def _is_user_suspended(username: str, home_dir: str) -> bool:
    """Check if user account is suspended."""
    try:
        # Check if shell is nologin
        user_info = pwd.getpwnam(username)
        if 'nologin' in user_info.pw_shell or 'false' in user_info.pw_shell:
            return True
        
        # Check if home directory has restrictive permissions
        stat = os.stat(home_dir)
        if stat.st_mode & 0o700 == 0:  # No owner permissions
            return True
            
        # Check for .suspended marker file
        if os.path.exists(os.path.join(home_dir, '.suspended')):
            return True
            
    except (KeyError, OSError):
        pass
    return False


def _get_last_login(username: str) -> Optional[str]:
    """Get user's last login time."""
    try:
        result = subprocess.run(
            ["lastlog", "-u", username],
            capture_output=True,
            text=True,
            timeout=5
        )
        lines = result.stdout.strip().split('\n')
        if len(lines) >= 2:
            # Skip header, parse data line
            data = lines[1]
            if "**Never logged in**" in data:
                return None
            # Extract date portion
            parts = data.split()
            if len(parts) >= 4:
                # Format: Username Port From Latest
                return ' '.join(parts[3:])
    except (subprocess.TimeoutExpired, FileNotFoundError):
        pass
    return None


def get_terms() -> list[str]:
    """List available terms (directories in /home)."""
    terms = []
    home_base = Path("/home")
    
    if not home_base.exists():
        return terms
        
    try:
        for entry in home_base.iterdir():
            if entry.is_dir():
                name = entry.name
                # Filter to term-like directories (e.g., 2025-fall, spring2026)
                # Also include standard year patterns
                if any(c.isdigit() for c in name) or name.lower() in ['students', 'users']:
                    terms.append(name)
    except PermissionError:
        pass
        
    return sorted(terms)


def list_users(term: Optional[str] = None) -> list[UserInfo]:
    """List all users, optionally filtered by term."""
    users = []
    home_base = Path("/home")
    
    if not home_base.exists():
        return users
    
    # Determine which term directories to scan
    if term:
        term_dirs = [home_base / term] if (home_base / term).exists() else []
    else:
        term_dirs = [d for d in home_base.iterdir() if d.is_dir()]
    
    for term_dir in term_dirs:
        term_name = term_dir.name
        
        # Skip system directories
        if term_name in ['lost+found']:
            continue
            
        try:
            for user_dir in term_dir.iterdir():
                if not user_dir.is_dir():
                    continue
                    
                username = user_dir.name
                home_path = str(user_dir)
                
                # Get user info from passwd
                try:
                    pw = pwd.getpwnam(username)
                except KeyError:
                    # User doesn't exist in passwd - skip or create minimal entry
                    continue
                
                # Get disk usage
                disk_used, file_count = _get_dir_size(home_path)
                disk_quota = _get_quota(username)
                
                # Calculate percent
                if disk_quota and disk_quota > 0:
                    disk_percent = min(100, (disk_used / disk_quota) * 100)
                else:
                    disk_percent = 0
                
                # Check public_html
                public_html = user_dir / "public_html"
                public_html_exists = public_html.exists() and public_html.is_dir()
                
                users.append(UserInfo(
                    username=username,
                    term=term_name,
                    uid=pw.pw_uid,
                    gid=pw.pw_gid,
                    home_dir=home_path,
                    shell=pw.pw_shell,
                    disk_used_bytes=disk_used,
                    disk_quota_bytes=disk_quota,
                    disk_percent=disk_percent,
                    is_suspended=_is_user_suspended(username, home_path),
                    public_html_exists=public_html_exists,
                    file_count=file_count,
                ))
                
        except PermissionError:
            continue
    
    return sorted(users, key=lambda u: (u.term, u.username))


def get_user_detail(username: str) -> Optional[UserDetail]:
    """Get detailed information about a specific user."""
    try:
        pw = pwd.getpwnam(username)
    except KeyError:
        return None
    
    home_path = pw.pw_dir
    
    # Determine term from home path
    parts = Path(home_path).parts
    term = parts[2] if len(parts) > 2 else "unknown"
    
    # Get disk usage
    disk_used, file_count = _get_dir_size(home_path)
    disk_quota = _get_quota(username)
    
    if disk_quota and disk_quota > 0:
        disk_percent = min(100, (disk_used / disk_quota) * 100)
    else:
        disk_percent = 0
    
    # Get groups
    groups = []
    try:
        gids = os.getgrouplist(username, pw.pw_gid)
        for gid in gids:
            try:
                groups.append(grp.getgrgid(gid).gr_name)
            except KeyError:
                groups.append(str(gid))
    except (KeyError, OSError):
        pass
    
    # Check public_html
    public_html = Path(home_path) / "public_html"
    public_html_exists = public_html.exists() and public_html.is_dir()
    
    # Count files in public_html
    public_html_files = 0
    index_exists = False
    if public_html_exists:
        _, public_html_files = _get_dir_size(str(public_html))
        index_exists = (public_html / "index.html").exists() or (public_html / "index.htm").exists()
    
    return UserDetail(
        username=username,
        term=term,
        uid=pw.pw_uid,
        gid=pw.pw_gid,
        home_dir=home_path,
        shell=pw.pw_shell,
        disk_used_bytes=disk_used,
        disk_quota_bytes=disk_quota,
        disk_percent=disk_percent,
        is_suspended=_is_user_suspended(username, home_path),
        public_html_exists=public_html_exists,
        file_count=file_count,
        groups=groups,
        last_login=_get_last_login(username),
        created_at=None,  # Would need to parse /etc/passwd or similar
        public_html_files=public_html_files,
        index_exists=index_exists,
    )


def suspend_user(username: str) -> tuple[bool, str]:
    """Suspend a user account."""
    if settings.execution_mode == "mock":
        return True, f"[MOCK] User {username} suspended"
    
    try:
        # Change shell to nologin
        subprocess.run(
            ["usermod", "-s", "/usr/sbin/nologin", username],
            check=True,
            capture_output=True,
            timeout=30
        )
        
        # Create marker file
        try:
            pw = pwd.getpwnam(username)
            marker = Path(pw.pw_dir) / ".suspended"
            marker.touch()
        except (KeyError, OSError):
            pass
        
        return True, f"User {username} suspended successfully"
    except subprocess.CalledProcessError as e:
        return False, f"Failed to suspend: {e.stderr.decode() if e.stderr else str(e)}"
    except subprocess.TimeoutExpired:
        return False, "Command timed out"


def unsuspend_user(username: str) -> tuple[bool, str]:
    """Unsuspend a user account."""
    if settings.execution_mode == "mock":
        return True, f"[MOCK] User {username} unsuspended"
    
    try:
        # Restore shell to bash
        subprocess.run(
            ["usermod", "-s", "/bin/bash", username],
            check=True,
            capture_output=True,
            timeout=30
        )
        
        # Remove marker file
        try:
            pw = pwd.getpwnam(username)
            marker = Path(pw.pw_dir) / ".suspended"
            if marker.exists():
                marker.unlink()
        except (KeyError, OSError):
            pass
        
        return True, f"User {username} unsuspended successfully"
    except subprocess.CalledProcessError as e:
        return False, f"Failed to unsuspend: {e.stderr.decode() if e.stderr else str(e)}"
    except subprocess.TimeoutExpired:
        return False, "Command timed out"


def set_quota(username: str, quota_mb: int) -> tuple[bool, str]:
    """Set disk quota for a user (in MB)."""
    if settings.execution_mode == "mock":
        return True, f"[MOCK] Quota set to {quota_mb}MB for {username}"
    
    try:
        # Convert MB to blocks (1 block = 1KB typically)
        blocks = quota_mb * 1024
        soft_limit = blocks
        hard_limit = int(blocks * 1.1)  # 10% grace
        
        subprocess.run(
            ["setquota", "-u", username, str(soft_limit), str(hard_limit), "0", "0", "/home"],
            check=True,
            capture_output=True,
            timeout=30
        )
        
        return True, f"Quota set to {quota_mb}MB for {username}"
    except subprocess.CalledProcessError as e:
        return False, f"Failed to set quota: {e.stderr.decode() if e.stderr else str(e)}"
    except FileNotFoundError:
        return False, "setquota command not found - quotas may not be enabled"
    except subprocess.TimeoutExpired:
        return False, "Command timed out"


def delete_user(username: str, remove_home: bool = False) -> tuple[bool, str]:
    """Delete a user account."""
    if settings.execution_mode == "mock":
        return True, f"[MOCK] User {username} deleted (remove_home={remove_home})"
    
    try:
        cmd = ["userdel"]
        if remove_home:
            cmd.append("-r")
        cmd.append(username)
        
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            timeout=60
        )
        
        return True, f"User {username} deleted successfully"
    except subprocess.CalledProcessError as e:
        return False, f"Failed to delete: {e.stderr.decode() if e.stderr else str(e)}"
    except subprocess.TimeoutExpired:
        return False, "Command timed out"


def format_bytes(b: int) -> str:
    """Public helper for formatting bytes."""
    return _format_bytes(b)
