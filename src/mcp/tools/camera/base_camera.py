"""
Base camera implementation.
"""

import threading
from abc import ABC, abstractmethod
from typing import Dict

from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class BaseCamera(ABC):
    """
    Base camera class, defines the interface.
    """

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        """
        Initialize the base camera.
        """
        self.jpeg_data = {"buf": b"", "len": 0}  # JPEG byte data of the image  # Length of the byte data

        # Read camera parameters from configuration
        config = ConfigManager.get_instance()
        self.camera_index = config.get_config("CAMERA.camera_index", 0)
        self.frame_width = config.get_config("CAMERA.frame_width", 640)
        self.frame_height = config.get_config("CAMERA.frame_height", 480)

    @abstractmethod
    def capture(self) -> bool:
        """
        Capture an image.
        """

    @abstractmethod
    def analyze(self, question: str) -> str:
        """
        Analyze the image.
        """

    def get_jpeg_data(self) -> Dict[str, any]:
        """
        Get JPEG data.
        """
        return self.jpeg_data

    def set_jpeg_data(self, data_bytes: bytes):
        """
        Set JPEG data.
        """
        self.jpeg_data["buf"] = data_bytes
        self.jpeg_data["len"] = len(data_bytes)
