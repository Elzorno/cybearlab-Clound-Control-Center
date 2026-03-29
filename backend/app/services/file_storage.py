import hashlib
import os
from pathlib import Path
from uuid import uuid4

from fastapi import HTTPException, UploadFile, status
from sqlalchemy.orm import Session

from ..config import settings
from ..models import FileUpload

_ALLOWED_EXTENSIONS = {".xlsx"}


def _safe_filename(name: str) -> str:
    base = os.path.basename(name)
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in base)


def save_roster_upload(db: Session, uploader_id: str, file: UploadFile) -> FileUpload:
    original_name = file.filename or "roster.xlsx"
    ext = Path(original_name).suffix.lower()
    if ext not in _ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Roster must be an .xlsx file")

    safe_name = _safe_filename(original_name)
    target_dir = Path(settings.upload_root_dir) / "rosters"
    target_dir.mkdir(parents=True, exist_ok=True)

    stored_name = f"{uuid4()}_{safe_name}"
    stored_path = target_dir / stored_name

    hasher = hashlib.sha256()
    size_bytes = 0

    with stored_path.open("wb") as out:
        while True:
            chunk = file.file.read(1024 * 1024)
            if not chunk:
                break
            size_bytes += len(chunk)
            if size_bytes > settings.max_roster_upload_bytes:
                out.close()
                try:
                    stored_path.unlink(missing_ok=True)
                except Exception:
                    pass
                raise HTTPException(
                    status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    detail=f"Roster exceeds max upload size ({settings.max_roster_upload_bytes} bytes)",
                )
            hasher.update(chunk)
            out.write(chunk)

    upload = FileUpload(
        uploader_id=uploader_id,
        original_name=original_name,
        content_type=file.content_type,
        stored_path=str(stored_path),
        sha256=hasher.hexdigest(),
        size_bytes=size_bytes,
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)
    return upload
