"""
Presence Manager - Tracks user presence for Away/Receptionist mode.

Detects user absence via:
- Manual away toggle (button or voice command)
- System idle time (no mouse/keyboard input)
- Screen lock detection (Windows)
"""

import ctypes
import platform
import threading
import time

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class PresenceManager:
    """
    Manages user presence state and triggers away/return callbacks.
    """

    _instance = None

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            cls._instance = PresenceManager()
        return cls._instance

    def __init__(self, idle_timeout: float = 600.0):
        self._away = False
        self._manual_away = False
        self._idle_timeout = idle_timeout  # seconds before auto-away
        self._on_away_callbacks = []
        self._on_return_callbacks = []
        self._monitor_thread = None
        self._running = False
        self._away_since: float = 0
        self._user_name = "the user"

    @property
    def is_away(self) -> bool:
        return self._away

    @property
    def away_duration(self) -> float:
        if not self._away:
            return 0
        return time.time() - self._away_since

    @property
    def away_duration_str(self) -> str:
        duration = self.away_duration
        if duration < 60:
            return "just now"
        elif duration < 3600:
            return f"{int(duration / 60)} minutes ago"
        else:
            return f"{int(duration / 3600)} hours ago"

    @property
    def user_name(self) -> str:
        return self._user_name

    @user_name.setter
    def user_name(self, name: str):
        self._user_name = name

    def on_away(self, callback):
        """Register a callback for when user goes away."""
        self._on_away_callbacks.append(callback)

    def on_return(self, callback):
        """Register a callback for when user returns."""
        self._on_return_callbacks.append(callback)

    def set_away(self, manual: bool = True):
        """Set status to away."""
        if self._away:
            return
        self._away = True
        self._manual_away = manual
        self._away_since = time.time()
        logger.info(f"User is now away (manual={manual})")
        for cb in self._on_away_callbacks:
            try:
                cb()
            except Exception as e:
                logger.error(f"Error in away callback: {e}")

    def set_present(self):
        """Set status to present (back at desk)."""
        if not self._away:
            return
        duration = self.away_duration_str
        self._away = False
        self._manual_away = False
        logger.info(f"User is back (was away {duration})")
        for cb in self._on_return_callbacks:
            try:
                cb()
            except Exception as e:
                logger.error(f"Error in return callback: {e}")

    def toggle_away(self):
        """Toggle away status."""
        if self._away:
            self.set_present()
        else:
            self.set_away(manual=True)

    def start_monitoring(self):
        """Start monitoring for idle/screen lock."""
        if self._running:
            return
        self._running = True
        self._monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._monitor_thread.start()
        logger.info(f"Presence monitoring started (idle timeout: {self._idle_timeout}s)")

    def stop_monitoring(self):
        """Stop monitoring."""
        self._running = False
        if self._monitor_thread:
            self._monitor_thread.join(timeout=2.0)
        logger.info("Presence monitoring stopped")

    def _monitor_loop(self):
        """Monitor loop checking idle time."""
        while self._running:
            try:
                idle_seconds = self._get_idle_time()

                if idle_seconds is not None:
                    if not self._away and idle_seconds > self._idle_timeout:
                        logger.info(f"User idle for {idle_seconds:.0f}s, auto-setting away")
                        self.set_away(manual=False)
                    elif self._away and not self._manual_away and idle_seconds < 5:
                        # Auto-return if they were auto-away and are now active
                        logger.info("User activity detected, auto-returning from away")
                        self.set_present()

            except Exception as e:
                logger.error(f"Error in presence monitor: {e}")

            time.sleep(10)  # Check every 10 seconds

    def _get_idle_time(self) -> float:
        """Get system idle time in seconds."""
        system = platform.system()

        if system == "Windows":
            return self._get_idle_time_windows()
        elif system == "Darwin":
            return self._get_idle_time_macos()
        elif system == "Linux":
            return self._get_idle_time_linux()

        return None

    def _get_idle_time_windows(self) -> float:
        """Get idle time on Windows using GetLastInputInfo."""
        try:
            class LASTINPUTINFO(ctypes.Structure):
                _fields_ = [
                    ("cbSize", ctypes.c_uint),
                    ("dwTime", ctypes.c_uint),
                ]

            lii = LASTINPUTINFO()
            lii.cbSize = ctypes.sizeof(LASTINPUTINFO)
            ctypes.windll.user32.GetLastInputInfo(ctypes.byref(lii))
            tick_count = ctypes.windll.kernel32.GetTickCount()
            idle_ms = tick_count - lii.dwTime
            return idle_ms / 1000.0
        except Exception as e:
            logger.debug(f"Failed to get Windows idle time: {e}")
            return None

    def _get_idle_time_macos(self) -> float:
        """Get idle time on macOS."""
        try:
            import subprocess
            result = subprocess.run(
                ["ioreg", "-c", "IOHIDSystem"],
                capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split("\n"):
                if "HIDIdleTime" in line:
                    # Value is in nanoseconds
                    ns = int(line.split("=")[-1].strip())
                    return ns / 1_000_000_000.0
        except Exception as e:
            logger.debug(f"Failed to get macOS idle time: {e}")
        return None

    def _get_idle_time_linux(self) -> float:
        """Get idle time on Linux using xprintidle."""
        try:
            import subprocess
            result = subprocess.run(
                ["xprintidle"],
                capture_output=True, text=True, timeout=5
            )
            return int(result.stdout.strip()) / 1000.0
        except Exception:
            return None

    def get_greeting(self) -> str:
        """Get the greeting message for visitors when user is away."""
        return (
            f"Hi there! {self._user_name} stepped away from their desk "
            f"{self.away_duration_str}. I'm their AI assistant. "
            f"I can take a message for them, or is there something I can help you with?"
        )
