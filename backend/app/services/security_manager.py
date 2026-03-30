"""
Security management service - SSH keys, fail2ban, UFW firewall, ModSecurity.
"""

import os
import pwd
import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple


@dataclass
class SSHKey:
    id: int  # Line number in authorized_keys
    type: str  # ssh-rsa, ssh-ed25519, etc.
    key: str  # The actual key (truncated for display)
    comment: str  # Usually email or identifier
    fingerprint: str
    added: Optional[str] = None


@dataclass
class Fail2BanJail:
    name: str
    enabled: bool
    filter: str
    action: str
    log_path: str
    max_retry: int
    ban_time: int
    find_time: int
    currently_banned: int = 0
    total_banned: int = 0


@dataclass
class Fail2BanBan:
    ip: str
    jail: str
    banned_at: Optional[str] = None
    ban_time: Optional[int] = None


@dataclass
class UFWRule:
    id: int
    action: str  # ALLOW, DENY, REJECT, LIMIT
    direction: str  # IN, OUT
    protocol: str  # tcp, udp, any
    port: str
    from_ip: str
    to_ip: str
    comment: Optional[str] = None


@dataclass
class UFWStatus:
    enabled: bool
    default_incoming: str
    default_outgoing: str
    rules: List[UFWRule]


@dataclass
class ModSecurityStatus:
    enabled: bool
    mode: str  # DetectionOnly, On
    rules_count: int
    last_blocked: Optional[str] = None


def _run_command(cmd: List[str], sudo: bool = True, timeout: int = 30) -> Tuple[bool, str]:
    """Run a system command."""
    if sudo:
        cmd = ["sudo"] + cmd
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode == 0:
            return True, result.stdout.strip()
        return False, result.stderr.strip() or result.stdout.strip()
    except subprocess.TimeoutExpired:
        return False, "Command timed out"
    except Exception as e:
        return False, str(e)


# ============================================================
# SSH Key Management
# ============================================================

def _get_ssh_dir(username: str) -> Path:
    """Get the .ssh directory for a user."""
    try:
        user_info = pwd.getpwnam(username)
        return Path(user_info.pw_dir) / ".ssh"
    except KeyError:
        raise ValueError(f"User not found: {username}")


def _get_key_fingerprint(key_line: str) -> str:
    """Get the fingerprint of an SSH key."""
    try:
        result = subprocess.run(
            ["ssh-keygen", "-lf", "-"],
            input=key_line,
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0:
            # Format: 2048 SHA256:xxx comment (RSA)
            parts = result.stdout.strip().split()
            if len(parts) >= 2:
                return parts[1]
        return "unknown"
    except Exception:
        return "unknown"


def list_ssh_keys(username: str) -> List[SSHKey]:
    """List all SSH keys for a user."""
    ssh_dir = _get_ssh_dir(username)
    auth_keys = ssh_dir / "authorized_keys"
    
    if not auth_keys.exists():
        return []
    
    keys = []
    try:
        with open(auth_keys, "r") as f:
            for i, line in enumerate(f, 1):
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                
                parts = line.split(None, 2)
                if len(parts) < 2:
                    continue
                
                key_type = parts[0]
                key_data = parts[1]
                comment = parts[2] if len(parts) > 2 else ""
                
                # Truncate key for display
                key_display = key_data[:20] + "..." + key_data[-20:] if len(key_data) > 44 else key_data
                
                fingerprint = _get_key_fingerprint(line)
                
                keys.append(SSHKey(
                    id=i,
                    type=key_type,
                    key=key_display,
                    comment=comment,
                    fingerprint=fingerprint,
                ))
    except PermissionError:
        raise ValueError(f"Cannot read SSH keys for {username}")
    
    return keys


def add_ssh_key(username: str, key: str, comment: Optional[str] = None) -> SSHKey:
    """Add an SSH key for a user."""
    ssh_dir = _get_ssh_dir(username)
    auth_keys = ssh_dir / "authorized_keys"
    
    # Validate key format
    key = key.strip()
    parts = key.split(None, 2)
    if len(parts) < 2:
        raise ValueError("Invalid SSH key format")
    
    key_type = parts[0]
    if key_type not in ["ssh-rsa", "ssh-ed25519", "ssh-ecdsa", "ecdsa-sha2-nistp256", 
                        "ecdsa-sha2-nistp384", "ecdsa-sha2-nistp521"]:
        raise ValueError(f"Unsupported key type: {key_type}")
    
    # Add comment if provided and not in key
    if comment and len(parts) == 2:
        key = f"{key} {comment}"
    
    # Ensure .ssh directory exists
    if not ssh_dir.exists():
        ssh_dir.mkdir(mode=0o700)
        try:
            user_info = pwd.getpwnam(username)
            os.chown(ssh_dir, user_info.pw_uid, user_info.pw_gid)
        except Exception:
            pass
    
    # Read existing keys
    existing = []
    if auth_keys.exists():
        with open(auth_keys, "r") as f:
            existing = f.readlines()
    
    # Check for duplicates
    key_data = parts[1]
    for line in existing:
        if key_data in line:
            raise ValueError("This key already exists")
    
    # Append the new key
    with open(auth_keys, "a") as f:
        f.write(key + "\n")
    
    # Set permissions
    auth_keys.chmod(0o600)
    try:
        user_info = pwd.getpwnam(username)
        os.chown(auth_keys, user_info.pw_uid, user_info.pw_gid)
    except Exception:
        pass
    
    fingerprint = _get_key_fingerprint(key)
    
    return SSHKey(
        id=len(existing) + 1,
        type=parts[0],
        key=parts[1][:20] + "..." + parts[1][-20:] if len(parts[1]) > 44 else parts[1],
        comment=parts[2] if len(parts) > 2 else (comment or ""),
        fingerprint=fingerprint,
    )


def delete_ssh_key(username: str, key_id: int) -> bool:
    """Delete an SSH key by line number."""
    ssh_dir = _get_ssh_dir(username)
    auth_keys = ssh_dir / "authorized_keys"
    
    if not auth_keys.exists():
        raise ValueError("No SSH keys found")
    
    with open(auth_keys, "r") as f:
        lines = f.readlines()
    
    # Filter out comments and empty lines to get actual key index
    key_lines = []
    for i, line in enumerate(lines):
        if line.strip() and not line.strip().startswith("#"):
            key_lines.append(i)
    
    if key_id < 1 or key_id > len(key_lines):
        raise ValueError(f"Invalid key ID: {key_id}")
    
    # Remove the key at the correct index
    actual_index = key_lines[key_id - 1]
    del lines[actual_index]
    
    with open(auth_keys, "w") as f:
        f.writelines(lines)
    
    return True


# ============================================================
# Fail2Ban Management
# ============================================================

def get_fail2ban_status() -> List[Fail2BanJail]:
    """Get status of all fail2ban jails."""
    success, output = _run_command(["fail2ban-client", "status"])
    if not success:
        raise ValueError(f"Failed to get fail2ban status: {output}")
    
    # Parse jail list
    jails = []
    for line in output.split("\n"):
        if "Jail list:" in line:
            jail_names = line.split(":")[1].strip().split(",")
            jail_names = [j.strip() for j in jail_names if j.strip()]
            break
    else:
        return []
    
    # Get details for each jail
    for jail_name in jail_names:
        success, detail = _run_command(["fail2ban-client", "status", jail_name])
        if not success:
            continue
        
        jail = Fail2BanJail(
            name=jail_name,
            enabled=True,
            filter=jail_name,
            action="",
            log_path="",
            max_retry=5,
            ban_time=600,
            find_time=600,
            currently_banned=0,
            total_banned=0,
        )
        
        for line in detail.split("\n"):
            line = line.strip()
            if "Currently banned:" in line:
                try:
                    jail.currently_banned = int(line.split(":")[1].strip())
                except ValueError:
                    pass
            elif "Total banned:" in line:
                try:
                    jail.total_banned = int(line.split(":")[1].strip())
                except ValueError:
                    pass
        
        jails.append(jail)
    
    return jails


def get_fail2ban_banned_ips(jail: Optional[str] = None) -> List[Fail2BanBan]:
    """Get list of currently banned IPs."""
    bans = []
    
    if jail:
        jails = [jail]
    else:
        status = get_fail2ban_status()
        jails = [j.name for j in status]
    
    for jail_name in jails:
        success, output = _run_command(["fail2ban-client", "status", jail_name])
        if not success:
            continue
        
        for line in output.split("\n"):
            if "Banned IP list:" in line:
                ips = line.split(":")[1].strip().split()
                for ip in ips:
                    if ip.strip():
                        bans.append(Fail2BanBan(
                            ip=ip.strip(),
                            jail=jail_name,
                        ))
    
    return bans


def ban_ip(ip: str, jail: str = "sshd") -> bool:
    """Manually ban an IP address."""
    # Validate IP format
    if not re.match(r'^(\d{1,3}\.){3}\d{1,3}$', ip):
        raise ValueError("Invalid IP address format")
    
    success, output = _run_command(["fail2ban-client", "set", jail, "banip", ip])
    if not success:
        raise ValueError(f"Failed to ban IP: {output}")
    return True


def unban_ip(ip: str, jail: str = "sshd") -> bool:
    """Unban an IP address."""
    success, output = _run_command(["fail2ban-client", "set", jail, "unbanip", ip])
    if not success:
        raise ValueError(f"Failed to unban IP: {output}")
    return True


# ============================================================
# UFW Firewall Management
# ============================================================

def get_ufw_status() -> UFWStatus:
    """Get UFW firewall status and rules."""
    success, output = _run_command(["ufw", "status", "verbose"])
    if not success:
        raise ValueError(f"Failed to get UFW status: {output}")
    
    enabled = "Status: active" in output
    default_incoming = "deny"
    default_outgoing = "allow"
    
    for line in output.split("\n"):
        if "Default:" in line:
            if "incoming" in line.lower():
                if "deny" in line.lower():
                    default_incoming = "deny"
                elif "allow" in line.lower():
                    default_incoming = "allow"
            if "outgoing" in line.lower():
                if "deny" in line.lower():
                    default_outgoing = "deny"
                elif "allow" in line.lower():
                    default_outgoing = "allow"
    
    # Get numbered rules
    success, output = _run_command(["ufw", "status", "numbered"])
    rules = []
    
    if success:
        # Parse rules like: [ 1] 22/tcp ALLOW IN Anywhere
        for line in output.split("\n"):
            match = re.match(r'\[\s*(\d+)\]\s+(.+)', line)
            if match:
                rule_num = int(match.group(1))
                rule_text = match.group(2).strip()
                
                # Parse the rule text
                parts = rule_text.split()
                if len(parts) >= 3:
                    port_proto = parts[0]
                    action = parts[1]
                    direction = parts[2] if len(parts) > 2 else "IN"
                    
                    # Parse port/protocol
                    if "/" in port_proto:
                        port, proto = port_proto.split("/")
                    else:
                        port = port_proto
                        proto = "any"
                    
                    rules.append(UFWRule(
                        id=rule_num,
                        action=action,
                        direction=direction,
                        protocol=proto,
                        port=port,
                        from_ip="Anywhere",
                        to_ip="Anywhere",
                    ))
    
    return UFWStatus(
        enabled=enabled,
        default_incoming=default_incoming,
        default_outgoing=default_outgoing,
        rules=rules,
    )


def enable_ufw() -> bool:
    """Enable UFW firewall."""
    success, output = _run_command(["ufw", "--force", "enable"])
    if not success:
        raise ValueError(f"Failed to enable UFW: {output}")
    return True


def disable_ufw() -> bool:
    """Disable UFW firewall."""
    success, output = _run_command(["ufw", "disable"])
    if not success:
        raise ValueError(f"Failed to disable UFW: {output}")
    return True


def add_ufw_rule(
    action: str,
    port: str,
    protocol: str = "tcp",
    from_ip: str = "any",
    direction: str = "in",
    comment: Optional[str] = None
) -> bool:
    """Add a UFW rule."""
    if action.lower() not in ["allow", "deny", "reject", "limit"]:
        raise ValueError(f"Invalid action: {action}")
    
    if protocol.lower() not in ["tcp", "udp", "any"]:
        raise ValueError(f"Invalid protocol: {protocol}")
    
    # Build the command
    cmd = ["ufw"]
    
    if comment:
        cmd.extend(["comment", comment])
    
    cmd.append(action.lower())
    
    if direction.lower() == "out":
        cmd.append("out")
    
    if from_ip != "any":
        cmd.extend(["from", from_ip])
    
    cmd.extend(["to", "any", "port", port])
    
    if protocol.lower() != "any":
        cmd.extend(["proto", protocol.lower()])
    
    success, output = _run_command(cmd)
    if not success:
        raise ValueError(f"Failed to add rule: {output}")
    return True


def delete_ufw_rule(rule_id: int) -> bool:
    """Delete a UFW rule by number."""
    success, output = _run_command(["ufw", "--force", "delete", str(rule_id)])
    if not success:
        raise ValueError(f"Failed to delete rule: {output}")
    return True


# ============================================================
# ModSecurity Management
# ============================================================

def get_modsecurity_status() -> ModSecurityStatus:
    """Get ModSecurity status."""
    enabled = False
    mode = "DetectionOnly"
    rules_count = 0
    
    # Check if ModSecurity is loaded in Apache
    success, output = _run_command(["apachectl", "-M"], sudo=True)
    if success and "security2_module" in output:
        enabled = True
    
    # Try to read ModSecurity config
    config_paths = [
        "/etc/modsecurity/modsecurity.conf",
        "/etc/apache2/mods-enabled/security2.conf",
        "/etc/httpd/conf.d/mod_security.conf",
    ]
    
    for config_path in config_paths:
        if os.path.exists(config_path):
            try:
                with open(config_path, "r") as f:
                    content = f.read()
                    if "SecRuleEngine On" in content:
                        mode = "On"
                    elif "SecRuleEngine DetectionOnly" in content:
                        mode = "DetectionOnly"
                    elif "SecRuleEngine Off" in content:
                        enabled = False
            except PermissionError:
                pass
            break
    
    # Count rules (approximate)
    rules_dir = Path("/etc/modsecurity/rules") if Path("/etc/modsecurity/rules").exists() else Path("/usr/share/modsecurity-crs/rules")
    if rules_dir.exists():
        try:
            for f in rules_dir.glob("*.conf"):
                with open(f, "r") as rf:
                    rules_count += rf.read().count("SecRule")
        except Exception:
            pass
    
    return ModSecurityStatus(
        enabled=enabled,
        mode=mode,
        rules_count=rules_count,
    )


def set_modsecurity_mode(mode: str) -> bool:
    """Set ModSecurity mode (On, Off, DetectionOnly)."""
    if mode not in ["On", "Off", "DetectionOnly"]:
        raise ValueError(f"Invalid mode: {mode}. Use On, Off, or DetectionOnly")
    
    config_path = "/etc/modsecurity/modsecurity.conf"
    if not os.path.exists(config_path):
        raise ValueError("ModSecurity configuration not found")
    
    # Read config
    with open(config_path, "r") as f:
        content = f.read()
    
    # Replace SecRuleEngine directive
    new_content = re.sub(
        r'SecRuleEngine\s+(On|Off|DetectionOnly)',
        f'SecRuleEngine {mode}',
        content
    )
    
    # Write back
    success, output = _run_command(
        ["sh", "-c", f"echo '{new_content}' > {config_path}"]
    )
    if not success:
        raise ValueError(f"Failed to update config: {output}")
    
    # Reload Apache
    success, output = _run_command(["systemctl", "reload", "apache2"])
    if not success:
        # Try httpd
        success, output = _run_command(["systemctl", "reload", "httpd"])
    
    return True
