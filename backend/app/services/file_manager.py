"""
File manager service - browse, view, edit, upload files in user directories.
"""

import grp
import mimetypes
import os
import pwd
import shutil
import stat
import subprocess
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Tuple

# Configurable paths - user home directories
HOME_BASE = Path("/home")
ALLOWED_TEXT_EXTENSIONS = {
    ".html", ".htm", ".css", ".js", ".json", ".xml", ".txt", ".md",
    ".php", ".py", ".sh", ".conf", ".cfg", ".ini", ".yaml", ".yml",
    ".htaccess", ".gitignore", ".env", ".csv", ".log", ".sql"
}
MAX_TEXT_FILE_SIZE = 5 * 1024 * 1024  # 5 MB max for text editing
MAX_UPLOAD_SIZE = 50 * 1024 * 1024  # 50 MB max upload


@dataclass
class FileInfo:
    name: str
    path: str  # Relative path from user root
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


@dataclass
class DirectoryListing:
    path: str
    parent: Optional[str]
    items: List[FileInfo]
    total_items: int
    total_size: int
    total_size_formatted: str


@dataclass
class FileContent:
    path: str
    name: str
    content: str
    size: int
    encoding: str
    mime_type: str
    modified: str


def _format_bytes(b: int) -> str:
    """Format bytes to human readable."""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024
    return f"{b:.1f} PB"


def _format_permissions(mode: int) -> str:
    """Convert numeric mode to rwx string."""
    perms = ""
    for who in range(3):  # owner, group, other
        for perm, char in [(stat.S_IRUSR, 'r'), (stat.S_IWUSR, 'w'), (stat.S_IXUSR, 'x')]:
            shifted = perm >> (who * 3)
            perms += char if mode & shifted else '-'
    return perms


def _get_owner_group(path: Path) -> Tuple[str, str]:
    """Get owner and group names for a path."""
    try:
        st = path.stat()
        owner = pwd.getpwuid(st.st_uid).pw_name
    except (KeyError, OSError):
        owner = str(st.st_uid if 'st' in dir() else "?")
    
    try:
        st = path.stat()
        group = grp.getgrgid(st.st_gid).gr_name
    except (KeyError, OSError):
        group = str(st.st_gid if 'st' in dir() else "?")
    
    return owner, group


def _is_text_file(path: Path) -> bool:
    """Check if file is likely a text file based on extension."""
    suffix = path.suffix.lower()
    if suffix in ALLOWED_TEXT_EXTENSIONS:
        return True
    # Check files without extension by name
    if path.name in {".htaccess", ".gitignore", "Makefile", "Dockerfile"}:
        return True
    return False


def _is_image_file(path: Path) -> bool:
    """Check if file is an image."""
    suffix = path.suffix.lower()
    return suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg", ".ico", ".bmp"}


def _get_mime_type(path: Path) -> Optional[str]:
    """Get MIME type for a file."""
    mime_type, _ = mimetypes.guess_type(str(path))
    return mime_type


def _resolve_user_path(username: str, relative_path: str) -> Tuple[Path, Path]:
    """
    Resolve a relative path within a user's web directory.
    Returns (full_path, user_root) or raises ValueError for invalid paths.
    """
    # User's web directory: /home/{username}/public_html
    user_root = HOME_BASE / username / "public_html"
    
    if not user_root.exists():
        raise ValueError(f"User directory not found: {username}")
    
    # Normalize and resolve path
    if relative_path:
        # Remove leading slashes and normalize
        clean_path = relative_path.lstrip("/")
        full_path = (user_root / clean_path).resolve()
    else:
        full_path = user_root.resolve()
    
    # Security: Ensure path is within user's directory
    try:
        full_path.relative_to(user_root.resolve())
    except ValueError:
        raise ValueError(f"Path escape attempt detected: {relative_path}")
    
    return full_path, user_root


def _get_file_info(path: Path, user_root: Path) -> FileInfo:
    """Get detailed information about a file or directory."""
    try:
        st = path.stat()
    except OSError as e:
        raise ValueError(f"Cannot access file: {e}")
    
    is_dir = path.is_dir()
    relative_path = str(path.relative_to(user_root))
    owner, group = _get_owner_group(path)
    
    return FileInfo(
        name=path.name,
        path=relative_path,
        type="directory" if is_dir else "file",
        size=0 if is_dir else st.st_size,
        size_formatted=_format_bytes(st.st_size) if not is_dir else "-",
        modified=datetime.fromtimestamp(st.st_mtime).isoformat(),
        modified_timestamp=st.st_mtime,
        permissions=_format_permissions(st.st_mode),
        owner=owner,
        group=group,
        is_readable=os.access(path, os.R_OK),
        is_writable=os.access(path, os.W_OK),
        is_executable=os.access(path, os.X_OK),
        mime_type=_get_mime_type(path) if not is_dir else None,
        is_text=_is_text_file(path) if not is_dir else False,
        is_image=_is_image_file(path) if not is_dir else False,
    )


def list_directory(username: str, relative_path: str = "") -> DirectoryListing:
    """
    List contents of a directory within user's home.
    
    Args:
        username: System username
        relative_path: Path relative to user's home directory
        
    Returns:
        DirectoryListing with items
        
    Raises:
        ValueError: For invalid paths or access errors
    """
    full_path, user_root = _resolve_user_path(username, relative_path)
    
    if not full_path.exists():
        raise ValueError(f"Path not found: {relative_path or '/'}")
    
    if not full_path.is_dir():
        raise ValueError(f"Not a directory: {relative_path}")
    
    items: List[FileInfo] = []
    total_size = 0
    
    try:
        for entry in sorted(full_path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
            try:
                info = _get_file_info(entry, user_root)
                items.append(info)
                total_size += info.size
            except (OSError, ValueError):
                # Skip files we can't access
                continue
    except PermissionError:
        raise ValueError(f"Permission denied: {relative_path}")
    
    # Calculate parent path
    current_relative = str(full_path.relative_to(user_root))
    if current_relative == ".":
        parent = None
    else:
        parent_path = Path(current_relative).parent
        parent = str(parent_path) if str(parent_path) != "." else ""
    
    return DirectoryListing(
        path=relative_path or "/",
        parent=parent,
        items=items,
        total_items=len(items),
        total_size=total_size,
        total_size_formatted=_format_bytes(total_size),
    )


def read_file(username: str, relative_path: str) -> FileContent:
    """
    Read contents of a text file.
    
    Args:
        username: System username
        relative_path: Path relative to user's home directory
        
    Returns:
        FileContent with file data
        
    Raises:
        ValueError: For invalid paths, non-text files, or access errors
    """
    full_path, user_root = _resolve_user_path(username, relative_path)
    
    if not full_path.exists():
        raise ValueError(f"File not found: {relative_path}")
    
    if full_path.is_dir():
        raise ValueError(f"Cannot read directory as file: {relative_path}")
    
    # Check file size
    size = full_path.stat().st_size
    if size > MAX_TEXT_FILE_SIZE:
        raise ValueError(f"File too large for editing: {_format_bytes(size)} (max {_format_bytes(MAX_TEXT_FILE_SIZE)})")
    
    # Check if it's a text file
    if not _is_text_file(full_path):
        raise ValueError(f"Not a text file: {relative_path}")
    
    # Read file content
    try:
        # Try UTF-8 first
        content = full_path.read_text(encoding="utf-8")
        encoding = "utf-8"
    except UnicodeDecodeError:
        try:
            # Fall back to latin-1
            content = full_path.read_text(encoding="latin-1")
            encoding = "latin-1"
        except Exception as e:
            raise ValueError(f"Cannot read file: {e}")
    
    return FileContent(
        path=relative_path,
        name=full_path.name,
        content=content,
        size=size,
        encoding=encoding,
        mime_type=_get_mime_type(full_path) or "text/plain",
        modified=datetime.fromtimestamp(full_path.stat().st_mtime).isoformat(),
    )


def write_file(username: str, relative_path: str, content: str) -> FileInfo:
    """
    Write content to a file.
    
    Args:
        username: System username
        relative_path: Path relative to user's home directory
        content: File content to write
        
    Returns:
        Updated FileInfo
        
    Raises:
        ValueError: For invalid paths or access errors
    """
    full_path, user_root = _resolve_user_path(username, relative_path)
    
    if full_path.is_dir():
        raise ValueError(f"Cannot write to directory: {relative_path}")
    
    # Check if it's a text file type
    if not _is_text_file(full_path):
        raise ValueError(f"Not a text file type: {relative_path}")
    
    # Ensure parent directory exists
    if not full_path.parent.exists():
        raise ValueError(f"Parent directory does not exist: {full_path.parent}")
    
    try:
        full_path.write_text(content, encoding="utf-8")
    except PermissionError:
        raise ValueError(f"Permission denied: {relative_path}")
    except OSError as e:
        raise ValueError(f"Cannot write file: {e}")
    
    return _get_file_info(full_path, user_root)


def create_file(username: str, relative_path: str, content: str = "") -> FileInfo:
    """
    Create a new file.
    
    Args:
        username: System username
        relative_path: Path relative to user's home directory
        content: Initial file content (optional)
        
    Returns:
        FileInfo for created file
        
    Raises:
        ValueError: For invalid paths or if file exists
    """
    full_path, user_root = _resolve_user_path(username, relative_path)
    
    if full_path.exists():
        raise ValueError(f"File already exists: {relative_path}")
    
    if not full_path.parent.exists():
        raise ValueError(f"Parent directory does not exist")
    
    try:
        full_path.write_text(content, encoding="utf-8")
    except PermissionError:
        raise ValueError(f"Permission denied: {relative_path}")
    except OSError as e:
        raise ValueError(f"Cannot create file: {e}")
    
    return _get_file_info(full_path, user_root)


def create_directory(username: str, relative_path: str) -> FileInfo:
    """
    Create a new directory.
    
    Args:
        username: System username
        relative_path: Path relative to user's home directory
        
    Returns:
        FileInfo for created directory
        
    Raises:
        ValueError: For invalid paths or if directory exists
    """
    full_path, user_root = _resolve_user_path(username, relative_path)
    
    if full_path.exists():
        raise ValueError(f"Path already exists: {relative_path}")
    
    if not full_path.parent.exists():
        raise ValueError(f"Parent directory does not exist")
    
    try:
        full_path.mkdir(mode=0o755)
    except PermissionError:
        raise ValueError(f"Permission denied")
    except OSError as e:
        raise ValueError(f"Cannot create directory: {e}")
    
    return _get_file_info(full_path, user_root)


def delete_item(username: str, relative_path: str, recursive: bool = False) -> bool:
    """
    Delete a file or directory.
    
    Args:
        username: System username
        relative_path: Path relative to user's home directory  
        recursive: If True, delete directory and contents
        
    Returns:
        True on success
        
    Raises:
        ValueError: For invalid paths or access errors
    """
    full_path, user_root = _resolve_user_path(username, relative_path)
    
    if not full_path.exists():
        raise ValueError(f"Path not found: {relative_path}")
    
    # Don't allow deleting user root
    if full_path.resolve() == user_root.resolve():
        raise ValueError("Cannot delete user root directory")
    
    try:
        if full_path.is_dir():
            if recursive:
                shutil.rmtree(full_path)
            else:
                # Check if directory is empty
                if any(full_path.iterdir()):
                    raise ValueError("Directory not empty. Use recursive=true to delete.")
                full_path.rmdir()
        else:
            full_path.unlink()
    except PermissionError:
        raise ValueError(f"Permission denied")
    except OSError as e:
        raise ValueError(f"Cannot delete: {e}")
    
    return True


def rename_item(username: str, relative_path: str, new_name: str) -> FileInfo:
    """
    Rename a file or directory.
    
    Args:
        username: System username
        relative_path: Path relative to user's home directory
        new_name: New name for the item (just filename, not path)
        
    Returns:
        FileInfo for renamed item
        
    Raises:
        ValueError: For invalid paths or names
    """
    full_path, user_root = _resolve_user_path(username, relative_path)
    
    if not full_path.exists():
        raise ValueError(f"Path not found: {relative_path}")
    
    # Validate new name (no path separators)
    if "/" in new_name or "\\" in new_name:
        raise ValueError("Invalid filename: contains path separator")
    
    if new_name in {".", ".."}:
        raise ValueError("Invalid filename")
    
    new_path = full_path.parent / new_name
    
    if new_path.exists():
        raise ValueError(f"Target already exists: {new_name}")
    
    try:
        full_path.rename(new_path)
    except PermissionError:
        raise ValueError(f"Permission denied")
    except OSError as e:
        raise ValueError(f"Cannot rename: {e}")
    
    return _get_file_info(new_path, user_root)


def move_item(username: str, relative_path: str, new_relative_path: str) -> FileInfo:
    """
    Move a file or directory to a new location.
    
    Args:
        username: System username
        relative_path: Current path relative to user's home
        new_relative_path: New path relative to user's home
        
    Returns:
        FileInfo for moved item
        
    Raises:
        ValueError: For invalid paths
    """
    full_path, user_root = _resolve_user_path(username, relative_path)
    new_full_path, _ = _resolve_user_path(username, new_relative_path)
    
    if not full_path.exists():
        raise ValueError(f"Source not found: {relative_path}")
    
    if new_full_path.exists():
        raise ValueError(f"Target already exists: {new_relative_path}")
    
    if not new_full_path.parent.exists():
        raise ValueError("Target directory does not exist")
    
    try:
        shutil.move(str(full_path), str(new_full_path))
    except PermissionError:
        raise ValueError(f"Permission denied")
    except OSError as e:
        raise ValueError(f"Cannot move: {e}")
    
    return _get_file_info(new_full_path, user_root)


def copy_item(username: str, relative_path: str, new_relative_path: str) -> FileInfo:
    """
    Copy a file or directory.
    
    Args:
        username: System username
        relative_path: Source path relative to user's home
        new_relative_path: Destination path relative to user's home
        
    Returns:
        FileInfo for copied item
        
    Raises:
        ValueError: For invalid paths
    """
    full_path, user_root = _resolve_user_path(username, relative_path)
    new_full_path, _ = _resolve_user_path(username, new_relative_path)
    
    if not full_path.exists():
        raise ValueError(f"Source not found: {relative_path}")
    
    if new_full_path.exists():
        raise ValueError(f"Target already exists: {new_relative_path}")
    
    try:
        if full_path.is_dir():
            shutil.copytree(str(full_path), str(new_full_path))
        else:
            shutil.copy2(str(full_path), str(new_full_path))
    except PermissionError:
        raise ValueError(f"Permission denied")
    except OSError as e:
        raise ValueError(f"Cannot copy: {e}")
    
    return _get_file_info(new_full_path, user_root)


def chmod_item(username: str, relative_path: str, mode: str) -> FileInfo:
    """
    Change file permissions.
    
    Args:
        username: System username
        relative_path: Path relative to user's home
        mode: Permission mode (octal string like "755" or "644")
        
    Returns:
        Updated FileInfo
        
    Raises:
        ValueError: For invalid paths or mode
    """
    full_path, user_root = _resolve_user_path(username, relative_path)
    
    if not full_path.exists():
        raise ValueError(f"Path not found: {relative_path}")
    
    # Parse octal mode
    try:
        mode_int = int(mode, 8)
        if mode_int < 0 or mode_int > 0o777:
            raise ValueError()
    except ValueError:
        raise ValueError(f"Invalid mode: {mode}. Use octal format like '755' or '644'")
    
    try:
        full_path.chmod(mode_int)
    except PermissionError:
        raise ValueError(f"Permission denied")
    except OSError as e:
        raise ValueError(f"Cannot chmod: {e}")
    
    return _get_file_info(full_path, user_root)


def chown_item(username: str, relative_path: str, owner: Optional[str] = None, group: Optional[str] = None) -> FileInfo:
    """
    Change file ownership.
    
    Args:
        username: System username (for path resolution)
        relative_path: Path relative to user's home
        owner: New owner username (optional)
        group: New group name (optional)
        
    Returns:
        Updated FileInfo
        
    Raises:
        ValueError: For invalid paths, owner, or group
    """
    full_path, user_root = _resolve_user_path(username, relative_path)
    
    if not full_path.exists():
        raise ValueError(f"Path not found: {relative_path}")
    
    if not owner and not group:
        raise ValueError("Must specify owner, group, or both")
    
    # Resolve uid/gid
    uid = -1
    gid = -1
    
    if owner:
        try:
            uid = pwd.getpwnam(owner).pw_uid
        except KeyError:
            raise ValueError(f"Unknown user: {owner}")
    
    if group:
        try:
            gid = grp.getgrnam(group).gr_gid
        except KeyError:
            raise ValueError(f"Unknown group: {group}")
    
    try:
        os.chown(str(full_path), uid, gid)
    except PermissionError:
        raise ValueError(f"Permission denied (chown requires root)")
    except OSError as e:
        raise ValueError(f"Cannot chown: {e}")
    
    return _get_file_info(full_path, user_root)


def save_uploaded_file(username: str, relative_dir: str, filename: str, content: bytes) -> FileInfo:
    """
    Save an uploaded file.
    
    Args:
        username: System username
        relative_dir: Target directory relative to user's home
        filename: Name for the uploaded file
        content: File content bytes
        
    Returns:
        FileInfo for uploaded file
        
    Raises:
        ValueError: For invalid paths or errors
    """
    if len(content) > MAX_UPLOAD_SIZE:
        raise ValueError(f"File too large: max {_format_bytes(MAX_UPLOAD_SIZE)}")
    
    # Sanitize filename
    safe_name = filename.replace("/", "_").replace("\\", "_").replace("..", "_")
    if not safe_name or safe_name in {".", ".."}:
        raise ValueError("Invalid filename")
    
    # Resolve target path
    target_dir, user_root = _resolve_user_path(username, relative_dir)
    
    if not target_dir.is_dir():
        raise ValueError(f"Target is not a directory: {relative_dir}")
    
    target_path = target_dir / safe_name
    
    # Check if file exists
    if target_path.exists():
        raise ValueError(f"File already exists: {safe_name}")
    
    try:
        target_path.write_bytes(content)
    except PermissionError:
        raise ValueError(f"Permission denied")
    except OSError as e:
        raise ValueError(f"Cannot save file: {e}")
    
    return _get_file_info(target_path, user_root)


def get_file_path(username: str, relative_path: str) -> Path:
    """
    Get the absolute path for file download.
    
    Args:
        username: System username
        relative_path: Path relative to user's home
        
    Returns:
        Absolute Path object
        
    Raises:
        ValueError: For invalid paths
    """
    full_path, _ = _resolve_user_path(username, relative_path)
    
    if not full_path.exists():
        raise ValueError(f"File not found: {relative_path}")
    
    if full_path.is_dir():
        raise ValueError(f"Cannot download directory: {relative_path}")
    
    return full_path


def get_user_root(username: str) -> Optional[Path]:
    """Get the root directory for a user, or None if not found."""
    user_root = HOME_BASE / username / "public_html"
    return user_root if user_root.exists() else None
