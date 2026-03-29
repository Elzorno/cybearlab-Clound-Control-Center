"""
Backup service - create and manage backups of student directories.
"""

import os
import subprocess
import tarfile
import shutil
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional
from pathlib import Path


# Configuration
STUDENT_BASE_DIR = "/srv/students"
BACKUP_DIR = "/var/backups/cybearlab"
DEFAULT_TERM = "2026SP"


@dataclass
class BackupInfo:
    filename: str
    path: str
    size_bytes: int
    created_at: str
    term: Optional[str]
    student: Optional[str]
    backup_type: str  # "full", "term", "student"


@dataclass
class BackupResult:
    success: bool
    message: str
    filename: Optional[str] = None
    path: Optional[str] = None
    size_bytes: int = 0
    duration_seconds: float = 0.0


def ensure_backup_dir() -> None:
    """Ensure backup directory exists."""
    os.makedirs(BACKUP_DIR, exist_ok=True)


def get_backup_list() -> List[BackupInfo]:
    """Get list of existing backups."""
    ensure_backup_dir()
    backups = []
    
    for filename in os.listdir(BACKUP_DIR):
        if not filename.endswith(('.tar.gz', '.tgz')):
            continue
        
        filepath = os.path.join(BACKUP_DIR, filename)
        stat = os.stat(filepath)
        
        # Parse filename for metadata
        # Format: cybearlab_<type>_<term>_<student>_<timestamp>.tar.gz
        parts = filename.replace('.tar.gz', '').replace('.tgz', '').split('_')
        
        backup_type = "unknown"
        term = None
        student = None
        
        if len(parts) >= 2:
            backup_type = parts[1] if parts[1] in ("full", "term", "student") else "full"
        if len(parts) >= 3 and parts[1] == "term":
            term = parts[2]
        if len(parts) >= 4 and parts[1] == "student":
            term = parts[2]
            student = parts[3]
        
        backups.append(BackupInfo(
            filename=filename,
            path=filepath,
            size_bytes=stat.st_size,
            created_at=datetime.fromtimestamp(stat.st_mtime).isoformat(),
            term=term,
            student=student,
            backup_type=backup_type,
        ))
    
    # Sort by creation time, newest first
    backups.sort(key=lambda b: b.created_at, reverse=True)
    return backups


def create_full_backup() -> BackupResult:
    """Create a full backup of all student directories."""
    ensure_backup_dir()
    
    if not os.path.isdir(STUDENT_BASE_DIR):
        return BackupResult(
            success=False,
            message=f"Student directory not found: {STUDENT_BASE_DIR}"
        )
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"cybearlab_full_{timestamp}.tar.gz"
    filepath = os.path.join(BACKUP_DIR, filename)
    
    start_time = datetime.now()
    
    try:
        # Use tar directly for better performance with large directories
        result = subprocess.run(
            [
                "tar", "-czf", filepath,
                "-C", os.path.dirname(STUDENT_BASE_DIR),
                os.path.basename(STUDENT_BASE_DIR)
            ],
            capture_output=True,
            text=True,
            timeout=3600,  # 1 hour timeout
        )
        
        if result.returncode != 0:
            return BackupResult(
                success=False,
                message=f"Backup failed: {result.stderr}"
            )
        
        duration = (datetime.now() - start_time).total_seconds()
        size = os.path.getsize(filepath)
        
        return BackupResult(
            success=True,
            message=f"Full backup created successfully",
            filename=filename,
            path=filepath,
            size_bytes=size,
            duration_seconds=duration,
        )
        
    except subprocess.TimeoutExpired:
        return BackupResult(
            success=False,
            message="Backup timed out after 1 hour"
        )
    except Exception as e:
        return BackupResult(
            success=False,
            message=f"Backup error: {str(e)}"
        )


def create_term_backup(term: str) -> BackupResult:
    """Create a backup of a specific term's student directories."""
    ensure_backup_dir()
    
    term_dir = os.path.join(STUDENT_BASE_DIR, term)
    
    if not os.path.isdir(term_dir):
        return BackupResult(
            success=False,
            message=f"Term directory not found: {term_dir}"
        )
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"cybearlab_term_{term}_{timestamp}.tar.gz"
    filepath = os.path.join(BACKUP_DIR, filename)
    
    start_time = datetime.now()
    
    try:
        result = subprocess.run(
            [
                "tar", "-czf", filepath,
                "-C", STUDENT_BASE_DIR,
                term
            ],
            capture_output=True,
            text=True,
            timeout=1800,  # 30 minute timeout
        )
        
        if result.returncode != 0:
            return BackupResult(
                success=False,
                message=f"Backup failed: {result.stderr}"
            )
        
        duration = (datetime.now() - start_time).total_seconds()
        size = os.path.getsize(filepath)
        
        return BackupResult(
            success=True,
            message=f"Term backup for {term} created successfully",
            filename=filename,
            path=filepath,
            size_bytes=size,
            duration_seconds=duration,
        )
        
    except subprocess.TimeoutExpired:
        return BackupResult(
            success=False,
            message="Backup timed out after 30 minutes"
        )
    except Exception as e:
        return BackupResult(
            success=False,
            message=f"Backup error: {str(e)}"
        )


def create_student_backup(term: str, username: str) -> BackupResult:
    """Create a backup of a specific student's directory."""
    ensure_backup_dir()
    
    student_dir = os.path.join(STUDENT_BASE_DIR, term, username)
    
    if not os.path.isdir(student_dir):
        return BackupResult(
            success=False,
            message=f"Student directory not found: {student_dir}"
        )
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"cybearlab_student_{term}_{username}_{timestamp}.tar.gz"
    filepath = os.path.join(BACKUP_DIR, filename)
    
    start_time = datetime.now()
    
    try:
        result = subprocess.run(
            [
                "tar", "-czf", filepath,
                "-C", os.path.join(STUDENT_BASE_DIR, term),
                username
            ],
            capture_output=True,
            text=True,
            timeout=300,  # 5 minute timeout
        )
        
        if result.returncode != 0:
            return BackupResult(
                success=False,
                message=f"Backup failed: {result.stderr}"
            )
        
        duration = (datetime.now() - start_time).total_seconds()
        size = os.path.getsize(filepath)
        
        return BackupResult(
            success=True,
            message=f"Student backup for {username} created successfully",
            filename=filename,
            path=filepath,
            size_bytes=size,
            duration_seconds=duration,
        )
        
    except subprocess.TimeoutExpired:
        return BackupResult(
            success=False,
            message="Backup timed out after 5 minutes"
        )
    except Exception as e:
        return BackupResult(
            success=False,
            message=f"Backup error: {str(e)}"
        )


def delete_backup(filename: str) -> tuple[bool, str]:
    """Delete a backup file."""
    filepath = os.path.join(BACKUP_DIR, filename)
    
    # Security: ensure the file is in the backup directory
    if not os.path.abspath(filepath).startswith(os.path.abspath(BACKUP_DIR)):
        return False, "Invalid backup path"
    
    if not os.path.isfile(filepath):
        return False, "Backup file not found"
    
    try:
        os.remove(filepath)
        return True, f"Backup {filename} deleted"
    except Exception as e:
        return False, f"Failed to delete backup: {str(e)}"


def get_backup_download_path(filename: str) -> Optional[str]:
    """Get the full path for downloading a backup (with validation)."""
    filepath = os.path.join(BACKUP_DIR, filename)
    
    # Security: ensure the file is in the backup directory
    if not os.path.abspath(filepath).startswith(os.path.abspath(BACKUP_DIR)):
        return None
    
    if not os.path.isfile(filepath):
        return None
    
    return filepath


def format_backup_size(size_bytes: int) -> str:
    """Format backup size to human-readable string."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def get_available_terms() -> List[str]:
    """Get list of available terms (subdirectories in student base)."""
    if not os.path.isdir(STUDENT_BASE_DIR):
        return []
    
    terms = []
    for name in os.listdir(STUDENT_BASE_DIR):
        path = os.path.join(STUDENT_BASE_DIR, name)
        if os.path.isdir(path) and not name.startswith('.'):
            terms.append(name)
    
    terms.sort(reverse=True)
    return terms


def get_students_in_term(term: str) -> List[str]:
    """Get list of students in a term."""
    term_dir = os.path.join(STUDENT_BASE_DIR, term)
    
    if not os.path.isdir(term_dir):
        return []
    
    students = []
    for name in os.listdir(term_dir):
        path = os.path.join(term_dir, name)
        if os.path.isdir(path) and not name.startswith('.'):
            students.append(name)
    
    students.sort()
    return students
