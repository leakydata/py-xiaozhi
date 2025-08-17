"""
Search MCP tool functions - asynchronous tool functions provided for MCP server calls.
"""

import json
from typing import Any, Dict

from src.utils.logging_config import get_logger

from .manager import get_search_manager

logger = get_logger(__name__)


async def search_bing(args: Dict[str, Any]) -> str:
    """Execute a Bing search.

    Args:
        args: A dictionary containing search parameters
            - query: Search keyword
            - num_results: Number of results to return (default: 5)
            - language: Search language (default: zh-cn)
            - region: Search region (default: CN)

    Returns:
        Search results in JSON format
    """
    try:
        query = args.get("query")
        if not query:
            return json.dumps(
                {"success": False, "message": "Search keyword cannot be empty"},
                ensure_ascii=False,
            )

        num_results = args.get("num_results", 5)
        language = args.get("language", "zh-cn")
        region = args.get("region", "CN")

        # Limit the number of search results
        if num_results > 10:
            num_results = 10
        elif num_results < 1:
            num_results = 1

        manager = get_search_manager()
        results = await manager.search(
            query=query,
            num_results=num_results,
            language=language,
            region=region,
        )

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append(
                {
                    "id": result.id,
                    "title": result.title,
                    "url": result.url,
                    "snippet": result.snippet,
                    "source": result.source,
                }
            )

        return json.dumps(
            {
                "success": True,
                "query": query,
                "num_results": len(formatted_results),
                "results": formatted_results,
                "session_info": manager.get_session_info(),
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        logger.error(f"Search failed: {e}")
        return json.dumps(
            {"success": False, "message": f"Search failed: {str(e)}"},
            ensure_ascii=False,
        )


async def fetch_webpage_content(args: Dict[str, Any]) -> str:
    """Fetch webpage content.

    Args:
        args: A dictionary containing fetch parameters
            - result_id: Search result ID
            - max_length: Maximum content length (default: 8000)

    Returns:
        Webpage content
    """
    try:
        result_id = args.get("result_id")
        if not result_id:
            return json.dumps(
                {"success": False, "message": "Search result ID cannot be empty"},
                ensure_ascii=False,
            )

        max_length = args.get("max_length", 8000)

        # Limit content length
        if max_length > 20000:
            max_length = 20000
        elif max_length < 1000:
            max_length = 1000

        manager = get_search_manager()
        content = await manager.fetch_content(result_id, max_length)

        # Get corresponding search result information
        cached_results = manager.get_cached_results()
        result_info = None
        for result in cached_results:
            if result.id == result_id:
                result_info = {
                    "id": result.id,
                    "title": result.title,
                    "url": result.url,
                    "snippet": result.snippet,
                    "source": result.source,
                }
                break

        return json.dumps(
            {
                "success": True,
                "result_id": result_id,
                "result_info": result_info,
                "content": content,
                "content_length": len(content),
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        logger.error(f"Failed to fetch webpage content: {e}")
        return json.dumps(
            {"success": False, "message": f"Failed to fetch webpage content: {str(e)}"},
            ensure_ascii=False,
        )


async def get_search_results(args: Dict[str, Any]) -> str:
    """Get search result cache.

    Args:
        args: A dictionary containing query parameters
            - session_id: Session ID (optional)

    Returns:
        Cached search results
    """
    try:
        session_id = args.get("session_id")

        manager = get_search_manager()
        results = manager.get_cached_results(session_id)

        # Format results
        formatted_results = []
        for result in results:
            formatted_results.append(
                {
                    "id": result.id,
                    "title": result.title,
                    "url": result.url,
                    "snippet": result.snippet,
                    "source": result.source,
                    "has_content": bool(result.content),
                    "created_at": result.created_at,
                }
            )

        return json.dumps(
            {
                "success": True,
                "session_id": session_id or manager.current_session.id,
                "total_results": len(formatted_results),
                "results": formatted_results,
                "session_info": manager.get_session_info(),
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        logger.error(f"Failed to get search result cache: {e}")
        return json.dumps(
            {"success": False, "message": f"Failed to get search result cache: {str(e)}"},
            ensure_ascii=False,
        )


async def clear_search_cache(args: Dict[str, Any]) -> str:
    """Clear search cache.

    Args:
        args: Empty dictionary

    Returns:
        Operation result
    """
    try:
        manager = get_search_manager()
        old_count = len(manager.get_cached_results())
        manager.clear_cache()

        return json.dumps(
            {
                "success": True,
                "message": f"Search cache cleared, {old_count} results removed",
                "cleared_count": old_count,
            },
            ensure_ascii=False,
        )

    except Exception as e:
        logger.error(f"Failed to clear search cache: {e}")
        return json.dumps(
            {"success": False, "message": f"Failed to clear search cache: {str(e)}"},
            ensure_ascii=False,
        )


async def get_session_info(args: Dict[str, Any]) -> str:
    """Get search session information.

    Args:
        args: Empty dictionary

    Returns:
        Session information
    """
    try:
        manager = get_search_manager()
        session_info = manager.get_session_info()

        return json.dumps(
            {
                "success": True,
                "session_info": session_info,
            },
            ensure_ascii=False,
            indent=2,
        )

    except Exception as e:
        logger.error(f"Failed to get session information: {e}")
        return json.dumps(
            {"success": False, "message": f"Failed to get session information: {str(e)}"},
            ensure_ascii=False,
        )
