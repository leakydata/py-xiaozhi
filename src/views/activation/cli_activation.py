# -*- coding: utf-8 -*-
"""
CLI mode device activation process. Provides the same functionality as the GUI activation window, but using pure terminal output.
"""

from datetime import datetime
from typing import Optional

from src.core.system_initializer import SystemInitializer
from src.utils.device_activator import DeviceActivator
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class CLIActivation:
    """
    CLI mode device activation handler.
    """

    def __init__(self, system_initializer: Optional[SystemInitializer] = None):
        # Component instances
        self.system_initializer = system_initializer
        self.device_activator: Optional[DeviceActivator] = None

        # State management
        self.current_stage = None
        self.activation_data = None
        self.is_activated = False

        self.logger = logger

    async def run_activation_process(self) -> bool:
        """Run the complete CLI activation process.

        Returns:
            bool: Whether the activation was successful
        """
        try:
            self._print_header()

            # If a SystemInitializer instance is already provided, use it directly
            if self.system_initializer:
                self._log_and_print("Using an initialized system")
                self._update_device_info()
                return await self._start_activation_process()
            else:
                # Otherwise, create a new instance and run initialization
                self._log_and_print("Starting system initialization process")
                self.system_initializer = SystemInitializer()

                # Run the initialization process
                init_result = await self.system_initializer.run_initialization()

                if init_result.get("success", False):
                    self._update_device_info()

                    # Display status message
                    status_message = init_result.get("status_message", "")
                    if status_message:
                        self._log_and_print(status_message)

                    # Check if activation is needed
                    if init_result.get("need_activation_ui", True):
                        return await self._start_activation_process()
                    else:
                        # No activation needed, complete directly
                        self.is_activated = True
                        self._log_and_print("Device is already activated, no further action needed")
                        return True
                else:
                    error_msg = init_result.get("error", "Initialization failed")
                    self._log_and_print(f"Error: {error_msg}")
                    return False

        except KeyboardInterrupt:
            self._log_and_print("\nUser interrupted the activation process")
            return False
        except Exception as e:
            self.logger.error(f"CLI activation process exception: {e}", exc_info=True)
            self._log_and_print(f"Activation exception: {e}")
            return False

    def _print_header(self):
        """
        Print the CLI activation process header information.
        """
        print("\n" + "=" * 60)
        print("Xiaozhi AI Client - Device Activation Process")
        print("=" * 60)
        print("Initializing device, please wait...")
        print()

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

        # Get device information
        serial_number = device_fp.get_serial_number()
        mac_address = device_fp.get_mac_address_from_efuse()

        # Get activation status
        activation_status = self.system_initializer.get_activation_status()
        local_activated = activation_status.get("local_activated", False)
        server_activated = activation_status.get("server_activated", False)
        status_consistent = activation_status.get("status_consistent", True)

        # Update activation status
        self.is_activated = local_activated

        # Display device information
        print("📱 Device Information:")
        print(f"   Serial Number: {serial_number if serial_number else '--'}")
        print(f"   MAC Address: {mac_address if mac_address else '--'}")

        # Display activation status
        if not status_consistent:
            if local_activated and not server_activated:
                status_text = "Status inconsistent (reactivation required)"
            else:
                status_text = "Status inconsistent (automatically repaired)"
        else:
            status_text = "Activated" if local_activated else "Not Activated"

        print(f"   Activation Status: {status_text}")

    async def _start_activation_process(self) -> bool:
        """
        Start the activation process.
        """
        try:
            # Get activation data
            activation_data = self.system_initializer.get_activation_data()

            if not activation_data:
                self._log_and_print("\nFailed to get activation data")
                print("Error: Failed to get activation data, please check your network connection")
                return False

            self.activation_data = activation_data

            # Display activation information
            self._show_activation_info(activation_data)

            # Initialize device activator
            config_manager = self.system_initializer.get_config_manager()
            self.device_activator = DeviceActivator(config_manager)

            # Start the activation process
            self._log_and_print("\nStarting device activation process...")
            print("Connecting to activation server, please maintain network connection...")

            activation_success = await self.device_activator.process_activation(
                activation_data
            )

            if activation_success:
                self._log_and_print("\nDevice activation successful!")
                self._print_activation_success()
                return True
            else:
                self._log_and_print("\nDevice activation failed")
                self._print_activation_failure()
                return False

        except Exception as e:
            self.logger.error(f"Activation process exception: {e}", exc_info=True)
            self._log_and_print(f"\nActivation exception: {e}")
            return False

    def _show_activation_info(self, activation_data: dict):
        """
        Show activation information.
        """
        code = activation_data.get("code", "------")
        message = activation_data.get("message", "Please visit xiaozhi.me and enter the verification code")

        print("\n" + "=" * 60)
        print("Device Activation Information")
        print("=" * 60)
        print(f"Activation Code: {code}")
        print(f"Activation Instructions: {message}")
        print("=" * 60)

        # Format and display the verification code (with spaces between characters)
        formatted_code = " ".join(code)
        print(f"\nVerification Code (please enter on the website): {formatted_code}")
        print("\nPlease follow the steps below to complete activation:")
        print("1. Open a browser and visit xiaozhi.me")
        print("2. Log in to your account")
        print("3. Select 'Add Device'")
        print(f"4. Enter the verification code: {formatted_code}")
        print("5. Confirm adding the device")
        print("\nWaiting for activation confirmation, please complete the operation on the website...")

        self._log_and_print(f"Activation Code: {code}")
        self._log_and_print(f"Activation Instructions: {message}")

    def _print_activation_success(self):
        """
        Print activation success message.
        """
        print("\n" + "=" * 60)
        print("Device activation successful!")
        print("=" * 60)
        print("The device has been successfully added to your account")
        print("Configuration has been updated automatically")
        print("Preparing to launch Xiaozhi AI Client...")
        print("=" * 60)

    def _print_activation_failure(self):
        """
        Print activation failure message.
        """
        print("\n" + "=" * 60)
        print("Device activation failed")
        print("=" * 60)
        print("Possible reasons:")
        print("• Unstable network connection")
        print("• Incorrect or expired verification code")
        print("• Server is temporarily unavailable")
        print("\nSolutions:")
        print("• Check your network connection")
        print("• Rerun the program to get a new verification code")
        print("• Ensure the verification code is entered correctly on the website")
        print("=" * 60)

    def _log_and_print(self, message: str):
        """
        Log the message and print it to the terminal.
        """
        timestamp = datetime.now().strftime("%H:%M:%S")
        log_message = f"[{timestamp}] {message}"
        print(log_message)
        self.logger.info(message)

    def get_activation_result(self) -> dict:
        """
        Get the activation result.
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
