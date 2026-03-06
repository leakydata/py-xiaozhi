"""Unified application launcher.

Automatically selects the appropriate launcher implementation based on the current system.
"""

import asyncio
import platform
from typing import Any, Dict, Optional

from src.utils.logging_config import get_logger

from .utils import find_best_matching_app

logger = get_logger(__name__)


async def launch_application(args: Dict[str, Any]) -> bool:
    """Launch an application.

    Args:
        args: Parameter dictionary containing the application name
            - app_name: Application name

    Returns:
        bool: Whether the launch was successful
    """
    try:
        app_name = args["app_name"]
        logger.info(f"[AppLauncher] Attempting to launch application: {app_name}")

        # First try to find an exact matching application through scanning
        matched_app = await _find_matching_application(app_name)
        if matched_app:
            logger.info(
                f"[AppLauncher] Found matching application: {matched_app.get('display_name', matched_app.get('name', ''))}"
            )
            # Use different launch methods based on application type
            success = await _launch_matched_app(matched_app, app_name)
        else:
            # If no match found, use the original method
            logger.info(f"[AppLauncher] No exact match found, using original name: {app_name}")
            success = await _launch_by_name(app_name)

        if success:
            logger.info(f"[AppLauncher] Successfully launched application: {app_name}")
        else:
            logger.warning(f"[AppLauncher] Failed to launch application: {app_name}")

        return success

    except KeyError:
        logger.error("[AppLauncher] Missing app_name parameter")
        return False
    except Exception as e:
        logger.error(f"[AppLauncher] Failed to launch application: {e}", exc_info=True)
        return False


async def _find_matching_application(app_name: str) -> Optional[Dict[str, Any]]:
    """Find a matching application through scanning.

    Args:
        app_name: Application name to search for

    Returns:
        Matching application information, or None if not found
    """
    try:
        # Use unified matching logic
        matched_app = await find_best_matching_app(app_name, "installed")

        if matched_app:
            logger.info(
                f"[AppLauncher] Found application via unified matching: {matched_app.get('display_name', matched_app.get('name', ''))}"
            )

        return matched_app

    except Exception as e:
        logger.warning(f"[AppLauncher] Error finding matching application: {e}")
        return None


async def _launch_matched_app(matched_app: Dict[str, Any], original_name: str) -> bool:
    """Launch the matched application.

    Args:
        matched_app: Matched application information
        original_name: Original application name

    Returns:
        bool: Whether the launch was successful
    """
    try:
        app_type = matched_app.get("type", "unknown")
        app_path = matched_app.get("path", matched_app.get("name", original_name))

        system = platform.system()

        if system == "Windows":
            # Windows system special handling
            if app_type == "uwp":
                # UWP apps use a special launch method
                from .windows.launcher import launch_uwp_app_by_path

                return await asyncio.to_thread(launch_uwp_app_by_path, app_path)
            elif app_type == "shortcut" and app_path.endswith(".lnk"):
                # Shortcut file
                from .windows.launcher import launch_shortcut

                return await asyncio.to_thread(launch_shortcut, app_path)

        # Regular application launch
        return await _launch_by_name(app_path)

    except Exception as e:
        logger.error(f"[AppLauncher] Failed to launch matched application: {e}")
        return False


async def _launch_by_name(app_name: str) -> bool:
    """根据名称启动应用程序.

    Args:
        app_name: 应用程序名称或路径

    Returns:
        bool: 启动是否成功
    """
    try:
        system = platform.system()

        if system == "Windows":
            from .windows.launcher import launch_application

            return await asyncio.to_thread(launch_application, app_name)
        elif system == "Darwin":  # macOS
            from .mac.launcher import launch_application

            return await asyncio.to_thread(launch_application, app_name)
        elif system == "Linux":
            from .linux.launcher import launch_application

            return await asyncio.to_thread(launch_application, app_name)
        else:
            logger.error(f"[AppLauncher] 不支持的操作系统: {system}")
            return False

    except Exception as e:
        logger.error(f"[AppLauncher] 启动应用程序失败: {e}")
        return False


def get_system_launcher():
    """根据当前系统获取对应的启动器模块.

    Returns:
        对应系统的启动器模块
    """
    system = platform.system()

    if system == "Darwin":  # macOS
        from .mac import launcher

        return launcher
    elif system == "Windows":  # Windows
        from .windows import launcher

        return launcher
    elif system == "Linux":  # Linux
        from .linux import launcher

        return launcher
    else:
        logger.warning(f"[AppLauncher] 不支持的系统: {system}")
        return None
