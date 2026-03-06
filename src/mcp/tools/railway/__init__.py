"""12306 railway ticket query tool module.

Provides train ticket query, train number lookup, station stop query, and other features.
"""

from .manager import RailwayToolsManager, get_railway_manager

# Global tool manager instance
_railway_tools_manager = None


def get_railway_tools_manager() -> RailwayToolsManager:
    """
    Get Railway tool manager instance - new version smart tool interface.
    """
    global _railway_tools_manager
    if _railway_tools_manager is None:
        _railway_tools_manager = RailwayToolsManager()
    return _railway_tools_manager


__all__ = [
    "get_railway_manager",       # Compatibility interface
    "get_railway_tools_manager", # New version smart tool interface
    "RailwayToolsManager"
]
