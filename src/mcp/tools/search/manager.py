"""
Search Manager - Responsible for managing and coordinating search functions.
"""

from typing import List

from src.utils.logging_config import get_logger

from .client import SearchClient
from .models import SearchQuery, SearchResult, SearchSession

logger = get_logger(__name__)


class SearchManager:
    """
    Search Manager - Manages search sessions and result caching.
    """

    def __init__(self):
        self.current_session = SearchSession()
        self.client = SearchClient()
        self._client_initialized = False

    async def _ensure_client_initialized(self):
        """
        Ensures the search client is initialized.
        """
        if not self._client_initialized:
            await self.client.__aenter__()
            self._client_initialized = True

    async def cleanup(self):
        """
        Cleans up resources.
        """
        if self._client_initialized:
            await self.client.__aexit__(None, None, None)
            self._client_initialized = False

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        """
        Initializes and registers all search tools.
        """
        from .tools import fetch_webpage_content, get_search_results, search_bing

        # Bing search tool
        search_bing_props = PropertyList(
            [
                Property("query", PropertyType.STRING),
                Property("num_results", PropertyType.INTEGER, default_value=5),
                Property("language", PropertyType.STRING, default_value="en-us"),
                Property("region", PropertyType.STRING, default_value="US"),
            ]
        )
        add_tool(
            (
                "self.search.bing_search",
                "Execute a Bing search and return structured search results.\n"
                "Use this tool when the user wants to:\n"
                "1. Search for information on the internet\n"
                "2. Find recent news, articles, or web content\n"
                "3. Look up specific topics, people, or events\n"
                "4. Research current information beyond training data\n"
                "5. Find official websites or documentation\n"
                "\nFeatures:\n"
                "- Intelligent content parsing and extraction\n"
                "- Fallback mechanisms for robust search\n"
                "- Structured result format with title, URL, and snippet\n"
                "- Automatic result caching for follow-up content fetching\n"
                "\nSearch Quality:\n"
                "- Uses bing.com for broad content\n"
                "- Proper language and region targeting\n"
                "- Anti-blocking measures with proper headers\n"
                "- Multiple parsing strategies for reliable results\n"
                "\nArgs:\n"
                "  query: Search keywords or phrase (required)\n"
                "  num_results: Number of results to return (default: 5, max: 10)\n"
                "  language: Search language code (default: 'en-us')\n"
                "  region: Search region code (default: 'US')",
                search_bing_props,
                search_bing,
            )
        )

        # Webpage content fetching tool
        fetch_webpage_props = PropertyList(
            [
                Property("result_id", PropertyType.STRING),
                Property("max_length", PropertyType.INTEGER, default_value=8000),
            ]
        )
        add_tool(
            (
                "self.search.fetch_webpage",
                "Fetch and extract the main content from a webpage using the "
                "result ID obtained from the search. Intelligently extracts the "
                "main content while filtering out navigation, ads, and irrelevant "
                "elements.\n"
                "Use this tool when the user wants to:\n"
                "1. Read the full content of a search result\n"
                "2. Get detailed information from a specific webpage\n"
                "3. Extract main content from articles or blog posts\n"
                "4. Access content that's summarized in search snippets\n"
                "5. Analyze or process webpage content for specific information\n"
                "\nContent Extraction Features:\n"
                "- Intelligent main content detection\n"
                "- Removes ads, navigation, and irrelevant elements\n"
                "- Handles various webpage structures and layouts\n"
                "- Preserves text formatting and structure\n"
                "- Automatic encoding detection and handling\n"
                "\nText Processing:\n"
                "- Extracts meaningful paragraphs and sections\n"
                "- Preserves article titles and headings\n"
                "- Cleans up whitespace and formatting\n"
                "- Configurable content length limits\n"
                "- Fallback strategies for difficult-to-parse pages\n"
                "\nArgs:\n"
                "  result_id: The ID of the search result from the search (required)\n"
                "  max_length: Maximum content length in characters (default: 8000)",
                fetch_webpage_props,
                fetch_webpage_content,
            )
        )

        # Get search results tool
        get_results_props = PropertyList(
            [
                Property("session_id", PropertyType.STRING, default_value=""),
            ]
        )
        add_tool(
            (
                "self.search.get_results",
                "Get all cached search results from the current or specified "
                "search session. Returns a list of all search results that were "
                "obtained from previous search operations.\n"
                "Use this tool when the user wants to:\n"
                "1. Review previous search results\n"
                "2. Get a summary of all found results\n"
                "3. Reference search results by ID for content fetching\n"
                "4. Check what information is available from recent searches\n"
                "\nArgs:\n"
                "  session_id: Optional session ID (default: current session)",
                get_results_props,
                get_search_results,
            )
        )

    async def search(
        self,
        query: str,
        num_results: int = 5,
        language: str = "en-us",
        region: str = "US",
    ) -> List[SearchResult]:
        """Performs a search and caches the results.

        Args:
            query: Search keywords
            num_results: Number of results to return
            language: Search language
            region: Search region

        Returns:
            List of search results
        """
        try:
            await self._ensure_client_initialized()

            # Create a search query
            search_query = SearchQuery(
                query=query,
                num_results=num_results,
                language=language,
                region=region,
            )

            # Perform the search
            results = await self.client.search_bing(search_query)

            # Cache the results
            for result in results:
                self.current_session.add_result(result)

            # Record the query
            self.current_session.add_query(search_query)

            logger.info(f"Search completed: {query}, returned {len(results)} results")
            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            raise e

    async def fetch_content(self, result_id: str, max_length: int = 8000) -> str:
        """Fetches webpage content.

        Args:
            result_id: Search result ID
            max_length: Maximum content length

        Returns:
            Webpage content
        """
        try:
            await self._ensure_client_initialized()

            # Get the search result from the cache
            result = self.current_session.get_result(result_id)
            if not result:
                raise ValueError(f"Could not find a search result with ID {result_id}")

            # Fetch the webpage content
            content = await self.client.fetch_webpage_content(result.url, max_length)

            # Update the content of the search result
            result.content = content
            self.current_session.add_result(result)  # Update the cache

            logger.info(f"Finished fetching webpage content: {result.url}")
            return content

        except Exception as e:
            logger.error(f"Failed to fetch webpage content: {e}")
            raise e

    def get_cached_results(self, session_id: str = None) -> List[SearchResult]:
        """Gets cached search results.

        Args:
            session_id: Session ID, uses the current session if None

        Returns:
            List of search results
        """
        if session_id and session_id != self.current_session.id:
            # If a different session ID is specified, temporarily return an empty list
            # In a real application, multi-session management could be implemented
            return []

        return list(self.current_session.results.values())

    def clear_cache(self):
        """
        Clears the search cache.
        """
        self.current_session.clear_results()
        logger.info("Search cache has been cleared")

    def get_session_info(self) -> dict:
        """
        Gets information about the current session.
        """
        return {
            "session_id": self.current_session.id,
            "total_results": len(self.current_session.results),
            "total_queries": len(self.current_session.queries),
            "created_at": self.current_session.created_at,
            "last_accessed": self.current_session.last_accessed,
        }


# Global manager instance
_search_manager = None


def get_search_manager() -> SearchManager:
    """
    Gets the singleton instance of the search manager.
    """
    global _search_manager
    if _search_manager is None:
        _search_manager = SearchManager()
    return _search_manager


async def cleanup_search_manager():
    """
    Cleans up the search manager resources.
    """
    global _search_manager
    if _search_manager:
        await _search_manager.cleanup()
        _search_manager = None
