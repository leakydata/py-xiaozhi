"""
Vision camera implementation using any OpenAI-compatible API (GPT-4o, local LLMs, etc).
"""

import base64
import json

import cv2
from openai import OpenAI

from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger

from .base_camera import BaseCamera

logger = get_logger(__name__)


class VLCamera(BaseCamera):
    """
    Vision-Language camera using OpenAI-compatible API for image analysis.
    Works with GPT-4o, GPT-4-turbo, local vision models, or any provider
    that supports the OpenAI chat completions format with image_url.
    """

    _instance = None

    def __init__(self):
        super().__init__()
        config = ConfigManager.get_instance()

        api_key = config.get_config("CAMERA.VLapi_key", "")
        base_url = config.get_config("CAMERA.Local_VL_url", "https://api.openai.com/v1")
        self.model = config.get_config("CAMERA.models", "gpt-4o")

        self.client = OpenAI(api_key=api_key, base_url=base_url)
        logger.info(f"Vision camera initialized - model: {self.model}, base_url: {base_url}")

    @classmethod
    def get_instance(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
        return cls._instance

    def capture(self) -> bool:
        """Capture an image from the webcam."""
        try:
            logger.info("Accessing camera...")
            cap = cv2.VideoCapture(self.camera_index)
            if not cap.isOpened():
                logger.error(f"Cannot open camera at index {self.camera_index}")
                return False

            cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.frame_width)
            cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.frame_height)

            # Read a few frames to let the camera auto-expose properly
            for _ in range(3):
                cap.read()

            ret, frame = cap.read()
            cap.release()

            if not ret:
                logger.error("Failed to capture image")
                return False

            # Scale to reasonable size for vision API (max 1024px, not 320)
            height, width = frame.shape[:2]
            max_dim = max(height, width)
            if max_dim > 1024:
                scale = 1024 / max_dim
                new_width = int(width * scale)
                new_height = int(height * scale)
                frame = cv2.resize(frame, (new_width, new_height), interpolation=cv2.INTER_AREA)

            # Encode to JPEG with good quality
            success, jpeg_data = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, 85])
            if not success:
                logger.error("Failed to encode image to JPEG")
                return False

            self.set_jpeg_data(jpeg_data.tobytes())
            logger.info(f"Image captured ({frame.shape[1]}x{frame.shape[0]}, {self.jpeg_data['len']} bytes)")
            return True

        except Exception as e:
            logger.error(f"Exception during capture: {e}")
            return False

    def analyze(self, question: str) -> str:
        """Analyze the captured image using the vision API."""
        try:
            if not self.jpeg_data["buf"]:
                return json.dumps({"success": False, "message": "Camera buffer is empty"})

            image_base64 = base64.b64encode(self.jpeg_data["buf"]).decode("utf-8")

            default_question = "Describe what you see in this image in detail."
            messages = [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/jpeg;base64,{image_base64}",
                                "detail": "auto",
                            },
                        },
                        {
                            "type": "text",
                            "text": question if question else default_question,
                        },
                    ],
                },
            ]

            completion = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                max_tokens=1024,
            )

            result = completion.choices[0].message.content or ""
            logger.info(f"Vision analysis complete, question={question}")
            return json.dumps({"success": True, "text": result})

        except Exception as e:
            error_msg = f"Vision analysis failed: {str(e)}"
            logger.error(error_msg)
            return json.dumps({"success": False, "message": error_msg})
