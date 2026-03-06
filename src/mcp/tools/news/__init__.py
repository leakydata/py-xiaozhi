"""
News tool module - provides US news headlines and search via free RSS feeds.
"""

from .manager import cleanup_news_manager, get_news_manager

__all__ = ["get_news_manager", "cleanup_news_manager"]
