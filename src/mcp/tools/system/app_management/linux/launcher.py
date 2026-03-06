"""Linux application launcher.

Provides application launching functionality for the Linux platform.
"""

import os
import subprocess

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def launch_application(app_name: str) -> bool:
    """Launch an application on Linux.

    Args:
        app_name: Application name

    Returns:
        bool: Whether the launch was successful
    """
    try:
        logger.info(f"[LinuxLauncher] Launching application: {app_name}")

        # Method 1: Use application name directly
        try:
            subprocess.Popen([app_name])
            logger.info(f"[LinuxLauncher] Successfully launched directly: {app_name}")
            return True
        except (OSError, subprocess.SubprocessError):
            logger.debug(f"[LinuxLauncher] Failed to launch directly: {app_name}")

        # Method 2: Use which to find application path
        try:
            result = subprocess.run(["which", app_name], capture_output=True, text=True)
            if result.returncode == 0:
                app_path = result.stdout.strip()
                subprocess.Popen([app_path])
                logger.info(f"[LinuxLauncher] Successfully launched via which: {app_name}")
                return True
        except (OSError, subprocess.SubprocessError):
            logger.debug(f"[LinuxLauncher] Failed to launch via which: {app_name}")

        # Method 3: Use xdg-open (for desktop environments)
        try:
            subprocess.Popen(["xdg-open", app_name])
            logger.info(f"[LinuxLauncher] Successfully launched using xdg-open: {app_name}")
            return True
        except (OSError, subprocess.SubprocessError):
            logger.debug(f"[LinuxLauncher] Failed to launch with xdg-open: {app_name}")

        # Method 4: Try common application paths
        common_paths = [
            f"/usr/bin/{app_name}",
            f"/usr/local/bin/{app_name}",
            f"/opt/{app_name}/{app_name}",
            f"/snap/bin/{app_name}",
        ]

        for path in common_paths:
            if os.path.exists(path):
                subprocess.Popen([path])
                logger.info(
                    f"[LinuxLauncher] Successfully launched via common path: {app_name} ({path})"
                )
                return True

        # Method 5: Try launching via .desktop file
        desktop_dirs = [
            "/usr/share/applications",
            "/usr/local/share/applications",
            os.path.expanduser("~/.local/share/applications"),
        ]

        for desktop_dir in desktop_dirs:
            desktop_file = os.path.join(desktop_dir, f"{app_name}.desktop")
            if os.path.exists(desktop_file):
                subprocess.Popen(["gtk-launch", f"{app_name}.desktop"])
                logger.info(f"[LinuxLauncher] Successfully launched via desktop file: {app_name}")
                return True

        logger.warning(f"[LinuxLauncher] All Linux launch methods failed: {app_name}")
        return False

    except Exception as e:
        logger.error(f"[LinuxLauncher] Linux launch failed: {e}")
        return False
