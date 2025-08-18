"""Windows System Application Launcher.

Provides application launching functionality on the Windows platform.
"""

import os
import subprocess
from typing import Optional

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


def launch_application(app_name: str) -> bool:
    """Launches an application on Windows.

    Args:
        app_name: Application name

    Returns:
        bool: Whether the launch was successful
    """
    try:
        logger.info(f"[WindowsLauncher] Launching application: {app_name}")

        # Try different launch methods in order of priority
        launch_methods = [
            ("PowerShell Start-Process", _try_powershell_start),
            ("start command", _try_start_command),
            ("os.startfile", _try_os_startfile),
            ("Registry search", _try_registry_launch),
            ("Common paths", _try_common_paths),
            ("where command", _try_where_command),
            ("UWP app", _try_uwp_launch),
        ]

        for method_name, method_func in launch_methods:
            try:
                if method_func(app_name):
                    logger.info(f"[WindowsLauncher] {method_name} successfully launched: {app_name}")
                    return True
                else:
                    logger.debug(f"[WindowsLauncher] {method_name} failed to launch: {app_name}")
            except Exception as e:
                logger.debug(f"[WindowsLauncher] {method_name} exception: {e}")

        logger.warning(f"[WindowsLauncher] All Windows launch methods failed for: {app_name}")
        return False

    except Exception as e:
        logger.error(f"[WindowsLauncher] Windows launch exception: {e}", exc_info=True)
        return False


def launch_uwp_app_by_path(uwp_path: str) -> bool:
    """Launches an application via its UWP path.

    Args:
        uwp_path: UWP application path (shell:AppsFolder\\... format)

    Returns:
        bool: Whether the launch was successful
    """
    try:
        if uwp_path.startswith("shell:AppsFolder\\"):
            # Use explorer to launch UWP app
            subprocess.Popen(["explorer.exe", uwp_path])
            logger.info(f"[WindowsLauncher] UWP app launched successfully: {uwp_path}")
            return True
        else:
            return False
    except Exception as e:
        logger.error(f"[WindowsLauncher] UWP app launch failed: {e}")
        return False


def launch_shortcut(shortcut_path: str) -> bool:
    """Launches a shortcut file.

    Args:
        shortcut_path: Shortcut file path

    Returns:
        bool: Whether the launch was successful
    """
    try:
        os.startfile(shortcut_path)
        logger.info(f"[WindowsLauncher] Shortcut launched successfully: {shortcut_path}")
        return True
    except Exception as e:
        logger.error(f"[WindowsLauncher] Shortcut launch failed: {e}")
        return False


def _try_powershell_start(app_name: str) -> bool:
    """
    Tries to launch an application using PowerShell Start-Process.
    """
    try:
        escaped_name = app_name.replace('"', '""').replace("'", "''")
        powershell_cmd = f"powershell -Command \"Start-Process '{escaped_name}'\""
        result = subprocess.run(
            powershell_cmd, shell=True, capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


def _try_start_command(app_name: str) -> bool:
    """
    Tries to launch an application using the start command.
    """
    try:
        start_cmd = f'start "" "{app_name}"'
        result = subprocess.run(
            start_cmd, shell=True, capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False


def _try_os_startfile(app_name: str) -> bool:
    """
    Tries to launch an application using os.startfile.
    """
    try:
        os.startfile(app_name)
        return True
    except OSError:
        return False


def _try_registry_launch(app_name: str) -> bool:
    """
    Tries to find and launch an application via the registry.
    """
    try:
        executable_path = _find_executable_in_registry(app_name)
        if executable_path:
            subprocess.Popen([executable_path])
            return True
    except Exception:
        pass
    return False


def _try_common_paths(app_name: str) -> bool:
    """
    Tries common application paths.
    """
    common_paths = [
        f"C:\\Program Files\\{app_name}\\{app_name}.exe",
        f"C:\\Program Files (x86)\\{app_name}\\{app_name}.exe",
        f"C:\\Users\\{os.getenv('USERNAME')}\\AppData\\Local\\Programs\\{app_name}\\{app_name}.exe",
        f"C:\\Users\\{os.getenv('USERNAME')}\\AppData\\Local\\{app_name}\\{app_name}.exe",
        f"C:\\Users\\{os.getenv('USERNAME')}\\AppData\\Roaming\\{app_name}\\{app_name}.exe",
    ]

    for path in common_paths:
        if os.path.exists(path):
            try:
                subprocess.Popen([path])
                return True
            except Exception:
                continue
    return False


def _try_where_command(app_name: str) -> bool:
    """
    Tries to find and launch an application using the where command.
    """
    try:
        result = subprocess.run(
            f"where {app_name}", shell=True, capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            exe_path = result.stdout.strip().split("\n")[0]  # Take the first result
            if exe_path and os.path.exists(exe_path):
                subprocess.Popen([exe_path])
                return True
    except Exception:
        pass
    return False


def _try_uwp_launch(app_name: str) -> bool:
    """
    Tries to launch a UWP application.
    """
    try:
        return _launch_uwp_app(app_name)
    except Exception:
        return False


def _find_executable_in_registry(app_name: str) -> Optional[str]:
    """Finds the executable path of an application through the registry.

    Args:
        app_name: Application name

    Returns:
        The application path, or None if not found
    """
    try:
        import winreg

        # Find uninstall information in the registry
        registry_paths = [
            r"SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall",
            r"SOFTWARE\WOW6432Node\Microsoft\Windows\CurrentVersion\Uninstall",
        ]

        for registry_path in registry_paths:
            try:
                with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, registry_path) as key:
                    for i in range(winreg.QueryInfoKey(key)[0]):
                        try:
                            subkey_name = winreg.EnumKey(key, i)
                            with winreg.OpenKey(key, subkey_name) as subkey:
                                try:
                                    display_name = winreg.QueryValueEx(
                                        subkey, "DisplayName"
                                    )[0]
                                    if app_name.lower() in display_name.lower():
                                        try:
                                            install_location = winreg.QueryValueEx(
                                                subkey, "InstallLocation"
                                            )[0]
                                            if install_location and os.path.exists(
                                                install_location
                                            ):
                                                # Find the main executable file
                                                for root, dirs, files in os.walk(
                                                    install_location
                                                ):
                                                    for file in files:
                                                        if (
                                                            file.lower().endswith(
                                                                ".exe"
                                                            )
                                                            and app_name.lower()
                                                            in file.lower()
                                                        ):
                                                            return os.path.join(
                                                                root, file
                                                            )
                                        except FileNotFoundError:
                                            pass

                                        try:
                                            display_icon = winreg.QueryValueEx(
                                                subkey, "DisplayIcon"
                                            )[0]
                                            if (
                                                display_icon
                                                and display_icon.endswith(".exe")
                                                and os.path.exists(display_icon)
                                            ):
                                                return display_icon
                                        except FileNotFoundError:
                                            pass

                                except FileNotFoundError:
                                    continue
                        except Exception:
                            continue
            except Exception:
                continue

        return None

    except ImportError:
        logger.debug("[WindowsLauncher] winreg module is not available, skipping registry search")
        return None
    except Exception as e:
        logger.debug(f"[WindowsLauncher] Registry search failed: {e}")
        return None


def _launch_uwp_app(app_name: str) -> bool:
    """Tries to launch a UWP (Windows Store) application.

    Args:
        app_name: Application name

    Returns:
        bool: Whether the launch was successful
    """
    try:
        # Use PowerShell to find and launch the UWP app
        powershell_script = f"""
        $app = Get-AppxPackage | Where-Object {{$_.Name -like "*{app_name}*" -or $_.PackageFullName -like "*{app_name}*"}} | Select-Object -First 1
        if ($app) {{
            $manifest = Get-AppxPackageManifest $app.PackageFullName
            $appId = $manifest.Package.Applications.Application.Id
            if ($appId) {{
                Start-Process "shell:AppsFolder\\$($app.PackageFullName)!$appId"
                Write-Output "Success"
            }}
        }}
        """

        result = subprocess.run(
            ["powershell", "-Command", powershell_script],
            capture_output=True,
            text=True,
            timeout=15,
        )

        if result.returncode == 0 and "Success" in result.stdout:
            return True

    except Exception as e:
        logger.debug(f"[WindowsLauncher] UWP launch exception: {e}")

    return False
