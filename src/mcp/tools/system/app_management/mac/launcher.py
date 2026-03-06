"""macOS application launcher.

Provides application launching functionality for the macOS platform.
"""

import os
import subprocess

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def launch_application(app_name: str) -> bool:
    """Launch an application on macOS.

    Args:
        app_name: Application name

    Returns:
        bool: Whether the launch was successful
    """
    try:
        logger.info(f"[MacLauncher] Launching application: {app_name}")

        # Method 1: Use open -a command
        try:
            subprocess.Popen(["open", "-a", app_name])
            logger.info(f"[MacLauncher] Successfully launched using open -a: {app_name}")
            return True
        except (OSError, subprocess.SubprocessError):
            logger.debug(f"[MacLauncher] Failed to launch with open -a: {app_name}")

        # Method 2: Use application name directly
        try:
            subprocess.Popen([app_name])
            logger.info(f"[MacLauncher] Successfully launched directly: {app_name}")
            return True
        except (OSError, subprocess.SubprocessError):
            logger.debug(f"[MacLauncher] Failed to launch directly: {app_name}")

        # Method 3: Try the Applications directory
        app_path = f"/Applications/{app_name}.app"
        if os.path.exists(app_path):
            subprocess.Popen(["open", app_path])
            logger.info(f"[MacLauncher] Successfully launched via Applications directory: {app_name}")
            return True

        # Method 4: Use osascript to launch
        script = f'tell application "{app_name}" to activate'
        subprocess.Popen(["osascript", "-e", script])
        logger.info(f"[MacLauncher] Successfully launched using osascript: {app_name}")
        return True

    except Exception as e:
        logger.error(f"[MacLauncher] macOS launch failed: {e}")
        return False
