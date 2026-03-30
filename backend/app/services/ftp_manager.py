"""
FTP account management service - create/manage FTP-only user accounts.
Uses vsftpd or proftpd configuration.
"""

import crypt
import grp
import os
import pwd
import re
import secrets
import string
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional, Tuple


# FTP configuration
FTP_GROUP = "ftpusers"
FTP_SHELL = "/usr/sbin/nologin"
HOME_BASE = Path("/home")
VSFTPD_USERLIST = Path("/etc/vsftpd/user_list")
VSFTPD_CHROOT_LIST = Path("/etc/vsftpd/chroot_list")

# FTP user naming: parentuser_ftpname
MAX_FTP_NAME_LENGTH = 32


@dataclass
class FTPAccount:
    username: str
    parent_user: str
    home_directory: str
    enabled: bool
    uid: int
    gid: int
    quota_mb: Optional[int] = None
    last_login: Optional[str] = None
    created: Optional[str] = None


@dataclass
class FTPSession:
    username: str
    ip_address: str
    connected_since: str
    idle_time: str
    current_dir: str


def _generate_password(length: int = 16) -> str:
    """Generate a secure random password."""
    chars = string.ascii_letters + string.digits + "!@#$%^&*"
    return ''.join(secrets.choice(chars) for _ in range(length))


def _validate_ftp_name(name: str, parent_user: str) -> str:
    """
    Validate and normalize FTP account name.
    Ensures the name follows the parentuser_ftpname convention.
    """
    # Clean the input
    clean = re.sub(r'[^a-zA-Z0-9_]', '', name)
    
    if not clean:
        raise ValueError("FTP account name cannot be empty")
    
    if len(clean) > MAX_FTP_NAME_LENGTH:
        raise ValueError(f"FTP account name too long (max {MAX_FTP_NAME_LENGTH})")
    
    # Enforce naming convention
    prefix = f"{parent_user}_"
    if not clean.lower().startswith(prefix.lower()):
        clean = f"{prefix}{clean}"
    
    clean = clean.lower()
    
    if len(clean) > MAX_FTP_NAME_LENGTH:
        raise ValueError(f"Full FTP account name too long (max {MAX_FTP_NAME_LENGTH})")
    
    return clean


def _run_command(cmd: List[str], sudo: bool = True) -> Tuple[bool, str]:
    """Run a system command."""
    if sudo:
        cmd = ["sudo"] + cmd
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30
        )
        if result.returncode == 0:
            return True, result.stdout.strip()
        else:
            return False, result.stderr.strip()
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


def _get_ftp_home(parent_user: str, ftp_name: str = "") -> Path:
    """Get the FTP home directory for a user."""
    # FTP users get access to /home/{parent_user}/public_html
    return HOME_BASE / parent_user / "public_html"


def _user_exists(username: str) -> bool:
    """Check if a system user exists."""
    try:
        pwd.getpwnam(username)
        return True
    except KeyError:
        return False


def _ensure_ftp_group() -> int:
    """Ensure FTP group exists and return its GID."""
    try:
        return grp.getgrnam(FTP_GROUP).gr_gid
    except KeyError:
        # Create the group
        success, output = _run_command(["groupadd", FTP_GROUP])
        if not success:
            raise ValueError(f"Failed to create FTP group: {output}")
        return grp.getgrnam(FTP_GROUP).gr_gid


def list_ftp_accounts(parent_user: str) -> List[FTPAccount]:
    """
    List all FTP accounts for a parent user.
    
    Args:
        parent_user: System username of the parent account
        
    Returns:
        List of FTPAccount objects
    """
    prefix = f"{parent_user}_"
    accounts = []
    
    # Read all users and filter by prefix
    try:
        for user in pwd.getpwall():
            if user.pw_name.startswith(prefix) or user.pw_name == parent_user:
                # Check if this is an FTP user (nologin shell or in ftpusers group)
                is_ftp = user.pw_shell in ["/usr/sbin/nologin", "/sbin/nologin", "/bin/false"]
                
                # Include if it's an FTP user or the parent user (who also has FTP access)
                if is_ftp or user.pw_name == parent_user:
                    # Check if user is enabled (not locked)
                    enabled = True
                    try:
                        with open('/etc/shadow', 'r') as f:
                            for line in f:
                                if line.startswith(f"{user.pw_name}:"):
                                    # Locked accounts have ! or * as first char of password hash
                                    parts = line.split(':')
                                    if len(parts) > 1 and parts[1].startswith(('!', '*')):
                                        enabled = False
                                    break
                    except PermissionError:
                        # Can't read shadow, assume enabled
                        pass
                    
                    accounts.append(FTPAccount(
                        username=user.pw_name,
                        parent_user=parent_user if user.pw_name != parent_user else parent_user,
                        home_directory=user.pw_dir,
                        enabled=enabled,
                        uid=user.pw_uid,
                        gid=user.pw_gid,
                    ))
    except Exception as e:
        raise ValueError(f"Failed to list FTP accounts: {e}")
    
    return accounts


def get_ftp_account(username: str) -> FTPAccount:
    """
    Get details of a specific FTP account.
    
    Args:
        username: FTP username
        
    Returns:
        FTPAccount object
    """
    try:
        user = pwd.getpwnam(username)
    except KeyError:
        raise ValueError(f"FTP account not found: {username}")
    
    # Determine parent user
    if "_" in username:
        parent_user = username.split("_")[0]
    else:
        parent_user = username
    
    # Check if enabled
    enabled = True
    try:
        with open('/etc/shadow', 'r') as f:
            for line in f:
                if line.startswith(f"{username}:"):
                    parts = line.split(':')
                    if len(parts) > 1 and parts[1].startswith(('!', '*')):
                        enabled = False
                    break
    except PermissionError:
        pass
    
    return FTPAccount(
        username=user.pw_name,
        parent_user=parent_user,
        home_directory=user.pw_dir,
        enabled=enabled,
        uid=user.pw_uid,
        gid=user.pw_gid,
    )


def create_ftp_account(
    parent_user: str,
    ftp_name: str,
    password: Optional[str] = None,
    directory: Optional[str] = None
) -> Tuple[FTPAccount, str]:
    """
    Create a new FTP-only account.
    
    Args:
        parent_user: System username of the parent account
        ftp_name: Name for the FTP account
        password: Optional password (generated if not provided)
        directory: Optional home directory (defaults to parent's home)
        
    Returns:
        Tuple of (FTPAccount, password)
    """
    # Validate parent user exists
    if not _user_exists(parent_user):
        raise ValueError(f"Parent user does not exist: {parent_user}")
    
    # Validate and normalize FTP name
    full_name = _validate_ftp_name(ftp_name, parent_user)
    
    # Check if account already exists
    if _user_exists(full_name):
        raise ValueError(f"FTP account already exists: {full_name}")
    
    # Generate password if not provided
    if not password:
        password = _generate_password()
    
    # Ensure FTP group exists
    gid = _ensure_ftp_group()
    
    # Determine home directory
    if directory:
        home_dir = Path(directory)
    else:
        home_dir = _get_ftp_home(parent_user, full_name)
    
    # Get parent user's GID for group membership
    try:
        parent_info = pwd.getpwnam(parent_user)
        parent_gid = parent_info.pw_gid
    except KeyError:
        parent_gid = gid
    
    # Create the user
    cmd = [
        "useradd",
        "-M",  # No home directory creation (we'll set permissions on existing)
        "-d", str(home_dir),
        "-s", FTP_SHELL,
        "-g", str(parent_gid),  # Primary group from parent
        "-G", FTP_GROUP,  # Additional FTP group
        full_name
    ]
    
    success, output = _run_command(cmd)
    if not success:
        raise ValueError(f"Failed to create FTP account: {output}")
    
    # Set password
    success, output = _run_command(["chpasswd"], sudo=False)
    # Use a different approach - echo password | chpasswd
    try:
        proc = subprocess.Popen(
            ["sudo", "chpasswd"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(f"{full_name}:{password}\n", timeout=10)
        if proc.returncode != 0:
            # Clean up
            _run_command(["userdel", full_name])
            raise ValueError(f"Failed to set password: {stderr}")
    except Exception as e:
        _run_command(["userdel", full_name])
        raise ValueError(f"Failed to set password: {e}")
    
    # Add to vsftpd user list if it exists
    if VSFTPD_USERLIST.exists():
        try:
            with open(VSFTPD_USERLIST, 'a') as f:
                f.write(f"{full_name}\n")
        except PermissionError:
            _run_command(["sh", "-c", f"echo '{full_name}' >> {VSFTPD_USERLIST}"])
    
    # Get the created account info
    account = get_ftp_account(full_name)
    
    return account, password


def delete_ftp_account(parent_user: str, ftp_name: str) -> bool:
    """
    Delete an FTP account.
    
    Args:
        parent_user: System username of the parent account
        ftp_name: FTP account name
        
    Returns:
        True if successful
    """
    # Validate name belongs to parent
    prefix = f"{parent_user}_"
    if not ftp_name.startswith(prefix):
        raise ValueError(f"FTP account {ftp_name} does not belong to {parent_user}")
    
    # Check account exists
    if not _user_exists(ftp_name):
        raise ValueError(f"FTP account not found: {ftp_name}")
    
    # Delete the user (without removing home since it's shared)
    success, output = _run_command(["userdel", ftp_name])
    if not success:
        raise ValueError(f"Failed to delete FTP account: {output}")
    
    # Remove from vsftpd user list if it exists
    if VSFTPD_USERLIST.exists():
        try:
            with open(VSFTPD_USERLIST, 'r') as f:
                lines = f.readlines()
            with open(VSFTPD_USERLIST, 'w') as f:
                for line in lines:
                    if line.strip() != ftp_name:
                        f.write(line)
        except PermissionError:
            # Try with sudo
            _run_command(["sed", "-i", f"/^{ftp_name}$/d", str(VSFTPD_USERLIST)])
    
    return True


def set_ftp_password(parent_user: str, ftp_name: str, password: str) -> bool:
    """
    Set/reset password for an FTP account.
    
    Args:
        parent_user: System username of the parent account
        ftp_name: FTP account name
        password: New password
        
    Returns:
        True if successful
    """
    # Validate ownership
    prefix = f"{parent_user}_"
    if ftp_name != parent_user and not ftp_name.startswith(prefix):
        raise ValueError(f"FTP account {ftp_name} does not belong to {parent_user}")
    
    # Check account exists
    if not _user_exists(ftp_name):
        raise ValueError(f"FTP account not found: {ftp_name}")
    
    # Set password using chpasswd
    try:
        proc = subprocess.Popen(
            ["sudo", "chpasswd"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        stdout, stderr = proc.communicate(f"{ftp_name}:{password}\n", timeout=10)
        if proc.returncode != 0:
            raise ValueError(f"Failed to set password: {stderr}")
    except Exception as e:
        raise ValueError(f"Failed to set password: {e}")
    
    return True


def enable_ftp_account(parent_user: str, ftp_name: str) -> bool:
    """
    Enable a disabled FTP account.
    
    Args:
        parent_user: System username of the parent account
        ftp_name: FTP account name
        
    Returns:
        True if successful
    """
    # Validate ownership
    prefix = f"{parent_user}_"
    if ftp_name != parent_user and not ftp_name.startswith(prefix):
        raise ValueError(f"FTP account {ftp_name} does not belong to {parent_user}")
    
    # Unlock the account
    success, output = _run_command(["usermod", "-U", ftp_name])
    if not success:
        raise ValueError(f"Failed to enable account: {output}")
    
    return True


def disable_ftp_account(parent_user: str, ftp_name: str) -> bool:
    """
    Disable an FTP account (lock it).
    
    Args:
        parent_user: System username of the parent account
        ftp_name: FTP account name
        
    Returns:
        True if successful
    """
    # Validate ownership
    prefix = f"{parent_user}_"
    if ftp_name != parent_user and not ftp_name.startswith(prefix):
        raise ValueError(f"FTP account {ftp_name} does not belong to {parent_user}")
    
    # Lock the account
    success, output = _run_command(["usermod", "-L", ftp_name])
    if not success:
        raise ValueError(f"Failed to disable account: {output}")
    
    return True


def set_ftp_directory(parent_user: str, ftp_name: str, directory: str) -> bool:
    """
    Set the home directory for an FTP account.
    
    Args:
        parent_user: System username of the parent account
        ftp_name: FTP account name
        directory: New home directory path
        
    Returns:
        True if successful
    """
    # Validate ownership
    prefix = f"{parent_user}_"
    if ftp_name != parent_user and not ftp_name.startswith(prefix):
        raise ValueError(f"FTP account {ftp_name} does not belong to {parent_user}")
    
    # Validate directory is within parent's home
    parent_home = _get_ftp_home(parent_user)
    new_dir = Path(directory).resolve()
    
    try:
        new_dir.relative_to(parent_home.resolve())
    except ValueError:
        raise ValueError(f"Directory must be within {parent_home}")
    
    # Update home directory
    success, output = _run_command(["usermod", "-d", str(new_dir), ftp_name])
    if not success:
        raise ValueError(f"Failed to set directory: {output}")
    
    return True


def get_active_ftp_sessions() -> List[FTPSession]:
    """
    Get list of active FTP sessions.
    
    Returns:
        List of FTPSession objects
    """
    sessions = []
    
    # Try to get sessions from pure-ftpwho, ftpwho, or /var/run
    for cmd in [["pure-ftpwho", "-n"], ["ftpwho"]]:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0 and result.stdout.strip():
                # Parse output (format varies by FTP server)
                for line in result.stdout.strip().split('\n')[1:]:  # Skip header
                    parts = line.split()
                    if len(parts) >= 4:
                        sessions.append(FTPSession(
                            username=parts[0],
                            ip_address=parts[1] if len(parts) > 1 else "unknown",
                            connected_since=parts[2] if len(parts) > 2 else "unknown",
                            idle_time=parts[3] if len(parts) > 3 else "0",
                            current_dir=parts[4] if len(parts) > 4 else "/"
                        ))
                break
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    
    return sessions


def kick_ftp_session(username: str) -> bool:
    """
    Disconnect an active FTP session.
    
    Args:
        username: Username to disconnect
        
    Returns:
        True if successful
    """
    # Try pure-ftpwho -k or similar
    for cmd in [["pure-ftpwho", "-k", username], ["ftpkick", username]]:
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return True
        except (subprocess.TimeoutExpired, FileNotFoundError):
            continue
    
    # Fallback: kill user's FTP processes
    success, _ = _run_command(["pkill", "-u", username, "-f", "ftp"])
    return success
