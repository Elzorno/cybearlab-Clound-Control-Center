"""
CSV Roster Processor

Parses a CSV with columns: FirstName, LastName, StudentID
Generates usernames (lastnamefirstinitial) and passwords (6-digit StudentID)
"""

import csv
import io
import re
import subprocess
from dataclasses import dataclass, field
from typing import List, Optional

from ..config import settings


@dataclass
class RosterEntry:
    first_name: str
    last_name: str
    student_id: str
    username: str
    password: str
    status: str = "pending"
    message: str = ""


@dataclass
class RosterPreview:
    entries: List[RosterEntry] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    valid_count: int = 0
    skip_count: int = 0


@dataclass
class ImportResult:
    username: str
    status: str  # "created", "failed", "skipped"
    message: str


@dataclass
class RosterImportResult:
    results: List[ImportResult] = field(default_factory=list)
    created_count: int = 0
    failed_count: int = 0
    skipped_count: int = 0


def _sanitize_name(name: str) -> str:
    """Remove non-alpha characters and lowercase."""
    return re.sub(r"[^a-z]", "", name.lower().strip())


def _generate_username(first: str, last: str, existing: set) -> str:
    """
    Generate username as lastnamefirstinitial.
    Handle duplicates by appending numbers.
    """
    last_clean = _sanitize_name(last)
    first_clean = _sanitize_name(first)
    
    if not last_clean or not first_clean:
        raise ValueError(f"Invalid name: '{first}' '{last}'")
    
    # Base username: lastname + first initial
    base = f"{last_clean}{first_clean[0]}"
    
    # Ensure it starts with a letter and max 15 chars (leave room for number)
    base = base[:15]
    
    if base not in existing:
        return base
    
    # Handle duplicates: smithj -> smithj2, smithj3, etc.
    for i in range(2, 100):
        candidate = f"{base}{i}"[:16]
        if candidate not in existing:
            return candidate
    
    raise ValueError(f"Cannot generate unique username for {first} {last}")


def _generate_password(student_id: str) -> str:
    """
    Generate password from StudentID.
    Zero-pad to 6 digits if less than 6.
    """
    # Extract digits only
    digits = re.sub(r"\D", "", str(student_id).strip())
    
    if not digits:
        raise ValueError(f"Invalid StudentID: '{student_id}' (no digits)")
    
    # Take last 6 digits if more than 6, or zero-pad if less
    if len(digits) > 6:
        return digits[-6:]
    else:
        return digits.zfill(6)


def parse_roster_csv(csv_content: str) -> RosterPreview:
    """
    Parse CSV content and generate preview of accounts to create.
    
    Expected columns: FirstName, LastName, StudentID
    """
    preview = RosterPreview()
    existing_usernames: set = set()
    
    try:
        # Parse CSV
        reader = csv.DictReader(io.StringIO(csv_content))
        
        # Normalize headers (case-insensitive)
        if reader.fieldnames is None:
            preview.errors.append("CSV file is empty or has no headers")
            return preview
        
        # Create header mapping (lowercase -> original)
        header_map = {h.lower().strip(): h for h in reader.fieldnames}
        
        # Find required columns (case-insensitive)
        first_col = None
        last_col = None
        id_col = None
        
        for h_lower, h_orig in header_map.items():
            if "first" in h_lower and "name" in h_lower:
                first_col = h_orig
            elif h_lower in ("firstname", "first"):
                first_col = h_orig
            elif "last" in h_lower and "name" in h_lower:
                last_col = h_orig
            elif h_lower in ("lastname", "last"):
                last_col = h_orig
            elif "student" in h_lower and "id" in h_lower:
                id_col = h_orig
            elif h_lower in ("studentid", "id", "student_id"):
                id_col = h_orig
        
        missing = []
        if not first_col:
            missing.append("FirstName")
        if not last_col:
            missing.append("LastName")
        if not id_col:
            missing.append("StudentID")
        
        if missing:
            preview.errors.append(f"Missing required columns: {', '.join(missing)}. Found: {', '.join(reader.fieldnames)}")
            return preview
        
        # Process rows
        for row_num, row in enumerate(reader, start=2):
            first = (row.get(first_col) or "").strip()
            last = (row.get(last_col) or "").strip()
            student_id = (row.get(id_col) or "").strip()
            
            # Skip empty rows
            if not first and not last and not student_id:
                continue
            
            # Validate row
            if not first or not last:
                preview.entries.append(RosterEntry(
                    first_name=first,
                    last_name=last,
                    student_id=student_id,
                    username="",
                    password="",
                    status="skip",
                    message=f"Row {row_num}: Missing first or last name"
                ))
                preview.skip_count += 1
                continue
            
            if not student_id:
                preview.entries.append(RosterEntry(
                    first_name=first,
                    last_name=last,
                    student_id=student_id,
                    username="",
                    password="",
                    status="skip",
                    message=f"Row {row_num}: Missing StudentID"
                ))
                preview.skip_count += 1
                continue
            
            # Generate username and password
            try:
                username = _generate_username(first, last, existing_usernames)
                existing_usernames.add(username)
            except ValueError as e:
                preview.entries.append(RosterEntry(
                    first_name=first,
                    last_name=last,
                    student_id=student_id,
                    username="",
                    password="",
                    status="skip",
                    message=f"Row {row_num}: {e}"
                ))
                preview.skip_count += 1
                continue
            
            try:
                password = _generate_password(student_id)
            except ValueError as e:
                preview.entries.append(RosterEntry(
                    first_name=first,
                    last_name=last,
                    student_id=student_id,
                    username=username,
                    password="",
                    status="skip",
                    message=f"Row {row_num}: {e}"
                ))
                preview.skip_count += 1
                continue
            
            preview.entries.append(RosterEntry(
                first_name=first,
                last_name=last,
                student_id=student_id,
                username=username,
                password=password,
                status="pending",
                message=""
            ))
            preview.valid_count += 1
    
    except csv.Error as e:
        preview.errors.append(f"CSV parsing error: {e}")
    except Exception as e:
        preview.errors.append(f"Unexpected error: {e}")
    
    return preview


def import_roster(entries: List[RosterEntry], term: Optional[str] = None) -> RosterImportResult:
    """
    Import roster entries by calling iscs1800-add-student for each.
    """
    result = RosterImportResult()
    
    for entry in entries:
        if entry.status == "skip":
            result.results.append(ImportResult(
                username=entry.username or "(none)",
                status="skipped",
                message=entry.message
            ))
            result.skipped_count += 1
            continue
        
        # Build command
        argv = [settings.script_add_student]
        if term:
            argv.extend(["--term", term])
        argv.extend([entry.username, entry.password])
        
        # Execute
        if settings.execution_mode == "mock":
            result.results.append(ImportResult(
                username=entry.username,
                status="created",
                message=f"MOCK: would create {entry.username}"
            ))
            result.created_count += 1
            continue
        
        try:
            proc = subprocess.run(
                ["sudo", "-n"] + argv,
                capture_output=True,
                text=True,
                timeout=settings.command_timeout_seconds,
                check=False,
            )
            
            if proc.returncode == 0:
                result.results.append(ImportResult(
                    username=entry.username,
                    status="created",
                    message=proc.stdout.strip() or "Account created"
                ))
                result.created_count += 1
            else:
                output = (proc.stdout or "") + " " + (proc.stderr or "")
                result.results.append(ImportResult(
                    username=entry.username,
                    status="failed",
                    message=output.strip()[:200]
                ))
                result.failed_count += 1
        
        except subprocess.TimeoutExpired:
            result.results.append(ImportResult(
                username=entry.username,
                status="failed",
                message="Command timed out"
            ))
            result.failed_count += 1
        except Exception as e:
            result.results.append(ImportResult(
                username=entry.username,
                status="failed",
                message=str(e)[:200]
            ))
            result.failed_count += 1
    
    return result
