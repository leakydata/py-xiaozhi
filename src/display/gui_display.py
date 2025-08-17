import os
import platform
from pathlib import Path
from typing import Callable, Optional

from PyQt5.QtCore import QObject, Qt
from PyQt5.QtGui import QFont, QMovie
from PyQt5.QtWidgets import (
    QApplication,
    QLabel,
    QLineEdit,
    QPushButton,
    QSizePolicy,
    QWidget,
)

# Handle pynput import according to different operating systems
try:
    if platform.system() == "Windows":
        from pynput import keyboard as pynput_keyboard
    elif os.environ.get("DISPLAY"):
        from pynput import keyboard as pynput_keyboard
    else:
        pynput_keyboard = None
except ImportError:
    pynput_keyboard = None

from abc import ABCMeta

from src.display.base_display import BaseDisplay
from src.utils.resource_finder import find_assets_dir


# Create a compatible metaclass
class CombinedMeta(type(QObject), ABCMeta):
    pass


class GuiDisplay(BaseDisplay, QObject, metaclass=CombinedMeta):
    def __init__(self):
        super().__init__()
        QObject.__init__(self)
        self.app = None
        self.root = None

        # UI controls
        self.status_label = None
        self.emotion_label = None
        self.tts_text_label = None
        self.manual_btn = None
        self.abort_btn = None
        self.auto_btn = None
        self.mode_btn = None
        self.text_input = None
        self.send_btn = None

        # Emotion management
        self.emotion_movie = None
        self._emotion_cache = {}
        self._last_emotion_name = None

        # Status management
        self.auto_mode = False
        self._running = True
        self.current_status = ""
        self.is_connected = True

        # Callback functions
        self.button_press_callback = None
        self.button_release_callback = None
        self.mode_callback = None
        self.auto_callback = None
        self.abort_callback = None
        self.send_text_callback = None

        # System tray component
        self.system_tray = None

    async def set_callbacks(
        self,
        press_callback: Optional[Callable] = None,
        release_callback: Optional[Callable] = None,
        mode_callback: Optional[Callable] = None,
        auto_callback: Optional[Callable] = None,
        abort_callback: Optional[Callable] = None,
        send_text_callback: Optional[Callable] = None,
    ):
        """
        Set callback functions.
        """
        self.button_press_callback = press_callback
        self.button_release_callback = release_callback
        self.mode_callback = mode_callback
        self.auto_callback = auto_callback
        self.abort_callback = abort_callback
        self.send_text_callback = send_text_callback

        # No longer register status listening callback, all logic is handled directly by update_status

    def _on_manual_button_press(self):
        """
        Manual mode button press event handler.
        """
        if self.manual_btn and self.manual_btn.isVisible():
            self.manual_btn.setText("Release to stop")
        if self.button_press_callback:
            self.button_press_callback()

    def _on_manual_button_release(self):
        """
        Manual mode button release event handler.
        """
        if self.manual_btn and self.manual_btn.isVisible():
            self.manual_btn.setText("Hold to talk")
        if self.button_release_callback:
            self.button_release_callback()

    def _on_auto_button_click(self):
        """
        Auto mode button click event handler.
        """
        if self.auto_callback:
            self.auto_callback()

    def _on_abort_button_click(self):
        """
        Handle abort button click event.
        """
        if self.abort_callback:
            self.abort_callback()

    def _on_mode_button_click(self):
        """
        Conversation mode switch button click event.
        """
        if self.mode_callback:
            if not self.mode_callback():
                return

        self.auto_mode = not self.auto_mode

        if self.auto_mode:
            self._update_mode_button_status("Auto Conversation")
            self._switch_to_auto_mode()
        else:
            self._update_mode_button_status("Manual Conversation")
            self._switch_to_manual_mode()

    def _switch_to_auto_mode(self):
        """
        UI update for switching to auto mode.
        """
        if self.manual_btn and self.auto_btn:
            self.manual_btn.hide()
            self.auto_btn.show()

    def _switch_to_manual_mode(self):
        """
        UI update for switching to manual mode.
        """
        if self.manual_btn and self.auto_btn:
            self.auto_btn.hide()
            self.manual_btn.show()

    async def update_status(self, status: str):
        """
        Update status text and handle related logic.
        """
        full_status_text = f"Status: {status}"
        self._safe_update_label(self.status_label, full_status_text)

        if status != self.current_status:
            self.current_status = status

            # Update connection status based on status
            self._update_connection_status(status)

            # Update system tray
            self._update_system_tray(status)

    async def update_text(self, text: str):
        """
        Update TTS text.
        """
        self._safe_update_label(self.tts_text_label, text)

    async def update_emotion(self, emotion_name: str):
        """
        Update emotion display.
        """
        if emotion_name == self._last_emotion_name:
            return

        self._last_emotion_name = emotion_name
        gif_path = self._get_emotion_gif_path(emotion_name)

        if self.emotion_label:
            try:
                self._set_emotion_gif(self.emotion_label, gif_path)
            except Exception as e:
                self.logger.error(f"Error setting emotion GIF: {str(e)}")

    def _get_emotion_gif_path(self, emotion_name: str) -> str:
        """
        Get emotion GIF file path.
        """
        if emotion_name in self._emotion_cache:
            return self._emotion_cache[emotion_name]

        assets_dir = find_assets_dir()
        if not assets_dir:
            path = "😊"
        else:
            emotion_dir = assets_dir / "emojis"
            gif_file = emotion_dir / f"{emotion_name}.gif"

            if gif_file.exists():
                path = str(gif_file)
            elif (emotion_dir / "neutral.gif").exists():
                path = str(emotion_dir / "neutral.gif")
            else:
                path = "😊"

        self._emotion_cache[emotion_name] = path
        return path

    def _set_emotion_gif(self, label, gif_path):
        """
        Set emotion GIF animation.
        """
        if not label:
            return

        # If it is an emoji string, set the text directly
        if not gif_path.endswith(".gif"):
            label.setText(gif_path)
            return

        try:
            # Check if the GIF is in the cache
            if hasattr(self, "_gif_movies") and gif_path in self._gif_movies:
                movie = self._gif_movies[gif_path]
            else:
                movie = QMovie(gif_path)
                if not movie.isValid():
                    label.setText("😊")
                    return

                movie.setCacheMode(QMovie.CacheAll)

                if not hasattr(self, "_gif_movies"):
                    self._gif_movies = {}
                self._gif_movies[gif_path] = movie

            # Save the animation object
            self.emotion_movie = movie

            # Set label properties
            label.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            label.setAlignment(Qt.AlignCenter)
            label.setMovie(movie)

            # Set animation speed and start playing
            movie.setSpeed(105)
            movie.start()

        except Exception as e:
            self.logger.error(f"Failed to set GIF animation: {e}")
            label.setText("😊")

    def _safe_update_label(self, label, text):
        """
        Safely update label text.
        """
        if label:
            try:
                label.setText(text)
            except RuntimeError as e:
                self.logger.error(f"Failed to update label: {e}")

    async def close(self):
        """
        Handle window closing.
        """
        self._running = False
        if self.system_tray:
            self.system_tray.hide()
        if self.root:
            self.root.close()

    async def start(self):
        """
        Start GUI.
        """
        try:
            # Set Qt environment variables
            os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.fonts.debug=false")

            self.app = QApplication.instance()
            if self.app is None:
                raise RuntimeError("QApplication not found, please make sure to run in a qasync environment")

            # Set default font
            default_font = QFont()
            default_font.setPointSize(12)
            self.app.setFont(default_font)

            # Load UI
            from PyQt5 import uic

            self.root = QWidget()
            ui_path = Path(__file__).parent / "gui_display.ui"
            uic.loadUi(str(ui_path), self.root)

            # Get controls and connect events
            self._init_ui_controls()
            self._connect_events()

            # Initialize system tray
            self._setup_system_tray()

            # Set default emotion
            await self._set_default_emotion()

            # Show window
            self.root.show()

        except Exception as e:
            self.logger.error(f"GUI startup failed: {e}", exc_info=True)
            raise

    def _init_ui_controls(self):
        """
        Initialize UI controls.
        """
        self.status_label = self.root.findChild(QLabel, "status_label")
        self.emotion_label = self.root.findChild(QLabel, "emotion_label")
        self.tts_text_label = self.root.findChild(QLabel, "tts_text_label")
        self.manual_btn = self.root.findChild(QPushButton, "manual_btn")
        self.abort_btn = self.root.findChild(QPushButton, "abort_btn")
        self.auto_btn = self.root.findChild(QPushButton, "auto_btn")
        self.mode_btn = self.root.findChild(QPushButton, "mode_btn")
        self.text_input = self.root.findChild(QLineEdit, "text_input")
        self.send_btn = self.root.findChild(QPushButton, "send_btn")

    def _connect_events(self):
        """
        Connect events.
        """
        if self.manual_btn:
            self.manual_btn.pressed.connect(self._on_manual_button_press)
            self.manual_btn.released.connect(self._on_manual_button_release)
        if self.abort_btn:
            self.abort_btn.clicked.connect(self._on_abort_button_click)
        if self.auto_btn:
            self.auto_btn.clicked.connect(self._on_auto_button_click)
            self.auto_btn.hide()
        if self.mode_btn:
            self.mode_btn.clicked.connect(self._on_mode_button_click)
        if self.text_input and self.send_btn:
            self.send_btn.clicked.connect(self._on_send_button_click)
            self.text_input.returnPressed.connect(self._on_send_button_click)

        # Set window close event
        self.root.closeEvent = self._closeEvent

    def _setup_system_tray(self):
        """
        Set up system tray.
        """
        try:
            from src.views.components.system_tray import SystemTray

            self.system_tray = SystemTray(self.root)
            self.system_tray.show_window_requested.connect(self._show_main_window)
            self.system_tray.settings_requested.connect(self._on_settings_button_click)
            self.system_tray.quit_requested.connect(self._quit_application)

        except Exception as e:
            self.logger.error(f"Failed to initialize system tray component: {e}", exc_info=True)

    async def _set_default_emotion(self):
        """
        Set default emotion.
        """
        try:
            await self.update_emotion("neutral")
        except Exception as e:
            self.logger.error(f"Failed to set default emotion: {e}", exc_info=True)

    def _update_system_tray(self, status):
        """
        Update system tray status.
        """
        if self.system_tray:
            self.system_tray.update_status(status, self.is_connected)

    def _show_main_window(self):
        """
        Show main window.
        """
        if self.root:
            if self.root.isMinimized():
                self.root.showNormal()
            if not self.root.isVisible():
                self.root.show()
            self.root.activateWindow()
            self.root.raise_()

    def _quit_application(self):
        """
        Exit application.
        """
        self.logger.info("Starting to exit application...")
        self._running = False

        if self.system_tray:
            self.system_tray.hide()

        try:
            from src.application import Application

            app = Application.get_instance()
            if app:
                # Asynchronously start the shutdown process, but set a timeout
                import asyncio

                from PyQt5.QtCore import QTimer

                loop = asyncio.get_event_loop()
                if loop.is_running():
                    # Create a shutdown task, but do not wait
                    shutdown_task = asyncio.create_task(app.shutdown())

                    # Force quit after timeout
                    def force_quit():
                        if not shutdown_task.done():
                            self.logger.warning("Shutdown timed out, forcing quit")
                            shutdown_task.cancel()
                        QApplication.quit()

                    # Force quit after 3 seconds
                    QTimer.singleShot(3000, force_quit)

                    # Quit normally when shutdown is complete
                    def on_shutdown_complete(task):
                        if not task.cancelled():
                            if task.exception():
                                self.logger.error(
                                    f"Application shutdown exception: {task.exception()}"
                                )
                            else:
                                self.logger.info("Application closed normally")
                        QApplication.quit()

                    shutdown_task.add_done_callback(on_shutdown_complete)
                else:
                    # If the event loop is not running, quit directly
                    QApplication.quit()
            else:
                QApplication.quit()

        except Exception as e:
            self.logger.error(f"Failed to close application: {e}")
            # Quit directly in case of exception
            QApplication.quit()

    def _closeEvent(self, event):
        """
        Handle window close event.
        """
        if self.system_tray and self.system_tray.is_visible():
            self.root.hide()
            self.system_tray.show_message(
                "Xiaozhi AI Assistant", "The program is still running, click the tray icon to reopen the window."
            )
            event.ignore()
        else:
            self._quit_application()
            event.accept()

    def _update_mode_button_status(self, text: str):
        """
        Update mode button status.
        """
        if self.mode_btn:
            self.mode_btn.setText(text)

    async def update_button_status(self, text: str):
        """
        Update button status.
        """
        if self.auto_mode and self.auto_btn:
            self.auto_btn.setText(text)

    def _on_send_button_click(self):
        """
        Handle send text button click event.
        """
        if not self.text_input or not self.send_text_callback:
            return

        text = self.text_input.text().strip()
        if not text:
            return

        self.text_input.clear()

        try:
            import asyncio

            asyncio.create_task(self.send_text_callback(text))
        except Exception as e:
            self.logger.error(f"Error sending text: {e}")

    def _on_settings_button_click(self):
        """
        Handle settings button click event.
        """
        try:
            from src.views.settings import SettingsWindow

            settings_window = SettingsWindow(self.root)
            settings_window.exec_()

        except Exception as e:
            self.logger.error(f"Failed to open settings window: {e}", exc_info=True)

    def _update_connection_status(self, status: str):
        """
        Update connection status based on status.
        """
        if status in ["Connecting...", "Listening...", "Speaking..."]:
            self.is_connected = True
        elif status == "Standby":
            # For standby status, need to check if the audio channel is really open
            from src.application import Application

            app = Application.get_instance()
            if app and app.protocol:
                self.is_connected = app.protocol.is_audio_channel_opened()
            else:
                self.is_connected = False
        else:
            # Other statuses (such as error status) are set to not connected
            self.is_connected = False

    async def toggle_mode(self):
        """
        Toggle mode.
        """
        # Call existing mode switching function
        if hasattr(self, "mode_callback") and self.mode_callback:
            self._on_mode_button_click()
            self.logger.debug("Switched conversation mode via shortcut key")

    async def toggle_window_visibility(self):
        """
        Toggle window visibility.
        """
        if self.root:
            if self.root.isVisible():
                self.logger.debug("Hide window via shortcut key")
                self.root.hide()
            else:
                self.logger.debug("Show window via shortcut key")
                self.root.show()
                self.root.activateWindow()
                self.root.raise_()
