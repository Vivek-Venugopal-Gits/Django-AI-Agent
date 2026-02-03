# from pathlib import Path
# from agent.workspace import WORKSPACE_ROOT
# import difflib


# class FileToolError(Exception):
#     pass


# def _resolve_path(relative_path: str) -> Path:
#     path = (WORKSPACE_ROOT / relative_path).resolve()
#     if not str(path).startswith(str(WORKSPACE_ROOT)):
#         raise FileToolError("Access outside workspace denied")
#     return path


# def read_file(path: str) -> str:
#     file_path = _resolve_path(path)
#     if not file_path.exists():
#         raise FileToolError(f"File not found: {path}")
#     return file_path.read_text(encoding="utf-8")


# def write_file(path: str, content: str):
#     file_path = _resolve_path(path)
#     if file_path.exists():
#         raise FileToolError(f"File already exists: {path}")
#     file_path.parent.mkdir(parents=True, exist_ok=True)
#     file_path.write_text(content, encoding="utf-8")


# def append_file(path: str, content: str):
#     file_path = _resolve_path(path)
#     if not file_path.exists():
#         raise FileToolError(f"File not found: {path}")
#     with file_path.open("a", encoding="utf-8") as f:
#         f.write("\n\n" + content)


# def update_file(path: str, new_content: str) -> str:
#     file_path = _resolve_path(path)
#     if not file_path.exists():
#         raise FileToolError(f"File not found: {path}")
#     old_content = file_path.read_text(encoding="utf-8")
#     diff = "\n".join(
#         difflib.unified_diff(
#             old_content.splitlines(),
#             new_content.splitlines(),
#             fromfile="before",
#             tofile="after",
#             lineterm=""
#         )
#     )
#     file_path.write_text(new_content, encoding="utf-8")
#     return diff


# def delete_file(path: str):
#     file_path = _resolve_path(path)
#     if not file_path.exists():
#         raise FileToolError(f"File not found: {path}")
#     file_path.unlink()

from pathlib import Path
from agent.workspace import WORKSPACE_ROOT
import difflib


# Global variable to hold current workspace root
_current_workspace_root = WORKSPACE_ROOT


class FileToolError(Exception):
    pass


def set_workspace_root(new_root):
    """
    Set the workspace root dynamically
    
    Args:
        new_root: String or Path object pointing to project directory
    
    Usage:
        # For Web UI
        set_workspace_root("/path/to/user/project")
        
        # For CLI (uses default from workspace.py)
        # Don't call this function, it uses WORKSPACE_ROOT by default
    """
    global _current_workspace_root
    _current_workspace_root = Path(new_root).resolve()
    print(f"[FILE_TOOLS] Workspace root set to: {_current_workspace_root}")


def get_workspace_root():
    """
    Get the current workspace root
    
    Returns:
        Path object of current workspace
    """
    return _current_workspace_root


# def _resolve_path(relative_path: str) -> Path:
#     """
#     Resolve a relative path within the current workspace
    
#     Args:
#         relative_path: Relative path from workspace root (e.g., "app/models.py")
    
#     Returns:
#         Absolute resolved Path object
    
#     Raises:
#         FileToolError: If path tries to escape workspace
#     """
#     workspace = get_workspace_root()
#     path = (workspace / relative_path).resolve()
    
#     # Security check: prevent directory traversal attacks
#     if not str(path).startswith(str(workspace)):
#         raise FileToolError(f"Access outside workspace denied: {relative_path}")
    
#     return path
def _resolve_path(relative_path: str) -> Path:
    workspace = get_workspace_root()
    path = (workspace / relative_path).resolve()

    if not str(path).startswith(str(workspace)):
        raise FileToolError(f"Access outside workspace denied: {relative_path}")

    # 🚨 Block paths like models.py/anything
    for parent in path.parents:
        if parent.suffix and parent.exists() and parent.is_file():
            raise FileToolError(
                f"Invalid path: treating file as directory → {parent}"
            )

    return path


def read_file(path: str) -> str:
    """
    Read file content from workspace
    
    Args:
        path: Relative path from workspace root
    
    Returns:
        File content as string
    
    Raises:
        FileToolError: If file not found
    """
    file_path = _resolve_path(path)
    if not file_path.exists():
        raise FileToolError(f"File not found: {path}")
    return file_path.read_text(encoding="utf-8")


# def write_file(path: str, content: str):
#     """
#     Write new file to workspace (fails if file exists)
    
#     Args:
#         path: Relative path from workspace root
#         content: File content to write
    
#     Raises:
#         FileToolError: If file already exists
#     """
#     file_path = _resolve_path(path)
#     if file_path.exists():
#         raise FileToolError(f"File already exists: {path}")
#     file_path.parent.mkdir(parents=True, exist_ok=True)
#     file_path.write_text(content, encoding="utf-8")
def write_file(path: str, content: str):
    """
    Write new file to workspace (fails if file exists)
    """
    file_path = _resolve_path(path)

    # If path already exists as a FILE → block
    if file_path.exists():
        raise FileToolError(f"File already exists: {path}")

    # 🚨 SAFETY: parent must not be a file
    if file_path.parent.exists() and file_path.parent.is_file():
        raise FileToolError(
            f"Invalid path: parent is a file, not a directory → {file_path.parent}"
        )

    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content, encoding="utf-8")



def append_file(path: str, content: str):
    """
    Append content to existing file
    
    Args:
        path: Relative path from workspace root
        content: Content to append
    
    Raises:
        FileToolError: If file not found
    """
    file_path = _resolve_path(path)
    if not file_path.exists():
        raise FileToolError(f"File not found: {path}")
    with file_path.open("a", encoding="utf-8") as f:
        f.write("\n\n" + content)


def update_file(path: str, new_content: str) -> str:
    """
    Update file with new content and return diff
    
    Args:
        path: Relative path from workspace root
        new_content: New file content
    
    Returns:
        Unified diff string showing changes
    
    Raises:
        FileToolError: If file not found
    """
    file_path = _resolve_path(path)
    if not file_path.exists():
        raise FileToolError(f"File not found: {path}")
    
    old_content = file_path.read_text(encoding="utf-8")
    diff = "\n".join(
        difflib.unified_diff(
            old_content.splitlines(),
            new_content.splitlines(),
            fromfile="before",
            tofile="after",
            lineterm=""
        )
    )
    file_path.write_text(new_content, encoding="utf-8")
    return diff


def delete_file(path: str):
    """
    Delete file from workspace
    
    Args:
        path: Relative path from workspace root
    
    Raises:
        FileToolError: If file not found
    """
    file_path = _resolve_path(path)
    if not file_path.exists():
        raise FileToolError(f"File not found: {path}")
    file_path.unlink()