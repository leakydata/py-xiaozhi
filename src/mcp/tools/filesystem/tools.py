import aiofiles
import os
from typing import List, Dict, Any

async def read_file(path: str) -> str:
    """
    Reads the content of a file.
    """
    try:
        async with aiofiles.open(path, mode='r', encoding='utf-8') as f:
            return await f.read()
    except FileNotFoundError:
        return f"Error: File not found at {path}"
    except Exception as e:
        return f"Error reading file: {e}"

async def write_file(path: str, content: str) -> str:
    """
    Writes content to a file. Creates the file if it doesn't exist.
    """
    try:
        async with aiofiles.open(path, mode='w', encoding='utf-8') as f:
            await f.write(content)
        return f"Successfully wrote to {path}"
    except Exception as e:
        return f"Error writing to file: {e}"

async def rename_file(old_path: str, new_path: str) -> str:
    """
    Renames or moves a file.
    """
    try:
        os.rename(old_path, new_path)
        return f"Successfully renamed {old_path} to {new_path}"
    except FileNotFoundError:
        return f"Error: File not found at {old_path}"
    except Exception as e:
        return f"Error renaming file: {e}"

async def list_directory(path: str) -> List[str]:
    """
    Lists the contents of a directory.
    """
    try:
        return os.listdir(path)
    except FileNotFoundError:
        return [f"Error: Directory not found at {path}"]
    except Exception as e:
        return [f"Error listing directory: {e}"]

async def get_file_info(path: str) -> Dict[str, Any]:
    """
    Gets information about a file or directory.
    """
    try:
        stat = os.stat(path)
        return {
            "path": path,
            "size": stat.st_size,
            "last_modified": stat.st_mtime,
            "created": stat.st_ctime,
            "is_directory": os.path.isdir(path),
        }
    except FileNotFoundError:
        return {"error": f"File or directory not found at {path}"}
    except Exception as e:
        return {"error": f"Error getting file info: {e}"}
