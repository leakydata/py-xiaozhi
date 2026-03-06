"""
Camera tool for MCP - captures photos and analyzes them using vision APIs.

Supports two analysis backends:
1. VLCamera: OpenAI-compatible vision API (GPT-4o, local models, etc.)
   - Configure CAMERA.VLapi_key and CAMERA.Local_VL_url in config
2. NormalCamera: Server-provided vision endpoint (set automatically by backend)
   - Falls back to VLCamera for analysis if no server vision URL is available
"""

import asyncio
import json

from src.utils.config_manager import ConfigManager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Shared capture camera instance (always NormalCamera for OpenCV capture)
_capture_camera = None
# Vision analysis camera instance (VLCamera if configured)
_vision_camera = None


def get_camera_instance():
    """
    Return the appropriate camera implementation based on config.
    If VL API key and URL are configured, use VLCamera (OpenAI-compatible vision).
    Otherwise fall back to NormalCamera (HTTP-based remote analysis).
    """
    config = ConfigManager.get_instance()

    vl_key = config.get_config("CAMERA.VLapi_key")
    vl_url = config.get_config("CAMERA.Local_VL_url")

    if vl_key and vl_url:
        from .vl_camera import VLCamera

        logger.info(f"Using vision camera with URL: {vl_url}")
        return VLCamera.get_instance()

    from .normal_camera import NormalCamera

    logger.info("VL configuration not found, using normal camera implementation")
    return NormalCamera.get_instance()


def _get_vision_analyzer():
    """
    Get a VLCamera instance for analysis if configured, even when the
    primary camera is NormalCamera. Returns None if no VL API is configured.
    """
    global _vision_camera
    if _vision_camera is not None:
        return _vision_camera

    config = ConfigManager.get_instance()
    vl_key = config.get_config("CAMERA.VLapi_key")
    vl_url = config.get_config("CAMERA.Local_VL_url")

    if vl_key and vl_url:
        from .vl_camera import VLCamera

        _vision_camera = VLCamera.get_instance()
        return _vision_camera

    return None


async def take_photo(arguments: dict) -> str:
    """
    Capture a photo and analyze it. Runs blocking camera I/O in a thread pool
    to avoid blocking the async event loop.

    Analysis pipeline:
    1. Try the primary camera's analyze() method
    2. If that fails (e.g. no server vision URL), try VLCamera as fallback
    3. If nothing works, return the captured image info with setup instructions
    """
    camera = get_camera_instance()
    logger.info(f"Using camera: {camera.__class__.__name__}")

    question = arguments.get("question", "")
    logger.info(f"Taking photo with question: {question}")

    loop = asyncio.get_event_loop()

    # Run capture in thread pool (blocking OpenCV call)
    success = await loop.run_in_executor(None, camera.capture)
    if not success:
        logger.error("Failed to capture photo")
        return json.dumps({
            "success": False,
            "message": "Failed to capture photo. Check camera connection and camera_index in config.",
        })

    # Run analysis in thread pool (blocking HTTP/API call)
    logger.info("Photo captured, starting analysis...")
    result_str = await loop.run_in_executor(None, camera.analyze, question)

    # Check if the primary analysis succeeded
    try:
        result = json.loads(result_str)
        if result.get("success") is False:
            # Primary analysis failed, try VLCamera fallback
            vl_camera = _get_vision_analyzer()
            if vl_camera and vl_camera is not camera:
                logger.info("Primary analysis failed, trying VLCamera fallback...")
                # Copy the captured JPEG data to VLCamera
                vl_camera.set_jpeg_data(camera.jpeg_data["buf"])
                result_str = await loop.run_in_executor(None, vl_camera.analyze, question)
                result = json.loads(result_str)

            # If still failing, give helpful error
            if result.get("success") is False:
                return json.dumps({
                    "success": False,
                    "message": (
                        "Photo captured successfully but no vision analysis service is available. "
                        "To enable image analysis, set CAMERA.VLapi_key and CAMERA.Local_VL_url "
                        "in your config. Supports any OpenAI-compatible vision API "
                        "(e.g. GPT-4o at https://api.openai.com/v1)."
                    ),
                    "image_captured": True,
                    "image_size_bytes": camera.jpeg_data["len"],
                })
    except (json.JSONDecodeError, KeyError):
        pass  # If we can't parse the result, just return it as-is

    return result_str
