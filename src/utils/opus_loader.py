# Handle opus dynamic library before importing opuslib
import ctypes
import os
import platform
import shutil
import sys
from pathlib import Path

# Get logger
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


# Platform and architecture constant definitions
WINDOWS = "windows"
MACOS = "darwin"
LINUX = "linux"

# Library file information
LIB_INFO = {
    WINDOWS: {"name": "opus.dll", "system_name": "opus"},
    MACOS: {"name": "libopus.dylib", "system_name": "libopus.dylib"},
    LINUX: {"name": "libopus.so", "system_name": ["libopus.so.0", "libopus.so"]},
}

# Directory structure definition - paths based on actual directory structure
DIR_STRUCTURE = {
    WINDOWS: {"arch": "x86_64", "path": "libs/libopus/win/x86_64"},
    MACOS: {
        "arch": {"arm": "arm64", "intel": "x64"},
        "path": "libs/libopus/mac/{arch}",
    },
    LINUX: {
        "arch": {"arm": "arm64", "intel": "x64"},
        "path": "libs/libopus/linux/{arch}",
    },
}


def get_system_info():
    """Get current system information."""
    system = platform.system().lower()
    architecture = platform.machine().lower()

    # Normalize system name
    if system == "windows" or system.startswith("win"):
        system = WINDOWS
    elif system == "darwin":
        system = MACOS
    elif system.startswith("linux"):
        system = LINUX

    # Normalize architecture name
    is_arm = "arm" in architecture or "aarch64" in architecture

    if system == MACOS:
        arch_name = DIR_STRUCTURE[MACOS]["arch"]["arm" if is_arm else "intel"]
    elif system == WINDOWS:
        arch_name = DIR_STRUCTURE[WINDOWS]["arch"]
    else:  # Linux
        arch_name = DIR_STRUCTURE[LINUX]["arch"]["arm" if is_arm else "intel"]

    return system, arch_name


def get_search_paths(system, arch_name):
    """Get library file search path list (using unified resource finder)."""
    from .resource_finder import find_libs_dir, get_project_root

    lib_name = LIB_INFO[system]["name"]
    search_paths = []

    # Map system names to directory names
    system_dir_map = {WINDOWS: "win", MACOS: "mac", LINUX: "linux"}

    system_dir = system_dir_map.get(system)

    # First try to find platform+architecture specific libs directory
    if system_dir:
        specific_libs_dir = find_libs_dir(f"libopus/{system_dir}", arch_name)
        if specific_libs_dir:
            search_paths.append((specific_libs_dir, lib_name))
            logger.debug(f"Found platform-specific libs directory: {specific_libs_dir}")

    # Then find platform-specific libs directory
    if system_dir:
        platform_libs_dir = find_libs_dir(f"libopus/{system_dir}")
        if platform_libs_dir:
            search_paths.append((platform_libs_dir, lib_name))
            logger.debug(f"Found platform libs directory: {platform_libs_dir}")

    # Find general libs directory
    general_libs_dir = find_libs_dir()
    if general_libs_dir:
        search_paths.append((general_libs_dir, lib_name))
        logger.debug(f"Added general libs directory: {general_libs_dir}")

    # Add project root as last fallback
    project_root = get_project_root()
    search_paths.append((project_root, lib_name))

    # Print all search paths for debugging
    for dir_path, filename in search_paths:
        full_path = dir_path / filename
        logger.debug(f"Search path: {full_path} (exists: {full_path.exists()})")
    return search_paths


def find_system_opus():
    """Find opus library from system paths."""
    system, _ = get_system_info()
    lib_path = None

    try:
        # Get opus library names for the system
        lib_names = LIB_INFO[system]["system_name"]
        if not isinstance(lib_names, list):
            lib_names = [lib_names]

        # Try loading each possible name
        for lib_name in lib_names:
            try:
                import ctypes.util

                system_lib_path = ctypes.util.find_library(lib_name)

                if system_lib_path:
                    lib_path = system_lib_path
                    logger.info(f"Found opus library in system path: {lib_path}")
                    break
                else:
                    # Try loading the library name directly
                    ctypes.cdll.LoadLibrary(lib_name)
                    lib_path = lib_name
                    logger.info(f"Loaded system opus library directly: {lib_name}")
                    break
            except Exception as e:
                logger.debug(f"Failed to load system library {lib_name}: {e}")
                continue

    except Exception as e:
        logger.error(f"Failed to find system opus library: {e}")

    return lib_path


def copy_opus_to_project(system_lib_path):
    """Copy system library to project directory."""
    from .resource_finder import get_project_root

    system, arch_name = get_system_info()

    if not system_lib_path:
        logger.error("Cannot copy opus library: system library path is empty")
        return None

    try:
        project_root = get_project_root()

        # Get target directory path based on actual directory structure
        if system == MACOS:
            target_path = DIR_STRUCTURE[MACOS]["path"].format(arch=arch_name)
        elif system == WINDOWS:
            target_path = DIR_STRUCTURE[WINDOWS]["path"]
        else:  # Linux
            target_path = DIR_STRUCTURE[LINUX]["path"]

        target_dir = project_root / target_path

        # Create target directory if it doesn't exist
        target_dir.mkdir(parents=True, exist_ok=True)

        # Determine target filename
        lib_name = LIB_INFO[system]["name"]
        target_file = target_dir / lib_name

        # Copy file
        shutil.copy2(system_lib_path, target_file)
        logger.info(f"Copied opus library from {system_lib_path} to {target_file}")

        return str(target_file)

    except Exception as e:
        logger.error(f"Failed to copy opus library to project directory: {e}")
        return None


def setup_opus():
    """Set up the opus dynamic library."""
    # Check if already loaded by runtime hook
    if hasattr(sys, "_opus_loaded"):
        logger.info("Opus library already loaded by runtime hook")
        return True

    # Get current system info
    system, arch_name = get_system_info()
    logger.info(f"Current system: {system}, architecture: {arch_name}")

    # Build search paths
    search_paths = get_search_paths(system, arch_name)

    # Find local library file
    lib_path = None
    lib_dir = None

    for dir_path, file_name in search_paths:
        full_path = dir_path / file_name
        if full_path.exists():
            lib_path = str(full_path)
            lib_dir = str(dir_path)
            logger.info(f"Found opus library file: {lib_path}")
            break

    # If not found locally, try loading from system
    if lib_path is None:
        logger.warning("Opus library not found locally, trying system paths")
        system_lib_path = find_system_opus()

        if system_lib_path:
            # First try using the system library directly
            try:
                _ = ctypes.cdll.LoadLibrary(system_lib_path)
                logger.info(f"Loaded opus library from system path: {system_lib_path}")
                sys._opus_loaded = True
                return True
            except Exception as e:
                logger.warning(f"Failed to load system opus library: {e}, trying to copy to project")

            # If direct loading fails, try copying to project directory
            lib_path = copy_opus_to_project(system_lib_path)
            if lib_path:
                lib_dir = str(Path(lib_path).parent)
            else:
                logger.error("Cannot find or copy opus library file")
                return False
        else:
            logger.error("Opus library not found in system either")
            return False

    # Windows-specific handling
    if system == WINDOWS and lib_dir:
        # Add DLL search path
        if hasattr(os, "add_dll_directory"):
            try:
                os.add_dll_directory(lib_dir)
                logger.debug(f"Added DLL search path: {lib_dir}")
            except Exception as e:
                logger.warning(f"Failed to add DLL search path: {e}")

        # Set environment variable
        os.environ["PATH"] = lib_dir + os.pathsep + os.environ.get("PATH", "")

    # Patch library path
    _patch_find_library("opus", lib_path)

    # Try loading the library
    try:
        _ = ctypes.CDLL(lib_path)
        logger.info(f"Successfully loaded opus library: {lib_path}")
        sys._opus_loaded = True
        return True
    except Exception as e:
        logger.error(f"Failed to load opus library: {e}")
        return False


def _patch_find_library(lib_name, lib_path):
    """Patch ctypes.util.find_library function."""
    import ctypes.util

    original_find_library = ctypes.util.find_library

    def patched_find_library(name):
        if name == lib_name:
            return lib_path
        return original_find_library(name)

    ctypes.util.find_library = patched_find_library
