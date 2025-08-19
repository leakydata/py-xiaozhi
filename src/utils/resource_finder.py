import sys
from pathlib import Path
from typing import List, Optional, Union

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class ResourceFinder:
    """
    A unified resource finder that supports resource finding in development environments,
    PyInstaller directory mode, and single-file mode.
    """

    _instance = None
    _base_paths = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        """
        Initializes the resource finder.
        """
        if self._base_paths is None:
            self._base_paths = self._get_base_paths()
            logger.debug(
                f"Resource finder initialized, base paths: {[str(p) for p in self._base_paths]}"
            )

    def _get_base_paths(self) -> List[Path]:
        """
        Get all possible base paths, sorted by priority:
        Project root > Current working directory > Executable directory > _MEIPASS.
        """
        base_paths = []

        # 1. Project root (development environment)
        project_root = Path(__file__).parent.parent.parent
        base_paths.append(project_root)

        # 2. Current working directory
        cwd = Path.cwd()
        if cwd != project_root:
            base_paths.append(cwd)

        # 3. If it is a packaged environment
        if getattr(sys, "frozen", False):
            # Directory where the executable file is located
            exe_dir = Path(sys.executable).parent
            if exe_dir not in base_paths:
                base_paths.append(exe_dir)

            # PyInstaller's _MEIPASS path (single file mode)
            if hasattr(sys, "_MEIPASS"):
                meipass_dir = Path(sys._MEIPASS)
                if meipass_dir not in base_paths:
                    base_paths.append(meipass_dir)

                # Parent directory of _MEIPASS (in some cases resources are here)
                meipass_parent = meipass_dir.parent
                if meipass_parent not in base_paths:
                    base_paths.append(meipass_parent)

            # Parent directory of the executable file (to handle some installation situations)
            exe_parent = exe_dir.parent
            if exe_parent not in base_paths:
                base_paths.append(exe_parent)

            # Support for PyInstaller 6.0.0+: check the _internal directory
            internal_dir = exe_dir / "_internal"
            if internal_dir.exists() and internal_dir not in base_paths:
                base_paths.append(internal_dir)

        return base_paths

    def find_resource(
        self, resource_path: Union[str, Path], resource_type: str = "file"
    ) -> Optional[Path]:
        """Find a resource file or directory.

        Args:
            resource_path: The resource path relative to the project root
            resource_type: The resource type, "file" or "dir"

        Returns:
            The absolute path of the found resource, or None if not found
        """
        resource_path = Path(resource_path)

        # If it is already an absolute path and exists, return it directly
        if resource_path.is_absolute():
            if resource_type == "file" and resource_path.is_file():
                return resource_path
            elif resource_type == "dir" and resource_path.is_dir():
                return resource_path
            else:
                return None

        # Search in all base paths
        for base_path in self._base_paths:
            full_path = base_path / resource_path

            if resource_type == "file" and full_path.is_file():
                logger.debug(f"Found file: {full_path}")
                return full_path
            elif resource_type == "dir" and full_path.is_dir():
                logger.debug(f"Found directory: {full_path}")
                return full_path

        logger.warning(f"Resource not found: {resource_path}")
        return None

    def find_file(self, file_path: Union[str, Path]) -> Optional[Path]:
        """Find a file.

        Args:
            file_path: The file path relative to the project root

        Returns:
            The absolute path of the found file, or None if not found
        """
        return self.find_resource(file_path, "file")

    def find_directory(self, dir_path: Union[str, Path]) -> Optional[Path]:
        """Find a directory.

        Args:
            dir_path: The directory path relative to the project root

        Returns:
            The absolute path of the found directory, or None if not found
        """
        return self.find_resource(dir_path, "dir")

    def find_models_dir(self) -> Optional[Path]:
        """Find the models directory.

        Returns:
            The absolute path of the found models directory, or None if not found
        """
        return self.find_directory("models")

    def find_config_dir(self) -> Optional[Path]:
        """Find the config directory.

        Returns:
            The absolute path of the found config directory, or None if not found
        """
        return self.find_directory("config")

    def find_assets_dir(self) -> Optional[Path]:
        """Find the assets directory.

        Returns:
            The absolute path of the found assets directory, or None if not found
        """
        return self.find_directory("assets")

    def find_libs_dir(self, system: str = None, arch: str = None) -> Optional[Path]:
        """Find the libs directory (for dynamic libraries)

        Args:
            system: System name (e.g., Windows, Linux, Darwin)
            arch: Architecture name (e.g., x64, x86, arm64)

        Returns:
            The absolute path of the found libs directory, or None if not found
        """
        # Base libs directory
        libs_dir = self.find_directory("libs")
        if not libs_dir:
            return None

        # If system and architecture are specified, find the specific subdirectory
        if system and arch:
            specific_dir = libs_dir / system / arch
            if specific_dir.is_dir():
                return specific_dir
        elif system:
            system_dir = libs_dir / system
            if system_dir.is_dir():
                return system_dir

        return libs_dir

    def get_project_root(self) -> Path:
        """Get the project root directory.

        Returns:
            The path to the project root directory
        """
        return self._base_paths[0]

    def get_app_path(self) -> Path:
        """Get the base path of the application (method compatible with ConfigManager)

        Returns:
            The base path of the application
        """
        if getattr(sys, "frozen", False) and hasattr(sys, "_MEIPASS"):
            # If running as a PyInstaller bundle
            return Path(sys._MEIPASS)
        else:
            # If running in a development environment
            return self.get_project_root()

    def list_files_in_directory(
        self, dir_path: Union[str, Path], pattern: str = "*"
    ) -> List[Path]:
        """List files in a directory.

        Args:
            dir_path: The directory path
            pattern: The file matching pattern

        Returns:
            A list of file paths
        """
        directory = self.find_directory(dir_path)
        if not directory:
            return []

        try:
            return list(directory.glob(pattern))
        except Exception as e:
            logger.error(f"Error listing directory files: {e}")
            return []


# Global singleton instance
resource_finder = ResourceFinder()


# Convenience functions
def find_file(file_path: Union[str, Path]) -> Optional[Path]:
    """
    Convenience function for finding a file.
    """
    return resource_finder.find_file(file_path)


def find_directory(dir_path: Union[str, Path]) -> Optional[Path]:
    """
    Convenience function for finding a directory.
    """
    return resource_finder.find_directory(dir_path)


def find_models_dir() -> Optional[Path]:
    """
    Convenience function to find the models directory.
    """
    return resource_finder.find_models_dir()


def find_config_dir() -> Optional[Path]:
    """
    Convenience function to find the config directory.
    """
    return resource_finder.find_config_dir()


def find_assets_dir() -> Optional[Path]:
    """
    Convenience function to find the assets directory.
    """
    return resource_finder.find_assets_dir()


def find_libs_dir(system: str = None, arch: str = None) -> Optional[Path]:
    """
    Convenience function to find the libs directory.
    """
    return resource_finder.find_libs_dir(system, arch)


def get_project_root() -> Path:
    """
    Convenience function to get the project root directory.
    """
    return resource_finder.get_project_root()


def get_app_path() -> Path:
    """
    Convenience function to get the application base path.
    """
    return resource_finder.get_app_path()
