"""Countdown timer service.

Manages countdown task creation, execution, cancellation, and status queries.
"""

import asyncio
import json
from asyncio import Task
from datetime import datetime, timedelta
from typing import Any, Dict, Optional

from src.utils.logging_config import get_logger

logger = get_logger(__name__)


class TimerService:
    """
    Countdown timer service that manages all countdown tasks.
    """

    def __init__(self):
        # Dictionary to store active timers, key is timer_id, value is TimerTask object
        self._timers: Dict[int, "TimerTask"] = {}
        self._next_timer_id = 0
        # Lock to protect access to _timers and _next_timer_id, ensuring thread safety
        self._lock = asyncio.Lock()
        self.DEFAULT_DELAY = 5  # Default delay in seconds

    async def start_countdown(
        self, command: str, delay: int = None, description: str = ""
    ) -> Dict[str, Any]:
        """Start a countdown task.

        Args:
            command: MCP tool call to execute (JSON string with name and arguments fields)
            delay: Delay time in seconds, defaults to 5 seconds
            description: Task description

        Returns:
            Dict[str, Any]: Dictionary containing task information
        """
        if delay is None:
            delay = self.DEFAULT_DELAY

        # Validate delay time
        try:
            delay = int(delay)
            if delay <= 0:
                logger.warning(
                    f"Provided delay {delay} is invalid, using default value {self.DEFAULT_DELAY} seconds"
                )
                delay = self.DEFAULT_DELAY
        except (ValueError, TypeError):
            logger.warning(
                f"Provided delay '{delay}' is invalid, using default value {self.DEFAULT_DELAY} seconds"
            )
            delay = self.DEFAULT_DELAY

        # Validate command format
        try:
            json.loads(command)
        except json.JSONDecodeError:
            logger.error(f"Failed to start countdown: invalid command format, cannot parse JSON: {command}")
            return {
                "success": False,
                "message": f"Invalid command format, cannot parse JSON: {command}",
            }

        # Get the current event loop
        loop = asyncio.get_running_loop()

        async with self._lock:
            timer_id = self._next_timer_id
            self._next_timer_id += 1

            # Create countdown task
            timer_task = TimerTask(
                timer_id=timer_id,
                command=command,
                delay=delay,
                description=description,
                service=self,
            )

            # Create async task
            task = loop.create_task(timer_task.run())
            timer_task.task = task

            self._timers[timer_id] = timer_task

        logger.info(f"Started countdown {timer_id}, will execute command in {delay} seconds: {command}")

        return {
            "success": True,
            "message": f"Countdown {timer_id} started, will execute in {delay} seconds",
            "timer_id": timer_id,
            "delay": delay,
            "command": command,
            "description": description,
            "start_time": datetime.now().isoformat(),
            "estimated_execution_time": (
                datetime.now() + timedelta(seconds=delay)
            ).isoformat(),
        }

    async def cancel_countdown(self, timer_id: int) -> Dict[str, Any]:
        """Cancel a specified countdown task.

        Args:
            timer_id: ID of the timer to cancel

        Returns:
            Dict[str, Any]: Cancellation result
        """
        try:
            timer_id = int(timer_id)
        except (ValueError, TypeError):
            logger.error(f"Failed to cancel countdown: invalid timer_id {timer_id}")
            return {"success": False, "message": f"Invalid timer_id: {timer_id}"}

        async with self._lock:
            if timer_id in self._timers:
                timer_task = self._timers.pop(timer_id)
                if timer_task.task:
                    timer_task.task.cancel()

                logger.info(f"Countdown {timer_id} successfully cancelled")
                return {
                    "success": True,
                    "message": f"Countdown {timer_id} cancelled",
                    "timer_id": timer_id,
                    "cancelled_at": datetime.now().isoformat(),
                }
            else:
                logger.warning(f"Attempted to cancel non-existent or completed countdown {timer_id}")
                return {
                    "success": False,
                    "message": f"No active countdown found with ID {timer_id}",
                    "timer_id": timer_id,
                }

    async def get_active_timers(self) -> Dict[str, Any]:
        """Get the status of all active countdown tasks.

        Returns:
            Dict[str, Any]: List of active timers
        """
        async with self._lock:
            active_timers = []
            current_time = datetime.now()

            for timer_id, timer_task in self._timers.items():
                remaining_time = timer_task.get_remaining_time()
                if remaining_time > 0:
                    active_timers.append(
                        {
                            "timer_id": timer_id,
                            "command": timer_task.command,
                            "description": timer_task.description,
                            "delay": timer_task.delay,
                            "remaining_seconds": remaining_time,
                            "start_time": timer_task.start_time.isoformat(),
                            "estimated_execution_time": timer_task.execution_time.isoformat(),
                            "progress": timer_task.get_progress(),
                        }
                    )

            return {
                "success": True,
                "total_active_timers": len(active_timers),
                "timers": active_timers,
                "current_time": current_time.isoformat(),
            }

    async def cleanup_timer(self, timer_id: int):
        """
        Remove a completed timer from the manager.
        """
        async with self._lock:
            if timer_id in self._timers:
                del self._timers[timer_id]
                logger.debug(f"Cleaned up completed countdown {timer_id}")

    async def cleanup_all(self):
        """
        Clean up all countdown tasks (called when application closes).
        """
        logger.info("Cleaning up all countdown tasks...")
        async with self._lock:
            active_timer_ids = list(self._timers.keys())
            for timer_id in active_timer_ids:
                if timer_id in self._timers:
                    timer_task = self._timers.pop(timer_id)
                    if timer_task.task:
                        timer_task.task.cancel()
                    logger.info(f"Cancelled countdown task {timer_id}")
        logger.info("Countdown task cleanup complete")


class TimerTask:
    """
    A single countdown task.
    """

    def __init__(
        self,
        timer_id: int,
        command: str,
        delay: int,
        description: str,
        service: TimerService,
    ):
        self.timer_id = timer_id
        self.command = command
        self.delay = delay
        self.description = description
        self.service = service
        self.start_time = datetime.now()
        self.execution_time = self.start_time + timedelta(seconds=delay)
        self.task: Optional[Task] = None

    async def run(self):
        """
        Execute the countdown task.
        """
        try:
            # Wait for the delay period
            await asyncio.sleep(self.delay)

            # Execute command
            await self._execute_command()

        except asyncio.CancelledError:
            logger.info(f"Countdown {self.timer_id} was cancelled")
        except Exception as e:
            logger.error(f"Countdown {self.timer_id} error during execution: {e}", exc_info=True)
        finally:
            # Clean up self
            await self.service.cleanup_timer(self.timer_id)

    async def _execute_command(self):
        """
        Execute the command after countdown ends.
        """
        logger.info(f"Countdown {self.timer_id} finished, preparing to execute MCP tool: {self.command}")

        try:
            # Parse MCP tool call command
            command_dict = json.loads(self.command)

            # Validate command format (MCP tool call format)
            if "name" not in command_dict or "arguments" not in command_dict:
                raise ValueError("Invalid MCP command format, must contain 'name' and 'arguments' fields")

            tool_name = command_dict["name"]
            arguments = command_dict["arguments"]

            # Get MCP server and execute tool
            from src.mcp.mcp_server import McpServer

            mcp_server = McpServer.get_instance()

            # Find tool
            tool = None
            for t in mcp_server.tools:
                if t.name == tool_name:
                    tool = t
                    break

            if not tool:
                raise ValueError(f"MCP tool does not exist: {tool_name}")

            # Execute MCP tool
            result = await tool.call(arguments)

            # Parse result
            result_data = json.loads(result)
            is_success = not result_data.get("isError", False)

            if is_success:
                logger.info(
                    f"Countdown {self.timer_id} MCP tool executed successfully, tool: {tool_name}"
                )
                await self._notify_execution_result(True, f"Executed {tool_name}")
            else:
                error_text = result_data.get("content", [{}])[0].get("text", "Unknown error")
                logger.error(f"Countdown {self.timer_id} MCP tool execution failed: {error_text}")
                await self._notify_execution_result(False, error_text)

        except json.JSONDecodeError:
            error_msg = f"Countdown {self.timer_id}: invalid MCP command format, cannot parse JSON"
            logger.error(error_msg)
            await self._notify_execution_result(False, error_msg)
        except Exception as e:
            error_msg = f"Countdown {self.timer_id} error executing MCP tool: {e}"
            logger.error(error_msg, exc_info=True)
            await self._notify_execution_result(False, error_msg)

    async def _notify_execution_result(self, success: bool, result: Any):
        """
        Notify execution result (via TTS announcement).
        """
        try:
            from src.application import Application

            app = Application.get_instance()
            if success:
                message = f"Countdown {self.timer_id} execution complete"
                if self.description:
                    message = f"{self.description} execution complete"
            else:
                message = f"Countdown {self.timer_id} execution failed"
                if self.description:
                    message = f"{self.description} execution failed"

            print("Countdown:", message)
            await app._send_text_tts(message)
        except Exception as e:
            logger.warning(f"Failed to notify countdown execution result: {e}")

    def get_remaining_time(self) -> float:
        """
        Get remaining time in seconds.
        """
        now = datetime.now()
        remaining = (self.execution_time - now).total_seconds()
        return max(0, remaining)

    def get_progress(self) -> float:
        """
        Get progress (float between 0 and 1).
        """
        elapsed = (datetime.now() - self.start_time).total_seconds()
        return min(1.0, elapsed / self.delay)


# Global service instance
_timer_service = None


def get_timer_service() -> TimerService:
    """
    Get the countdown timer service singleton.
    """
    global _timer_service
    if _timer_service is None:
        _timer_service = TimerService()
        logger.debug("Created countdown timer service instance")
    return _timer_service
