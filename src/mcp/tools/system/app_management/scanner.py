"""Unified application scanner entry point.

Automatically selects the appropriate scanner implementation based on the current system.
"""

import asyncio
import json
from typing import Any, Dict

from src.utils.logging_config import get_logger

from .utils import get_system_scanner

logger = get_logger(__name__)


async def scan_installed_applications(args: Dict[str, Any]) -> str:
    """Scan all installed applications on the system.

    Args:
        args: Dictionary containing scan parameters
            - force_refresh: Whether to force re-scan (optional, defaults to False)

    Returns:
        str: JSON-formatted application list
    """
    try:
        force_refresh = args.get("force_refresh", False)
        logger.info(f"[AppScanner] Starting to scan installed applications, force refresh: {force_refresh}")

        # Get the scanner for the current system
        scanner = get_system_scanner()
        if not scanner:
            error_msg = "Unsupported operating system"
            logger.error(f"[AppScanner] {error_msg}")
            return json.dumps(
                {
                    "success": False,
                    "total_count": 0,
                    "applications": [],
                    "message": error_msg,
                },
                ensure_ascii=False,
            )

        # Use thread pool for scanning to avoid blocking the event loop
        apps = await asyncio.to_thread(scanner.scan_installed_applications)

        result = {
            "success": True,
            "total_count": len(apps),
            "applications": apps,
            "message": f"Successfully scanned {len(apps)} installed applications",
        }

        logger.info(f"[AppScanner] Scan complete, found {len(apps)} applications")
        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        error_msg = f"Failed to scan applications: {str(e)}"
        logger.error(f"[AppScanner] {error_msg}", exc_info=True)
        return json.dumps(
            {
                "success": False,
                "total_count": 0,
                "applications": [],
                "message": error_msg,
            },
            ensure_ascii=False,
        )


async def list_running_applications(args: Dict[str, Any]) -> str:
    """List currently running applications on the system.

    Args:
        args: Dictionary containing filter parameters
            - filter_name: Application name filter (optional)

    Returns:
        str: JSON-formatted list of running applications
    """
    try:
        filter_name = args.get("filter_name", "")
        logger.info(f"[AppScanner] Starting to list running applications, filter: {filter_name}")

        # Get the scanner for the current system
        scanner = get_system_scanner()
        if not scanner:
            error_msg = "Unsupported operating system"
            logger.error(f"[AppScanner] {error_msg}")
            return json.dumps(
                {
                    "success": False,
                    "total_count": 0,
                    "applications": [],
                    "message": error_msg,
                },
                ensure_ascii=False,
            )

        # Use thread pool for scanning to avoid blocking the event loop
        apps = await asyncio.to_thread(scanner.scan_running_applications)

        # Apply filter conditions
        if filter_name:
            filter_lower = filter_name.lower()
            filtered_apps = []
            for app in apps:
                if (
                    filter_lower in app.get("name", "").lower()
                    or filter_lower in app.get("display_name", "").lower()
                    or filter_lower in app.get("command", "").lower()
                ):
                    filtered_apps.append(app)
            apps = filtered_apps

        result = {
            "success": True,
            "total_count": len(apps),
            "applications": apps,
            "message": f"Found {len(apps)} running applications",
        }

        logger.info(f"[AppScanner] Listing complete, found {len(apps)} running applications")
        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        error_msg = f"Failed to list running applications: {str(e)}"
        logger.error(f"[AppScanner] {error_msg}", exc_info=True)
        return json.dumps(
            {
                "success": False,
                "total_count": 0,
                "applications": [],
                "message": error_msg,
            },
            ensure_ascii=False,
        )
