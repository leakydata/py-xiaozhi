"""System tools implementation.

Provides specific system tool functionality.
"""

import asyncio
import json
from typing import Any, Dict

from src.utils.logging_config import get_logger

from .device_status import get_device_status

logger = get_logger(__name__)


async def get_system_status(args: Dict[str, Any]) -> str:
    """
    Get the complete system status.
    """
    try:
        logger.info("[SystemTools] Starting to get system status")

        # Use a thread pool to execute synchronous device status retrieval to avoid blocking the event loop
        status = await asyncio.to_thread(get_device_status)

        # Add audio/volume status information
        audio_status = await _get_audio_status()
        status["audio_speaker"] = audio_status

        # Add application status information
        app_status = _get_application_status()
        status["application"] = app_status

        logger.info("[SystemTools] System status obtained successfully")
        return json.dumps(status, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"[SystemTools] Failed to get system status: {e}", exc_info=True)
        # Return default status
        fallback_status = {
            "error": str(e),
            "audio_speaker": {"volume": 50, "muted": False, "available": False},
            "application": {"device_state": "unknown", "iot_devices": 0},
        }
        return json.dumps(fallback_status, ensure_ascii=False)


async def set_volume(args: Dict[str, Any]) -> bool:
    """
    Set the volume.
    """
    try:
        volume = args["volume"]
        logger.info(f"[SystemTools] Setting volume to {volume}")

        # Validate volume range
        if not (0 <= volume <= 100):
            logger.warning(f"[SystemTools] Volume value out of range: {volume}")
            return False

        # Directly use VolumeController to set volume
        from src.utils.volume_controller import VolumeController

        # Check dependencies and create volume controller
        if not VolumeController.check_dependencies():
            logger.warning("[SystemTools] Volume control dependencies are incomplete, cannot set volume")
            return False

        volume_controller = VolumeController()
        await asyncio.to_thread(volume_controller.set_volume, volume)
        logger.info(f"[SystemTools] Volume set successfully: {volume}")
        return True

    except KeyError:
        logger.error("[SystemTools] Missing volume parameter")
        return False
    except Exception as e:
        logger.error(f"[SystemTools] Failed to set volume: {e}", exc_info=True)
        return False


async def _get_audio_status() -> Dict[str, Any]:
    """
    Get audio status.
    """
    try:
        from src.utils.volume_controller import VolumeController

        if VolumeController.check_dependencies():
            volume_controller = VolumeController()
            # Use a thread pool to get volume to avoid blocking
            current_volume = await asyncio.to_thread(volume_controller.get_volume)
            return {
                "volume": current_volume,
                "muted": current_volume == 0,
                "available": True,
            }
        else:
            return {
                "volume": 50,
                "muted": False,
                "available": False,
                "reason": "Dependencies not available",
            }

    except Exception as e:
        logger.warning(f"[SystemTools] Failed to get audio status: {e}")
        return {"volume": 50, "muted": False, "available": False, "error": str(e)}


def _get_application_status() -> Dict[str, Any]:
    """
    Get application status information.
    """
    try:
        from src.application import Application
        from src.iot.thing_manager import ThingManager

        app = Application.get_instance()
        thing_manager = ThingManager.get_instance()

        # The value of DeviceState is a string directly, no need to access the .name attribute
        device_state = str(app.device_state)
        iot_count = len(thing_manager.things) if thing_manager else 0

        return {
            "device_state": device_state,
            "iot_devices": iot_count,
        }

    except Exception as e:
        logger.warning(f"[SystemTools] Failed to get application status: {e}")
        return {"device_state": "unknown", "iot_devices": 0, "error": str(e)}
