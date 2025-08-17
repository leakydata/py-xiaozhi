import asyncio
import time
from dataclasses import dataclass
from typing import Dict, Optional, Set

from src.constants.constants import AbortReason
from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class ShortcutConfig:
    """
    Shortcut configuration data class.
    """

    modifier: str
    key: str
    description: str


class ShortcutManager:
    """
    Global shortcut manager.
    """

    def __init__(self):
        """
        Initialize the shortcut manager.
        """
        self.config = ConfigManager.get_instance()
        self.shortcuts_config = self.config.get_config("SHORTCUTS", {})
        self.enabled = self.shortcuts_config.get("ENABLED", True)

        # Internal state
        self.pressed_keys: Set[str] = set()
        self.manual_press_active = False
        self.running = False
        
        # Key state tracking
        self.key_states = {
            "MANUAL_PRESS": False,  # Hold-to-talk state
            "last_manual_press_time": 0,  # Last trigger time
            "ABORT": False  # Interrupt state
        }

        # Windows key mapping
        self.key_mapping = {
            '\x17': 'w',  # Ctrl+W
            '\x01': 'a',  # Ctrl+A 
            '\x13': 's',  # Ctrl+S
            '\x04': 'd',  # Ctrl+D
            '\x05': 'e',  # Ctrl+E
            '\x12': 'r',  # Ctrl+R
            '\x14': 't',  # Ctrl+T
            '\x06': 'f',  # Ctrl+F
            '\x07': 'g',  # Ctrl+G
            '\x08': 'h',  # Ctrl+H
            '\x0A': 'j',  # Ctrl+J
            '\x0B': 'k',  # Ctrl+K
            '\x0C': 'l',  # Ctrl+L
            '\x1A': 'z',  # Ctrl+Z
            '\x18': 'x',  # Ctrl+X
            '\x03': 'c',  # Ctrl+C
            '\x16': 'v',  # Ctrl+V
            '\x02': 'b',  # Ctrl+B
            '\x0E': 'n',  # Ctrl+N
            '\x0D': 'm',  # Ctrl+M
            '\x11': 'q',  # Ctrl+Q
        }

        # Component references
        self.application = None
        self.display = None

        # Event loop reference
        self._main_loop: Optional[asyncio.AbstractEventLoop] = None
        self._listener = None

        # Shortcut configuration mapping
        self.shortcuts: Dict[str, ShortcutConfig] = {}
        self._load_shortcuts()
        
        # Error recovery mechanism
        self._last_activity_time = 0
        self._listener_error_count = 0
        self._max_error_count = 3
        self._health_check_task = None
        self._restart_in_progress = False

    def _load_shortcuts(self):
        """
        Load shortcut settings from configuration.
        """
        shortcut_types = [
            "MANUAL_PRESS",
            "AUTO_TOGGLE",
            "ABORT",
            "MODE_TOGGLE",
            "WINDOW_TOGGLE",
        ]

        for shortcut_type in shortcut_types:
            config = self.shortcuts_config.get(shortcut_type, {})
            if config:
                self.shortcuts[shortcut_type] = ShortcutConfig(
                    modifier=config.get("modifier", "ctrl"),
                    key=config.get("key", "").lower(),
                    description=config.get("description", ""),
                )

    async def start(self) -> bool:
        """
        Start shortcut listener.
        """
        if not self.enabled:
            logger.info("Global shortcuts are disabled.")
            return False

        try:
            # Save main event loop reference
            self._main_loop = asyncio.get_running_loop()

            # Import pynput library and check platform compatibility
            try:
                from pynput import keyboard
                logger.info(f"pynput library imported successfully, current platform: {self._get_platform_info()}")
            except ImportError as e:
                logger.error(f"pynput library not installed: {e}")
                logger.error("Please install pynput: pip install pynput")
                return False

            # Check platform permissions
            if not self._check_platform_permissions():
                return False

            # Get Application instance
            from src.application import Application

            self.application = Application.get_instance()
            self.display = self.application.display

            # Log configured shortcuts
            self._log_shortcut_config()

            # Set key callbacks
            self._listener = keyboard.Listener(
                on_press=self._on_key_press, on_release=self._on_key_release
            )
            self._listener.start()
            self.running = True
            
            # Start health check task
            self._start_health_check_task()

            logger.info("Global shortcut listener started.")
            return True

        except ImportError:
            logger.error("pynput library not installed, global shortcut functionality is unavailable.")
            return False
        except Exception as e:
            logger.error(f"Failed to start global shortcut listener: {e}", exc_info=True)
            return False
            
    def _check_platform_permissions(self) -> bool:
        """Check platform permissions"""
        import platform
        
        system = platform.system()
        
        if system == "Darwin":  # macOS
            logger.info("macOS system detected, please confirm the following permissions:")
            logger.info("1. System Preferences > Security & Privacy > Privacy > Accessibility")
            logger.info("2. Make sure the application is added to the Accessibility list and enabled")
            logger.info("3. If running from the terminal, the terminal needs Accessibility permissions")
            
        elif system == "Linux":
            logger.info("Linux system detected, please confirm:")
            logger.info("1. User is in the input group: sudo usermod -a -G input $USER")
            logger.info("2. X11 or Wayland environment is running correctly")
            
        elif system == "Windows":
            logger.info("Windows system detected, please confirm:")
            logger.info("1. Run with administrator privileges (required in some cases)")
            logger.info("2. Antivirus software is not blocking keyboard listening")
            
        return True
            
    def _get_platform_info(self) -> str:
        """Get platform information"""
        import platform
        return f"{platform.system()} {platform.release()}"
        
    def _log_shortcut_config(self):
        """Log shortcut configuration"""
        logger.info("Configured shortcuts:")
        for shortcut_type, config in self.shortcuts.items():
            logger.info(f"  {shortcut_type}: {config.modifier}+{config.key} - {config.description}")
        if not self.shortcuts:
            logger.warning("No shortcuts configured.")

    def _on_key_press(self, key):
        """
        Key press callback.
        """
        if not self.running:
            return

        try:
            # Update activity time
            self._last_activity_time = time.time()
            
            key_name = self._get_key_name(key)
            if key_name:
                logger.debug(f"Key pressed: {key_name}")
                # If it's a special character and ctrl is pressed, handle the interrupt function directly
                if (hasattr(key, 'char') and key.char == '\x11' and 
                    any(k in self.pressed_keys for k in ["ctrl", "ctrl_l", "ctrl_r"])):
                    logger.debug("Ctrl+Q combination detected, triggering interrupt")
                    self._handle_abort()
                    return
                    
                self.pressed_keys.add(key_name)
                logger.debug(f"Currently pressed keys: {sorted(self.pressed_keys)}")
                self._check_shortcuts(True)
        except Exception as e:
            logger.error(f"Key press processing error: {e}", exc_info=True)
            self._handle_listener_error()

    def _on_key_release(self, key):
        """
        Key release callback.
        """
        if not self.running:
            return

        try:
            # Update activity time
            self._last_activity_time = time.time()
            
            key_name = self._get_key_name(key)
            if key_name:
                logger.debug(f"Key released: {key_name}")
                if key_name in self.pressed_keys:
                    self.pressed_keys.remove(key_name)
                logger.debug(f"Currently pressed keys: {sorted(self.pressed_keys)}")
                
                # Check if it's necessary to stop hold-to-talk
                if (self.key_states["MANUAL_PRESS"] and 
                    len(self.pressed_keys) == 0):  # All keys have been released
                    self.key_states["MANUAL_PRESS"] = False
                    self.manual_press_active = False
                    if self.application:
                        logger.debug("Force stop listening")
                        self._run_coroutine_threadsafe(self.application.stop_listening())
                
                self._check_shortcuts(False)
        except Exception as e:
            logger.error(f"Key release processing error: {e}", exc_info=True)
            self._handle_listener_error()

    def _get_key_name(self, key) -> Optional[str]:
        """
        Get key name.
        """
        try:
            # Handle special keys
            if hasattr(key, "name"):
                # Handle modifier keys
                if key.name in ["ctrl_l", "ctrl_r"]:
                    return "ctrl"
                if key.name in ["alt_l", "alt_r"]:
                    return "alt"
                if key.name in ["shift_l", "shift_r"]:
                    return "shift"
                if key.name == "cmd":  # Windows key/Command key
                    return "cmd"
                if key.name == "esc":
                    return "esc"
                if key.name == "enter":
                    return "enter"
                return key.name.lower()
            # Handle character keys
            elif hasattr(key, "char") and key.char:
                # Handle enter key
                if key.char == '\n':
                    return "enter"
                # Check if it is a Windows special character mapping
                if key.char in self.key_mapping:
                    return self.key_mapping[key.char]
                # Convert to lowercase
                return key.char.lower()
            return None
        except Exception as e:
            logger.error(f"Error getting key name: {e}")
            return None

    def _check_shortcuts(self, is_press: bool):
        """
        Check shortcut combinations.
        """
        # Check modifier key status
        ctrl_pressed = any(
            key in self.pressed_keys for key in [
                "ctrl", "ctrl_l", "ctrl_r", "control", "control_l", "control_r"
            ]
        )
        
        # Check Alt key
        alt_pressed = any(
            key in self.pressed_keys for key in [
                "alt", "alt_l", "alt_r", "option", "option_l", "option_r"
            ]
        )
        
        # Check Shift key
        shift_pressed = any(
            key in self.pressed_keys for key in [
                "shift", "shift_l", "shift_r"
            ]
        )

        # Check Windows/Command key
        cmd_pressed = "cmd" in self.pressed_keys

        # Check each shortcut
        for shortcut_type, config in self.shortcuts.items():
            if self._is_shortcut_match(config, ctrl_pressed, alt_pressed, shift_pressed, cmd_pressed):
                self._handle_shortcut(shortcut_type, is_press)
                
    def _is_shortcut_match(self, config: ShortcutConfig, ctrl_pressed: bool, alt_pressed: bool, shift_pressed: bool, cmd_pressed: bool) -> bool:
        """
        Check if the shortcut matches.
        """
        # Check modifier key
        modifier_check = True
        if config.modifier == "ctrl" and not ctrl_pressed:
            modifier_check = False
        elif config.modifier == "alt" and not alt_pressed:
            modifier_check = False
        elif config.modifier == "shift" and not shift_pressed:
            modifier_check = False
        elif config.modifier == "cmd" and not cmd_pressed:
            modifier_check = False
        elif config.modifier == "ctrl+alt" and not (ctrl_pressed and alt_pressed):
            modifier_check = False
        elif config.modifier == "ctrl+shift" and not (ctrl_pressed and shift_pressed):
            modifier_check = False
        elif config.modifier == "alt+shift" and not (alt_pressed and shift_pressed):
            modifier_check = False
            
        # Check if the main key is pressed (case-insensitive)
        key_pressed = config.key.lower() in {k.lower() for k in self.pressed_keys}
        
        return modifier_check and key_pressed

    def _handle_shortcut(self, shortcut_type: str, is_press: bool):
        """
        Handle shortcut action.
        """
        # Special handling for hold-to-talk function
        if shortcut_type == "MANUAL_PRESS":
            current_time = time.time()
            # If it is in the pressed state
            if is_press:
                # Only trigger start_listening if it was not previously in the pressed state
                if not self.key_states["MANUAL_PRESS"]:
                    self.key_states["MANUAL_PRESS"] = True
                    self.key_states["last_manual_press_time"] = current_time
                    logger.info(f"Trigger shortcut: {shortcut_type}, Pressed state: {is_press}")
                    self._handle_manual_press(True)
            else:
                # Only trigger stop_listening if it was previously in the pressed state
                if self.key_states["MANUAL_PRESS"]:
                    self.key_states["MANUAL_PRESS"] = False
                    logger.info(f"Trigger shortcut: {shortcut_type}, Pressed state: {is_press}")
                    self._handle_manual_press(False)
            return
            
        # Special handling for interrupt function
        if shortcut_type == "ABORT":
            # Trigger only once on press
            if is_press and not self.key_states["ABORT"]:
                self.key_states["ABORT"] = True
                logger.info(f"Trigger shortcut: {shortcut_type}, Pressed state: {is_press}")
                self._handle_abort()
            elif not is_press:
                self.key_states["ABORT"] = False
            return

        # Handling of other shortcuts remains unchanged
        logger.info(f"Trigger shortcut: {shortcut_type}, Pressed state: {is_press}")
        
        handlers = {
            "AUTO_TOGGLE": lambda: self._handle_auto_toggle() if is_press else None,
            "MODE_TOGGLE": lambda: self._handle_mode_toggle() if is_press else None,
            "WINDOW_TOGGLE": lambda: self._handle_window_toggle() if is_press else None,
        }

        handler = handlers.get(shortcut_type)
        if handler:
            try:
                result = handler()
                if result is not None:
                    logger.debug(f"Shortcut {shortcut_type} processing complete.")
            except Exception as e:
                logger.error(f"Error processing shortcut {shortcut_type}: {e}", exc_info=True)
        else:
            logger.warning(f"Shortcut handler not found: {shortcut_type}")

    def _run_coroutine_threadsafe(self, coro):
        """
        Run coroutine thread-safely.
        """
        if not self._main_loop or not self.running:
            logger.warning("Event loop is not running or shortcut manager has stopped.")
            return

        try:
            asyncio.run_coroutine_threadsafe(coro, self._main_loop)
        except Exception as e:
            logger.error(f"Failed to run coroutine thread-safely: {e}")

    def _handle_manual_press(self, is_press: bool):
        """
        Handle hold-to-talk shortcut.
        """
        if not self.application:
            return

        try:
            if is_press and not self.manual_press_active:
                logger.debug("Shortcut: Start listening")
                self._run_coroutine_threadsafe(self.application.start_listening())
                self.manual_press_active = True
            elif not is_press:  # Regardless of the previous state, stop on release
                logger.debug("Shortcut: Stop listening")
                self._run_coroutine_threadsafe(self.application.stop_listening())
                self.manual_press_active = False
                self.key_states["MANUAL_PRESS"] = False
        except Exception as e:
            logger.error(f"Error handling hold-to-talk: {e}", exc_info=True)
            # Reset state on error
            self.manual_press_active = False
            self.key_states["MANUAL_PRESS"] = False

    def _handle_auto_toggle(self):
        """
        Handle auto-chat shortcut.
        """
        if self.application:
            self._run_coroutine_threadsafe(self.application.toggle_chat_state())

    def _handle_abort(self):
        """
        Handle interrupt chat shortcut.
        """
        if self.application:
            logger.debug("Shortcut: Interrupt chat")
            try:
                self._run_coroutine_threadsafe(
                    self.application.abort_speaking(AbortReason.NONE)
                )
            except Exception as e:
                logger.error(f"Error executing interrupt operation: {e}", exc_info=True)

    def _handle_mode_toggle(self):
        """
        Handle mode toggle shortcut.
        """
        if self.display:
            self._run_coroutine_threadsafe(self.display.toggle_mode())

    def _handle_window_toggle(self):
        """
        Handle window show/hide shortcut.
        """
        if self.display:
            self._run_coroutine_threadsafe(self.display.toggle_window_visibility())

    def _start_health_check_task(self):
        """
        Start health check task.
        """
        if self._main_loop and not self._health_check_task:
            self._health_check_task = asyncio.run_coroutine_threadsafe(
                self._health_check_loop(), self._main_loop
            )
            logger.debug("Shortcut health check task started.")

    async def _health_check_loop(self):
        """
        Health check loop - check if the keyboard listener is working correctly.
        """
        import time
        while self.running and not self._restart_in_progress:
            try:
                await asyncio.sleep(30)  # Check every 30 seconds
                
                if not self.running:
                    break
                    
                # Check if the listener exists and is running
                if not self._listener or not self._listener.running:
                    logger.warning("Keyboard listener stopped, attempting to restart.")
                    await self._restart_listener()
                    continue
                
                # Check for long periods of inactivity (may indicate listener failure)
                current_time = time.time()
                if (self._last_activity_time > 0 and 
                    current_time - self._last_activity_time > 300):  # 5 minutes of inactivity
                    logger.info("Long period of inactivity, performing listener health check.")
                    # Reset activity time to avoid frequent checks
                    self._last_activity_time = current_time
                    
            except Exception as e:
                logger.error(f"Health check error: {e}", exc_info=True)
                await asyncio.sleep(10)

    def _handle_listener_error(self):
        """
        Handle listener error.
        """
        self._listener_error_count += 1
        logger.warning(f"Keyboard listener error count: {self._listener_error_count}/{self._max_error_count}")
        
        if self._listener_error_count >= self._max_error_count:
            logger.error(f"Keyboard listener error count exceeded, attempting to restart.")
            if self._main_loop:
                asyncio.run_coroutine_threadsafe(
                    self._restart_listener(), self._main_loop
                )

    async def _restart_listener(self):
        """
        Restart keyboard listener.
        """
        if self._restart_in_progress:
            logger.debug("Listener restart already in progress, skipping.")
            return
            
        self._restart_in_progress = True
        logger.info("Starting to restart keyboard listener...")
        
        try:
            # Stop current listener
            if self._listener:
                try:
                    self._listener.stop()
                    await asyncio.sleep(1)  # Waiting for stop to complete
                except Exception as e:
                    logger.warning(f"Error stopping listener: {e}")
                finally:
                    self._listener = None
            
            # Clean up state
            self.pressed_keys.clear()
            self.manual_press_active = False
            self._listener_error_count = 0
            
            # Re-import pynput and create a new listener
            try:
                from pynput import keyboard
                
                self._listener = keyboard.Listener(
                    on_press=self._on_key_press, 
                    on_release=self._on_key_release
                )
                self._listener.start()
                
                # Update activity time
                import time
                self._last_activity_time = time.time()
                
                logger.info("Keyboard listener restarted successfully.")
                
            except Exception as e:
                logger.error(f"Failed to restart listener: {e}", exc_info=True)
                # Wait for a while and try again
                await asyncio.sleep(5)
                
        except Exception as e:
            logger.error(f"Error occurred during listener restart process: {e}", exc_info=True)
        finally:
            self._restart_in_progress = False

    async def stop(self):
        """
        Stop shortcut listener.
        """
        self.running = False
        self.manual_press_active = False
        
        # Stop health check task
        if self._health_check_task and not self._health_check_task.done():
            self._health_check_task.cancel()
            try:
                await asyncio.wrap_future(self._health_check_task)
            except (asyncio.CancelledError, Exception):
                pass
            self._health_check_task = None
        
        if self._listener:
            self._listener.stop()
            self._listener = None
        logger.info("Global shortcut listener stopped.")


async def start_global_shortcuts_async(
    logger_instance=None,
) -> Optional[ShortcutManager]:
    """Asynchronously start the global shortcut manager.

    Returns:     ShortcutManager instance or None (if startup fails)
    """
    try:
        shortcut_manager = ShortcutManager()
        success = await shortcut_manager.start()

        if success:
            if logger_instance:
                logger_instance.info("Global shortcut manager started successfully.")
            return shortcut_manager
        else:
            if logger_instance:
                logger_instance.warning("Global shortcut manager failed to start.")
            return None
    except Exception as e:
        if logger_instance:
            logger_instance.error(f"Error starting global shortcut manager: {e}")
        return None
