"""Countdown timer tool manager.

Responsible for countdown timer tool initialization, configuration, and MCP tool registration.
"""

from typing import Any, Dict

from src.utils.logging_config import get_logger

from .tools import (
    cancel_countdown_timer,
    get_active_countdown_timers,
    start_countdown_timer,
)

logger = get_logger(__name__)


class TimerToolsManager:
    """
    Countdown timer tool manager.
    """

    def __init__(self):
        """
        Initialize the countdown timer tool manager.
        """
        self._initialized = False
        logger.info("[TimerManager] Countdown timer tool manager initialized")

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        """
        Initialize and register all countdown timer tools.
        """
        try:
            logger.info("[TimerManager] Starting to register countdown timer tools")

            # Register start countdown tool
            self._register_start_countdown_tool(
                add_tool, PropertyList, Property, PropertyType
            )

            # Register cancel countdown tool
            self._register_cancel_countdown_tool(
                add_tool, PropertyList, Property, PropertyType
            )

            # Register get active timers tool
            self._register_get_active_timers_tool(add_tool, PropertyList)

            self._initialized = True
            logger.info("[TimerManager] Countdown timer tool registration complete")

        except Exception as e:
            logger.error(f"[TimerManager] Countdown timer tool registration failed: {e}", exc_info=True)
            raise

    def _register_start_countdown_tool(
        self, add_tool, PropertyList, Property, PropertyType
    ):
        """
        Register the start countdown tool.
        """
        timer_props = PropertyList(
            [
                Property(
                    "command",
                    PropertyType.STRING,
                ),
                Property(
                    "delay",
                    PropertyType.INTEGER,
                    default_value=5,
                    min_value=1,
                    max_value=3600,  # Maximum 1 hour
                ),
                Property(
                    "description",
                    PropertyType.STRING,
                    default_value="",
                ),
            ]
        )

        add_tool(
            (
                "timer.start_countdown",
                "Start a countdown timer that will execute an MCP tool after a specified delay. "
                "The command should be a JSON string containing MCP tool name and arguments. "
                'For example: \'{"name": "self.audio_speaker.set_volume", "arguments": {"volume": 50}}\' '
                "Use this when the user wants to: \n"
                "1. Set a timer to control system settings (volume, device status, etc.) \n"
                "2. Schedule delayed MCP tool executions \n"
                "3. Create reminders with automatic tool calls \n"
                "The timer will return a timer_id that can be used to cancel it later.",
                timer_props,
                start_countdown_timer,
            )
        )
        logger.debug("[TimerManager] Registered start countdown tool successfully")

    def _register_cancel_countdown_tool(
        self, add_tool, PropertyList, Property, PropertyType
    ):
        """
        Register the cancel countdown tool.
        """
        cancel_props = PropertyList(
            [
                Property(
                    "timer_id",
                    PropertyType.INTEGER,
                )
            ]
        )

        add_tool(
            (
                "timer.cancel_countdown",
                "Cancel an active countdown timer by its ID. "
                "Use this when the user wants to: \n"
                "1. Cancel a previously set timer \n"
                "2. Stop a scheduled action before it executes \n"
                "You need the timer_id which is returned when starting a countdown.",
                cancel_props,
                cancel_countdown_timer,
            )
        )
        logger.debug("[TimerManager] Registered cancel countdown tool successfully")

    def _register_get_active_timers_tool(self, add_tool, PropertyList):
        """
        Register the get active timers tool.
        """
        add_tool(
            (
                "timer.get_active_timers",
                "Get information about all currently active countdown timers. "
                "Returns details including timer IDs, remaining time, commands to execute, "
                "and progress for each active timer. "
                "Use this when the user wants to: \n"
                "1. Check what timers are currently running \n"
                "2. See remaining time for active timers \n"
                "3. Get timer IDs for cancellation \n"
                "4. Monitor timer progress and status",
                PropertyList(),
                get_active_countdown_timers,
            )
        )
        logger.debug("[TimerManager] Registered get active timers tool successfully")

    def is_initialized(self) -> bool:
        """
        Check if the manager is initialized.
        """
        return self._initialized

    def get_status(self) -> Dict[str, Any]:
        """
        Get the manager status.
        """
        return {
            "initialized": self._initialized,
            "tools_count": 3,  # Number of currently registered tools
            "available_tools": [
                "start_countdown",
                "cancel_countdown",
                "get_active_timers",
            ],
        }


# Global manager instance
_timer_tools_manager = None


def get_timer_manager() -> TimerToolsManager:
    """
    Get the countdown timer tool manager singleton.
    """
    global _timer_tools_manager
    if _timer_tools_manager is None:
        _timer_tools_manager = TimerToolsManager()
        logger.debug("[TimerManager] Created countdown timer tool manager instance")
    return _timer_tools_manager
