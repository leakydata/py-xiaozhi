import threading

import cv2
import requests

from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class Camera:
    _instance = None
    _lock = threading.Lock()  # Thread safe

    def __init__(self):
        self.explain_url = ""
        self.explain_token = ""
        self.jpeg_data = {"buf": b"", "len": 0}  # JPEG byte data of the image  # Length of the byte data

        # Read camera parameters from configuration
        config = ConfigManager.get_instance()
        self.camera_index = config.get_config("CAMERA.camera_index", 0)
        self.frame_width = config.get_config("CAMERA.frame_width", 640)
        self.frame_height = config.get_config("CAMERA.frame_height", 480)

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def set_explain_url(self, url):
        """
        Set the URL for the explanation service.
        """
        self.explain_url = url
        logger.info(f"Vision service URL set to: {url}")

    def set_explain_token(self, token):
        """
        Set the token for the explanation service.
        """
        self.explain_token = token
        if token:
            logger.info("Vision service token has been set")

    def set_jpeg_data(self, data_bytes):
        """
        Set the JPEG image data.
        """
        self.jpeg_data["buf"] = data_bytes
        self.jpeg_data["len"] = len(data_bytes)

    def capture(self) -> bool:
        """
        Capture an image.
        """
        try:
            logger.info("Accessing camera...")

            # Try to open the camera
            cap = cv2.VideoCapture(self.camera_index)
            if not cap.isOpened():
                logger.error(f"Cannot open camera at index {self.camera_index}")
                return False

            # Set camera parameters
            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)

            # Read the image
            ret, frame = cap.read()
            cap.release()

            if not ret:
                logger.error("Failed to capture image")
                return False

            # Get original image dimensions
            height, width = frame.shape[:2]

            # Calculate scaling factor to make the longest side 320
            max_dim = max(height, width)
            scale = 320 / max_dim if max_dim > 320 else 1.0

            # Scale the image proportionally
            if scale < 1.0:
                new_width = int(width * scale)
                new_height = int(height * scale)
                frame = cv2.resize(
                    frame, (new_width, new_height), interpolation=cv2.INTER_AREA
                )

            # Directly encode the image into a JPEG byte stream
            success, jpeg_data = cv2.imencode(".jpg", frame)

            if not success:
                logger.error("Failed to encode image to JPEG")
                return False

            # Get byte data
            self.jpeg_data["buf"] = jpeg_data.tobytes()
            self.jpeg_data["len"] = len(self.jpeg_data["buf"])
            logger.info(
                f"Image captured successfully (size: {self.jpeg_data['len']} bytes)"
            )
            return True

        except Exception as e:
            logger.error(f"Exception during capture: {e}")
            return False

    def get_device_id(self):
        """
        Get the device ID.
        """
        return ConfigManager.get_instance().get_config("SYSTEM_OPTIONS.DEVICE_ID")

    def get_client_id(self):
        """
        Get the client ID.
        """
        return ConfigManager.get_instance().get_config("SYSTEM_OPTIONS.CLIENT_ID")

    def explain(self, question: str) -> str:
        """
        Send an image analysis request.
        """
        if not self.explain_url:
            return '{"success": false, "message": "Image explain URL is not set"}'

        if not self.jpeg_data["buf"]:
            return '{"success": false, "message": "Camera buffer is empty"}'

        # Prepare request headers
        headers = {"Device-Id": self.get_device_id(), "Client-Id": self.get_client_id()}

        if self.explain_token:
            headers["Authorization"] = f"Bearer {self.explain_token}"

        # Prepare file data
        files = {
            "question": (None, question),
            "file": ("camera.jpg", self.jpeg_data["buf"], "image/jpeg"),
        }

        try:
            # Send the request
            response = requests.post(
                self.explain_url, headers=headers, files=files, timeout=10
            )

            # Check the response status
            if response.status_code != 200:
                error_msg = (
                    f"Failed to upload photo, status code: {response.status_code}"
                )
                logger.error(error_msg)
                return f'{{"success": false, "message": "{error_msg}"}}'

            # Log the response
            logger.info(
                f"Explain image size={self.jpeg_data['len']}, "
                f"question={question}\n{response.text}"
            )
            return response.text

        except requests.RequestException as e:
            error_msg = f"Failed to connect to explain URL: {str(e)}"
            logger.error(error_msg)
            return f'{{"success": false, "message": "{error_msg}"}}'


def take_photo(arguments: dict) -> str:
    """
    Tool function to take a photo and explain it.
    """
    camera = Camera.get_instance()
    question = arguments.get("question", "")

    # Take a photo
    success = camera.capture()
    if not success:
        return '{"success": false, "message": "Failed to capture photo"}'

    # Send an explanation request
    return camera.explain(question)
