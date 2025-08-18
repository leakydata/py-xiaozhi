"""
Search Client - Implements asynchronous Bing search and webpage content fetching.
"""

import re
from typing import List, Optional
from urllib.parse import urlencode

import aiohttp
from bs4 import BeautifulSoup

from src.utils.logging_config import get_logger

from .models import SearchQuery, SearchResult

logger = get_logger(__name__)


class SearchClient:
    """
    Asynchronous search client.
    """

    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.user_agent = (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.base_headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
            "Accept-Encoding": "gzip, deflate, br",
            "Cache-Control": "no-cache",
            "Pragma": "no-cache",
            "Sec-Fetch-Dest": "document",
            "Sec-Fetch-Mode": "navigate",
            "Sec-Fetch-Site": "none",
            "Sec-Fetch-User": "?1",
            "Upgrade-Insecure-Requests": "1",
            "Cookie": "SRCHHPGUSR=SRCHLANG=en-US; _EDGE_S=ui=en-us; _EDGE_V=1",
        }
        self.timeout = aiohttp.ClientTimeout(total=15)

    async def __aenter__(self):
        """
        Asynchronous context manager entry.
        """
        if self.session is None:
            self.session = aiohttp.ClientSession(
                timeout=self.timeout,
                headers=self.base_headers,
                connector=aiohttp.TCPConnector(limit=10, limit_per_host=5),
            )
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Asynchronous context manager exit.
        """
        if self.session:
            await self.session.close()

    async def search_bing(self, query: SearchQuery) -> List[SearchResult]:
        """Performs a Bing search.

        Args:
            query: Search query object

        Returns:
            List of search results
        """
        try:
            if not self.session:
                raise RuntimeError(
                    "SearchClient not initialized. Use 'async with' statement."
                )

            # Build the search URL
            search_params = {
                "q": query.query,
                "setlang": query.language,
                "ensearch": "0",
                "count": str(query.num_results),
            }

            search_url = f"https://www.bing.com/search?{urlencode(search_params)}"
            logger.info(f"Searching: {search_url}")

            # Send the request
            async with self.session.get(search_url) as response:
                response.raise_for_status()
                html = await response.text()
                logger.info(f"Search response status: {response.status}")

            # Parse the search results
            results = await self._parse_search_results(html, query)
            logger.info(f"Parsed {len(results)} search results")

            return results

        except Exception as e:
            logger.error(f"Bing search failed: {e}")
            # Return an error message as a search result
            error_result = SearchResult(
                title=f'Error searching for "{query.query}"',
                url=f"https://www.bing.com/search?q={query.query}",
                snippet=f"An error occurred during the search: {str(e)}",
                source="bing",
            )
            return [error_result]

    async def _parse_search_results(
        self, html: str, query: SearchQuery
    ) -> List[SearchResult]:
        """Parses the search results page.

        Args:
            html: HTML of the search results page
            query: Search query object

        Returns:
            List of search results
        """
        soup = BeautifulSoup(html, "html.parser")
        results = []

        # Try multiple selector strategies
        selectors = [
            "#b_results > li.b_algo",
            "#b_results > .b_ans",
            "#b_results > li:not(.b_ad)",
            ".b_algo",
        ]

        for selector in selectors:
            elements = soup.select(selector)
            logger.info(f"Selector '{selector}' found {len(elements)} elements")

            for i, element in enumerate(elements):
                if len(results) >= query.num_results:
                    break

                try:
                    # Extract title and link
                    title_element = element.select_one("h2 a")
                    if not title_element:
                        title_element = element.select_one(".b_title a")

                    if title_element:
                        title = title_element.get_text(strip=True)
                        url = title_element.get("href", "")

                        # Fix relative links
                        if url.startswith("/"):
                            url = f"https://www.bing.com{url}"

                        # Extract snippet
                        snippet_element = element.select_one(".b_caption p")
                        if not snippet_element:
                            snippet_element = element.select_one(".b_snippet")

                        snippet = ""
                        if snippet_element:
                            snippet = snippet_element.get_text(strip=True)

                        # If no snippet, try to get the text content of the element
                        if not snippet:
                            text = element.get_text(strip=True)
                            if title in text:
                                text = text.replace(title, "", 1)
                            snippet = text[:200] + "..." if len(text) > 200 else text

                        # Skip invalid results
                        if not title or not url:
                            continue

                        result = SearchResult(
                            title=title,
                            url=url,
                            snippet=snippet,
                            source="bing",
                        )
                        results.append(result)

                except Exception as e:
                    logger.warning(f"Failed to parse search result element: {e}")
                    continue

            # If results are found, stop trying other selectors
            if results:
                break

        # If no results are found, return a default result
        if not results:
            logger.warning("No search results found, returning a default result")
            default_result = SearchResult(
                title=f"Search results for: {query.query}",
                url=f"https://www.bing.com/search?q={query.query}",
                snippet=f'Could not parse search results for "{query.query}", but you can visit the Bing search page directly.',
                source="bing",
            )
            results.append(default_result)

        return results

    async def fetch_webpage_content(self, url: str, max_length: int = 8000) -> str:
        """Fetches webpage content.

        Args:
            url: Webpage URL
            max_length: Maximum content length

        Returns:
            Webpage text content
        """
        try:
            if not self.session:
                raise RuntimeError(
                    "SearchClient not initialized. Use 'async with' statement."
                )

            logger.info(f"Fetching webpage content: {url}")

            # Set request headers
            headers = self.base_headers.copy()
            headers["Referer"] = "https://www.bing.com/"

            async with self.session.get(url, headers=headers) as response:
                # Check response status
                response.raise_for_status()

                # Get content type
                content_type = response.headers.get("content-type", "").lower()
                if "text/html" not in content_type:
                    return f"Unsupported content type: {content_type}"

                # Read content
                content = await response.read()

                # Try to detect encoding
                encoding = "utf-8"
                charset_match = re.search(r"charset=([^;]+)", content_type)
                if charset_match:
                    encoding = charset_match.group(1).strip()

                try:
                    html = content.decode(encoding)
                except UnicodeDecodeError:
                    logger.warning(f"Failed to decode with {encoding}, falling back to utf-8")
                    html = content.decode("utf-8", errors="ignore")

                # Parse webpage content
                return await self._extract_webpage_content(html, url, max_length)

        except Exception as e:
            logger.error(f"Failed to fetch webpage content: {e}")
            raise Exception(f"Failed to fetch webpage content: {str(e)}")

    async def _extract_webpage_content(
        self, html: str, url: str, max_length: int
    ) -> str:
        """Extracts the main content from HTML.

        Args:
            html: HTML content
            url: Webpage URL
            max_length: Maximum content length

        Returns:
            Extracted text content
        """
        soup = BeautifulSoup(html, "html.parser")

        # Remove unnecessary elements
        for tag in soup(
            ["script", "style", "iframe", "noscript", "nav", "header", "footer"]
        ):
            tag.decompose()

        # Remove elements with specific class names
        for selector in [
            ".ad",
            ".advertisement",
            ".sidebar",
            ".nav",
            ".header",
            ".footer",
        ]:
            for element in soup.select(selector):
                element.decompose()

        # Try to find the main content area
        main_content = ""
        content_selectors = [
            "main",
            "article",
            ".article",
            ".post",
            ".content",
            "#content",
            ".main",
            "#main",
            ".body",
            "#body",
            ".entry",
            ".entry-content",
            ".post-content",
            ".article-content",
            ".text",
            ".detail",
        ]

        for selector in content_selectors:
            element = soup.select_one(selector)
            if element:
                main_content = element.get_text(separator=" ", strip=True)
                if len(main_content) > 100:  # Content is long enough
                    break

        # If no main content is found, try to extract all paragraphs
        if not main_content or len(main_content) < 100:
            paragraphs = []
            for p in soup.find_all("p"):
                text = p.get_text(strip=True)
                if len(text) > 20:  # Only keep meaningful paragraphs
                    paragraphs.append(text)

            if paragraphs:
                main_content = "\n\n".join(paragraphs)

        # If still no content, get the body content
        if not main_content or len(main_content) < 100:
            body = soup.find("body")
            if body:
                main_content = body.get_text(separator=" ", strip=True)

        # Clean up the text
        main_content = re.sub(r"\s+", " ", main_content).strip()

        # Add the title
        title_element = soup.find("title")
        if title_element:
            title = title_element.get_text(strip=True)
            main_content = f"Title: {title}\n\n{main_content}"

        # Limit the content length
        if len(main_content) > max_length:
            main_content = main_content[:max_length] + "... (Content truncated)"

        return main_content if main_content else "Could not extract webpage content"
