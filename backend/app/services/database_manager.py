"""
Database management service - MySQL database operations for student hosting.
"""

import re
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Tuple


# MySQL configuration - adjust if using socket or different credentials
MYSQL_CMD = ["mysql"]
MYSQLADMIN_CMD = ["mysqladmin"]

# Database naming convention: username_dbname
# User naming convention: username (same as system username)
MAX_DB_NAME_LENGTH = 64
MAX_USER_NAME_LENGTH = 32


@dataclass
class DatabaseInfo:
    name: str
    tables: int
    size_bytes: int
    size_formatted: str
    created: Optional[str] = None


@dataclass
class DatabaseUser:
    username: str
    host: str
    databases: List[str]
    privileges: List[str]


@dataclass
class TableInfo:
    name: str
    engine: str
    rows: int
    size_bytes: int
    size_formatted: str
    created: Optional[str] = None
    updated: Optional[str] = None


@dataclass
class DatabaseDetail:
    name: str
    tables: List[TableInfo]
    total_size_bytes: int
    total_size_formatted: str
    table_count: int
    row_count: int


def _format_bytes(b: int) -> str:
    """Format bytes to human readable."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


def _run_mysql(sql: str, database: str = "") -> Tuple[bool, str]:
    """
    Execute MySQL command and return success/failure with output.
    """
    cmd = MYSQL_CMD.copy()
    if database:
        cmd.extend(["-D", database])
    cmd.extend(["-N", "-B", "-e", sql])
    
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
        return False, "Query timed out"
    except Exception as e:
        return False, str(e)


def _validate_db_name(name: str, username: str) -> str:
    """
    Validate and normalize database name.
    Ensures the name follows the username_dbname convention.
    """
    # Clean the input
    clean = re.sub(r'[^a-zA-Z0-9_]', '', name)
    
    if not clean:
        raise ValueError("Database name cannot be empty")
    
    if len(clean) > MAX_DB_NAME_LENGTH:
        raise ValueError(f"Database name too long (max {MAX_DB_NAME_LENGTH})")
    
    # Enforce naming convention
    prefix = f"{username}_"
    if not clean.startswith(prefix):
        clean = f"{prefix}{clean}"
    
    if len(clean) > MAX_DB_NAME_LENGTH:
        raise ValueError(f"Full database name too long (max {MAX_DB_NAME_LENGTH})")
    
    return clean


def _validate_username(name: str) -> str:
    """Validate MySQL username."""
    clean = re.sub(r'[^a-zA-Z0-9_]', '', name)
    
    if not clean:
        raise ValueError("Username cannot be empty")
    
    if len(clean) > MAX_USER_NAME_LENGTH:
        raise ValueError(f"Username too long (max {MAX_USER_NAME_LENGTH})")
    
    return clean


def list_databases(username: str) -> List[DatabaseInfo]:
    """
    List all databases owned by a user (prefixed with username_).
    
    Args:
        username: System username
        
    Returns:
        List of DatabaseInfo objects
    """
    prefix = f"{username}_"
    
    # Get list of databases with sizes
    sql = """
    SELECT 
        table_schema AS db_name,
        COUNT(*) AS tables,
        SUM(data_length + index_length) AS size
    FROM information_schema.TABLES
    WHERE table_schema LIKE %s
    GROUP BY table_schema
    ORDER BY table_schema
    """
    
    # For security, we escape the prefix properly
    escaped_prefix = prefix.replace('_', '\\_').replace('%', '\\%')
    sql_formatted = f"""
    SELECT 
        table_schema AS db_name,
        COUNT(*) AS tables,
        COALESCE(SUM(data_length + index_length), 0) AS size
    FROM information_schema.TABLES
    WHERE table_schema LIKE '{escaped_prefix}%'
    GROUP BY table_schema
    ORDER BY table_schema
    """
    
    success, output = _run_mysql(sql_formatted)
    
    databases = []
    if success and output:
        for line in output.split('\n'):
            parts = line.split('\t')
            if len(parts) >= 3:
                name = parts[0]
                tables = int(parts[1]) if parts[1].isdigit() else 0
                size = int(parts[2]) if parts[2].isdigit() else 0
                databases.append(DatabaseInfo(
                    name=name,
                    tables=tables,
                    size_bytes=size,
                    size_formatted=_format_bytes(size)
                ))
    
    # Also check for empty databases (no tables)
    sql_all = f"SHOW DATABASES LIKE '{escaped_prefix}%'"
    success, all_output = _run_mysql(sql_all)
    
    if success and all_output:
        existing_names = {db.name for db in databases}
        for line in all_output.split('\n'):
            name = line.strip()
            if name and name not in existing_names:
                databases.append(DatabaseInfo(
                    name=name,
                    tables=0,
                    size_bytes=0,
                    size_formatted="0 B"
                ))
    
    return sorted(databases, key=lambda x: x.name)


def get_database_detail(username: str, db_name: str) -> DatabaseDetail:
    """
    Get detailed information about a database.
    
    Args:
        username: System username  
        db_name: Database name
        
    Returns:
        DatabaseDetail with table information
    """
    # Verify database belongs to user
    prefix = f"{username}_"
    if not db_name.startswith(prefix):
        raise ValueError(f"Database {db_name} does not belong to user {username}")
    
    # Escape for SQL LIKE
    escaped_name = db_name.replace('_', '\\_').replace('%', '\\%').replace("'", "\\'")
    
    # Get table details
    sql = f"""
    SELECT 
        TABLE_NAME,
        ENGINE,
        TABLE_ROWS,
        DATA_LENGTH + INDEX_LENGTH AS size,
        CREATE_TIME,
        UPDATE_TIME
    FROM information_schema.TABLES
    WHERE TABLE_SCHEMA = '{db_name}'
    ORDER BY TABLE_NAME
    """
    
    success, output = _run_mysql(sql)
    
    tables = []
    total_size = 0
    total_rows = 0
    
    if success and output:
        for line in output.split('\n'):
            parts = line.split('\t')
            if len(parts) >= 4:
                name = parts[0]
                engine = parts[1] if parts[1] != "NULL" else ""
                rows = int(parts[2]) if parts[2].isdigit() else 0
                size = int(parts[3]) if parts[3].isdigit() else 0
                created = parts[4] if len(parts) > 4 and parts[4] != "NULL" else None
                updated = parts[5] if len(parts) > 5 and parts[5] != "NULL" else None
                
                tables.append(TableInfo(
                    name=name,
                    engine=engine,
                    rows=rows,
                    size_bytes=size,
                    size_formatted=_format_bytes(size),
                    created=created,
                    updated=updated
                ))
                total_size += size
                total_rows += rows
    
    return DatabaseDetail(
        name=db_name,
        tables=tables,
        total_size_bytes=total_size,
        total_size_formatted=_format_bytes(total_size),
        table_count=len(tables),
        row_count=total_rows
    )


def create_database(username: str, db_name: str) -> DatabaseInfo:
    """
    Create a new database for a user.
    
    Args:
        username: System username
        db_name: Desired database name (will be prefixed if necessary)
        
    Returns:
        DatabaseInfo for the created database
    """
    # Validate and normalize name
    full_name = _validate_db_name(db_name, username)
    
    # Create the database
    sql = f"CREATE DATABASE IF NOT EXISTS `{full_name}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
    success, output = _run_mysql(sql)
    
    if not success:
        raise ValueError(f"Failed to create database: {output}")
    
    # Grant privileges to the user on this database
    grant_sql = f"GRANT ALL PRIVILEGES ON `{full_name}`.* TO '{username}'@'localhost'"
    success, output = _run_mysql(grant_sql)
    
    if not success:
        # Database was created but grants failed - try to clean up
        _run_mysql(f"DROP DATABASE IF EXISTS `{full_name}`")
        raise ValueError(f"Failed to grant privileges: {output}")
    
    # Flush privileges
    _run_mysql("FLUSH PRIVILEGES")
    
    return DatabaseInfo(
        name=full_name,
        tables=0,
        size_bytes=0,
        size_formatted="0 B",
        created=datetime.now().isoformat()
    )


def drop_database(username: str, db_name: str) -> bool:
    """
    Drop a database.
    
    Args:
        username: System username (to verify ownership)
        db_name: Database name to drop
        
    Returns:
        True if successful
    """
    # Verify database belongs to user
    prefix = f"{username}_"
    if not db_name.startswith(prefix):
        raise ValueError(f"Database {db_name} does not belong to user {username}")
    
    # Drop the database
    sql = f"DROP DATABASE IF EXISTS `{db_name}`"
    success, output = _run_mysql(sql)
    
    if not success:
        raise ValueError(f"Failed to drop database: {output}")
    
    return True


def get_database_user(username: str) -> DatabaseUser:
    """
    Get MySQL user info for a system user.
    
    Args:
        username: System username
        
    Returns:
        DatabaseUser with privileges info
    """
    # Check if MySQL user exists
    sql = f"SELECT User, Host FROM mysql.user WHERE User = '{username}'"
    success, output = _run_mysql(sql)
    
    if not success or not output:
        # User doesn't exist
        return DatabaseUser(
            username=username,
            host="localhost",
            databases=[],
            privileges=[]
        )
    
    parts = output.split('\t')
    host = parts[1] if len(parts) > 1 else "localhost"
    
    # Get databases this user has access to
    prefix = f"{username}_"
    escaped_prefix = prefix.replace('_', '\\_')
    
    sql = f"""
    SELECT DISTINCT TABLE_SCHEMA 
    FROM information_schema.SCHEMA_PRIVILEGES 
    WHERE GRANTEE = \"'{username}'@'{host}'\" 
    AND TABLE_SCHEMA LIKE '{escaped_prefix}%'
    """
    
    success, db_output = _run_mysql(sql)
    databases = []
    if success and db_output:
        databases = [line.strip() for line in db_output.split('\n') if line.strip()]
    
    # Get global privileges
    sql = f"SHOW GRANTS FOR '{username}'@'{host}'"
    success, grants_output = _run_mysql(sql)
    
    privileges = []
    if success and grants_output:
        for line in grants_output.split('\n'):
            if "GRANT" in line:
                privileges.append(line.strip())
    
    return DatabaseUser(
        username=username,
        host=host,
        databases=databases,
        privileges=privileges
    )


def create_database_user(username: str, password: str) -> bool:
    """
    Create a MySQL user for a system user.
    
    Args:
        username: System username
        password: Password for the MySQL user
        
    Returns:
        True if successful
    """
    clean_username = _validate_username(username)
    
    # Create user (or update if exists)
    sql = f"CREATE USER IF NOT EXISTS '{clean_username}'@'localhost' IDENTIFIED BY '{password}'"
    success, output = _run_mysql(sql)
    
    if not success:
        # Try ALTER if CREATE fails
        sql = f"ALTER USER '{clean_username}'@'localhost' IDENTIFIED BY '{password}'"
        success, output = _run_mysql(sql)
        if not success:
            raise ValueError(f"Failed to create/update MySQL user: {output}")
    
    _run_mysql("FLUSH PRIVILEGES")
    
    return True


def set_database_password(username: str, password: str) -> bool:
    """
    Set/reset MySQL password for a user.
    
    Args:
        username: System username
        password: New password
        
    Returns:
        True if successful
    """
    clean_username = _validate_username(username)
    
    sql = f"ALTER USER '{clean_username}'@'localhost' IDENTIFIED BY '{password}'"
    success, output = _run_mysql(sql)
    
    if not success:
        raise ValueError(f"Failed to set password: {output}")
    
    _run_mysql("FLUSH PRIVILEGES")
    
    return True


def delete_database_user(username: str) -> bool:
    """
    Delete a MySQL user and all their databases.
    
    Args:
        username: System username
        
    Returns:
        True if successful
    """
    clean_username = _validate_username(username)
    
    # First drop all databases owned by this user
    databases = list_databases(username)
    for db in databases:
        try:
            drop_database(username, db.name)
        except ValueError:
            pass  # Continue even if one fails
    
    # Drop the user
    sql = f"DROP USER IF EXISTS '{clean_username}'@'localhost'"
    success, output = _run_mysql(sql)
    
    if not success:
        raise ValueError(f"Failed to delete user: {output}")
    
    _run_mysql("FLUSH PRIVILEGES")
    
    return True


def execute_sql(username: str, db_name: str, sql: str) -> Tuple[bool, str]:
    """
    Execute arbitrary SQL on a database (for phpMyAdmin-like functionality).
    Limited to SELECT, INSERT, UPDATE, DELETE, CREATE TABLE, ALTER TABLE, DROP TABLE.
    
    Args:
        username: System username
        db_name: Database name
        sql: SQL to execute
        
    Returns:
        (success, output/error)
    """
    # Verify database belongs to user
    prefix = f"{username}_"
    if not db_name.startswith(prefix):
        raise ValueError(f"Database {db_name} does not belong to user {username}")
    
    # Basic SQL injection prevention (allow only safe statements)
    sql_upper = sql.strip().upper()
    allowed_starts = ('SELECT', 'INSERT', 'UPDATE', 'DELETE', 'CREATE TABLE', 
                      'ALTER TABLE', 'DROP TABLE', 'SHOW', 'DESCRIBE', 'EXPLAIN')
    
    if not any(sql_upper.startswith(s) for s in allowed_starts):
        raise ValueError("Only SELECT, INSERT, UPDATE, DELETE, CREATE/ALTER/DROP TABLE, SHOW, DESCRIBE, EXPLAIN statements allowed")
    
    # Prevent dangerous operations
    forbidden = ['DROP DATABASE', 'CREATE DATABASE', 'GRANT', 'REVOKE', 
                 'CREATE USER', 'DROP USER', 'FLUSH', 'SHUTDOWN']
    if any(f in sql_upper for f in forbidden):
        raise ValueError("Statement contains forbidden operations")
    
    return _run_mysql(sql, database=db_name)


def export_database(username: str, db_name: str) -> Tuple[bool, str]:
    """
    Export a database as SQL dump.
    
    Args:
        username: System username
        db_name: Database name
        
    Returns:
        (success, SQL dump content or error message)
    """
    # Verify database belongs to user
    prefix = f"{username}_"
    if not db_name.startswith(prefix):
        raise ValueError(f"Database {db_name} does not belong to user {username}")
    
    try:
        result = subprocess.run(
            ["mysqldump", db_name],
            capture_output=True,
            text=True,
            timeout=120
        )
        if result.returncode == 0:
            return True, result.stdout
        else:
            return False, result.stderr
    except subprocess.TimeoutExpired:
        return False, "Export timed out"
    except Exception as e:
        return False, str(e)


def import_database(username: str, db_name: str, sql_content: str) -> bool:
    """
    Import SQL content into a database.
    
    Args:
        username: System username
        db_name: Database name
        sql_content: SQL dump content
        
    Returns:
        True if successful
    """
    # Verify database belongs to user
    prefix = f"{username}_"
    if not db_name.startswith(prefix):
        raise ValueError(f"Database {db_name} does not belong to user {username}")
    
    try:
        result = subprocess.run(
            ["mysql", db_name],
            input=sql_content,
            capture_output=True,
            text=True,
            timeout=300
        )
        if result.returncode != 0:
            raise ValueError(f"Import failed: {result.stderr}")
        return True
    except subprocess.TimeoutExpired:
        raise ValueError("Import timed out")
