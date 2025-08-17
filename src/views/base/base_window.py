# -*- coding: utf-8 -*-
"""
Base window class - base class for all PyQt windows
Supports asynchronous operations and qasync integration
"""

import asyncio
from typing import Optional

from PyQt5.QtCore import QTimer, pyqtSignal
from PyQt5.QtWidgets import QMainWindow, QWidget

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class BaseWindow(QMainWindow):
    """
    Base class for all windows, providing asynchronous support.
    """

    # Define signals
    window_closed = pyqtSignal()
    status_updated = pyqtSignal(str)

    def __init__(self, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.logger = get_logger(self.__class__.__name__)

        # Asynchronous task management
        self._tasks = set()
        self._shutdown_event = asyncio.Event()

        # Timer for periodic UI updates (in conjunction with asynchronous operations)
        self._update_timer = QTimer()
        self._update_timer.timeout.connect(self._on_timer_update)

        # Initialize UI
        self._setup_ui()
        self._setup_connections()
        self._setup_styles()

        self.logger.debug(f"{self.__class__.__name__} initialization complete")

    def _setup_ui(self):
        """Set up UI - subclass override"""

    def _setup_connections(self):
        """Set up signal connections - subclass override"""

    def _setup_styles(self):
        """Set up styles - subclass override"""

    def _on_timer_update(self):
        """Timer update callback - subclass override"""

    def start_update_timer(self, interval_ms: int = 1000):
        """
        Start timed updates.
        """
        self._update_timer.start(interval_ms)
        self.logger.debug(f"Started timed updates, interval: {interval_ms}ms")

    def stop_update_timer(self):
        """
        Stop timed updates.
        """
        self._update_timer.stop()
        self.logger.debug("Stopped timed updates")

    def create_task(self, coro, name: str = None):
        """
        Create and manage asynchronous tasks.
        """
        task = asyncio.create_task(coro, name=name)
        self._tasks.add(task)

        def done_callback(t):
            self._tasks.discard(t)
            if not t.cancelled() and t.exception():
                self.logger.error(f"Asynchronous task exception: {t.exception()}", exc_info=True)

        task.add_done_callback(done_callback)
        return task

    async def shutdown_async(self):
        """
        Asynchronously close the window.
        """
        self.logger.info("Starting to close the window asynchronously")

        # Set shutdown event
        self._shutdown_event.set()

        # Stop timer
        self.stop_update_timer()

        # Cancel all tasks
        for task in self._tasks.copy():
            if not task.done():
                task.cancel()

        # Wait for tasks to complete
        if self._tasks:
            await asyncio.gather(*self._tasks, return_exceptions=True)

        self.logger.info("Window closed asynchronously")

    def closeEvent(self, event):
        """
        Window close event.
        """
        self.logger.info("Window close event triggered")

        # Set shutdown event flag
        self._shutdown_event.set()

        # If it is an activation window, cancel the activation process
        if hasattr(self, "device_activator") and self.device_activator:
            self.device_activator.cancel_activation()
            self.logger.info("Activation cancellation signal sent")

        # Emit close signal
        self.window_closed.emit()

        # Stop timer
        self.stop_update_timer()

        # Cancel all tasks (synchronously)
        for task in self._tasks.copy():
            if not task.done():
                task.cancel()

        # Accept close event
        event.accept()

        self.logger.info("Window close processing complete")

    def update_status(self, message: str):
        """
        Update status message.
        """
        self.status_updated.emit(message)
        self.logger.debug(f"Status update: {message}")

    def is_shutdown_requested(self) -> bool:
        """
        Check if shutdown is requested.
        """
        return self._shutdown_event.is_set()
