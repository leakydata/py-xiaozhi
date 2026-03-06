"""
News MCP tool functions - asynchronous tool functions provided for MCP server calls.
"""

import json
from typing import Any, Dict

from src.utils.logging_config import get_logger

from .manager import get_news_manager

logger = get_logger(__name__)


async def get_top_headlines(args: Dict[str, Any]) -> str:
    """Fetch top US news headlines from RSS feeds.

    Args:
        args: A dictionary containing parameters
            - category: News category filter (optional)
            - num_results: Number of headlines to return (default: 10)

    Returns:
        Top headlines in JSON format
    """
    try:
        category = args.get("category", "")
        num_results = args.get("num_results", 10)

        if num_results > 25:
            num_results = 25
        elif num_results < 1:
            num_results = 1

        manager = get_news_manager()
        articles = await manager.fetch_top_headlines(
            category=category,
            num_results=num_results,
        )

        return json.dumps(
            {
                "success": True,
                "category": category or "top news",
                "num_results": len(articles),
                "articles": articles,
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        logger.error(f"Failed to fetch top headlines: {e}")
        return json.dumps(
            {"success": False, "message": f"Failed to fetch top headlines: {str(e)}"},
            ensure_ascii=False,
        )


async def search_news(args: Dict[str, Any]) -> str:
    """Search for US news articles by keyword.

    Args:
        args: A dictionary containing parameters
            - query: Search keyword (required)
            - num_results: Number of results to return (default: 10)

    Returns:
        Matching news articles in JSON format
    """
    try:
        query = args.get("query")
        if not query:
            return json.dumps(
                {"success": False, "message": "Search query cannot be empty"},
                ensure_ascii=False,
            )

        num_results = args.get("num_results", 10)

        if num_results > 25:
            num_results = 25
        elif num_results < 1:
            num_results = 1

        manager = get_news_manager()
        articles = await manager.search_news(
            query=query,
            num_results=num_results,
        )

        return json.dumps(
            {
                "success": True,
                "query": query,
                "num_results": len(articles),
                "articles": articles,
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        logger.error(f"News search failed: {e}")
        return json.dumps(
            {"success": False, "message": f"News search failed: {str(e)}"},
            ensure_ascii=False,
        )
