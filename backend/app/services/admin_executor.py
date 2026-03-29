import os
import shlex
import subprocess
from dataclasses import dataclass

from ..config import settings
from ..schemas import AdminActionRequest, AdminActionType


@dataclass
class ExecutionResult:
    status: str
    exit_code: int | None
    summary: str
    output: str


def _require(value: str | None, field: str) -> str:
    if not value:
        raise ValueError(f"Missing required field: {field}")
    return value


def _build_argv(payload: AdminActionRequest) -> list[str]:
    if payload.action in {AdminActionType.ADD_STUDENT, AdminActionType.RESET_PASSWORD}:
        user = _require(payload.username, "username")
        mode = payload.password_mode or "random"
        if mode == "manual":
            password = _require(payload.password, "password")
        else:
            password = payload.password or "AUTO_GENERATED_PASSWORD"

        script = settings.script_add_student if payload.action == AdminActionType.ADD_STUDENT else settings.script_reset_password
        argv = [script]
        if payload.term:
            argv.extend(["--term", payload.term])
        argv.extend([user, password])
        return argv

    if payload.action == AdminActionType.DISABLE_STUDENT:
        user = _require(payload.username, "username")
        argv = [settings.script_disable_student]
        if payload.term:
            argv.extend(["--term", payload.term])
        argv.append(user)
        return argv

    if payload.action == AdminActionType.BULK_ADD:
        term = _require(payload.term, "term")
        roster = _require(payload.roster_file_ref, "roster_file_ref")
        if not os.path.isfile(roster):
            raise ValueError("roster_file_ref does not exist on server")
        mode = payload.password_mode or "random"
        argv = [settings.script_bulk_add, "--term", term, "--file", roster, "--password-mode", mode]
        if payload.dry_run:
            argv.append("--dry-run")
        return argv

    if payload.action == AdminActionType.FIX_PERMS_ONE:
        user = _require(payload.username, "username")
        return [settings.script_fix_perms, user]

    if payload.action == AdminActionType.FIX_PERMS_ALL:
        return [settings.script_fix_perms, "--all"]

    if payload.action == AdminActionType.HTTPS_STUDENTS_ONE:
        user = _require(payload.username, "username")
        return [settings.script_https_students, user]

    if payload.action == AdminActionType.HTTPS_STUDENTS_ALL:
        return [settings.script_https_students, "--all"]

    if payload.action == AdminActionType.HTTPS_ADMIN:
        email = _require(payload.admin_email, "admin_email")
        return [settings.script_https_admin, "--email", email]

    if payload.action == AdminActionType.HTTPS_WILDCARD:
        email = _require(payload.admin_email, "admin_email")
        propagation = str(payload.propagation_seconds or 180)
        return [settings.script_https_wildcard, "--email", email, "--propagation-seconds", propagation]

    raise ValueError(f"Unsupported action: {payload.action}")


def execute_admin_action(payload: AdminActionRequest) -> ExecutionResult:
    argv = _build_argv(payload)

    if settings.execution_mode == "mock":
        cmd = " ".join(shlex.quote(arg) for arg in argv)
        return ExecutionResult(
            status="success",
            exit_code=0,
            summary="Mock execution completed",
            output=f"MOCK MODE: would run: {cmd}",
        )

    script_path = argv[0]
    if not os.path.exists(script_path):
        return ExecutionResult(
            status="failed",
            exit_code=127,
            summary="Script not found",
            output=f"Missing script: {script_path}",
        )

    try:
        proc = subprocess.run(
            ["sudo", "-n", *argv],
            capture_output=True,
            text=True,
            timeout=settings.command_timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired as exc:
        return ExecutionResult(
            status="timed_out",
            exit_code=None,
            summary="Execution timed out",
            output=(exc.stdout or "") + "\n" + (exc.stderr or ""),
        )

    output = (proc.stdout or "") + ("\n" + proc.stderr if proc.stderr else "")
    status = "success" if proc.returncode == 0 else "failed"
    summary = "Execution completed" if status == "success" else "Execution failed"
    return ExecutionResult(status=status, exit_code=proc.returncode, summary=summary, output=output.strip())
