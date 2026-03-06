"""
Messages tool module - provides message taking and retrieval for away/receptionist mode.
"""

from .manager import cleanup_messages_manager, get_messages_manager

__all__ = ["get_messages_manager", "cleanup_messages_manager"]
