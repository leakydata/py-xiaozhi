"""System tools package.

Provides comprehensive system management functionality, including device status queries, audio control, and more.
"""

from .device_status import get_device_status
from .manager import SystemToolsManager, get_system_tools_manager
from .tools import get_system_status, set_volume

__all__ = [
    "SystemToolsManager",
    "get_system_tools_manager",
    "get_device_status",
    "get_system_status",
    "set_volume",
]
