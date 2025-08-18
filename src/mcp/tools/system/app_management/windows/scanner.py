"""Windows Application Scanner.

Specialized for application scanning and management on Windows systems.
"""

import json
import os
import platform
import subprocess
from typing import Dict, List, Optional

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def scan_installed_applications() -> List[Dict[str, str]]:
    """Scans installed applications on a Windows system.

    Returns:
        List[Dict[str, str]]: List of applications
    """
    if platform.system() != "Windows":
        return []

    apps = []

    # 1. Scan major applications in the Start Menu (most direct method)
    try:
        logger.info("[WindowsScanner] Starting to scan major applications in the Start Menu")
        start_menu_apps = _scan_main_start_menu_apps()
        apps.extend(start_menu_apps)
        logger.info(
            f"[WindowsScanner] Scanned {len(start_menu_apps)} major applications from the Start Menu"
        )
    except Exception as e:
        logger.warning(f"[WindowsScanner] Start Menu scan failed: {e}")

    # 2. Scan major third-party applications in the registry (filtering system components)
    try:
        logger.info("[WindowsScanner] Starting to scan major installed applications")
        registry_apps = _scan_main_registry_apps()
        # Deduplication: Avoid adding applications from the Start Menu again
        existing_names = {app["display_name"].lower() for app in apps}
        for app in registry_apps:
            if app["display_name"].lower() not in existing_names:
                apps.append(app)
        logger.info(
            f"[WindowsScanner] Scanned {len([a for a in registry_apps if a['display_name'].lower() not in existing_names])} new major applications from the registry"
        )
    except Exception as e:
        logger.warning(f"[WindowsScanner] Registry scan failed: {e}")

    # 3. Add common system applications (keeping only those frequently used by users)
    system_apps = [
        {
            "name": "Calculator",
            "display_name": "Calculator",
            "path": "calc",
            "type": "system",
        },
        {
            "name": "Notepad",
            "display_name": "Notepad",
            "path": "notepad",
            "type": "system",
        },
        {"name": "Paint", "display_name": "Paint", "path": "mspaint", "type": "system"},
        {
            "name": "File Explorer",
            "display_name": "File Explorer",
            "path": "explorer",
            "type": "system",
        },
        {
            "name": "Task Manager",
            "display_name": "Task Manager",
            "path": "taskmgr",
            "type": "system",
        },
        {
            "name": "Control Panel",
            "display_name": "Control Panel",
            "path": "control",
            "type": "system",
        },
        {
            "name": "Settings",
            "display_name": "Settings",
            "path": "ms-settings:",
            "type": "system",
        },
    ]
    apps.extend(system_apps)

    logger.info(
        f"[WindowsScanner] Windows application scan completed, found a total of {len(apps)} major applications"
    )
    return apps


def scan_running_applications() -> List[Dict[str, str]]:
    """Scans running applications on a Windows system.

    Returns:
        List[Dict[str, str]]: List of running applications
    """
    if platform.system() != "Windows":
        return []

    apps = []

    try:
        # Use the tasklist command to get process information
        result = subprocess.run(
            ["tasklist", "/fo", "csv", "/v"], capture_output=True, text=True, timeout=10
        )

        if result.returncode == 0:
            lines = result.stdout.strip().split("\n")[1:]  # Skip the header line

            for line in lines:
                try:
                    # Parse CSV format
                    parts = [part.strip('"') for part in line.split('","')]
                    if len(parts) >= 8:
                        image_name = parts[0].strip('"')
                        pid = parts[1]
                        window_title = parts[8] if len(parts) > 8 else ""

                        # Filter out unnecessary processes
                        if _should_include_process(image_name, window_title):
                            display_name = _extract_app_name(image_name, window_title)
                            clean_name = _clean_app_name(display_name)

                            apps.append(
                                {
                                    "pid": int(pid),
                                    "name": clean_name,
                                    "display_name": display_name,
                                    "command": image_name,
                                    "window_title": window_title,
                                    "type": "application",
                                }
                            )
                except (ValueError, IndexError):
                    continue

        logger.info(f"[WindowsScanner] Found {len(apps)} running applications")
        return apps

    except Exception as e:
        logger.error(f"[WindowsScanner] Failed to scan running applications: {e}")
        return []


def _scan_main_start_menu_apps() -> List[Dict[str, str]]:
    """
    Scans major applications in the Start Menu (filtering out system components and utilities).
    """
    apps = []

    # Start Menu directories
    start_menu_paths = [
        os.path.join(
            os.environ.get("PROGRAMDATA", ""),
            "Microsoft",
            "Windows",
            "Start Menu",
            "Programs",
        ),
        os.path.join(
            os.environ.get("APPDATA", ""),
            "Microsoft",
            "Windows",
            "Start Menu",
            "Programs",
        ),
    ]

    for start_path in start_menu_paths:
        if os.path.exists(start_path):
            try:
                for root, dirs, files in os.walk(start_path):
                    for file in files:
                        if file.lower().endswith(".lnk"):
                            try:
                                shortcut_path = os.path.join(root, file)
                                display_name = file[:-4]  # Remove .lnk extension

                                # Filter out unnecessary applications
                                if _should_include_app(display_name):
                                    clean_name = _clean_app_name(display_name)
                                    target_path = _resolve_shortcut_target(
                                        shortcut_path
                                    )

                                    apps.append(
                                        {
                                            "name": clean_name,
                                            "display_name": display_name,
                                            "path": target_path or shortcut_path,
                                            "type": "shortcut",
                                        }
                                    )

                            except Exception as e:
                                logger.debug(
                                    f"[WindowsScanner] Failed to process shortcut {file}: {e}"
                                )

            except Exception as e:
                logger.debug(f"[WindowsScanner] Failed to scan Start Menu {start_path}: {e}")

    return apps


def _scan_main_registry_apps() -> List[Dict[str, str]]:
    """
    Scans major applications in the registry (filtering out system components).
    """
    apps = []

    try:
        powershell_cmd = [
            "powershell",
            "-Command",
            "Get-ItemProperty HKLM:\\Software\\Microsoft\\Windows\\CurrentVersion\\Uninstall\\* | "
            "Select-Object DisplayName, InstallLocation, Publisher | "
            "Where-Object {$_.DisplayName -ne $null} | "
            "ConvertTo-Json",
        ]

        result = subprocess.run(
            powershell_cmd, capture_output=True, text=True, timeout=30
        )
        if result.returncode == 0 and result.stdout:
            try:
                installed_apps = json.loads(result.stdout)
                if isinstance(installed_apps, dict):
                    installed_apps = [installed_apps]

                for app in installed_apps:
                    display_name = app.get("DisplayName", "")
                    publisher = app.get("Publisher", "")

                    if display_name and _should_include_app(display_name, publisher):
                        clean_name = _clean_app_name(display_name)
                        apps.append(
                            {
                                "name": clean_name,
                                "display_name": display_name,
                                "path": app.get("InstallLocation", ""),
                                "type": "installed",
                            }
                        )

            except json.JSONDecodeError:
                logger.warning("[WindowsScanner] Failed to parse PowerShell output")

    except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
        logger.warning(f"[WindowsScanner] PowerShell scan failed: {e}")

    return apps


def _should_include_app(display_name: str, publisher: str = "") -> bool:
    """Determines whether the application should be included.

    Args:
        display_name: Application display name
        publisher: Publisher (optional)

    Returns:
        bool: Whether it should be included
    """
    name_lower = display_name.lower()

    # Explicitly excluded system components and runtimes
    exclude_keywords = [
        # Microsoft system components
        "microsoft visual c++",
        "microsoft .net",
        "microsoft office",
        "microsoft edge webview",
        "microsoft visual studio",
        "microsoft redistributable",
        "microsoft windows sdk",
        # System tools and drivers
        "uninstall",
        "readme",
        "help",
        "documentation",
        "driver",
        "update",
        "hotfix",
        "patch",
        # Developer tool components
        "development",
        "sdk",
        "runtime",
        "redistributable",
        "framework",
        "python documentation",
        "python test suite",
        "python executables",
        "java update",
        "java development kit",
        # System services
        "service pack",
        "security update",
        "language pack",
        # Useless shortcuts
        "website",
        "web site",
        "online",
        "report",
        "feedback",
    ]

    # Check if it contains exclusion keywords
    for keyword in exclude_keywords:
        if keyword in name_lower:
            return False

    # Explicitly included well-known applications
    include_keywords = [
        # Browsers
        "chrome",
        "firefox",
        "edge",
        "safari",
        "opera",
        "brave",
        # Office software
        "office",
        "word",
        "excel",
        "powerpoint",
        "outlook",
        "onenote",
        "wps",
        "typora",
        "notion",
        "obsidian",
        # Developer tools
        "visual studio code",
        "vscode",
        "pycharm",
        "idea",
        "eclipse",
        "git",
        "docker",
        "nodejs",
        "android studio",
        # Communication software
        "qq",
        "wechat",
        "skype",
        "zoom",
        "teams",
        "feishu",
        "discord",
        "slack",
        "telegram",
        # Media software
        "vlc",
        "potplayer",
        "netease cloud music",
        "spotify",
        "itunes",
        "photoshop",
        "premiere",
        "after effects",
        "illustrator",
        # Gaming platforms
        "steam",
        "epic",
        "origin",
        "uplay",
        "battlenet",
        # Utility tools
        "7-zip",
        "winrar",
        "bandizip",
        "everything",
        "listary",
        "notepad++",
        "sublime",
        "atom",
    ]

    # Check if it contains explicitly included keywords
    for keyword in include_keywords:
        if keyword in name_lower:
            return True

    # If there is publisher information, exclude system components published by Microsoft
    if publisher:
        publisher_lower = publisher.lower()
        if "microsoft corporation" in publisher_lower and any(
            x in name_lower
            for x in [
                "visual c++",
                ".net",
                "redistributable",
                "runtime",
                "framework",
                "update",
            ]
        ):
            return False

    # By default, include other applications (assuming they are user-installed)
    # But exclude obvious system components
    system_indicators = ["(x64)", "(x86)", "redistributable", "runtime", "framework"]
    if any(indicator in name_lower for indicator in system_indicators):
        return False

    return True


def _should_include_process(image_name: str, window_title: str) -> bool:
    """Determines whether the process should be included.

    Args:
        image_name: Process image name
        window_title: Window title

    Returns:
        bool: Whether to include
    """
    # Exclude system processes
    system_processes = {
        "dwm.exe",
        "winlogon.exe",
        "csrss.exe",
        "smss.exe",
        "lsass.exe",
        "services.exe",
        "svchost.exe",
        "explorer.exe",
        "taskhostw.exe",
        "conhost.exe",
        "dllhost.exe",
        "rundll32.exe",
        "msiexec.exe",
        "wininit.exe",
        "lsm.exe",
        "spoolsv.exe",
        "audiodg.exe",
    }

    image_lower = image_name.lower()

    # Exclude system processes
    if image_lower in system_processes:
        return False

    # Exclude processes without a window title (usually background services)
    if not window_title or window_title == "N/A":
        return False

    # Only include meaningful window titles
    if len(window_title.strip()) < 3:
        return False

    return True


def _extract_app_name(image_name: str, window_title: str) -> str:
    """Extracts the application name from the process information.

    Args:
        image_name: Process image name
        window_title: Window title

    Returns:
        str: Application name
    """
    # Prioritize using the window title
    if window_title and window_title != "N/A" and len(window_title.strip()) > 0:
        return window_title.strip()

    # Use the process name (remove .exe suffix)
    if image_name.lower().endswith(".exe"):
        return image_name[:-4]

    return image_name


def _resolve_shortcut_target(shortcut_path: str) -> Optional[str]:
    """Resolves the target path of a Windows shortcut.

    Args:
        shortcut_path: Shortcut file path

    Returns:
        The target path, or None if resolution fails
    """
    try:
        import win32com.client

        shell = win32com.client.Dispatch("WScript.Shell")
        shortcut = shell.CreateShortCut(shortcut_path)
        target_path = shortcut.Targetpath

        if target_path and os.path.exists(target_path):
            return target_path

    except ImportError:
        logger.debug("[WindowsScanner] win32com module is not available, cannot resolve shortcuts")
    except Exception as e:
        logger.debug(f"[WindowsScanner] Failed to resolve shortcut: {e}")

    return None


def _clean_app_name(name: str) -> str:
    """Cleans the application name, removing version numbers and special characters.

    Args:
        name: Original name

    Returns:
        str: Cleaned name
    """
    if not name:
        return ""

    # Remove common version number patterns
    import re

    # Remove version numbers (e.g., "App 1.0", "App v2.1", "App (2023)")
    name = re.sub(r"\s+v?\d+[\.\d]*", "", name)
    name = re.sub(r"\s*\(\d+\)", "", name)
    name = re.sub(r"\s*\[.*?\]", "", name)

    # Remove extra spaces
    name = " ".join(name.split())

    return name.strip()
