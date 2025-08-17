from abc import ABC, abstractmethod
from typing import Callable, Optional

from src.utils.logging_config import get_logger


class BaseDisplay(ABC):
    """
    Abstract base class for display interfaces.
    """

    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)

    @abstractmethod
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

    @abstractmethod
    async def update_button_status(self, text: str):
        """
        Update button status.
        """

    @abstractmethod
    async def update_status(self, status: str):
        """
        Update status text.
        """

    @abstractmethod
    async def update_text(self, text: str):
        """
        Update TTS text.
        """

    @abstractmethod
    async def update_emotion(self, emotion_name: str):
        """
        Update emotion.
        """

    @abstractmethod
    async def start(self):
        """
        Start display.
        """

    @abstractmethod
    async def close(self):
        """
        Close display.
        """

    async def toggle_mode(self):
        """
        Toggle mode (define interface in base class)
        """
        self.logger.debug("toggle_mode in base class called")

    async def toggle_window_visibility(self):
        """
        Toggle window visibility (define interface in base class)
        """
        self.logger.debug("toggle_window_visibility in base class called")
