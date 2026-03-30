"""
Cron job management service - list, create, edit, delete cron jobs for users.
"""

import os
import pwd
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional, Tuple


# Common cron expressions for quick selection
COMMON_SCHEDULES = {
    "every_minute": "* * * * *",
    "every_5_minutes": "*/5 * * * *",
    "every_15_minutes": "*/15 * * * *",
    "every_30_minutes": "*/30 * * * *",
    "hourly": "0 * * * *",
    "daily_midnight": "0 0 * * *",
    "daily_noon": "0 12 * * *",
    "weekly_sunday": "0 0 * * 0",
    "weekly_monday": "0 0 * * 1",
    "monthly": "0 0 1 * *",
    "yearly": "0 0 1 1 *",
}


@dataclass
class CronJob:
    id: int  # Line number in crontab
    minute: str
    hour: str
    day: str
    month: str
    weekday: str
    command: str
    schedule: str  # Full cron expression
    enabled: bool
    comment: Optional[str] = None
    next_run: Optional[str] = None


@dataclass
class CronJobRequest:
    minute: str
    hour: str
    day: str
    month: str
    weekday: str
    command: str
    comment: Optional[str] = None


def _validate_cron_field(value: str, field: str, min_val: int, max_val: int) -> bool:
    """Validate a single cron field."""
    if value == "*":
        return True
    
    # Handle */n syntax
    if value.startswith("*/"):
        try:
            step = int(value[2:])
            return 1 <= step <= max_val
        except ValueError:
            return False
    
    # Handle ranges like 1-5
    if "-" in value and not value.startswith("-"):
        parts = value.split("-")
        if len(parts) == 2:
            try:
                start, end = int(parts[0]), int(parts[1])
                return min_val <= start <= max_val and min_val <= end <= max_val and start <= end
            except ValueError:
                return False
    
    # Handle comma-separated values
    if "," in value:
        parts = value.split(",")
        for part in parts:
            if not _validate_cron_field(part.strip(), field, min_val, max_val):
                return False
        return True
    
    # Single value
    try:
        val = int(value)
        return min_val <= val <= max_val
    except ValueError:
        # Handle day names (sun-sat) and month names
        if field == "weekday":
            return value.lower() in ["sun", "mon", "tue", "wed", "thu", "fri", "sat"]
        if field == "month":
            return value.lower() in ["jan", "feb", "mar", "apr", "may", "jun", 
                                     "jul", "aug", "sep", "oct", "nov", "dec"]
        return False


def _validate_cron_expression(minute: str, hour: str, day: str, month: str, weekday: str) -> Tuple[bool, str]:
    """Validate a full cron expression."""
    if not _validate_cron_field(minute, "minute", 0, 59):
        return False, "Invalid minute field (0-59)"
    if not _validate_cron_field(hour, "hour", 0, 23):
        return False, "Invalid hour field (0-23)"
    if not _validate_cron_field(day, "day", 1, 31):
        return False, "Invalid day field (1-31)"
    if not _validate_cron_field(month, "month", 1, 12):
        return False, "Invalid month field (1-12)"
    if not _validate_cron_field(weekday, "weekday", 0, 7):
        return False, "Invalid weekday field (0-7, where 0 and 7 are Sunday)"
    return True, ""


def _parse_cron_line(line: str, line_num: int) -> Optional[CronJob]:
    """Parse a single crontab line into a CronJob object."""
    line = line.strip()
    
    # Skip empty lines and pure comments
    if not line or line.startswith("#"):
        return None
    
    # Check for disabled job (commented out cron expression)
    enabled = True
    if line.startswith("# "):
        # Check if this is a disabled job (has cron pattern after #)
        rest = line[2:].strip()
        if rest and re.match(r'^[\d\*\/\-,]+\s', rest):
            enabled = False
            line = rest
        else:
            return None
    
    # Parse the cron expression
    parts = line.split(None, 5)
    if len(parts) < 6:
        return None
    
    minute, hour, day, month, weekday = parts[:5]
    command = parts[5]
    
    # Extract comment if present (after #)
    comment = None
    if " #" in command:
        cmd_parts = command.rsplit(" #", 1)
        command = cmd_parts[0].strip()
        comment = cmd_parts[1].strip()
    
    schedule = f"{minute} {hour} {day} {month} {weekday}"
    
    return CronJob(
        id=line_num,
        minute=minute,
        hour=hour,
        day=day,
        month=month,
        weekday=weekday,
        command=command,
        schedule=schedule,
        enabled=enabled,
        comment=comment,
    )


def _get_crontab(username: str) -> Tuple[bool, str]:
    """Get the crontab for a user."""
    try:
        result = subprocess.run(
            ["crontab", "-l", "-u", username],
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return True, result.stdout
        # No crontab for user is not an error
        if "no crontab" in result.stderr.lower():
            return True, ""
        return False, result.stderr
    except subprocess.TimeoutExpired:
        return False, "Timeout reading crontab"
    except Exception as e:
        return False, str(e)


def _set_crontab(username: str, content: str) -> Tuple[bool, str]:
    """Set the crontab for a user."""
    try:
        result = subprocess.run(
            ["crontab", "-u", username, "-"],
            input=content,
            capture_output=True,
            text=True,
            timeout=10
        )
        if result.returncode == 0:
            return True, ""
        return False, result.stderr
    except subprocess.TimeoutExpired:
        return False, "Timeout setting crontab"
    except Exception as e:
        return False, str(e)


def list_cron_jobs(username: str) -> List[CronJob]:
    """
    List all cron jobs for a user.
    
    Args:
        username: System username
        
    Returns:
        List of CronJob objects
    """
    success, content = _get_crontab(username)
    if not success:
        raise ValueError(f"Failed to read crontab: {content}")
    
    jobs = []
    for i, line in enumerate(content.split("\n"), 1):
        job = _parse_cron_line(line, i)
        if job:
            jobs.append(job)
    
    return jobs


def get_cron_job(username: str, job_id: int) -> CronJob:
    """
    Get a specific cron job by line number.
    
    Args:
        username: System username
        job_id: Line number of the job
        
    Returns:
        CronJob object
    """
    jobs = list_cron_jobs(username)
    for job in jobs:
        if job.id == job_id:
            return job
    raise ValueError(f"Cron job {job_id} not found")


def create_cron_job(username: str, job: CronJobRequest) -> CronJob:
    """
    Create a new cron job for a user.
    
    Args:
        username: System username
        job: CronJobRequest with schedule and command
        
    Returns:
        Created CronJob object
    """
    # Validate the cron expression
    valid, error = _validate_cron_expression(job.minute, job.hour, job.day, job.month, job.weekday)
    if not valid:
        raise ValueError(error)
    
    # Validate command is not empty
    if not job.command or not job.command.strip():
        raise ValueError("Command cannot be empty")
    
    # Get existing crontab
    success, content = _get_crontab(username)
    if not success:
        raise ValueError(f"Failed to read crontab: {content}")
    
    # Build the new cron line
    schedule = f"{job.minute} {job.hour} {job.day} {job.month} {job.weekday}"
    line = f"{schedule} {job.command}"
    if job.comment:
        line += f" # {job.comment}"
    
    # Append to crontab
    lines = content.split("\n") if content else []
    lines = [l for l in lines if l.strip()]  # Remove empty lines
    lines.append(line)
    new_content = "\n".join(lines) + "\n"
    
    # Set the new crontab
    success, error = _set_crontab(username, new_content)
    if not success:
        raise ValueError(f"Failed to save crontab: {error}")
    
    return CronJob(
        id=len(lines),
        minute=job.minute,
        hour=job.hour,
        day=job.day,
        month=job.month,
        weekday=job.weekday,
        command=job.command,
        schedule=schedule,
        enabled=True,
        comment=job.comment,
    )


def update_cron_job(username: str, job_id: int, job: CronJobRequest) -> CronJob:
    """
    Update an existing cron job.
    
    Args:
        username: System username
        job_id: Line number of the job to update
        job: New CronJobRequest data
        
    Returns:
        Updated CronJob object
    """
    # Validate the cron expression
    valid, error = _validate_cron_expression(job.minute, job.hour, job.day, job.month, job.weekday)
    if not valid:
        raise ValueError(error)
    
    # Get existing crontab
    success, content = _get_crontab(username)
    if not success:
        raise ValueError(f"Failed to read crontab: {content}")
    
    lines = content.split("\n")
    if job_id < 1 or job_id > len(lines):
        raise ValueError(f"Invalid job ID: {job_id}")
    
    # Build the new cron line
    schedule = f"{job.minute} {job.hour} {job.day} {job.month} {job.weekday}"
    new_line = f"{schedule} {job.command}"
    if job.comment:
        new_line += f" # {job.comment}"
    
    # Replace the line
    lines[job_id - 1] = new_line
    new_content = "\n".join(lines)
    if not new_content.endswith("\n"):
        new_content += "\n"
    
    # Set the new crontab
    success, error = _set_crontab(username, new_content)
    if not success:
        raise ValueError(f"Failed to save crontab: {error}")
    
    return CronJob(
        id=job_id,
        minute=job.minute,
        hour=job.hour,
        day=job.day,
        month=job.month,
        weekday=job.weekday,
        command=job.command,
        schedule=schedule,
        enabled=True,
        comment=job.comment,
    )


def delete_cron_job(username: str, job_id: int) -> bool:
    """
    Delete a cron job.
    
    Args:
        username: System username
        job_id: Line number of the job to delete
        
    Returns:
        True if successful
    """
    success, content = _get_crontab(username)
    if not success:
        raise ValueError(f"Failed to read crontab: {content}")
    
    lines = content.split("\n")
    if job_id < 1 or job_id > len(lines):
        raise ValueError(f"Invalid job ID: {job_id}")
    
    # Remove the line
    del lines[job_id - 1]
    new_content = "\n".join(l for l in lines if l.strip())
    if new_content and not new_content.endswith("\n"):
        new_content += "\n"
    
    # Set the new crontab
    success, error = _set_crontab(username, new_content)
    if not success:
        raise ValueError(f"Failed to save crontab: {error}")
    
    return True


def toggle_cron_job(username: str, job_id: int) -> CronJob:
    """
    Enable or disable a cron job.
    
    Args:
        username: System username
        job_id: Line number of the job to toggle
        
    Returns:
        Updated CronJob object
    """
    success, content = _get_crontab(username)
    if not success:
        raise ValueError(f"Failed to read crontab: {content}")
    
    lines = content.split("\n")
    if job_id < 1 or job_id > len(lines):
        raise ValueError(f"Invalid job ID: {job_id}")
    
    line = lines[job_id - 1]
    
    # Toggle the comment
    if line.startswith("# "):
        # Enable it
        new_line = line[2:]
        enabled = True
    else:
        # Disable it
        new_line = "# " + line
        enabled = False
    
    lines[job_id - 1] = new_line
    new_content = "\n".join(lines)
    if not new_content.endswith("\n"):
        new_content += "\n"
    
    success, error = _set_crontab(username, new_content)
    if not success:
        raise ValueError(f"Failed to save crontab: {error}")
    
    # Parse and return the updated job
    job = _parse_cron_line(new_line, job_id)
    if not job:
        raise ValueError("Failed to parse updated job")
    
    return job


def get_common_schedules() -> dict:
    """Return common cron schedule presets."""
    return COMMON_SCHEDULES


def describe_schedule(minute: str, hour: str, day: str, month: str, weekday: str) -> str:
    """
    Generate a human-readable description of a cron schedule.
    
    Args:
        minute, hour, day, month, weekday: Cron expression fields
        
    Returns:
        Human-readable description
    """
    # Simple descriptions for common patterns
    schedule = f"{minute} {hour} {day} {month} {weekday}"
    
    # Check against common schedules
    for name, expr in COMMON_SCHEDULES.items():
        if schedule == expr:
            return name.replace("_", " ").title()
    
    # Build a description
    parts = []
    
    # Time
    if minute == "*" and hour == "*":
        parts.append("Every minute")
    elif minute.startswith("*/"):
        parts.append(f"Every {minute[2:]} minutes")
    elif hour == "*":
        parts.append(f"At minute {minute} of every hour")
    else:
        time_str = f"{hour.zfill(2) if hour != '*' else '??'}:{minute.zfill(2) if minute != '*' else '??'}"
        parts.append(f"At {time_str}")
    
    # Day/Month/Weekday
    if day != "*" and month != "*":
        parts.append(f"on day {day} of month {month}")
    elif day != "*":
        parts.append(f"on day {day}")
    elif weekday != "*":
        days = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"]
        if weekday.isdigit():
            parts.append(f"on {days[int(weekday) % 7]}")
        else:
            parts.append(f"on {weekday}")
    
    return " ".join(parts) if parts else schedule
