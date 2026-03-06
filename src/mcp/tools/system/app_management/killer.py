"""Unified application killer.

Automatically selects the appropriate killer implementation based on the current system.
"""

import asyncio
import json
import platform
from typing import Any, Dict, List

from src.utils.logging_config import get_logger

from .utils import AppMatcher

logger = get_logger(__name__)


async def kill_application(args: Dict[str, Any]) -> bool:
    """Close an application.

    Args:
        args: Parameter dictionary containing the application name
            - app_name: Application name
            - force: Whether to force close (optional, defaults to False)

    Returns:
        bool: Whether the close was successful
    """
    try:
        app_name = args["app_name"]
        force = args.get("force", False)
        logger.info(f"[AppKiller] Attempting to close application: {app_name}, force: {force}")

        # First try to find running applications through scanning
        running_apps = await _find_running_applications(app_name)

        if not running_apps:
            logger.warning(f"[AppKiller] No running application found: {app_name}")
            return False

        # Select close strategy based on system
        system = platform.system()
        if system == "Windows":
            # Windows uses complex grouped close strategy
            success = await asyncio.to_thread(
                _kill_windows_app_group, running_apps, app_name, force
            )
        else:
            # macOS and Linux use simple sequential close strategy
            success_count = 0
            for app in running_apps:
                success = await asyncio.to_thread(_kill_app_sync, app, force, system)
                if success:
                    success_count += 1
                    logger.info(
                        f"[AppKiller] Successfully closed application: {app['name']} (PID: {app.get('pid', 'N/A')})"
                    )
                else:
                    logger.warning(
                        f"[AppKiller] Failed to close application: {app['name']} (PID: {app.get('pid', 'N/A')})"
                    )

            success = success_count > 0
            logger.info(
                f"[AppKiller] Close operation complete, successfully closed {success_count}/{len(running_apps)} processes"
            )

        return success

    except Exception as e:
        logger.error(f"[AppKiller] Error closing application: {e}", exc_info=True)
        return False


async def list_running_applications(args: Dict[str, Any]) -> str:
    """List all currently running applications.

    Args:
        args: Dictionary containing listing parameters
            - filter_name: Filter by application name (optional)

    Returns:
        str: JSON-formatted list of running applications
    """
    try:
        filter_name = args.get("filter_name", "")
        logger.info(f"[AppKiller] Starting to list running applications, filter: {filter_name}")

        # Use thread pool for scanning to avoid blocking the event loop
        apps = await asyncio.to_thread(_list_running_apps_sync, filter_name)

        result = {
            "success": True,
            "total_count": len(apps),
            "applications": apps,
            "message": f"Found {len(apps)} running applications",
        }

        logger.info(f"[AppKiller] Listing complete, found {len(apps)} running applications")
        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        error_msg = f"Failed to list running applications: {str(e)}"
        logger.error(f"[AppKiller] {error_msg}", exc_info=True)
        return json.dumps(
            {
                "success": False,
                "total_count": 0,
                "applications": [],
                "message": error_msg,
            },
            ensure_ascii=False,
        )


async def _find_running_applications(app_name: str) -> List[Dict[str, Any]]:
    """Find running applications that match.

    Args:
        app_name: Application name to search for

    Returns:
        List of matching running applications
    """
    try:
        # Get all running applications
        all_apps = await asyncio.to_thread(_list_running_apps_sync, "")

        # Use unified matcher to find best matches
        matched_apps = []

        for app in all_apps:
            score = AppMatcher.match_application(app_name, app)
            if score >= 50:  # Match threshold
                matched_apps.append(app)

        # Sort by match score
        matched_apps.sort(
            key=lambda x: AppMatcher.match_application(app_name, x), reverse=True
        )

        logger.info(f"[AppKiller] Found {len(matched_apps)} matching running applications")
        return matched_apps

    except Exception as e:
        logger.warning(f"[AppKiller] Error finding running applications: {e}")
        return []


def _list_running_apps_sync(filter_name: str = "") -> List[Dict[str, Any]]:
    """Synchronously list running applications.

    Args:
        filter_name: Filter by application name

    Returns:
        List of running applications
    """
    system = platform.system()

    if system == "Darwin":  # macOS
        from .mac.killer import list_running_applications

        return list_running_applications(filter_name)
    elif system == "Windows":  # Windows
        from .windows.killer import list_running_applications

        return list_running_applications(filter_name)
    elif system == "Linux":  # Linux
        from .linux.killer import list_running_applications

        return list_running_applications(filter_name)
    else:
        logger.warning(f"[AppKiller] Unsupported operating system: {system}")
        return []


def _kill_app_sync(app: Dict[str, Any], force: bool, system: str) -> bool:
    """Synchronously close an application.

    Args:
        app: Application information
        force: Whether to force close
        system: Operating system type

    Returns:
        bool: Whether the close was successful
    """
    try:
        pid = app.get("pid")
        if not pid:
            return False

        if system == "Windows":
            from .windows.killer import kill_application

            return kill_application(pid, force)
        elif system == "Darwin":  # macOS
            from .mac.killer import kill_application

            return kill_application(pid, force)
        elif system == "Linux":  # Linux
            from .linux.killer import kill_application

            return kill_application(pid, force)
        else:
            logger.error(f"[AppKiller] Unsupported operating system: {system}")
            return False

    except Exception as e:
        logger.error(f"[AppKiller] Synchronous application close failed: {e}")
        return False


def _kill_windows_app_group(
    apps: List[Dict[str, Any]], app_name: str, force: bool
) -> bool:
    """Windows system grouped close strategy.

    Args:
        apps: List of matching application processes
        app_name: Application name
        force: Whether to force close

    Returns:
        bool: Whether the close was successful
    """
    try:
        from .windows.killer import kill_application_group

        return kill_application_group(apps, app_name, force)
    except Exception as e:
        logger.error(f"[AppKiller] Windows grouped close failed: {e}")
        return False


def get_system_killer():
    """Get the killer module for the current system.

    Returns:
        The killer module for the corresponding system
    """
    system = platform.system()

    if system == "Darwin":  # macOS
        from .mac import killer

        return killer
    elif system == "Windows":  # Windows
        from .windows import killer

        return killer
    elif system == "Linux":  # Linux
        from .linux import killer

        return killer
    else:
        logger.warning(f"[AppKiller] Unsupported system: {system}")
        return None
