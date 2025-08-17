import asyncio
import json
from asyncio import Task
from typing import Any, Dict

from src.iot.thing import Parameter, Thing
from src.iot.thing_manager import ThingManager
from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class CountdownTimer(Thing):
    """
    A countdown timer device for delayed command execution.
    """

    DEFAULT_DELAY = 5  # seconds

    def __init__(self):
        super().__init__("CountdownTimer", "A countdown timer for delayed command execution")
        # Use a dictionary to store active timers, with timer_id as the key and asyncio.Task object as the value
        self._timers: Dict[int, Task] = {}
        self._next_timer_id = 0
        # Use a lock to protect access to _timers and _next_timer_id, ensuring thread safety
        self._lock = asyncio.Lock()

        # Define methods - using Parameter objects
        self.add_method(
            "StartCountdown",
            "Starts a countdown, and executes the specified command when it ends",
            [
                Parameter(
                    "command",
                    "The IoT command to execute (JSON format string "
                    "{'name': 'DeviceName', 'method': 'MethodName', "
                    "'parameters': {'ParamName': 'ParamValue'}})",
                    "string",
                    required=True,
                ),
                Parameter(
                    "delay", "Delay time in seconds, defaults to 5 seconds", "integer", required=False
                ),  # Use required=False to mark optional parameters
            ],
            self._start_countdown,  # Use method reference directly, no lambda
        )
        self.add_method(
            "CancelCountdown",
            "Cancels the specified countdown",
            [Parameter("timer_id", "The ID of the timer to cancel", "integer", required=True)],
            self._cancel_countdown,  # Use method reference directly, no lambda
        )

    async def _execute_command(self, timer_id: int, command_str: str) -> None:
        """
        Callback function executed when the timer expires.
        """
        # First, remove itself from the list of active timers
        async with self._lock:
            if timer_id not in self._timers:
                # May have already been canceled
                logger.info(f"Countdown {timer_id} was canceled or does not exist before execution.")
                return
            del self._timers[timer_id]

        logger.info(f"Countdown {timer_id} finished, preparing to execute command: {command_str}")

        try:
            # The command should be a JSON formatted string representing a command dictionary
            command_dict = json.loads(command_str)
            # Get the ThingManager singleton and execute the command
            thing_manager = ThingManager.get_instance()
            result = await thing_manager.invoke(command_dict)
            logger.info(f"Countdown {timer_id} executed command '{command_str}' with result: {result}")
        except json.JSONDecodeError:
            logger.error(
                f"Countdown {timer_id}: Command '{command_str}' format error, cannot parse JSON."
            )
        except Exception as e:
            logger.error(
                f"Countdown {timer_id} encountered an error while executing command '{command_str}': {e}", exc_info=True
            )

    async def _delayed_execution(
        self, delay: int, timer_id: int, command_str: str
    ) -> None:
        """
        Asynchronous delayed execution function.
        """
        try:
            await asyncio.sleep(delay)
            await self._execute_command(timer_id, command_str)
        except asyncio.CancelledError:
            logger.info(f"Countdown {timer_id} was canceled")
        except Exception as e:
            logger.error(f"Countdown {timer_id} encountered an error during execution: {e}", exc_info=True)

    async def _start_countdown(
        self, params_dict: Dict[str, Parameter]
    ) -> Dict[str, Any]:
        """
        Handles the StartCountdown method call. Note: params is now a dictionary of Parameter objects.
        """
        # Get values from the Parameter object dictionary
        command_param = params_dict.get("command")
        delay_param = params_dict.get("delay")

        command_str = command_param.get_value() if command_param else None
        # Handle the optional parameter delay
        delay = (
            delay_param.get_value()
            if delay_param and delay_param.get_value() is not None
            else self.DEFAULT_DELAY
        )

        if not command_str:
            logger.error("Failed to start countdown: missing 'command' parameter value.")
            return {"status": "error", "message": "Missing 'command' parameter value"}

        # Validate the delay time
        try:
            # Ensure delay is an integer
            if not isinstance(delay, int):
                delay = int(delay)

            if delay <= 0:
                logger.warning(
                    f"Provided delay time {delay} is invalid, using default value "
                    f"{self.DEFAULT_DELAY} seconds."
                )
                delay = self.DEFAULT_DELAY
        except (ValueError, TypeError):
            logger.warning(
                f"Provided delay time '{delay}' is invalid, using default value "
                f"{self.DEFAULT_DELAY} seconds."
            )
            delay = self.DEFAULT_DELAY

        # Try to parse the command string for early validation
        try:
            json.loads(command_str)
        except json.JSONDecodeError:
            logger.error(f"Failed to start countdown: command format error, cannot parse JSON: {command_str}")
            return {
                "status": "error",
                "message": f"Command format error, cannot parse JSON: {command_str}",
            }

        # Get the current event loop
        loop = asyncio.get_running_loop()

        async with self._lock:
            timer_id = self._next_timer_id
            self._next_timer_id += 1
            # Create an async task and ensure it runs in the current event loop
            task = loop.create_task(
                self._delayed_execution(delay, timer_id, command_str)
            )
            self._timers[timer_id] = task

        logger.info(f"Started countdown {timer_id}, will execute command in {delay} seconds: {command_str}")
        return {
            "status": "success",
            "message": f"Countdown {timer_id} has started and will execute in {delay} seconds.",
            "timer_id": timer_id,
        }

    async def _cancel_countdown(
        self, params_dict: Dict[str, Parameter]
    ) -> Dict[str, Any]:
        """
        Handles the CancelCountdown method call. Note: params is now a dictionary of Parameter objects.
        """
        timer_id_param = params_dict.get("timer_id")
        timer_id = timer_id_param.get_value() if timer_id_param else None

        if timer_id is None:
            logger.error("Failed to cancel countdown: missing 'timer_id' parameter value.")
            return {"status": "error", "message": "Missing 'timer_id' parameter value"}

        try:
            # Ensure timer_id is an integer
            if not isinstance(timer_id, int):
                timer_id = int(timer_id)
        except (ValueError, TypeError):
            logger.error(f"Failed to cancel countdown: invalid 'timer_id' {timer_id}.")
            return {"status": "error", "message": f"Invalid 'timer_id': {timer_id}"}

        async with self._lock:
            if timer_id in self._timers:
                task = self._timers.pop(timer_id)
                task.cancel()
                logger.info(f"Countdown {timer_id} has been successfully canceled.")
                return {"status": "success", "message": f"Countdown {timer_id} has been canceled"}
            else:
                logger.warning(f"Attempted to cancel a non-existent or completed countdown {timer_id}.")
                return {
                    "status": "error",
                    "message": f"Could not find an active countdown with ID {timer_id}",
                }

    async def cleanup(self) -> None:
        """
        Cleans up all active timers when the application is shutting down.
        """
        logger.info("Cleaning up countdown timers...")
        async with self._lock:
            active_timer_ids = list(self._timers.keys())  # Create a copy of keys for safe iteration
            for timer_id in active_timer_ids:
                if timer_id in self._timers:
                    task = self._timers.pop(timer_id)
                    task.cancel()
                    logger.info(f"Canceled background timer {timer_id}")
        logger.info("Countdown timer cleanup complete.")


# Note: This cleanup method needs to be explicitly called when the application is shutting down.
# The ThingManager or Application class can be responsible for calling the cleanup method of its managed Things during the shutdown process.
