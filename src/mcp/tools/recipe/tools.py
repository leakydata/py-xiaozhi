"""
Recipe tool implementation - specific MCP tool functions.
"""

import json
from typing import Any, Dict

from src.utils.logging_config import get_logger

from .manager import get_recipe_manager

logger = get_logger(__name__)


async def get_all_recipes(args: Dict[str, Any]) -> str:
    """Get all recipes tool.

    Args:
        args: Dictionary containing page and page_size

    Returns:
        Paginated results in JSON format
    """
    try:
        page = args.get("page", 1)
        page_size = min(args.get("page_size", 10), 50)  # Limit max page_size

        manager = get_recipe_manager()
        result = await manager.get_all_recipes(page, page_size)

        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Failed to get all recipes: {e}")
        return json.dumps(
            {"error": "Failed to get recipes", "message": str(e)}, ensure_ascii=False
        )


async def get_recipe_by_id(args: Dict[str, Any]) -> str:
    """Get recipe details by ID tool.

    Args:
        args: Dictionary containing query

    Returns:
        Recipe details in JSON format
    """
    try:
        query = args.get("query", "")
        if not query:
            return json.dumps(
                {"error": "Missing query parameter", "message": "Please provide a recipe name or ID"},
                ensure_ascii=False,
            )

        manager = get_recipe_manager()
        result = await manager.get_recipe_by_id(query)

        return json.dumps(result, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Failed to get recipe details: {e}")
        return json.dumps(
            {"error": "Failed to get recipe details", "message": str(e)}, ensure_ascii=False
        )


async def get_recipes_by_category(args: Dict[str, Any]) -> str:
    """Get recipes by category tool.

    Args:
        args: Dictionary containing category, page, and page_size

    Returns:
        Paginated results in JSON format
    """
    try:
        category = args.get("category", "")
        if not category:
            return json.dumps(
                {"error": "Missing category parameter", "message": "Please provide a recipe category name"},
                ensure_ascii=False,
            )

        page = args.get("page", 1)
        page_size = min(args.get("page_size", 10), 50)  # Limit max page_size

        manager = get_recipe_manager()
        result = await manager.get_recipes_by_category(category, page, page_size)

        return json.dumps(result.to_dict(), ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Failed to get recipes by category: {e}")
        return json.dumps(
            {"error": "Failed to get recipes by category", "message": str(e)}, ensure_ascii=False
        )


async def recommend_meals(args: Dict[str, Any]) -> str:
    """Recommend meals tool.

    Args:
        args: Dictionary containing people_count, meal_type, page, and page_size

    Returns:
        Paginated results in JSON format
    """
    try:
        people_count = args.get("people_count", 2)
        meal_type = args.get("meal_type", "dinner")
        page = args.get("page", 1)
        page_size = min(args.get("page_size", 10), 50)  # Limit max page_size

        manager = get_recipe_manager()
        result = await manager.recommend_meals(people_count, meal_type, page, page_size)

        # Add recommendation information
        response = result.to_dict()
        response["recommendation_info"] = {
            "people_count": people_count,
            "meal_type": meal_type,
            "message": f"Recommended dishes for {people_count} people for {meal_type}",
        }

        return json.dumps(response, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Failed to recommend dishes: {e}")
        return json.dumps(
            {"error": "Failed to recommend dishes", "message": str(e)}, ensure_ascii=False
        )


async def what_to_eat(args: Dict[str, Any]) -> str:
    """Randomly recommend dishes tool.

    Args:
        args: Dictionary containing meal_type, page, and page_size

    Returns:
        Paginated results in JSON format
    """
    try:
        meal_type = args.get("meal_type", "any")
        page = args.get("page", 1)
        page_size = min(args.get("page_size", 10), 50)  # Limit max page_size

        manager = get_recipe_manager()
        result = await manager.what_to_eat(meal_type, page, page_size)

        # Add recommendation information
        response = result.to_dict()
        response["recommendation_info"] = {
            "meal_type": meal_type,
            "message": (
                f"Randomly recommend {meal_type} dishes" if meal_type != "any" else "Randomly recommend dishes"
            ),
        }

        return json.dumps(response, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Failed to randomly recommend dishes: {e}")
        return json.dumps(
            {"error": "Failed to randomly recommend dishes", "message": str(e)}, ensure_ascii=False
        )


async def search_recipes_fuzzy(args: Dict[str, Any]) -> str:
    """Fuzzy search for recipes tool.

    Args:
        args: Dictionary containing query, page, and page_size

    Returns:
        Paginated results in JSON format
    """
    try:
        query = args.get("query", "")
        if not query:
            return json.dumps(
                {"error": "Missing search keyword", "message": "Please provide a search keyword"},
                ensure_ascii=False,
            )

        page = args.get("page", 1)
        page_size = min(args.get("page_size", 10), 50)  # Limit max page_size

        manager = get_recipe_manager()
        result = await manager.search_recipes(query, page, page_size)

        # Add search information
        response = result.to_dict()
        response["search_info"] = {"query": query, "message": f"Search keyword: {query}"}

        return json.dumps(response, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Fuzzy search for recipes failed: {e}")
        return json.dumps(
            {"error": "Fuzzy search for recipes failed", "message": str(e)}, ensure_ascii=False
        )
