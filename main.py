import argparse
import asyncio
import sys
import time

from src.application import Application
from src.utils.logging_config import get_logger, setup_logging

logger = get_logger(__name__)


def parse_args():
    """
    Parse command line arguments.
    """
    parser = argparse.ArgumentParser(description="Xiaozhi AI Client")
    parser.add_argument(
        "--mode",
        choices=["gui", "cli"],
        default="gui",
        help="Running mode: gui (graphical interface) or cli (command line)",
    )
    parser.add_argument(
        "--protocol",
        choices=["mqtt", "websocket"],
        default="websocket",
        help="Communication protocol: mqtt or websocket",
    )
    parser.add_argument(
        "--skip-activation",
        action="store_true",
        help="Skip the activation process and start the application directly (for debugging only)",
    )
    return parser.parse_args()


async def handle_activation(mode: str) -> bool:
    """Handle device activation process.

    Args:
        mode: Running mode, "gui" or "cli"

    Returns:
        bool: Whether the activation is successful
    """
    try:
        from src.core.system_initializer import SystemInitializer

        logger.info("Start device activation process check...")

        # Create SystemInitializer instance
        system_initializer = SystemInitializer()

        # Run initialization process
        init_result = await system_initializer.run_initialization()

        # Check if initialization is successful
        if not init_result.get("success", False):
            logger.error(f"System initialization failed: {init_result.get('error', 'Unknown error')}")
            return False

        # Get activation version
        activation_version = init_result.get("activation_version", "v1")
        logger.info(f"Current activation version: {activation_version}")

        # If it is v1 protocol, return success directly
        if activation_version == "v1":
            logger.info("v1 protocol: System initialization is complete, no activation process is required")
            return True

        # If it is v2 protocol, check if activation interface is needed
        if not init_result.get("need_activation_ui", False):
            logger.info("v2 protocol: No need to display the activation interface, the device is already activated")
            return True

        logger.info("v2 protocol: Need to display the activation interface, prepare for the activation process")

        # Need activation interface, process according to mode
        if mode == "gui":
            # GUI mode needs to create QApplication first
            try:
                # Import necessary libraries
                import qasync
                from PyQt5.QtCore import QTimer
                from PyQt5.QtWidgets import QApplication

                # Create a temporary QApplication instance
                logger.info("Create a temporary QApplication instance for the activation process")
                temp_app = QApplication(sys.argv)

                # Create event loop
                loop = qasync.QEventLoop(temp_app)
                asyncio.set_event_loop(loop)

                # Create a Future to wait for activation to complete (using a new event loop)
                activation_future = loop.create_future()

                # Create activation window
                from src.views.activation.activation_window import ActivationWindow

                activation_window = ActivationWindow(system_initializer)

                # Set activation completion callback
                def on_activation_completed(success: bool):
                    logger.info(f"Activation completed, result: {success}")
                    if not activation_future.done():
                        activation_future.set_result(success)

                # Set window closing callback
                def on_window_closed():
                    logger.info("Activation window was closed")
                    if not activation_future.done():
                        activation_future.set_result(False)

                # Connect signal
                activation_window.activation_completed.connect(on_activation_completed)
                activation_window.window_closed.connect(on_window_closed)

                # Show activation window
                activation_window.show()
                logger.info("Activation window has been displayed")

                # Make sure the window is displayed
                QTimer.singleShot(100, lambda: logger.info("Activation window display confirmation"))

                # Start waiting for activation to complete
                try:
                    logger.info("Start waiting for activation to complete")
                    activation_success = loop.run_until_complete(activation_future)
                    logger.info(f"Activation process completed, result: {activation_success}")
                except Exception as e:
                    logger.error(f"Activation process exception: {e}")
                    activation_success = False

                # Close window
                activation_window.close()

                # Destroy temporary QApplication
                logger.info("Activation process is complete, destroy the temporary QApplication instance")
                activation_window = None
                temp_app = None

                # Force garbage collection to ensure QApplication is destroyed
                import gc

                gc.collect()

                # Wait for a short period of time to ensure that resources are released (using synchronous sleep)
                logger.info("Waiting for resource release...")
                time.sleep(0.5)

                return activation_success

            except ImportError as e:
                logger.error(f"GUI mode requires qasync and PyQt5 libraries: {e}")
                return False
        else:
            # CLI mode
            from src.views.activation.cli_activation import CLIActivation

            cli_activation = CLIActivation(system_initializer)
            return await cli_activation.run_activation_process()

    except Exception as e:
        logger.error(f"Activation process exception: {e}", exc_info=True)
        return False


async def main():
    """
    Main function.
    """
    setup_logging()
    args = parse_args()

    logger.info("Start Xiaozhi AI client")

    # Handle activation process
    if not args.skip_activation:
        activation_success = await handle_activation(args.mode)
        if not activation_success:
            logger.error("Device activation failed, program exits")
            return 1
    else:
        logger.warning("Skip activation process (debug mode)")

    # Create and start the application
    app = Application.get_instance()
    return await app.run(mode=args.mode, protocol=args.protocol)


if __name__ == "__main__":
    try:
        sys.exit(asyncio.run(main()))
    except KeyboardInterrupt:
        logger.info("Program was interrupted by the user")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Program exited abnormally: {e}", exc_info=True)
        sys.exit(1)
