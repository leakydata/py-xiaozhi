"""Countdown timer MCP tool module.

Provides countdown timer functionality for delayed command execution, with AI model status queries and feedback.
"""

from .manager import get_timer_manager

__all__ = ["get_timer_manager"]
