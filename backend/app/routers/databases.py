"""
Database router - MySQL database management endpoints.
"""

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File
from fastapi.responses import PlainTextResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from ..deps import get_current_user_id, get_db
from ..services import database_manager
from ..services.audit import write_audit

router = APIRouter(prefix="/databases", tags=["Databases"])


# ============================================================
# Schemas
# ============================================================

class DatabaseInfoResponse(BaseModel):
    name: str
    tables: int
    size_bytes: int
    size_formatted: str
    created: Optional[str] = None


class TableInfoResponse(BaseModel):
    name: str
    engine: str
    rows: int
    size_bytes: int
    size_formatted: str
    created: Optional[str] = None
    updated: Optional[str] = None


class DatabaseDetailResponse(BaseModel):
    name: str
    tables: List[TableInfoResponse]
    total_size_bytes: int
    total_size_formatted: str
    table_count: int
    row_count: int


class DatabaseUserResponse(BaseModel):
    username: str
    host: str
    databases: List[str]
    privileges: List[str]


class CreateDatabaseRequest(BaseModel):
    name: str


class CreateUserRequest(BaseModel):
    password: str


class SetPasswordRequest(BaseModel):
    password: str


class ExecuteSQLRequest(BaseModel):
    sql: str


class SQLResultResponse(BaseModel):
    success: bool
    output: str


class SuccessResponse(BaseModel):
    success: bool
    message: str


# ============================================================
# Endpoints
# ============================================================

@router.get("/{username}", response_model=List[DatabaseInfoResponse])
def list_databases(
    username: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> List[DatabaseInfoResponse]:
    """List all databases for a user."""
    try:
        databases = database_manager.list_databases(username)
        return [
            DatabaseInfoResponse(
                name=d.name,
                tables=d.tables,
                size_bytes=d.size_bytes,
                size_formatted=d.size_formatted,
                created=d.created
            )
            for d in databases
        ]
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{username}/detail/{db_name}", response_model=DatabaseDetailResponse)
def get_database_detail(
    username: str,
    db_name: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> DatabaseDetailResponse:
    """Get detailed information about a database."""
    try:
        detail = database_manager.get_database_detail(username, db_name)
        return DatabaseDetailResponse(
            name=detail.name,
            tables=[
                TableInfoResponse(
                    name=t.name,
                    engine=t.engine,
                    rows=t.rows,
                    size_bytes=t.size_bytes,
                    size_formatted=t.size_formatted,
                    created=t.created,
                    updated=t.updated
                )
                for t in detail.tables
            ],
            total_size_bytes=detail.total_size_bytes,
            total_size_formatted=detail.total_size_formatted,
            table_count=detail.table_count,
            row_count=detail.row_count
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{username}", response_model=DatabaseInfoResponse)
def create_database(
    username: str,
    request: CreateDatabaseRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> DatabaseInfoResponse:
    """Create a new database for a user."""
    try:
        result = database_manager.create_database(username, request.name)
        write_audit(db, current_user_id, "database.create", f"{username}/{result.name}", "success")
        return DatabaseInfoResponse(
            name=result.name,
            tables=result.tables,
            size_bytes=result.size_bytes,
            size_formatted=result.size_formatted,
            created=result.created
        )
    except ValueError as e:
        write_audit(db, current_user_id, "database.create", f"{username}/{request.name}", "error", str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{username}/{db_name}", response_model=SuccessResponse)
def drop_database(
    username: str,
    db_name: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """Drop a database."""
    try:
        database_manager.drop_database(username, db_name)
        write_audit(db, current_user_id, "database.drop", f"{username}/{db_name}", "success")
        return SuccessResponse(success=True, message=f"Database {db_name} dropped successfully")
    except ValueError as e:
        write_audit(db, current_user_id, "database.drop", f"{username}/{db_name}", "error", str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{username}/user/info", response_model=DatabaseUserResponse)
def get_database_user(
    username: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> DatabaseUserResponse:
    """Get MySQL user information for a system user."""
    try:
        user = database_manager.get_database_user(username)
        return DatabaseUserResponse(
            username=user.username,
            host=user.host,
            databases=user.databases,
            privileges=user.privileges
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{username}/user", response_model=SuccessResponse)
def create_database_user(
    username: str,
    request: CreateUserRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """Create a MySQL user for a system user."""
    try:
        database_manager.create_database_user(username, request.password)
        write_audit(db, current_user_id, "database.user.create", username, "success")
        return SuccessResponse(success=True, message=f"MySQL user {username} created successfully")
    except ValueError as e:
        write_audit(db, current_user_id, "database.user.create", username, "error", str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.put("/{username}/user/password", response_model=SuccessResponse)
def set_database_password(
    username: str,
    request: SetPasswordRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """Set/reset MySQL password for a user."""
    try:
        database_manager.set_database_password(username, request.password)
        write_audit(db, current_user_id, "database.user.password", username, "success")
        return SuccessResponse(success=True, message="Password updated successfully")
    except ValueError as e:
        write_audit(db, current_user_id, "database.user.password", username, "error", str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.delete("/{username}/user", response_model=SuccessResponse)
def delete_database_user(
    username: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """Delete a MySQL user and all their databases."""
    try:
        database_manager.delete_database_user(username)
        write_audit(db, current_user_id, "database.user.delete", username, "success")
        return SuccessResponse(success=True, message=f"MySQL user {username} and databases deleted")
    except ValueError as e:
        write_audit(db, current_user_id, "database.user.delete", username, "error", str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{username}/{db_name}/sql", response_model=SQLResultResponse)
def execute_sql(
    username: str,
    db_name: str,
    request: ExecuteSQLRequest,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SQLResultResponse:
    """Execute SQL on a database (limited to safe statements)."""
    try:
        success, output = database_manager.execute_sql(username, db_name, request.sql)
        write_audit(db, current_user_id, "database.sql", f"{username}/{db_name}", "success" if success else "error")
        return SQLResultResponse(success=success, output=output)
    except ValueError as e:
        write_audit(db, current_user_id, "database.sql", f"{username}/{db_name}", "error", str(e))
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{username}/{db_name}/export", response_class=PlainTextResponse)
def export_database(
    username: str,
    db_name: str,
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
):
    """Export database as SQL dump."""
    try:
        success, output = database_manager.export_database(username, db_name)
        if success:
            write_audit(db, current_user_id, "database.export", f"{username}/{db_name}", "success")
            return PlainTextResponse(
                content=output,
                headers={
                    "Content-Disposition": f"attachment; filename={db_name}.sql"
                }
            )
        else:
            write_audit(db, current_user_id, "database.export", f"{username}/{db_name}", "error", output)
            raise HTTPException(status_code=500, detail=output)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{username}/{db_name}/import", response_model=SuccessResponse)
def import_database(
    username: str,
    db_name: str,
    file: UploadFile = File(...),
    current_user_id: str = Depends(get_current_user_id),
    db: Session = Depends(get_db),
) -> SuccessResponse:
    """Import SQL file into a database."""
    try:
        # Read the uploaded file
        content = file.file.read().decode('utf-8')
        
        database_manager.import_database(username, db_name, content)
        write_audit(db, current_user_id, "database.import", f"{username}/{db_name}", "success")
        return SuccessResponse(success=True, message="Database imported successfully")
    except ValueError as e:
        write_audit(db, current_user_id, "database.import", f"{username}/{db_name}", "error", str(e))
        raise HTTPException(status_code=400, detail=str(e))
    except UnicodeDecodeError:
        raise HTTPException(status_code=400, detail="File must be a valid UTF-8 encoded SQL file")
