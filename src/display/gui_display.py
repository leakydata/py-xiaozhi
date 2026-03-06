import os
import platform
from pathlib import Path
from typing import Callable, Optional

from PyQt5.QtCore import QObject, Qt, QTimer
from PyQt5.QtGui import QFont, QMovie
from PyQt5.QtWidgets import (
    QApplication,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
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


# Style constants for chat bubbles
BUBBLE_USER_STYLE = """
QLabel {
    background-color: #DCF8C6;
    border-radius: 16px;
    padding: 10px 14px;
    color: #1a1a1a;
    font-size: 13px;
    border: none;
}
"""

BUBBLE_ASSISTANT_STYLE = """
QLabel {
    background-color: #ffffff;
    border-radius: 16px;
    padding: 10px 14px;
    color: #1a1a1a;
    font-size: 13px;
    border: 1px solid #e8e8e8;
}
"""

BUBBLE_STATUS_STYLE = """
QLabel {
    background-color: transparent;
    color: #999999;
    font-size: 11px;
    padding: 4px 0;
    border: none;
}
"""


class ChatBubble(QWidget):
    """A single chat message bubble."""

    def __init__(self, text: str, role: str = "assistant", parent=None):
        super().__init__(parent)
        self.role = role

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 2, 0, 2)
        layout.setSpacing(0)

        label = QLabel(text)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        label.setSizePolicy(QSizePolicy.Preferred, QSizePolicy.Minimum)
        label.setMaximumWidth(340)

        if role == "user":
            label.setStyleSheet(BUBBLE_USER_STYLE)
            label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            layout.addStretch()
            layout.addWidget(label)
        elif role == "status":
            label.setStyleSheet(BUBBLE_STATUS_STYLE)
            label.setAlignment(Qt.AlignCenter)
            layout.addStretch()
            layout.addWidget(label)
            layout.addStretch()
        else:
            label.setStyleSheet(BUBBLE_ASSISTANT_STYLE)
            label.setAlignment(Qt.AlignLeft | Qt.AlignVCenter)
            layout.addWidget(label)
            layout.addStretch()

        self.label = label

    def update_text(self, text: str):
        self.label.setText(text)


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

        # Chat bubble area
        self.chat_scroll_area = None
        self.chat_layout = None
        self._chat_bubbles = []
        self._current_assistant_bubble = None
        self._max_bubbles = 100

        # Emotion management
        self.emotion_movie = None
        self._emotion_cache = {}
        self._last_emotion_name = None

        # Status management
        self.auto_mode = True
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
        """Set callback functions."""
        self.button_press_callback = press_callback
        self.button_release_callback = release_callback
        self.mode_callback = mode_callback
        self.auto_callback = auto_callback
        self.abort_callback = abort_callback
        self.send_text_callback = send_text_callback

    def _add_chat_bubble(self, text: str, role: str = "assistant"):
        """Add a chat bubble to the chat area."""
        if not self.chat_layout:
            return

        bubble = ChatBubble(text, role)
        self._chat_bubbles.append(bubble)

        # Insert before the spacer (which is the last item)
        spacer_index = self.chat_layout.count() - 1
        self.chat_layout.insertWidget(spacer_index, bubble)

        # Trim old messages
        while len(self._chat_bubbles) > self._max_bubbles:
            old = self._chat_bubbles.pop(0)
            self.chat_layout.removeWidget(old)
            old.deleteLater()

        # Scroll to bottom
        QTimer.singleShot(50, self._scroll_to_bottom)

        return bubble

    def _scroll_to_bottom(self):
        """Scroll the chat area to the bottom."""
        if self.chat_scroll_area:
            vbar = self.chat_scroll_area.verticalScrollBar()
            vbar.setValue(vbar.maximum())

    def _on_manual_button_press(self):
        """Manual mode button press event handler."""
        if self.manual_btn and self.manual_btn.isVisible():
            self.manual_btn.setText("Release to stop")
        if self.button_press_callback:
            self.button_press_callback()

    def _on_manual_button_release(self):
        """Manual mode button release event handler."""
        if self.manual_btn and self.manual_btn.isVisible():
            self.manual_btn.setText("Hold to Talk")
        if self.button_release_callback:
            self.button_release_callback()

    def _on_auto_button_click(self):
        """Auto mode button click event handler."""
        if self.auto_callback:
            self.auto_callback()

    def _on_abort_button_click(self):
        """Handle abort button click event."""
        if self.abort_callback:
            self.abort_callback()

    def _on_mode_button_click(self):
        """Conversation mode switch button click event."""
        if self.mode_callback:
            if not self.mode_callback():
                return

        self.auto_mode = not self.auto_mode

        if self.auto_mode:
            self._update_mode_button_status("Auto")
            self._switch_to_auto_mode()
        else:
            self._update_mode_button_status("Manual")
            self._switch_to_manual_mode()

    def _switch_to_auto_mode(self):
        """UI update for switching to auto mode."""
        if self.manual_btn and self.auto_btn:
            self.manual_btn.hide()
            self.auto_btn.show()

    def _switch_to_manual_mode(self):
        """UI update for switching to manual mode."""
        if self.manual_btn and self.auto_btn:
            self.auto_btn.hide()
            self.manual_btn.show()

    async def update_status(self, status: str):
        """Update status text."""
        self._safe_update_label(self.status_label, status)

        if status != self.current_status:
            old_status = self.current_status
            self.current_status = status
            self._update_connection_status(status)
            self._update_system_tray(status)

            # Add status transitions as subtle notifications in chat
            if status == "Listening..." and old_status != "Listening...":
                self._add_chat_bubble("Listening...", "status")
            elif status == "Speaking..." and old_status != "Speaking...":
                self._current_assistant_bubble = None  # Reset for new response

    async def update_text(self, text: str):
        """Update TTS text - adds or updates chat bubbles."""
        if not text or not text.strip():
            return

        # Determine role from context
        from src.utils.conversation_history import ConversationHistory
        history = ConversationHistory.get_instance()
        last_msg = None
        messages = history.get_messages(limit=1)
        if messages:
            last_msg = messages[-1]

        if last_msg and last_msg.content == text:
            role = last_msg.role
        else:
            # Default: if we're speaking, it's assistant; otherwise user
            role = "assistant" if self.current_status == "Speaking..." else "user"

        if role == "user":
            self._add_chat_bubble(text, "user")
            self._current_assistant_bubble = None
        else:
            # For assistant messages, update the current bubble or create a new one
            if self._current_assistant_bubble:
                # Append to existing bubble (streaming feel)
                current_text = self._current_assistant_bubble.label.text()
                if text != current_text:
                    self._current_assistant_bubble.update_text(text)
                    QTimer.singleShot(50, self._scroll_to_bottom)
            else:
                self._current_assistant_bubble = self._add_chat_bubble(text, "assistant")

        # Also update the hidden tts_text_label for backward compatibility
        self._safe_update_label(self.tts_text_label, text)

    async def update_emotion(self, emotion_name: str):
        """Update emotion display."""
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
        """Get emotion GIF file path."""
        if emotion_name in self._emotion_cache:
            return self._emotion_cache[emotion_name]

        assets_dir = find_assets_dir()
        if not assets_dir:
            path = self._emotion_to_emoji(emotion_name)
        else:
            emotion_dir = assets_dir / "emojis"
            gif_file = emotion_dir / f"{emotion_name}.gif"

            if gif_file.exists():
                path = str(gif_file)
            elif (emotion_dir / "neutral.gif").exists():
                path = str(emotion_dir / "neutral.gif")
            else:
                path = self._emotion_to_emoji(emotion_name)

        self._emotion_cache[emotion_name] = path
        return path

    @staticmethod
    def _emotion_to_emoji(emotion_name: str) -> str:
        """Map emotion names to emoji."""
        mapping = {
            "neutral": "\U0001f916",
            "happy": "\U0001f60a",
            "sad": "\U0001f614",
            "angry": "\U0001f620",
            "surprised": "\U0001f632",
            "thinking": "\U0001f914",
            "confused": "\U0001f615",
            "laughing": "\U0001f602",
        }
        return mapping.get(emotion_name, "\U0001f916")

    def _set_emotion_gif(self, label, gif_path):
        """Set emotion GIF animation."""
        if not label:
            return

        if not gif_path.endswith(".gif"):
            label.setText(gif_path)
            return

        try:
            if hasattr(self, "_gif_movies") and gif_path in self._gif_movies:
                movie = self._gif_movies[gif_path]
            else:
                movie = QMovie(gif_path)
                if not movie.isValid():
                    label.setText("\U0001f916")
                    return

                movie.setCacheMode(QMovie.CacheAll)

                if not hasattr(self, "_gif_movies"):
                    self._gif_movies = {}
                self._gif_movies[gif_path] = movie

            self.emotion_movie = movie
            label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
            label.setAlignment(Qt.AlignCenter)
            label.setMovie(movie)
            movie.setSpeed(105)
            movie.start()

        except Exception as e:
            self.logger.error(f"Failed to set GIF animation: {e}")
            label.setText("\U0001f916")

    def _safe_update_label(self, label, text):
        """Safely update label text."""
        if label:
            try:
                label.setText(text)
            except RuntimeError as e:
                self.logger.error(f"Failed to update label: {e}")

    async def close(self):
        """Handle window closing."""
        self._running = False
        if self.system_tray:
            self.system_tray.hide()
        if self.root:
            self.root.close()

    async def start(self):
        """Start GUI."""
        try:
            os.environ.setdefault("QT_LOGGING_RULES", "qt.qpa.fonts.debug=false")

            self.app = QApplication.instance()
            if self.app is None:
                raise RuntimeError("QApplication not found, please make sure to run in a qasync environment")

            default_font = QFont()
            default_font.setPointSize(12)
            self.app.setFont(default_font)

            from PyQt5 import uic

            self.root = QWidget()
            ui_path = Path(__file__).parent / "gui_display.ui"
            uic.loadUi(str(ui_path), self.root)

            self._init_ui_controls()
            self._connect_events()
            self._setup_system_tray()
            await self._set_default_emotion()

            # Add welcome message
            self._add_chat_bubble(
                "Hi! I'm your AI assistant. Click 'Start Conversation' or type a message to get started.",
                "assistant",
            )

            self.root.show()

        except Exception as e:
            self.logger.error(f"GUI startup failed: {e}", exc_info=True)
            raise

    def _init_ui_controls(self):
        """Initialize UI controls."""
        self.status_label = self.root.findChild(QLabel, "status_label")
        self.emotion_label = self.root.findChild(QLabel, "emotion_label")
        self.tts_text_label = self.root.findChild(QLabel, "tts_text_label")
        self.manual_btn = self.root.findChild(QPushButton, "manual_btn")
        self.abort_btn = self.root.findChild(QPushButton, "abort_btn")
        self.auto_btn = self.root.findChild(QPushButton, "auto_btn")
        self.mode_btn = self.root.findChild(QPushButton, "mode_btn")
        self.text_input = self.root.findChild(QLineEdit, "text_input")
        self.send_btn = self.root.findChild(QPushButton, "send_btn")

        # Chat area
        self.chat_scroll_area = self.root.findChild(QScrollArea, "chat_scroll_area")
        chat_content = self.root.findChild(QWidget, "chat_content")
        if chat_content:
            self.chat_layout = chat_content.layout()

    def _connect_events(self):
        """Connect events."""
        if self.manual_btn:
            self.manual_btn.pressed.connect(self._on_manual_button_press)
            self.manual_btn.released.connect(self._on_manual_button_release)
        if self.abort_btn:
            self.abort_btn.clicked.connect(self._on_abort_button_click)
        if self.auto_btn:
            self.auto_btn.clicked.connect(self._on_auto_button_click)
            self.auto_btn.show()
        if self.manual_btn:
            self.manual_btn.hide()
        if self.mode_btn:
            self.mode_btn.clicked.connect(self._on_mode_button_click)
        if self.text_input and self.send_btn:
            self.send_btn.clicked.connect(self._on_send_button_click)
            self.text_input.returnPressed.connect(self._on_send_button_click)

        self.root.closeEvent = self._closeEvent

    def _setup_system_tray(self):
        """Set up system tray."""
        try:
            from src.views.components.system_tray import SystemTray

            self.system_tray = SystemTray(self.root)
            self.system_tray.show_window_requested.connect(self._show_main_window)
            self.system_tray.settings_requested.connect(self._on_settings_button_click)
            self.system_tray.quit_requested.connect(self._quit_application)

        except Exception as e:
            self.logger.error(f"Failed to initialize system tray component: {e}", exc_info=True)

    async def _set_default_emotion(self):
        """Set default emotion."""
        try:
            await self.update_emotion("neutral")
        except Exception as e:
            self.logger.error(f"Failed to set default emotion: {e}", exc_info=True)

    def _update_system_tray(self, status):
        """Update system tray status."""
        if self.system_tray:
            self.system_tray.update_status(status, self.is_connected)

    def _show_main_window(self):
        """Show main window."""
        if self.root:
            if self.root.isMinimized():
                self.root.showNormal()
            if not self.root.isVisible():
                self.root.show()
            self.root.activateWindow()
            self.root.raise_()

    def _quit_application(self):
        """Exit application."""
        self.logger.info("Starting to exit application...")
        self._running = False

        if self.system_tray:
            self.system_tray.hide()

        try:
            from src.application import Application

            app = Application.get_instance()
            if app:
                import asyncio

                from PyQt5.QtCore import QTimer

                loop = asyncio.get_event_loop()
                if loop.is_running():
                    shutdown_task = asyncio.create_task(app.shutdown())

                    def force_quit():
                        if not shutdown_task.done():
                            self.logger.warning("Shutdown timed out, forcing quit")
                            shutdown_task.cancel()
                        QApplication.quit()

                    QTimer.singleShot(3000, force_quit)

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
                    QApplication.quit()
            else:
                QApplication.quit()

        except Exception as e:
            self.logger.error(f"Failed to close application: {e}")
            QApplication.quit()

    def _closeEvent(self, event):
        """Handle window close event."""
        if self.system_tray and self.system_tray.is_visible():
            self.root.hide()
            self.system_tray.show_message(
                "AI Assistant", "The app is still running in the background."
            )
            event.ignore()
        else:
            self._quit_application()
            event.accept()

    def _update_mode_button_status(self, text: str):
        """Update mode button status."""
        if self.mode_btn:
            self.mode_btn.setText(text)

    async def update_button_status(self, text: str):
        """Update button status."""
        if self.auto_mode and self.auto_btn:
            self.auto_btn.setText(text)

    def _on_send_button_click(self):
        """Handle send text button click event."""
        if not self.text_input or not self.send_text_callback:
            return

        text = self.text_input.text().strip()
        if not text:
            return

        self.text_input.clear()

        # Show user message as a bubble immediately
        self._add_chat_bubble(text, "user")
        self._current_assistant_bubble = None

        try:
            import asyncio

            asyncio.create_task(self.send_text_callback(text))
        except Exception as e:
            self.logger.error(f"Error sending text: {e}")

    def _on_settings_button_click(self):
        """Handle settings button click event."""
        try:
            from src.views.settings import SettingsWindow

            settings_window = SettingsWindow(self.root)
            settings_window.exec_()

        except Exception as e:
            self.logger.error(f"Failed to open settings window: {e}", exc_info=True)

    def _update_connection_status(self, status: str):
        """Update connection status based on status."""
        if status in ["Connecting...", "Listening...", "Speaking..."]:
            self.is_connected = True
        elif status == "Standby" or status == "Ready":
            from src.application import Application

            app = Application.get_instance()
            if app and app.protocol:
                self.is_connected = app.protocol.is_audio_channel_opened()
            else:
                self.is_connected = False
        else:
            self.is_connected = False

    async def toggle_mode(self):
        """Toggle mode."""
        if hasattr(self, "mode_callback") and self.mode_callback:
            self._on_mode_button_click()
            self.logger.debug("Switched conversation mode via shortcut key")

    async def toggle_window_visibility(self):
        """Toggle window visibility."""
        if self.root:
            if self.root.isVisible():
                self.logger.debug("Hide window via shortcut key")
                self.root.hide()
            else:
                self.logger.debug("Show window via shortcut key")
                self.root.show()
                self.root.activateWindow()
                self.root.raise_()
