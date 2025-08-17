#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# Filename: camera_scanner.py

import json
import logging
import sys
import time
from pathlib import Path

import cv2

# Import the ConfigManager class
from src.utils.config_manager import ConfigManager

# Add the project root to the system path to import modules from src
project_root = Path(__file__).parent.parent
sys.path.append(str(project_root))

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("CameraScanner")


def get_camera_capabilities(cam):
    """
    Get the parameters and capabilities of the camera.
    """
    capabilities = {}

    # Get available resolutions
    standard_resolutions = [
        (640, 480),  # VGA
        (800, 600),  # SVGA
        (1024, 768),  # XGA
        (1280, 720),  # HD
        (1280, 960),  # 4:3 HD
        (1920, 1080),  # Full HD
        (2560, 1440),  # QHD
        (3840, 2160),  # 4K UHD
    ]

    supported_resolutions = []
    original_width = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH))
    original_height = int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))

    # Record the original resolution
    capabilities["default_resolution"] = (original_width, original_height)

    # Test standard resolutions
    for width, height in standard_resolutions:
        cam.set(cv2.CAP_PROP_FRAME_WIDTH, width)
        cam.set(cv2.CAP_PROP_FRAME_HEIGHT, height)
        actual_width = int(cam.get(cv2.CAP_PROP_FRAME_WIDTH))
        actual_height = int(cam.get(cv2.CAP_PROP_FRAME_HEIGHT))

        # If the setting is successful (actual resolution matches the requested one)
        if actual_width == width and actual_height == height:
            supported_resolutions.append((width, height))

    # Restore the original resolution
    cam.set(cv2.CAP_PROP_FRAME_WIDTH, original_width)
    cam.set(cv2.CAP_PROP_FRAME_HEIGHT, original_height)

    capabilities["supported_resolutions"] = supported_resolutions

    # Get the frame rate
    fps = int(cam.get(cv2.CAP_PROP_FPS))
    capabilities["fps"] = fps if fps > 0 else 30  # Default to 30fps

    # Get the backend name
    backend_name = cam.getBackendName()
    capabilities["backend"] = backend_name

    return capabilities


def detect_cameras():
    """
    Detect and list all available cameras.
    """
    print("\n===== Camera Device Detection =====\n")

    # Get the ConfigManager instance
    config_manager = ConfigManager.get_instance()

    # Get the current camera configuration
    current_camera_config = config_manager.get_config("CAMERA", {})
    logger.info(f"Current camera configuration: {current_camera_config}")

    # Display the current configuration
    if current_camera_config:
        print("Current camera configuration:")
        print(f"  - Index: {current_camera_config.get('camera_index', 'Not set')}")
        print(f"  - Resolution: {current_camera_config.get('frame_width', 'Not set')}x{current_camera_config.get('frame_height', 'Not set')}")
        print(f"  - FPS: {current_camera_config.get('fps', 'Not set')}")
        print(f"  - VL Model: {current_camera_config.get('models', 'Not set')}")
        print("")

    # Store found devices
    camera_devices = []

    # Try to open multiple camera indices
    max_cameras_to_check = 10  # Check up to 10 camera indices

    for i in range(max_cameras_to_check):
        try:
            # Try to open the camera
            cap = cv2.VideoCapture(i)

            if cap.isOpened():
                # Get camera information
                device_name = f"Camera {i}"
                try:
                    # On some systems, it might be possible to get the device name
                    device_name = cap.getBackendName() + f" Camera {i}"
                except Exception as e:
                    logger.warning(f"Failed to get device {i} name: {e}")

                # Read a frame to ensure the camera is working properly
                ret, frame = cap.read()
                if not ret:
                    print(f"Device {i}: Opened successfully but cannot read frame, skipping")
                    cap.release()
                    continue

                # Get camera capabilities
                capabilities = get_camera_capabilities(cap)

                # Print device information
                width, height = capabilities["default_resolution"]
                resolutions_str = ", ".join(
                    [f"{w}x{h}" for w, h in capabilities["supported_resolutions"]]
                )

                print(f"Device {i}: {device_name}")
                print(f"  - Default Resolution: {width}x{height}")
                print(f"  - Supported Resolutions: {resolutions_str}")
                print(f"  - FPS: {capabilities['fps']}")
                print(f"  - Backend: {capabilities['backend']}")
                
                # Mark the camera used in the current configuration
                current_index = current_camera_config.get('camera_index')
                if current_index == i:
                    print(f"  - 📹 Camera used in current configuration")
                
                print("")

                # Add to the device list
                camera_devices.append(
                    {"index": i, "name": device_name, "capabilities": capabilities}
                )

                # Test camera functionality
                print(f"Testing camera functionality for device {i}...")
                try:
                    # Quick test - read a few frames
                    test_frames = 0
                    start_time = time.time()
                    
                    while test_frames < 10 and time.time() - start_time < 2:
                        ret, frame = cap.read()
                        if ret:
                            test_frames += 1
                        else:
                            break
                    
                    if test_frames >= 5:
                        print(f"  ✓ Camera functionality is normal (tested reading {test_frames} frames)")
                    else:
                        print(f"  ⚠ Camera functionality might be abnormal (only read {test_frames} frames)")
                        
                except Exception as e:
                    print(f"  ✗ Camera functionality test failed: {e}")

                # Ask whether to show a preview
                print(f"Show preview for device {i}? (y/n, default n): ", end="")
                show_preview = input().strip().lower()
                
                if show_preview == 'y':
                    print(f"Showing preview for device {i}, press 'q' or wait 3 seconds to continue...")
                    preview_start = time.time()

                    while time.time() - preview_start < 3:
                        ret, frame = cap.read()
                        if ret:
                            cv2.imshow(f"Camera {i} Preview", frame)
                            if cv2.waitKey(1) & 0xFF == ord("q"):
                                break

                    cv2.destroyAllWindows()
                
                cap.release()

            else:
                # If two consecutive indices fail to open, assume there are no more cameras
                consecutive_failures = 0
                for j in range(i, i + 2):
                    temp_cap = cv2.VideoCapture(j)
                    if not temp_cap.isOpened():
                        consecutive_failures += 1
                    temp_cap.release()

                if consecutive_failures >= 2 and i > 0:
                    break

        except Exception as e:
            print(f"Error while detecting device {i}: {e}")

    # Summarize found devices
    print("\n===== Device Summary =====\n")

    if not camera_devices:
        print("No available camera devices found!")
        return None

    print(f"Found {len(camera_devices)} camera devices:")
    for device in camera_devices:
        width, height = device["capabilities"]["default_resolution"]
        print(f"  - Device {device['index']}: {device['name']}")
        print(f"    Resolution: {width}x{height}")

    # Recommend the best device
    print("\n===== Recommended Device =====\n")

    # Prefer HD cameras, then the one with the highest resolution
    recommended_camera = None
    highest_resolution = 0

    for device in camera_devices:
        width, height = device["capabilities"]["default_resolution"]
        resolution = width * height

        # If it's HD or higher resolution
        if width >= 1280 and height >= 720:
            if resolution > highest_resolution:
                highest_resolution = resolution
                recommended_camera = device
        elif recommended_camera is None or resolution > highest_resolution:
            highest_resolution = resolution
            recommended_camera = device

    # Print the recommended device
    if recommended_camera:
        r_width, r_height = recommended_camera["capabilities"]["default_resolution"]
        print(
            f"Recommended camera: Device {recommended_camera['index']} "
            f"({recommended_camera['name']})"
        )
        print(f"  - Resolution: {r_width}x{r_height}")
        print(f"  - FPS: {recommended_camera['capabilities']['fps']}")

    # Get VL API information from the existing configuration
    vl_url = current_camera_config.get(
        "Loacl_VL_url", "https://open.bigmodel.cn/api/paas/v4/"
    )
    vl_api_key = current_camera_config.get("VLapi_key", "your_own_key")
    model = current_camera_config.get("models", "glm-4v-plus")

    # Generate a configuration file example
    print("\n===== Configuration File Example =====\n")

    if recommended_camera:
        new_camera_config = {
            "camera_index": recommended_camera["index"],
            "frame_width": r_width,
            "frame_height": r_height,
            "fps": recommended_camera["capabilities"]["fps"],
            "Local_VL_url": vl_url,  # Keep the original value
            "VLapi_key": vl_api_key,  # Keep the original value
            "models": model,  # Keep the original value
        }

        print("Recommended camera configuration:")
        print(json.dumps(new_camera_config, indent=2, ensure_ascii=False))

        # Compare configuration changes
        print("\n===== Configuration Change Comparison =====\n")
        current_index = current_camera_config.get('camera_index')
        current_width = current_camera_config.get('frame_width')
        current_height = current_camera_config.get('frame_height')
        current_fps = current_camera_config.get('fps')
        
        changes = []
        if current_index != recommended_camera["index"]:
            changes.append(f"Camera Index: {current_index} → {recommended_camera['index']}")
        if current_width != r_width or current_height != r_height:
            changes.append(f"Resolution: {current_width}x{current_height} → {r_width}x{r_height}")
        if current_fps != recommended_camera["capabilities"]["fps"]:
            changes.append(f"FPS: {current_fps} → {recommended_camera['capabilities']['fps']}")
        
        if changes:
            print("The following configuration changes were detected:")
            for change in changes:
                print(f"  - {change}")
        else:
            print("Recommended configuration is the same as the current one, no update needed")

        # Ask whether to update the configuration file
        if changes:
            print("\nDo you want to update the camera configuration in the config file? (y/n): ", end="")
            choice = input().strip().lower()

            if choice == "y":
                try:
                    # Use ConfigManager to update the configuration
                    success = config_manager.update_config("CAMERA", new_camera_config)

                    if success:
                        print("\n✓ Camera configuration successfully updated in config.json!")
                        print("\n===== Latest Configuration =====\n")
                        updated_config = config_manager.get_config("CAMERA", {})
                        print(json.dumps(updated_config, indent=2, ensure_ascii=False))
                    else:
                        print("\n✗ Failed to update camera configuration!")

                except Exception as e:
                    logger.error(f"Error while updating configuration: {e}")
                    print(f"\n✗ Error while updating configuration: {e}")
            else:
                print("\nConfiguration not updated")
    else:
        print("No recommended camera configuration found")

    return camera_devices


if __name__ == "__main__":
    try:
        cameras = detect_cameras()
        if cameras:
            print(f"\nDetected {len(cameras)} camera devices!")
        else:
            print("\nNo available camera devices detected!")
    except Exception as e:
        logger.error(f"An error occurred during detection: {e}")
        print(f"An error occurred during detection: {e}")
