"""Countdown timer MCP tool functions.

Async tool functions for MCP server invocation.
"""

import json
from typing import Any, Dict

from src.utils.logging_config import get_logger

from .timer_service import get_timer_service

logger = get_logger(__name__)


async def start_countdown_timer(args: Dict[str, Any]) -> str:
    """Start a countdown task.

    Args:
        args: Dictionary containing the following parameters
            - command: MCP tool call to execute (JSON string with name and arguments fields)
            - delay: Delay time in seconds, optional, defaults to 5 seconds
            - description: Task description, optional

    Returns:
        str: JSON-formatted result string
    """
    try:
        command = args["command"]
        delay = args.get("delay")
        description = args.get("description", "")

        logger.info(f"[TimerTools] Starting countdown - command: {command}, delay: {delay}s")

        timer_service = get_timer_service()
        result = await timer_service.start_countdown(
            command=command, delay=delay, description=description
        )

        logger.info(f"[TimerTools] Countdown start result: {result['success']}")
        return json.dumps(result, ensure_ascii=False, indent=2)

    except KeyError as e:
        error_msg = f"Missing required parameter: {e}"
        logger.error(f"[TimerTools] {error_msg}")
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
    except Exception as e:
        error_msg = f"Failed to start countdown: {str(e)}"
        logger.error(f"[TimerTools] {error_msg}", exc_info=True)
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)


async def cancel_countdown_timer(args: Dict[str, Any]) -> str:
    """Cancel a specified countdown task.

    Args:
        args: Dictionary containing the following parameters
            - timer_id: ID of the timer to cancel

    Returns:
        str: JSON-formatted result string
    """
    try:
        timer_id = args["timer_id"]

        logger.info(f"[TimerTools] Cancelling countdown {timer_id}")

        timer_service = get_timer_service()
        result = await timer_service.cancel_countdown(timer_id)

        logger.info(f"[TimerTools] Countdown cancel result: {result['success']}")
        return json.dumps(result, ensure_ascii=False, indent=2)

    except KeyError as e:
        error_msg = f"Missing required parameter: {e}"
        logger.error(f"[TimerTools] {error_msg}")
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
    except Exception as e:
        error_msg = f"Failed to cancel countdown: {str(e)}"
        logger.error(f"[TimerTools] {error_msg}", exc_info=True)
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)


async def get_active_countdown_timers(args: Dict[str, Any]) -> str:
    """Get the status of all active countdown tasks.

    Args:
        args: Empty dictionary (this function requires no parameters)

    Returns:
        str: JSON-formatted list of active timers
    """
    try:
        logger.info("[TimerTools] Getting active countdown list")

        timer_service = get_timer_service()
        result = await timer_service.get_active_timers()

        logger.info(f"[TimerTools] Current active countdown count: {result['total_active_timers']}")
        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        error_msg = f"Failed to get active countdowns: {str(e)}"
        logger.error(f"[TimerTools] {error_msg}", exc_info=True)
        return json.dumps({"success": False, "message": error_msg}, ensure_ascii=False)
