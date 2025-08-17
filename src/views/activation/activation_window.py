# -*- coding: utf-8 -*-
"""
Device activation window, displays the activation process, device information, and activation progress.
"""

from pathlib import Path
from typing import Optional

from PyQt5 import uic
from PyQt5.QtCore import QSize, pyqtSignal
from PyQt5.QtWidgets import QApplication

from src.core.system_initializer import SystemInitializer
from src.utils.device_activator import DeviceActivator
from src.utils.logging_config import get_logger

from ..base.async_mixins import AsyncMixin, AsyncSignalEmitter
from ..base.base_window import BaseWindow

logger = get_logger(__name__)


class ActivationWindow(BaseWindow, AsyncMixin):
    """
    Device Activation Window.
    """

    # Custom signals
    activation_completed = pyqtSignal(bool)  # Activation completed signal
    window_closed = pyqtSignal()  # Window closed signal

    def __init__(
        self,
        system_initializer: Optional[SystemInitializer] = None,
        parent: Optional = None,
    ):
        super().__init__(parent)

        # Component instances
        self.system_initializer = system_initializer
        self.device_activator: Optional[DeviceActivator] = None

        # State management
        self.current_stage = None
        self.activation_data = None
        self.is_activated = False
        self.initialization_started = False
        self.status_message = ""

        # Async signal emitter
        self.signal_emitter = AsyncSignalEmitter()
        self._setup_signal_connections()

        # Delayed start of initialization (after event loop starts)
        self.start_update_timer(100)  # Start initialization after 100ms

    def _setup_ui(self):
        """
        Set up UI.
        """
        ui_file = Path(__file__).parent / "activation_window.ui"
        uic.loadUi(str(ui_file), self)

        # Set window properties and adaptive size
        self.setWindowTitle("Device Activation - py-xiaozhi")
        self._setup_adaptive_size()

        # Hide log area
        if hasattr(self, "log_text"):
            self.log_text.hide()

        self.logger.info("Activation window UI loaded successfully")

    def _setup_adaptive_size(self):
        """
        Set adaptive window size.
        """
        # Get screen size
        screen = QApplication.primaryScreen()
        screen_size = screen.size()
        screen_width = screen_size.width()
        screen_height = screen_size.height()

        self.logger.info(f"Detected screen resolution: {screen_width}x{screen_height}")

        # Select appropriate window size based on screen size
        if screen_width <= 480 or screen_height <= 320:
            # Very small screen (e.g., 3.5 inch 480x320)
            window_width, window_height = 450, 250
            self.setMinimumSize(QSize(450, 250))
            self._apply_compact_styles()
        elif screen_width <= 800 or screen_height <= 480:
            # Small screen (e.g., 7 inch 800x480)
            window_width, window_height = 480, 280
            self.setMinimumSize(QSize(480, 280))
            self._apply_small_screen_styles()
        elif screen_width <= 1024 or screen_height <= 600:
            # Medium screen
            window_width, window_height = 520, 300
            self.setMinimumSize(QSize(520, 300))
        else:
            # Large screen (PC monitor)
            window_width, window_height = 550, 320
            self.setMinimumSize(QSize(550, 320))

        # Ensure the window does not exceed the screen size
        max_width = min(window_width, screen_width - 50)
        max_height = min(window_height, screen_height - 50)

        self.resize(max_width, max_height)

        # Center display
        self.move((screen_width - max_width) // 2, (screen_height - max_height) // 2)

        self.logger.info(f"Set window size: {max_width}x{max_height}")

    def _apply_compact_styles(self):
        """Apply compact styles - suitable for very small screens"""
        # Adjust font size
        self.setStyleSheet(
            """
            QLabel { font-size: 10px; }
            QPushButton { font-size: 10px; padding: 4px 8px; }
            QTextEdit { font-size: 8px; }
        """
        )

    def _apply_small_screen_styles(self):
        """
        Apply small screen styles.
        """
        # Adjust font size
        self.setStyleSheet(
            """
            QLabel { font-size: 11px; }
            QPushButton { font-size: 11px; padding: 6px 10px; }
            QTextEdit { font-size: 9px; }
        """
        )

    def _setup_connections(self):
        """
        Set up signal connections.
        """
        # Button connections
        self.close_btn.clicked.connect(self.close)
        self.retry_btn.clicked.connect(self._on_retry_clicked)
        self.copy_code_btn.clicked.connect(self._on_copy_code_clicked)

        self.logger.debug("Signal connections set up successfully")

    def _setup_signal_connections(self):
        """
        Set up async signal connections.
        """
        self.signal_emitter.status_changed.connect(self._on_status_changed)
        self.signal_emitter.error_occurred.connect(self._on_error_occurred)
        self.signal_emitter.data_ready.connect(self._on_data_ready)

    def _setup_styles(self):
        """
        Set up styles.
        """
        # Basic styles are defined in the UI file

    def _on_timer_update(self):
        """Timer update callback - start initialization"""
        if not self.initialization_started:
            self.initialization_started = True
            self.stop_update_timer()  # Stop timer

            # The event loop should be running now, async tasks can be created
            try:
                self.create_task(self._start_initialization(), "initialization")
            except RuntimeError as e:
                self.logger.error(f"Failed to create initialization task: {e}")
                # If it fails again, try again
                self.start_update_timer(500)

    async def _start_initialization(self):
        """
        Start system initialization process.
        """
        try:
            # If a SystemInitializer instance is already provided, use it directly
            if self.system_initializer:
                self._update_device_info()
                await self._start_activation_process()
            else:
                # Otherwise, create a new instance and run initialization
                self.system_initializer = SystemInitializer()

                # Run initialization process
                init_result = await self.system_initializer.run_initialization()

                if init_result.get("success", False):
                    self._update_device_info()

                    # Show status message
                    self.status_message = init_result.get("status_message", "")
                    if self.status_message:
                        self.signal_emitter.emit_status(self.status_message)

                    # Check if activation is needed
                    if init_result.get("need_activation_ui", True):
                        await self._start_activation_process()
                    else:
                        # No activation needed, complete directly
                        self.is_activated = True
                        self.activation_completed.emit(True)
                else:
                    error_msg = init_result.get("error", "Initialization failed")
                    self.signal_emitter.emit_error(error_msg)

        except Exception as e:
            self.logger.error(f"Exception during initialization process: {e}", exc_info=True)
            self.signal_emitter.emit_error(f"Initialization exception: {e}")

    def _update_device_info(self):
        """
        Update device information display.
        """
        if (
            not self.system_initializer
            or not self.system_initializer.device_fingerprint
        ):
            return

        device_fp = self.system_initializer.device_fingerprint

        # Update serial number
        serial_number = device_fp.get_serial_number()
        self.serial_value.setText(serial_number if serial_number else "--")

        # Update MAC address
        mac_address = device_fp.get_mac_address_from_efuse()
        self.mac_value.setText(mac_address if mac_address else "--")

        # Get activation status
        activation_status = self.system_initializer.get_activation_status()
        local_activated = activation_status.get("local_activated", False)
        server_activated = activation_status.get("server_activated", False)
        status_consistent = activation_status.get("status_consistent", True)

        # Update activation status display
        self.is_activated = local_activated

        if not status_consistent:
            if local_activated and not server_activated:
                status_text = "Status inconsistent (reactivation required)"
                status_style = "color: #ff9900;"  # Orange warning
            else:
                status_text = "Status inconsistent (fixed)"
                status_style = "color: #28a745;"  # Green
        else:
            status_text = "Activated" if local_activated else "Not Activated"
            status_style = "color: #28a745;" if local_activated else "color: #dc3545;"

        self.status_value.setText(status_text)
        self.status_value.setStyleSheet(status_style)

        # Initialize activation code display
        self.activation_code_value.setText("--")

    async def _start_activation_process(self):
        """
        Start activation process.
        """
        try:
            # Get activation data
            activation_data = self.system_initializer.get_activation_data()

            if not activation_data:
                self.signal_emitter.emit_error("Failed to get activation data, please check network connection")
                return

            self.activation_data = activation_data

            # Show activation information
            self._show_activation_info(activation_data)

            # Initialize device activator
            config_manager = self.system_initializer.get_config_manager()
            self.device_activator = DeviceActivator(config_manager)

            # Start activation process
            self.signal_emitter.emit_status("Starting device activation process...")
            activation_success = await self.device_activator.process_activation(
                activation_data
            )

            # Check if it was cancelled due to window closing
            if self.is_shutdown_requested():
                self.signal_emitter.emit_status("Activation process cancelled")
                return

            if activation_success:
                self.signal_emitter.emit_status("Device activated successfully!")
                self._on_activation_success()
            else:
                self.signal_emitter.emit_status("Device activation failed")
                self.signal_emitter.emit_error("Device activation failed, please try again")

        except Exception as e:
            self.logger.error(f"Exception in activation process: {e}", exc_info=True)
            self.signal_emitter.emit_error(f"Activation exception: {e}")

    def _show_activation_info(self, activation_data: dict):
        """
        Show activation information.
        """
        code = activation_data.get("code", "------")

        # Update activation code in device information
        self.activation_code_value.setText(code)

        # Information is already displayed on the UI, only a brief log is recorded
        self.logger.info(f"Get activation code: {code}")

    def _on_activation_success(self):
        """
        Handle activation success.
        """
        # Update status display
        self.status_value.setText("Activated")
        self.status_value.setStyleSheet("color: #28a745;")

        # Clear activation code display
        self.activation_code_value.setText("--")

        # Emit completion signal
        self.activation_completed.emit(True)
        self.is_activated = True

    def _on_status_changed(self, status: str):
        """
        Handle status change.
        """
        self.update_status(status)

    def _on_error_occurred(self, error_message: str):
        """
        Handle error.
        """
        self.logger.error(f"Error: {error_message}")
        self.update_status(f"Error: {error_message}")

    def _on_data_ready(self, data):
        """
        Handle data ready.
        """
        self.logger.debug(f"Received data: {data}")

    def _on_retry_clicked(self):
        """
        Retry button clicked.
        """
        self.logger.info("User requested reactivation")

        # Check if already closed
        if self.is_shutdown_requested():
            return

        # Reset status
        self.activation_code_value.setText("--")

        # Restart initialization
        self.create_task(self._start_initialization(), "retry_initialization")

    def _on_copy_code_clicked(self):
        """
        Copy code button clicked.
        """
        if self.activation_data:
            code = self.activation_data.get("code", "")
            if code:
                clipboard = QApplication.clipboard()
                clipboard.setText(code)
                self.update_status(f"Verification code copied to clipboard: {code}")

    def update_status(self, message: str):
        """
        Update status information.
        """
        self.logger.info(message)

        # If there is a status label, update it
        if hasattr(self, "status_label"):
            self.status_label.setText(message)

    def get_activation_result(self) -> dict:
        """
        Get activation result.
        """
        device_fingerprint = None
        config_manager = None

        if self.system_initializer:
            device_fingerprint = self.system_initializer.device_fingerprint
            config_manager = self.system_initializer.config_manager

        return {
            "is_activated": self.is_activated,
            "device_fingerprint": device_fingerprint,
            "config_manager": config_manager,
        }

    async def shutdown_async(self):
        """
        Async shutdown.
        """
        self.logger.info("Closing activation window...")

        # Cancel activation process (if in progress)
        if self.device_activator:
            self.device_activator.cancel_activation()
            self.logger.info("Activation cancellation signal sent")

        # Clean up async tasks first
        await self.cleanup_async_tasks()

        # Then call parent class close
        await super().shutdown_async()

    def closeEvent(self, event):
        """
        Handle window close event.
        """
        self.logger.info("Activation window close event triggered")
        self.window_closed.emit()
        event.accept()
