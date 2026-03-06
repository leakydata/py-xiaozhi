import aiofiles
import os
from pathlib import Path
from typing import List, Dict, Any

# Restrict filesystem access to user's home directory and common safe locations
ALLOWED_ROOTS = [
    Path.home(),
    Path.home() / "Documents",
    Path.home() / "Desktop",
    Path.home() / "Downloads",
]

# Deny access to these patterns
BLOCKED_PATTERNS = [
    ".ssh", ".gnupg", ".aws", ".azure", ".config/gcloud",
    "AppData/Roaming", ".env", "credentials", "secrets",
    "id_rsa", "id_ed25519", ".git/config",
]


def _validate_path(path: str) -> Path:
    """Validate and sanitize a file path to prevent path traversal attacks."""
    resolved = Path(path).resolve()

    # Check for blocked patterns
    path_str = str(resolved).replace("\\", "/").lower()
    for pattern in BLOCKED_PATTERNS:
        if pattern.lower() in path_str:
            raise PermissionError(f"Access denied: path contains restricted pattern '{pattern}'")

    # Check if path is under an allowed root
    for root in ALLOWED_ROOTS:
        try:
            resolved.relative_to(root.resolve())
            return resolved
        except ValueError:
            continue

    raise PermissionError(
        f"Access denied: path '{path}' is outside allowed directories. "
        f"Allowed: {', '.join(str(r) for r in ALLOWED_ROOTS)}"
    )


async def read_file(path: str) -> str:
    """Reads the content of a file."""
    try:
        validated = _validate_path(path)
        async with aiofiles.open(validated, mode='r', encoding='utf-8') as f:
            return await f.read()
    except UnicodeDecodeError:
        try:
            async with aiofiles.open(validated, mode='r', encoding='latin-1') as f:
                return await f.read()
        except Exception as e:
            return f"Error reading file with fallback encoding: {e}"
    except PermissionError as e:
        return f"Error: {e}"
    except FileNotFoundError:
        return f"Error: File not found at {path}"
    except Exception as e:
        return f"Error reading file: {e}"


async def write_file(path: str, content: str) -> str:
    """Writes content to a file. Creates the file if it doesn't exist."""
    try:
        validated = _validate_path(path)
        # Ensure parent directory exists
        validated.parent.mkdir(parents=True, exist_ok=True)
        async with aiofiles.open(validated, mode='w', encoding='utf-8') as f:
            await f.write(content)
        return f"Successfully wrote to {path}"
    except PermissionError as e:
        return f"Error: {e}"
    except Exception as e:
        return f"Error writing to file: {e}"


async def rename_file(old_path: str, new_path: str) -> str:
    """Renames or moves a file."""
    try:
        validated_old = _validate_path(old_path)
        validated_new = _validate_path(new_path)
        os.rename(validated_old, validated_new)
        return f"Successfully renamed {old_path} to {new_path}"
    except PermissionError as e:
        return f"Error: {e}"
    except FileNotFoundError:
        return f"Error: File not found at {old_path}"
    except Exception as e:
        return f"Error renaming file: {e}"


async def list_directory(path: str) -> List[str]:
    """Lists the contents of a directory."""
    try:
        validated = _validate_path(path)
        return os.listdir(validated)
    except PermissionError as e:
        return [f"Error: {e}"]
    except FileNotFoundError:
        return [f"Error: Directory not found at {path}"]
    except Exception as e:
        return [f"Error listing directory: {e}"]


async def get_file_info(path: str) -> Dict[str, Any]:
    """Gets information about a file or directory."""
    try:
        validated = _validate_path(path)
        stat = os.stat(validated)
        return {
            "path": str(validated),
            "size": stat.st_size,
            "last_modified": stat.st_mtime,
            "created": stat.st_ctime,
            "is_directory": os.path.isdir(validated),
        }
    except PermissionError as e:
        return {"error": str(e)}
    except FileNotFoundError:
        return {"error": f"File or directory not found at {path}"}
    except Exception as e:
        return {"error": f"Error getting file info: {e}"}
