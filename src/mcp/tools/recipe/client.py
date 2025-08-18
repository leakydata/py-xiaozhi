"""
Recipe data client - responsible for fetching recipe data from a remote API.
"""

import math
from typing import List, Optional

import aiohttp

from src.utils.logging_config import get_logger

from .models import PaginatedResult, Recipe

logger = get_logger(__name__)


class RecipeClient:
    """
    Recipe data client.
    """

    def __init__(self, recipes_url: str = "https://weilei.site/all_recipes.json"):
        self.recipes_url = recipes_url
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self):
        """
        Asynchronous context manager entry.
        """
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            },
        )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Asynchronous context manager exit.
        """
        if self.session:
            await self.session.close()

    async def fetch_recipes(self) -> List[Recipe]:
        """Fetch all recipe data from the remote API.

        Returns:
            A list of recipes.
        """
        try:
            if not self.session:
                raise RuntimeError("Client session not initialized")

            logger.info(f"Fetching recipe data from {self.recipes_url}...")

            async with self.session.get(self.recipes_url) as response:
                if response.status != 200:
                    raise Exception(f"HTTP error: {response.status}")

                data = await response.json()

                # Convert to Recipe objects
                recipes = []
                for recipe_data in data:
                    try:
                        recipe = Recipe.from_dict(recipe_data)
                        recipes.append(recipe)
                    except Exception as e:
                        logger.warning(
                            f"Failed to parse recipe: {recipe_data.get('name', 'Unknown')}, error: {e}"
                        )
                        continue

                logger.info(f"Successfully fetched {len(recipes)} recipes")
                return recipes

        except Exception as e:
            logger.error(f"Failed to fetch recipe data: {e}")
            return []

    def get_all_categories(self, recipes: List[Recipe]) -> List[str]:
        """Extract all categories from a list of recipes.

        Args:
            recipes: A list of recipes.

        Returns:
            A list of categories.
        """
        categories = set()
        for recipe in recipes:
            if recipe.category:
                categories.add(recipe.category)
        return sorted(list(categories))

    def paginate_recipes(
        self, recipes: List[Recipe], page: int = 1, page_size: int = 10
    ) -> PaginatedResult:
        """Paginate a list of recipes.

        Args:
            recipes: A list of recipes.
            page: Page number (starting from 1).
            page_size: Number of items per page.

        Returns:
            A paginated result.
        """
        total_records = len(recipes)
        total_pages = math.ceil(total_records / page_size) if total_records > 0 else 0

        # Validate page number
        if page < 1:
            page = 1
        if page > total_pages and total_pages > 0:
            page = total_pages

        # Calculate start and end indices
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        # Get paginated data
        paginated_data = recipes[start_idx:end_idx]

        return PaginatedResult(
            data=[recipe.to_dict() for recipe in paginated_data],
            page=page,
            page_size=page_size,
            total_records=total_records,
            total_pages=total_pages,
        )

    def paginate_simple_recipes(
        self, recipes: List[Recipe], page: int = 1, page_size: int = 10
    ) -> PaginatedResult:
        """Paginate a list of recipes, returning simplified data.

        Args:
            recipes: A list of recipes.
            page: Page number (starting from 1).
            page_size: Number of items per page.

        Returns:
            A paginated result.
        """
        total_records = len(recipes)
        total_pages = math.ceil(total_records / page_size) if total_records > 0 else 0

        # Validate page number
        if page < 1:
            page = 1
        if page > total_pages and total_pages > 0:
            page = total_pages

        # Calculate start and end indices
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        # Get paginated data
        paginated_data = recipes[start_idx:end_idx]

        return PaginatedResult(
            data=[recipe.to_simple_dict() for recipe in paginated_data],
            page=page,
            page_size=page_size,
            total_records=total_records,
            total_pages=total_pages,
        )

    def paginate_name_only_recipes(
        self, recipes: List[Recipe], page: int = 1, page_size: int = 10
    ) -> PaginatedResult:
        """Paginate a list of recipes, returning only name and description.

        Args:
            recipes: A list of recipes.
            page: Page number (starting from 1).
            page_size: Number of items per page.

        Returns:
            A paginated result.
        """
        total_records = len(recipes)
        total_pages = math.ceil(total_records / page_size) if total_records > 0 else 0

        # Validate page number
        if page < 1:
            page = 1
        if page > total_pages and total_pages > 0:
            page = total_pages

        # Calculate start and end indices
        start_idx = (page - 1) * page_size
        end_idx = start_idx + page_size

        # Get paginated data
        paginated_data = recipes[start_idx:end_idx]

        return PaginatedResult(
            data=[recipe.to_name_only_dict() for recipe in paginated_data],
            page=page,
            page_size=page_size,
            total_records=total_records,
            total_pages=total_pages,
        )

    def search_recipes(
        self, recipes: List[Recipe], query: str, page: int = 1, page_size: int = 10
    ) -> PaginatedResult:
        """Search recipes and return paginated results.

        Args:
            recipes: A list of recipes.
            query: Search keyword.
            page: Page number (starting from 1).
            page_size: Number of items per page.

        Returns:
            A paginated result.
        """
        query_lower = query.lower()
        filtered_recipes = []

        for recipe in recipes:
            # Check name
            if query_lower in recipe.name.lower():
                filtered_recipes.append(recipe)
                continue

            # Check description
            if query_lower in recipe.description.lower():
                filtered_recipes.append(recipe)
                continue

            # Check ingredients
            for ingredient in recipe.ingredients:
                if query_lower in ingredient.name.lower():
                    filtered_recipes.append(recipe)
                    break

        logger.info(f"Search keyword '{query}' found {len(filtered_recipes)} matching recipes")

        return self.paginate_simple_recipes(filtered_recipes, page, page_size)

    def get_recipes_by_category(
        self, recipes: List[Recipe], category: str, page: int = 1, page_size: int = 10
    ) -> PaginatedResult:
        """Get recipes by category and return paginated results.

        Args:
            recipes: A list of recipes.
            category: Category name.
            page: Page number (starting from 1).
            page_size: Number of items per page.

        Returns:
            A paginated result.
        """
        filtered_recipes = [recipe for recipe in recipes if recipe.category == category]

        logger.info(f"Category '{category}' found {len(filtered_recipes)} recipes")

        return self.paginate_simple_recipes(filtered_recipes, page, page_size)
