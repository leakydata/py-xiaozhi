"""
Search tool module - provides Bing search and web page content acquisition functions
"""

from .manager import cleanup_search_manager, get_search_manager

__all__ = ["get_search_manager", "cleanup_search_manager"]
