#!/usr/bin/env python3
"""
Four-stage initialization process test script.
Demonstrates the coordinated work of device identity preparation, configuration management, and OTA configuration retrieval.
The activation process is implemented by the user.
"""

import asyncio
import json
from pathlib import Path
from typing import Dict

from src.constants.system import InitializationStage
from src.core.ota import Ota
from src.utils.config_manager import ConfigManager
from src.utils.device_fingerprint import DeviceFingerprint
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class SystemInitializer:
    """System Initializer - coordinates the four stages"""

    def __init__(self):
        self.device_fingerprint = None
        self.config_manager = None
        self.ota = None
        self.current_stage = None
        self.activation_data = None
        self.activation_status = {
            "local_activated": False,  # Local activation status
            "server_activated": False,  # Server activation status
            "status_consistent": True,  # Whether the statuses are consistent
        }

    async def run_initialization(self) -> Dict:
        """Run the complete initialization process.

        Returns:
            Dict: Initialization result, including activation status and whether an activation UI is needed.
        """
        logger.info("Starting system initialization process")

        try:
            # Stage 1: Device Identity Preparation
            await self.stage_1_device_fingerprint()

            # Stage 2: Configuration Management Initialization
            await self.stage_2_config_management()

            # Stage 3: OTA Configuration Retrieval
            await self.stage_3_ota_config()

            # Get activation version configuration
            activation_version = self.config_manager.get_config(
                "SYSTEM_OPTIONS.NETWORK.ACTIVATION_VERSION", "v1"
            )

            logger.info(f"Activation version: {activation_version}")

            # Decide whether an activation process is needed based on the activation version
            if activation_version == "v1":
                # v1 protocol: return success directly after completing the first three stages
                logger.info("v1 protocol: First three stages completed, no activation process needed")
                return {
                    "success": True,
                    "local_activated": True,
                    "server_activated": True,
                    "status_consistent": True,
                    "need_activation_ui": False,
                    "status_message": "v1 protocol initialization complete",
                    "activation_version": activation_version,
                }
            else:
                # v2 protocol: need to analyze activation status
                logger.info("v2 protocol: Analyzing activation status")
                activation_result = self.analyze_activation_status()
                activation_result["activation_version"] = activation_version

                # Decide whether an activation process is needed based on the analysis result
                if activation_result["need_activation_ui"]:
                    logger.info("Activation UI needs to be displayed")
                else:
                    logger.info("No need to display activation UI, device is already activated")

                return activation_result

        except Exception as e:
            logger.error(f"System initialization failed: {e}")
            return {"success": False, "error": str(e), "need_activation_ui": False}

    async def stage_1_device_fingerprint(self):
        """
        Stage 1: Device Identity Preparation.
        """
        self.current_stage = InitializationStage.DEVICE_FINGERPRINT
        logger.info(f"Starting {self.current_stage.value}")

        # Initialize device fingerprint
        self.device_fingerprint = DeviceFingerprint.get_instance()

        # Ensure device identity information is complete
        (
            serial_number,
            hmac_key,
            is_activated,
        ) = self.device_fingerprint.ensure_device_identity()

        # Record local activation status
        self.activation_status["local_activated"] = is_activated

        # Get MAC address and ensure lowercase format
        mac_address = self.device_fingerprint.get_mac_address_from_efuse()

        logger.info(f"Device serial number: {serial_number}")
        logger.info(f"MAC address: {mac_address}")
        logger.info(f"HMAC key: {hmac_key[:8] if hmac_key else None}...")
        logger.info(f"Local activation status: {'Activated' if is_activated else 'Not activated'}")

        # Verify if efuse.json file is complete
        efuse_file = Path("config/efuse.json")
        if efuse_file.exists():
            logger.info(f"efuse.json file location: {efuse_file.absolute()}")
            with open(efuse_file, "r", encoding="utf-8") as f:
                efuse_data = json.load(f)
            logger.debug(
                f"efuse.json content: "
                f"{json.dumps(efuse_data, indent=2, ensure_ascii=False)}"
            )
        else:
            logger.warning("efuse.json file does not exist")

        logger.info(f"Completed {self.current_stage.value}")

    async def stage_2_config_management(self):
        """
        Stage 2: Configuration Management Initialization.
        """
        self.current_stage = InitializationStage.CONFIG_MANAGEMENT
        logger.info(f"Starting {self.current_stage.value}")

        # Initialize configuration manager
        self.config_manager = ConfigManager.get_instance()

        # Ensure CLIENT_ID exists
        self.config_manager.initialize_client_id()

        # Initialize DEVICE_ID from device fingerprint
        self.config_manager.initialize_device_id_from_fingerprint(
            self.device_fingerprint
        )

        # Verify key configurations
        client_id = self.config_manager.get_config("SYSTEM_OPTIONS.CLIENT_ID")
        device_id = self.config_manager.get_config("SYSTEM_OPTIONS.DEVICE_ID")

        logger.info(f"Client ID: {client_id}")
        logger.info(f"Device ID: {device_id}")

        logger.info(f"Completed {self.current_stage.value}")

    async def stage_3_ota_config(self):
        """
        Stage 3: OTA Configuration Retrieval.
        """
        self.current_stage = InitializationStage.OTA_CONFIG
        logger.info(f"Starting {self.current_stage.value}")

        # Initialize OTA
        self.ota = await Ota.get_instance()

        # Get and update configuration
        try:
            config_result = await self.ota.fetch_and_update_config()

            logger.info("OTA configuration retrieval result:")
            mqtt_status = "Retrieved" if config_result["mqtt_config"] else "Not retrieved"
            logger.info(f"- MQTT configuration: {mqtt_status}")

            ws_status = "Retrieved" if config_result["websocket_config"] else "Not retrieved"
            logger.info(f"- WebSocket configuration: {ws_status}")

            # Display summary of retrieved configuration information
            response_data = config_result["response_data"]
            # Detailed configuration information is only displayed in debug mode
            logger.debug(
                f"OTA response data: {json.dumps(response_data, indent=2, ensure_ascii=False)}"
            )

            if "websocket" in response_data:
                ws_info = response_data["websocket"]
                logger.info(f"WebSocket URL: {ws_info.get('url', 'N/A')}")

            # Check for activation information
            if "activation" in response_data:
                logger.info("Activation information detected, device needs activation")
                self.activation_data = response_data["activation"]
                # Server considers the device not activated
                self.activation_status["server_activated"] = False
            else:
                logger.info("No activation information detected, device may be activated")
                self.activation_data = None
                # Server considers the device activated
                self.activation_status["server_activated"] = True

        except Exception as e:
            logger.error(f"OTA configuration retrieval failed: {e}")
            raise

        logger.info(f"Completed {self.current_stage.value}")

    def analyze_activation_status(self) -> Dict:
        """Analyze activation status to decide the subsequent process.

        Returns:
            Dict: Analysis result, including whether an activation UI is needed.
        """
        local_activated = self.activation_status["local_activated"]
        server_activated = self.activation_status["server_activated"]

        # Check if statuses are consistent
        status_consistent = local_activated == server_activated
        self.activation_status["status_consistent"] = status_consistent

        result = {
            "success": True,
            "local_activated": local_activated,
            "server_activated": server_activated,
            "status_consistent": status_consistent,
            "need_activation_ui": False,
            "status_message": "",
        }

        # Case 1: Locally not activated, server returns activation data - normal activation process
        if not local_activated and not server_activated:
            result["need_activation_ui"] = True
            result["status_message"] = "Device needs activation"

        # Case 2: Locally activated, server has no activation data - normal activated state
        elif local_activated and server_activated:
            result["need_activation_ui"] = False
            result["status_message"] = "Device is activated"

        # Case 3: Locally not activated, but server has no activation data - inconsistent state, auto-repair
        elif not local_activated and server_activated:
            logger.warning(
                "Inconsistent state: Locally not activated, but server considers it activated. Auto-repairing local state."
            )
            # Automatically update local state to activated
            self.device_fingerprint.set_activation_status(True)
            result["need_activation_ui"] = False
            result["status_message"] = "Activation status has been auto-repaired"
            result["local_activated"] = True  # Update status in the result

        # Case 4: Locally activated, but server returns activation data - inconsistent state, try to auto-repair
        elif local_activated and not server_activated:
            logger.warning("Inconsistent state: Locally activated, but server considers it not activated. Attempting to auto-repair.")

            # Check for activation data
            if self.activation_data and isinstance(self.activation_data, dict):
                # If there is an activation code, re-activation is needed
                if "code" in self.activation_data:
                    logger.info("Server returned an activation code, re-activation is needed")
                    result["need_activation_ui"] = True
                    result["status_message"] = "Inconsistent activation status, re-activation is needed"
                else:
                    # No activation code, server state may not be updated, try to continue using
                    logger.info("Server did not return an activation code, maintaining local activation status")
                    result["need_activation_ui"] = False
                    result["status_message"] = "Maintaining local activation status"
            else:
                # No activation data, could be a network issue, maintain local state
                logger.info("No activation data retrieved, maintaining local activation status")
                result["need_activation_ui"] = False
                result["status_message"] = "Maintaining local activation status"
                # Force update of status consistency to avoid repeated activation
                result["status_consistent"] = True
                self.activation_status["status_consistent"] = True
                self.activation_status["server_activated"] = True

        return result

    def get_activation_data(self):
        """
        Get activation data (for use by the activation module)
        """
        return getattr(self, "activation_data", None)

    def get_device_fingerprint(self):
        """
        Get the device fingerprint instance.
        """
        return self.device_fingerprint

    def get_config_manager(self):
        """
        Get the configuration manager instance.
        """
        return self.config_manager

    def get_activation_status(self) -> Dict:
        """
        Get activation status information.
        """
        return self.activation_status

    async def handle_activation_process(self, mode: str = "gui") -> Dict:
        """Handle the activation process, creating an activation UI if needed.

        Args:
            mode: UI mode, "gui" or "cli"

        Returns:
            Dict: Activation result
        """
        # Run the initialization process first
        init_result = await self.run_initialization()

        # If no activation UI is needed, return the result directly
        if not init_result.get("need_activation_ui", False):
            return {
                "is_activated": True,
                "device_fingerprint": self.device_fingerprint,
                "config_manager": self.config_manager,
            }

        # Activation UI is needed, create based on the mode
        if mode == "gui":
            return await self._run_gui_activation()
        else:
            return await self._run_cli_activation()

    async def _run_gui_activation(self) -> Dict:
        """Run the GUI activation process.

        Returns:
            Dict: Activation result
        """
        try:
            from src.views.activation.activation_window import ActivationWindow

            # Create activation window
            activation_window = ActivationWindow(self)

            # Create a Future to wait for activation to complete
            activation_future = asyncio.Future()

            # Set activation completion callback
            def on_activation_completed(success: bool):
                if not activation_future.done():
                    activation_future.set_result(success)

            # Set window close callback
            def on_window_closed():
                if not activation_future.done():
                    activation_future.set_result(False)

            # Connect signals
            activation_window.activation_completed.connect(on_activation_completed)
            activation_window.window_closed.connect(on_window_closed)

            # Show activation window
            activation_window.show()

            # Wait for activation to complete
            activation_success = await activation_future

            # Close window
            activation_window.close()

            return {
                "is_activated": activation_success,
                "device_fingerprint": self.device_fingerprint,
                "config_manager": self.config_manager,
            }

        except Exception as e:
            logger.error(f"GUI activation process exception: {e}", exc_info=True)
            return {"is_activated": False, "error": str(e)}

    async def _run_cli_activation(self) -> Dict:
        """Run the CLI activation process.

        Returns:
            Dict: Activation result
        """
        try:
            from src.views.activation.cli_activation import CLIActivation

            # Create CLI activation handler
            cli_activation = CLIActivation(self)

            # Run the activation process
            activation_success = await cli_activation.run_activation_process()

            return {
                "is_activated": activation_success,
                "device_fingerprint": self.device_fingerprint,
                "config_manager": self.config_manager,
            }

        except Exception as e:
            logger.error(f"CLI activation process exception: {e}", exc_info=True)
            return {"is_activated": False, "error": str(e)}
