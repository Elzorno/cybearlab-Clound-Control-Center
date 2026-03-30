"""
Files router - file manager for browsing and editing user files.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..deps import get_current_user_id, get_db
from ..services import file_manager
from ..services.audit import write_audit

router = APIRouter(prefix="/files", tags=["Files"])


# ============================================================
# Schemas
# ============================================================

class FileInfoResponse(BaseModel):
    name: str
    path: str
    type: str  # "file" or "directory"
    size: int
    size_formatted: str
    modified: str
    modified_timestamp: float
    permissions: str
    owner: str
    group: str
    is_readable: bool
    is_writable: bool
    is_executable: bool
    mime_type: Optional[str] = None
    is_text: bool = False
    is_image: bool = False


class DirectoryListingResponse(BaseModel):
    path: str
    parent: Optional[str]
    items: List[FileInfoResponse]
    total_items: int
    total_size: int
    total_size_formatted: str


class FileContentResponse(BaseModel):
    path: str
    name: str
    content: str
    size: int
    encoding: str
    mime_type: str
    modified: str


class WriteFileRequest(BaseModel):
    content: str


class CreateFileRequest(BaseModel):
    name: str
    content: str = ""


class CreateDirectoryRequest(BaseModel):
    name: str


class RenameRequest(BaseModel):
    new_name: str


class MoveRequest(BaseModel):
    destination: str


class CopyRequest(BaseModel):
    destination: str


class ChmodRequest(BaseModel):
    mode: str  # Octal string like "755"


class ChownRequest(BaseModel):
    owner: Optional[str] = None
    group: Optional[str] = None


class DeleteRequest(BaseModel):
    recursive: bool = False


class SuccessResponse(BaseModel):
    success: bool
    message: str


# ============================================================
# Endpoints
# ============================================================

@router.get("/browse/{username}", response_model=DirectoryListingResponse)
def list_directory(
    username: str,
    path: str = Query("", description="Relative path within user's directory"),
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> DirectoryListingResponse:
    """List contents of a directory within user's home."""
    try:
        result = file_manager.list_directory(username, path)
        return DirectoryListingResponse(
            path=result.path,
            parent=result.parent,
            items=[
                FileInfoResponse(
                    name=item.name,
                    path=item.path,
                    type=item.type,
                    size=item.size,
                    size_formatted=item.size_formatted,
                    modified=item.modified,
                    modified_timestamp=item.modified_timestamp,
                    permissions=item.permissions,
                    owner=item.owner,
                    group=item.group,
                    is_readable=item.is_readable,
                    is_writable=item.is_writable,
                    is_executable=item.is_executable,
                    mime_type=item.mime_type,
                    is_text=item.is_text,
                    is_image=item.is_image,
                )
                for item in result.items
            ],
            total_items=result.total_items,
            total_size=result.total_size,
            total_size_formatted=result.total_size_formatted,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/read/{username}", response_model=FileContentResponse)
def read_file(
    username: str,
    path: str = Query(..., description="Relative path to file"),
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> FileContentResponse:
    """Read contents of a text file."""
    try:
        result = file_manager.read_file(username, path)
        return FileContentResponse(
            path=result.path,
            name=result.name,
            content=result.content,
            size=result.size,
            encoding=result.encoding,
            mime_type=result.mime_type,
            modified=result.modified,
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/write/{username}", response_model=FileInfoResponse)
def write_file(
    username: str,
    request: WriteFileRequest,
    path: str = Query(..., description="Relative path to file"),
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> FileInfoResponse:
    """Write content to a file."""
    try:
        result = file_manager.write_file(username, path, request.content)
        
        # Audit log
        write_audit(
            db=db,
            actor=current_user_id,
            action_type="file_write",
            entity_id=f"{username}:{path}",
            status="success",
        )
        
        return _file_info_to_response(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/create-file/{username}", response_model=FileInfoResponse)
def create_file(
    username: str,
    request: CreateFileRequest,
    path: str = Query("", description="Directory path for the new file"),
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> FileInfoResponse:
    """Create a new file."""
    try:
        # Combine directory path and filename
        target_path = f"{path}/{request.name}".strip("/")
        result = file_manager.create_file(username, target_path, request.content)
        
        write_audit(
            db=db,
            actor=current_user_id,
            action_type="file_create",
            entity_id=f"{username}:{target_path}",
            status="success",
        )
        
        return _file_info_to_response(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/create-directory/{username}", response_model=FileInfoResponse)
def create_directory(
    username: str,
    request: CreateDirectoryRequest,
    path: str = Query("", description="Parent directory path"),
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> FileInfoResponse:
    """Create a new directory."""
    try:
        target_path = f"{path}/{request.name}".strip("/")
        result = file_manager.create_directory(username, target_path)
        
        write_audit(
            db=db,
            actor=current_user_id,
            action_type="directory_create",
            entity_id=f"{username}:{target_path}",
            status="success",
        )
        
        return _file_info_to_response(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/delete/{username}", response_model=SuccessResponse)
def delete_item(
    username: str,
    path: str = Query(..., description="Path to delete"),
    recursive: bool = Query(False, description="Delete directory recursively"),
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """Delete a file or directory."""
    try:
        file_manager.delete_item(username, path, recursive=recursive)
        
        write_audit(
            db=db,
            actor=current_user_id,
            action_type="file_delete",
            entity_id=f"{username}:{path}",
            status="success",
        )
        
        return SuccessResponse(success=True, message=f"Deleted: {path}")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/rename/{username}", response_model=FileInfoResponse)
def rename_item(
    username: str,
    request: RenameRequest,
    path: str = Query(..., description="Path to rename"),
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> FileInfoResponse:
    """Rename a file or directory."""
    try:
        result = file_manager.rename_item(username, path, request.new_name)
        
        write_audit(
            db=db,
            actor=current_user_id,
            action_type="file_rename",
            entity_id=f"{username}:{path} -> {request.new_name}",
            status="success",
        )
        
        return _file_info_to_response(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/move/{username}", response_model=FileInfoResponse)
def move_item(
    username: str,
    request: MoveRequest,
    path: str = Query(..., description="Source path"),
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> FileInfoResponse:
    """Move a file or directory."""
    try:
        result = file_manager.move_item(username, path, request.destination)
        
        write_audit(
            db=db,
            actor=current_user_id,
            action_type="file_move",
            entity_id=f"{username}:{path} -> {request.destination}",
            status="success",
        )
        
        return _file_info_to_response(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/copy/{username}", response_model=FileInfoResponse)
def copy_item(
    username: str,
    request: CopyRequest,
    path: str = Query(..., description="Source path"),
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> FileInfoResponse:
    """Copy a file or directory."""
    try:
        result = file_manager.copy_item(username, path, request.destination)
        
        write_audit(
            db=db,
            actor=current_user_id,
            action_type="file_copy",
            entity_id=f"{username}:{path} -> {request.destination}",
            status="success",
        )
        
        return _file_info_to_response(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/chmod/{username}", response_model=FileInfoResponse)
def chmod_item(
    username: str,
    request: ChmodRequest,
    path: str = Query(..., description="Path to file/directory"),
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> FileInfoResponse:
    """Change file permissions."""
    try:
        result = file_manager.chmod_item(username, path, request.mode)
        
        write_audit(
            db=db,
            actor=current_user_id,
            action_type="file_chmod",
            entity_id=f"{username}:{path} -> {request.mode}",
            status="success",
        )
        
        return _file_info_to_response(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/chown/{username}", response_model=FileInfoResponse)
def chown_item(
    username: str,
    request: ChownRequest,
    path: str = Query(..., description="Path to file/directory"),
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> FileInfoResponse:
    """Change file ownership."""
    try:
        result = file_manager.chown_item(username, path, request.owner, request.group)
        
        write_audit(
            db=db,
            actor=current_user_id,
            action_type="file_chown",
            entity_id=f"{username}:{path} -> {request.owner or ''}:{request.group or ''}",
            status="success",
        )
        
        return _file_info_to_response(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/upload/{username}", response_model=FileInfoResponse)
async def upload_file(
    username: str,
    file: UploadFile = File(...),
    path: str = Query("", description="Target directory path"),
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> FileInfoResponse:
    """Upload a file to user's directory."""
    try:
        content = await file.read()
        result = file_manager.save_uploaded_file(
            username, path, file.filename, content
        )
        
        write_audit(
            db=db,
            actor=current_user_id,
            action_type="file_upload",
            entity_id=f"{username}:{path}/{file.filename}",
            status="success",
        )
        
        return _file_info_to_response(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/download/{username}")
def download_file(
    username: str,
    path: str = Query(..., description="Path to file"),
    current_user_id: str = Depends(get_current_user_id),
):
    """Download a file."""
    try:
        file_path = file_manager.get_file_path(username, path)
        return FileResponse(
            path=file_path,
            filename=file_path.name,
            media_type="application/octet-stream",
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/info/{username}", response_model=FileInfoResponse)
def get_file_info(
    username: str,
    path: str = Query(..., description="Path to file/directory"),
    current_user_id: str = Depends(get_current_user_id),
) -> FileInfoResponse:
    """Get information about a file or directory."""
    try:
        full_path, user_root = file_manager._resolve_user_path(username, path)
        
        if not full_path.exists():
            raise ValueError(f"Path not found: {path}")
        
        result = file_manager._get_file_info(full_path, user_root)
        return _file_info_to_response(result)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================
# Helper Functions
# ============================================================

def _file_info_to_response(info: file_manager.FileInfo) -> FileInfoResponse:
    """Convert FileInfo dataclass to response model."""
    return FileInfoResponse(
        name=info.name,
        path=info.path,
        type=info.type,
        size=info.size,
        size_formatted=info.size_formatted,
        modified=info.modified,
        modified_timestamp=info.modified_timestamp,
        permissions=info.permissions,
        owner=info.owner,
        group=info.group,
        is_readable=info.is_readable,
        is_writable=info.is_writable,
        is_executable=info.is_executable,
        mime_type=info.mime_type,
        is_text=info.is_text,
        is_image=info.is_image,
    )
