"""
Update manager service — check for and apply OS/package updates.
"""

import subprocess
import re
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional


@dataclass
class PackageUpdate:
    name: str
    current_version: str
    new_version: str
    source: str  # "apt", "pip"
    is_security: bool = False


@dataclass
class UpdateSummary:
    timestamp: str
    total: int
    security: int
    packages: List[PackageUpdate] = field(default_factory=list)
    last_check: Optional[str] = None
    last_update: Optional[str] = None
    reboot_required: bool = False


@dataclass
class UpdateResult:
    success: bool
    message: str
    updated_count: int = 0
    errors: List[str] = field(default_factory=list)
    timestamp: str = ""


def _run(cmd: List[str], timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
    )


def check_reboot_required() -> bool:
    import os
    return os.path.exists("/var/run/reboot-required")


def get_last_update_time() -> Optional[str]:
    import os
    stamp = "/var/lib/apt/periodic/update-success-stamp"
    if os.path.exists(stamp):
        mtime = os.path.getmtime(stamp)
        return datetime.fromtimestamp(mtime).isoformat()
    return None


def refresh_package_list() -> tuple[bool, str]:
    try:
        result = _run(["sudo", "apt-get", "update", "-qq"], timeout=180)
        if result.returncode == 0:
            return True, "Package list updated"
        return False, result.stderr.strip() or "apt-get update failed"
    except subprocess.TimeoutExpired:
        return False, "Timed out refreshing package list"
    except Exception as e:
        return False, str(e)


def check_updates() -> UpdateSummary:
    packages: List[PackageUpdate] = []

    # Get list of upgradable apt packages
    try:
        result = _run(["apt", "list", "--upgradable"], timeout=60)
        if result.returncode == 0:
            for line in result.stdout.strip().splitlines():
                if "/" not in line or "Listing..." in line:
                    continue
                # Format: package/source version [upgradable from: old_version]
                match = re.match(
                    r"^(\S+)/(\S+)\s+(\S+)\s+\S+\s+\[upgradable from:\s+(\S+)\]",
                    line,
                )
                if match:
                    name, source, new_ver, old_ver = match.groups()
                    is_security = "security" in source.lower()
                    packages.append(PackageUpdate(
                        name=name,
                        current_version=old_ver,
                        new_version=new_ver,
                        source="apt",
                        is_security=is_security,
                    ))
    except (subprocess.TimeoutExpired, Exception):
        pass

    security_count = sum(1 for p in packages if p.is_security)

    return UpdateSummary(
        timestamp=datetime.utcnow().isoformat(),
        total=len(packages),
        security=security_count,
        packages=packages,
        last_check=datetime.utcnow().isoformat(),
        last_update=get_last_update_time(),
        reboot_required=check_reboot_required(),
    )


def apply_updates(package_names: Optional[List[str]] = None, security_only: bool = False) -> UpdateResult:
    timestamp = datetime.utcnow().isoformat()
    errors: List[str] = []

    try:
        # Refresh first
        _run(["sudo", "apt-get", "update", "-qq"], timeout=180)

        if package_names:
            # Update specific packages
            cmd = ["sudo", "apt-get", "install", "-y", "--only-upgrade"] + package_names
        elif security_only:
            cmd = ["sudo", "apt-get", "upgrade", "-y", "-o", "Dir::Etc::SourceList=/etc/apt/sources.list.d/security.list"]
        else:
            cmd = ["sudo", "apt-get", "upgrade", "-y"]

        result = _run(cmd, timeout=600)

        if result.returncode == 0:
            # Count updated packages from output
            count = 0
            for line in result.stdout.splitlines():
                if "newly installed" in line or "upgraded" in line:
                    match = re.search(r"(\d+)\s+upgraded", line)
                    if match:
                        count = int(match.group(1))
                    break

            return UpdateResult(
                success=True,
                message=f"Successfully updated {count} package(s)",
                updated_count=count,
                timestamp=timestamp,
            )
        else:
            return UpdateResult(
                success=False,
                message="Update failed",
                errors=[result.stderr.strip()],
                timestamp=timestamp,
            )
    except subprocess.TimeoutExpired:
        return UpdateResult(
            success=False,
            message="Update timed out (10 min limit)",
            errors=["Process timed out"],
            timestamp=timestamp,
        )
    except Exception as e:
        return UpdateResult(
            success=False,
            message=f"Update error: {e}",
            errors=[str(e)],
            timestamp=timestamp,
        )


def get_service_versions() -> dict:
    versions = {}
    checks = {
        "nginx": ["nginx", "-v"],
        "mysql": ["mysql", "--version"],
        "python": ["python3", "--version"],
        "php": ["php", "--version"],
        "node": ["node", "--version"],
        "openssl": ["openssl", "version"],
    }
    for name, cmd in checks.items():
        try:
            result = _run(cmd, timeout=10)
            output = (result.stdout or result.stderr).strip().splitlines()
            versions[name] = output[0] if output else "unknown"
        except Exception:
            versions[name] = "not installed"
    return versions
