"""Windows system application killer.

Provides application closing functionality for the Windows platform.
"""

import json
import subprocess
from typing import Any, Dict, List

from src.utils.logging_config import get_logger

from ..utils import AppMatcher

logger = get_logger(__name__)


def list_running_applications(filter_name: str = "") -> List[Dict[str, Any]]:
    """
    List running applications on Windows.
    """
    apps = []

    # Method 1: Use optimized PowerShell scan (preferred, fastest, and most accurate)
    try:
        logger.debug("[WindowsKiller] Scanning processes using optimized PowerShell")
        # More concise and efficient PowerShell script
        powershell_script = """
        Get-Process | Where-Object {
            $_.ProcessName -notmatch '^(dwm|winlogon|csrss|smss|wininit|services|lsass|svchost|spoolsv|taskhostw|explorer|fontdrvhost|dllhost|conhost|sihost|runtimebroker)$' -and
            ($_.MainWindowTitle -or $_.ProcessName -match '(chrome|firefox|edge|qq|wechat|notepad|calc|typora|vscode|pycharm|feishu|qqmusic)')
        } | Select-Object Id, ProcessName, MainWindowTitle, Path | ConvertTo-Json
        """

        result = subprocess.run(
            ["powershell", "-Command", powershell_script],
            capture_output=True,
            text=True,
            timeout=8,
        )

        if result.returncode == 0 and result.stdout.strip():
            try:
                process_data = json.loads(result.stdout)
                if isinstance(process_data, dict):
                    process_data = [process_data]

                for proc in process_data:
                    proc_name = proc.get("ProcessName", "")
                    pid = proc.get("Id", 0)
                    window_title = proc.get("MainWindowTitle", "")
                    exe_path = proc.get("Path", "")

                    if proc_name and pid:
                        # Apply filter conditions
                        if not filter_name or _matches_process_name(
                            filter_name, proc_name, window_title, exe_path
                        ):
                            apps.append(
                                {
                                    "pid": int(pid),
                                    "name": proc_name,
                                    "display_name": f"{proc_name}.exe",
                                    "command": exe_path or f"{proc_name}.exe",
                                    "window_title": window_title,
                                    "type": "application",
                                }
                            )

                if apps:
                    logger.info(
                        f"[WindowsKiller] PowerShell scan successful, found {len(apps)} processes"
                    )
                    return _deduplicate_and_sort_apps(apps)

            except json.JSONDecodeError as e:
                logger.debug(f"[WindowsKiller] PowerShell JSON parsing failed: {e}")

    except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
        logger.warning(f"[WindowsKiller] PowerShell process scan failed: {e}")

    # Method 2: Use simplified tasklist command (alternative)
    if not apps:
        try:
            logger.debug("[WindowsKiller] Using simplified tasklist command")
            result = subprocess.run(
                ["tasklist", "/fo", "csv"],
                capture_output=True,
                text=True,
                timeout=5,
                encoding="gbk",
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")[1:]  # Skip header line

                for line in lines:
                    try:
                        # Parse CSV format
                        parts = [p.strip('"') for p in line.split('","')]
                        if len(parts) >= 2:
                            image_name = parts[0]
                            pid = parts[1]

                            # Basic filtering
                            if not image_name.lower().endswith(".exe"):
                                continue

                            app_name = image_name.replace(".exe", "")

                            # Filter system processes
                            if _is_system_process(app_name):
                                continue

                            # Apply filter conditions
                            if not filter_name or _matches_process_name(
                                filter_name, app_name, "", image_name
                            ):
                                apps.append(
                                    {
                                        "pid": int(pid),
                                        "name": app_name,
                                        "display_name": image_name,
                                        "command": image_name,
                                        "type": "application",
                                    }
                                )
                    except (ValueError, IndexError):
                        continue

            if apps:
                logger.info(
                    f"[WindowsKiller] tasklist scan successful, found {len(apps)} processes"
                )
                return _deduplicate_and_sort_apps(apps)

        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            logger.warning(f"[WindowsKiller] tasklist command failed: {e}")

    # Method 3: Use wmic as a last resort
    if not apps:
        try:
            logger.debug("[WindowsKiller] Using wmic command")
            result = subprocess.run(
                [
                    "wmic",
                    "process",
                    "get",
                    "ProcessId,Name,ExecutablePath",
                    "/format:csv",
                ],
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                lines = result.stdout.strip().split("\n")[1:]  # Skip header line

                for line in lines:
                    parts = line.split(",")
                    if len(parts) >= 3:
                        try:
                            exe_path = parts[1].strip() if len(parts) > 1 else ""
                            name = parts[2].strip() if len(parts) > 2 else ""
                            pid = parts[3].strip() if len(parts) > 3 else ""

                            if name.lower().endswith(".exe") and pid.isdigit():
                                app_name = name.replace(".exe", "")

                                if _is_system_process(app_name):
                                    continue

                                # Apply filter conditions
                                if not filter_name or _matches_process_name(
                                    filter_name, app_name, "", exe_path
                                ):
                                    apps.append(
                                        {
                                            "pid": int(pid),
                                            "name": app_name,
                                            "display_name": name,
                                            "command": exe_path or name,
                                            "type": "application",
                                        }
                                    )
                        except (ValueError, IndexError):
                            continue

        except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
            logger.warning(f"[WindowsKiller] wmic process scan failed: {e}")

    return _deduplicate_and_sort_apps(apps)


def kill_application_group(
    apps: List[Dict[str, Any]], app_name: str, force: bool
) -> bool:
    """Close Windows applications by group.

    Args:
        apps: List of matching application processes
        app_name: Application name
        force: Whether to force close

    Returns:
        bool: Whether the closing was successful
    """
    try:
        logger.info(
            f"[WindowsKiller] Starting to close Windows application by group: {app_name}, found {len(apps)} related processes"
        )

        # 1. First, try to close by application name as a whole (recommended method)
        success = _kill_by_image_name(apps, force)
        if success:
            logger.info(f"[WindowsKiller] Successfully closed as a whole by application name: {app_name}")
            return True

        # 2. If closing as a whole fails, try smart group closing
        success = _kill_by_process_groups(apps, force)
        if success:
            logger.info(f"[WindowsKiller] Successfully closed by process group: {app_name}")
            return True

        # 3. Finally, try to close one by one (fallback solution)
        success = _kill_individual_processes(apps, force)
        logger.info(f"[WindowsKiller] Closing one by one completed: {app_name}, success: {success}")
        return success

    except Exception as e:
        logger.error(f"[WindowsKiller] Windows group closing failed: {e}")
        return False


def kill_application(pid: int, force: bool) -> bool:
    """
    Close a single application on Windows.
    """
    try:
        logger.info(
            f"[WindowsKiller] Attempting to close Windows application, PID: {pid}, Force close: {force}"
        )

        if force:
            # Force close
            result = subprocess.run(
                ["taskkill", "/PID", str(pid), "/F"],
                capture_output=True,
                text=True,
                timeout=10,
            )
        else:
            # Normal close
            result = subprocess.run(
                ["taskkill", "/PID", str(pid)],
                capture_output=True,
                text=True,
                timeout=10,
            )

        success = result.returncode == 0

        if success:
            logger.info(f"[WindowsKiller] Successfully closed application, PID: {pid}")
        else:
            logger.warning(
                f"[WindowsKiller] Failed to close application, PID: {pid}, Error message: {result.stderr}"
            )

        return success

    except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
        logger.error(f"[WindowsKiller] Exception when closing Windows application, PID: {pid}, Error: {e}")
        return False


def _matches_process_name(
    filter_name: str, proc_name: str, window_title: str = "", exe_path: str = ""
) -> bool:
    """
    Smartly match process name.
    """
    try:
        # Construct application information object
        app_info = {
            "name": proc_name,
            "display_name": proc_name,
            "window_title": window_title,
            "command": exe_path,
        }

        # Use a unified matcher, a match score greater than 30 is considered a match
        score = AppMatcher.match_application(filter_name, app_info)
        return score >= 30

    except Exception:
        # Fallback simplified implementation
        filter_lower = filter_name.lower()
        proc_lower = proc_name.lower()

        return (
            filter_lower == proc_lower
            or filter_lower in proc_lower
            or (bool(window_title) and filter_lower in window_title.lower())
        )


def _is_system_process(proc_name: str) -> bool:
    """
    Determine if it is a system process.
    """
    system_processes = {
        "dwm",
        "winlogon",
        "csrss",
        "smss",
        "wininit",
        "services",
        "lsass",
        "svchost",
        "spoolsv",
        "explorer",
        "taskhostw",
        "fontdrvhost",
        "dllhost",
        "ctfmon",
        "audiodg",
        "conhost",
        "sihost",
        "shellexperiencehost",
        "startmenuexperiencehost",
        "runtimebroker",
        "applicationframehost",
        "searchui",
        "cortana",
        "useroobebroker",
        "lockapp",
    }

    return proc_name.lower() in system_processes


def _deduplicate_and_sort_apps(apps: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Deduplicate and sort the application list.
    """
    # Deduplicate by PID
    seen_pids = set()
    unique_apps = []
    for app in apps:
        if app["pid"] not in seen_pids:
            seen_pids.add(app["pid"])
            unique_apps.append(app)

    # Sort by name
    unique_apps.sort(key=lambda x: x["name"].lower())

    logger.info(
        f"[WindowsKiller] Process scan completed, found {len(unique_apps)} applications after deduplication"
    )
    return unique_apps


def _kill_by_image_name(apps: List[Dict[str, Any]], force: bool) -> bool:
    """
    Close applications as a whole by image name.
    """
    try:
        # Get the main process names
        image_names = set()
        for app in apps:
            name = app.get("name", "")
            if name:
                # Uniformly add .exe suffix
                if not name.lower().endswith(".exe"):
                    name += ".exe"
                image_names.add(name)

        if not image_names:
            return False

        logger.info(f"[WindowsKiller] Attempting to close by image name: {list(image_names)}")

        # Close by image name
        success_count = 0
        for image_name in image_names:
            try:
                if force:
                    cmd = ["taskkill", "/IM", image_name, "/F", "/T"]  # /T closes the child process tree
                else:
                    cmd = ["taskkill", "/IM", image_name, "/T"]

                result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)

                if result.returncode == 0:
                    success_count += 1
                    logger.info(f"[WindowsKiller] Successfully closed image: {image_name}")
                else:
                    logger.debug(
                        f"[WindowsKiller] Failed to close image: {image_name}, Error: {result.stderr}"
                    )

            except (subprocess.TimeoutExpired, subprocess.SubprocessError) as e:
                logger.debug(f"[WindowsKiller] Exception when closing image: {image_name}, Error: {e}")

        return success_count > 0

    except Exception as e:
        logger.debug(f"[WindowsKiller] Exception when closing by image name: {e}")
        return False


def _kill_by_process_groups(apps: List[Dict[str, Any]], force: bool) -> bool:
    """
    Smartly close applications by process group.
    """
    try:
        # Group by process name
        process_groups = {}
        for app in apps:
            name = app.get("name", "")
            if name:
                base_name = _get_base_process_name(name)
                if base_name not in process_groups:
                    process_groups[base_name] = []
                process_groups[base_name].append(app)

        logger.info(
            f"[WindowsKiller] Identified {len(process_groups)} process groups: {list(process_groups.keys())}"
        )

        # Identify and close the main process for each group
        success_count = 0
        for group_name, group_apps in process_groups.items():
            try:
                # Find the main process (usually the one with the smallest PPID or with a window title)
                main_process = _find_main_process(group_apps)

                if main_process:
                    # Close the main process (will also close child processes)
                    pid = main_process.get("pid")
                    if pid:
                        success = kill_application(pid, force)
                        if success:
                            success_count += 1
                            logger.info(
                                f"[WindowsKiller] Successfully closed the main process of group {group_name} (PID: {pid})"
                            )
                        else:
                            # If closing the main process fails, try to close all processes in the group
                            for app in group_apps:
                                if kill_application(app.get("pid"), force):
                                    success_count += 1

            except Exception as e:
                logger.debug(f"[WindowsKiller] Failed to close process group: {group_name}, Error: {e}")

        return success_count > 0

    except Exception as e:
        logger.debug(f"[WindowsKiller] Exception when closing by process group: {e}")
        return False


def _kill_individual_processes(apps: List[Dict[str, Any]], force: bool) -> bool:
    """
    Close processes one by one (fallback solution).
    """
    try:
        logger.info(f"[WindowsKiller] Starting to close {len(apps)} processes one by one")

        success_count = 0
        for app in apps:
            pid = app.get("pid")
            if pid:
                success = kill_application(pid, force)
                if success:
                    success_count += 1
                    logger.debug(
                        f"[WindowsKiller] Successfully closed process: {app.get('name')} (PID: {pid})"
                    )

        logger.info(
            f"[WindowsKiller] Closing one by one completed, successfully closed {success_count}/{len(apps)} processes"
        )
        return success_count > 0

    except Exception as e:
        logger.error(f"[WindowsKiller] Exception when closing one by one: {e}")
        return False


def _get_base_process_name(process_name: str) -> str:
    """
    Get the base process name (for grouping).
    """
    try:
        return AppMatcher.get_process_group(process_name)
    except Exception:
        # Fallback implementation
        name = process_name.lower().replace(".exe", "")
        if "chrome" in name:
            return "chrome"
        elif "qq" in name and "music" not in name:
            return "qq"
        return name


def _find_main_process(processes: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Find the main process in a process group.
    """
    if not processes:
        return {}

    # Strategy 1: A process with a window title is usually the main process
    for proc in processes:
        window_title = proc.get("window_title", "")
        if window_title and window_title.strip():
            return proc

    # Strategy 2: The process with the smallest PPID (usually the parent process)
    try:
        main_proc = min(processes, key=lambda p: p.get("ppid", p.get("pid", 999999)))
        return main_proc
    except (ValueError, TypeError):
        pass

    # Strategy 3: The process with the smallest PID
    try:
        main_proc = min(processes, key=lambda p: p.get("pid", 999999))
        return main_proc
    except (ValueError, TypeError):
        pass

    # Fallback: return the first process
    return processes[0]
