"""
News Manager - Responsible for fetching and managing US news from free RSS feeds.
"""

import xml.etree.ElementTree as ET
from typing import Any, Dict, List, Optional

import aiohttp

from src.utils.logging_config import get_logger

logger = get_logger(__name__)

# Category keyword mappings for filtering articles
CATEGORY_KEYWORDS: Dict[str, List[str]] = {
    "politics": [
        "politics", "political", "congress", "senate", "president",
        "democrat", "republican", "election", "vote", "legislation",
        "white house", "governor", "policy", "campaign", "biden",
        "trump", "supreme court", "federal", "gop", "liberal",
        "conservative",
    ],
    "technology": [
        "technology", "tech", "software", "hardware", "ai",
        "artificial intelligence", "computer", "internet", "cyber",
        "digital", "startup", "silicon valley", "app", "data",
        "robot", "machine learning", "crypto", "blockchain", "apple",
        "google", "microsoft", "amazon", "meta",
    ],
    "business": [
        "business", "economy", "economic", "market", "stock",
        "wall street", "trade", "finance", "financial", "bank",
        "investment", "corporate", "company", "industry", "gdp",
        "inflation", "recession", "jobs", "unemployment", "fed",
        "interest rate",
    ],
    "sports": [
        "sports", "nfl", "nba", "mlb", "nhl", "soccer", "football",
        "basketball", "baseball", "hockey", "tennis", "golf",
        "olympic", "athlete", "championship", "tournament", "game",
        "coach", "player", "team", "league", "espn",
    ],
    "entertainment": [
        "entertainment", "movie", "film", "music", "celebrity",
        "hollywood", "tv", "television", "streaming", "netflix",
        "disney", "show", "concert", "album", "actor", "actress",
        "award", "grammy", "oscar", "emmy", "box office",
    ],
    "health": [
        "health", "medical", "medicine", "hospital", "doctor",
        "disease", "virus", "vaccine", "covid", "mental health",
        "treatment", "drug", "fda", "cdc", "cancer", "heart",
        "diet", "wellness", "patient", "healthcare", "surgery",
    ],
    "science": [
        "science", "scientific", "research", "study", "nasa",
        "space", "climate", "environment", "energy", "physics",
        "biology", "chemistry", "discovery", "experiment", "nature",
        "species", "planet", "fossil", "genome", "ocean",
        "earthquake", "weather",
    ],
}

# RSS feed sources
RSS_FEEDS = [
    {
        "name": "AP News",
        "url": "https://rsshub.app/apnews/topics/apf-topnews",
        "type": "rss",
    },
    {
        "name": "NPR",
        "url": "https://feeds.npr.org/1001/rss.xml",
        "type": "rss",
    },
    {
        "name": "Reuters",
        "url": (
            "https://www.rss-bridge.org/bridge01/?action=display"
            "&bridge=Reuters&feed=home%2Ftopnews&format=Atom"
        ),
        "type": "atom",
    },
]

# Atom namespace
ATOM_NS = "http://www.w3.org/2005/Atom"


class NewsManager:
    """
    News Manager - Fetches US news from free RSS feeds with fallback to Bing search.
    """

    def __init__(self):
        self._session: Optional[aiohttp.ClientSession] = None

    async def _ensure_session(self):
        """Ensures an aiohttp session exists."""
        if self._session is None or self._session.closed:
            timeout = aiohttp.ClientTimeout(total=15)
            self._session = aiohttp.ClientSession(
                timeout=timeout,
                headers={
                    "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/120.0.0.0 Safari/537.36"
                    ),
                },
            )

    async def cleanup(self):
        """Cleans up resources."""
        if self._session and not self._session.closed:
            await self._session.close()
            self._session = None

    def init_tools(self, add_tool, PropertyList, Property, PropertyType):
        """
        Initializes and registers all news tools.
        """
        from .tools import get_top_headlines, search_news

        # Top headlines tool
        top_headlines_props = PropertyList(
            [
                Property(
                    "category",
                    PropertyType.STRING,
                    default_value="",
                ),
                Property(
                    "num_results",
                    PropertyType.INTEGER,
                    default_value=10,
                ),
            ]
        )
        add_tool(
            (
                "self.news.get_top_headlines",
                "Fetch the latest top US news headlines from major news sources "
                "(AP News, NPR, Reuters).\n"
                "Use this tool when the user wants to:\n"
                "1. Get the latest news or current events\n"
                "2. See today's top headlines\n"
                "3. Browse news by category\n"
                "4. Stay informed about what's happening in the US\n"
                "\nFeatures:\n"
                "- Aggregates headlines from AP News, NPR, and Reuters\n"
                "- Supports category filtering\n"
                "- Returns structured results with title, description, source, "
                "published date, and link\n"
                "- Falls back to Bing search if RSS feeds are unavailable\n"
                "\nSupported categories:\n"
                "- politics: US political news\n"
                "- technology: Tech industry and innovation\n"
                "- business: Economy, markets, and finance\n"
                "- sports: US and world sports\n"
                "- entertainment: Movies, music, and pop culture\n"
                "- health: Medical and health news\n"
                "- science: Scientific discoveries and research\n"
                "\nArgs:\n"
                "  category: Filter by category (optional, leave empty for all news)\n"
                "  num_results: Number of headlines to return (default: 10, max: 25)",
                top_headlines_props,
                get_top_headlines,
            )
        )

        # Search news tool
        search_news_props = PropertyList(
            [
                Property("query", PropertyType.STRING),
                Property(
                    "num_results",
                    PropertyType.INTEGER,
                    default_value=10,
                ),
            ]
        )
        add_tool(
            (
                "self.news.search_news",
                "Search for US news articles matching a specific keyword or topic.\n"
                "Use this tool when the user wants to:\n"
                "1. Find news about a specific topic or event\n"
                "2. Search for articles mentioning a person, place, or thing\n"
                "3. Get news coverage on a particular subject\n"
                "\nFeatures:\n"
                "- Searches across AP News, NPR, and Reuters RSS feeds\n"
                "- Keyword matching in titles and descriptions\n"
                "- Falls back to Bing news search if RSS feeds fail\n"
                "- Returns structured results with title, description, source, "
                "published date, and link\n"
                "\nArgs:\n"
                "  query: Search keyword or phrase (required)\n"
                "  num_results: Number of results to return (default: 10, max: 25)",
                search_news_props,
                search_news,
            )
        )

    async def _fetch_feed(self, feed: Dict[str, str]) -> List[Dict[str, str]]:
        """Fetches and parses a single RSS/Atom feed.

        Args:
            feed: Feed configuration dict with name, url, and type.

        Returns:
            List of article dicts.
        """
        await self._ensure_session()
        articles = []

        try:
            async with self._session.get(feed["url"]) as response:
                if response.status != 200:
                    logger.warning(
                        f"Feed {feed['name']} returned status {response.status}"
                    )
                    return articles

                text = await response.text()
                root = ET.fromstring(text)

                if feed["type"] == "atom":
                    articles = self._parse_atom(root, feed["name"])
                else:
                    articles = self._parse_rss(root, feed["name"])

        except ET.ParseError as e:
            logger.warning(f"Failed to parse XML from {feed['name']}: {e}")
        except aiohttp.ClientError as e:
            logger.warning(f"HTTP error fetching {feed['name']}: {e}")
        except Exception as e:
            logger.warning(f"Unexpected error fetching {feed['name']}: {e}")

        return articles

    def _parse_rss(self, root: ET.Element, source: str) -> List[Dict[str, str]]:
        """Parses an RSS 2.0 feed XML element.

        Args:
            root: XML root element.
            source: Name of the news source.

        Returns:
            List of article dicts.
        """
        articles = []
        channel = root.find("channel")
        if channel is None:
            return articles

        for item in channel.findall("item"):
            title = self._text(item, "title")
            if not title:
                continue

            articles.append(
                {
                    "title": title,
                    "description": self._clean_html(
                        self._text(item, "description") or ""
                    ),
                    "source": source,
                    "published": self._text(item, "pubDate") or "",
                    "link": self._text(item, "link") or "",
                }
            )

        return articles

    def _parse_atom(self, root: ET.Element, source: str) -> List[Dict[str, str]]:
        """Parses an Atom feed XML element.

        Args:
            root: XML root element.
            source: Name of the news source.

        Returns:
            List of article dicts.
        """
        articles = []

        for entry in root.findall(f"{{{ATOM_NS}}}entry"):
            title = self._text(entry, f"{{{ATOM_NS}}}title")
            if not title:
                continue

            # Atom links are in an attribute
            link_el = entry.find(f"{{{ATOM_NS}}}link")
            link = link_el.get("href", "") if link_el is not None else ""

            summary = self._text(entry, f"{{{ATOM_NS}}}summary") or self._text(
                entry, f"{{{ATOM_NS}}}content"
            ) or ""

            published = self._text(
                entry, f"{{{ATOM_NS}}}published"
            ) or self._text(entry, f"{{{ATOM_NS}}}updated") or ""

            articles.append(
                {
                    "title": title,
                    "description": self._clean_html(summary),
                    "source": source,
                    "published": published,
                    "link": link,
                }
            )

        return articles

    @staticmethod
    def _text(element: ET.Element, tag: str) -> Optional[str]:
        """Safely gets text content of a child element."""
        child = element.find(tag)
        if child is not None and child.text:
            return child.text.strip()
        return None

    @staticmethod
    def _clean_html(text: str) -> str:
        """Removes basic HTML tags from text."""
        import re
        clean = re.sub(r"<[^>]+>", "", text)
        clean = clean.replace("&amp;", "&").replace("&lt;", "<").replace(
            "&gt;", ">"
        ).replace("&quot;", '"').replace("&#39;", "'").replace("&nbsp;", " ")
        # Collapse whitespace
        clean = re.sub(r"\s+", " ", clean).strip()
        return clean

    def _matches_category(self, article: Dict[str, str], category: str) -> bool:
        """Checks whether an article matches a given category.

        Args:
            article: Article dict.
            category: Category name (lowercase).

        Returns:
            True if the article matches the category.
        """
        if not category:
            return True

        category = category.lower()
        keywords = CATEGORY_KEYWORDS.get(category)
        if keywords is None:
            return True  # Unknown category passes everything through

        text = (
            f"{article.get('title', '')} {article.get('description', '')}"
        ).lower()

        return any(kw in text for kw in keywords)

    async def _fallback_bing_search(self, query: str, num_results: int) -> List[Dict[str, str]]:
        """Falls back to Bing search when RSS feeds fail.

        Args:
            query: Search query string.
            num_results: Number of results to request.

        Returns:
            List of article-like dicts from Bing search results.
        """
        try:
            from src.mcp.tools.search.manager import get_search_manager

            search_manager = get_search_manager()
            results = await search_manager.search(
                query=query,
                num_results=num_results,
                language="en-us",
                region="US",
            )

            articles = []
            for result in results:
                articles.append(
                    {
                        "title": result.title,
                        "description": result.snippet or "",
                        "source": f"Bing Search ({result.source or 'web'})",
                        "published": "",
                        "link": result.url,
                    }
                )
            return articles

        except Exception as e:
            logger.error(f"Bing search fallback also failed: {e}")
            return []

    async def fetch_top_headlines(
        self,
        category: str = "",
        num_results: int = 10,
    ) -> List[Dict[str, str]]:
        """Fetches top US news headlines from RSS feeds.

        Args:
            category: Optional category filter.
            num_results: Maximum number of articles to return.

        Returns:
            List of article dicts.
        """
        all_articles: List[Dict[str, str]] = []

        for feed in RSS_FEEDS:
            articles = await self._fetch_feed(feed)
            all_articles.extend(articles)

        # Filter by category if specified
        if category:
            all_articles = [
                a for a in all_articles if self._matches_category(a, category)
            ]

        # If no articles from RSS, fall back to Bing search
        if not all_articles:
            logger.info("No RSS articles retrieved, falling back to Bing search")
            fallback_query = f"latest US {category} news" if category else "latest US news"
            all_articles = await self._fallback_bing_search(
                fallback_query, num_results
            )

        return all_articles[:num_results]

    async def search_news(
        self,
        query: str,
        num_results: int = 10,
    ) -> List[Dict[str, str]]:
        """Searches news articles by keyword across RSS feeds.

        Args:
            query: Search keyword.
            num_results: Maximum number of articles to return.

        Returns:
            List of matching article dicts.
        """
        all_articles: List[Dict[str, str]] = []

        for feed in RSS_FEEDS:
            articles = await self._fetch_feed(feed)
            all_articles.extend(articles)

        # Filter by keyword
        query_lower = query.lower()
        query_terms = query_lower.split()

        matching = []
        for article in all_articles:
            text = (
                f"{article.get('title', '')} {article.get('description', '')}"
            ).lower()
            if any(term in text for term in query_terms):
                matching.append(article)

        # If no matches from RSS, fall back to Bing search
        if not matching:
            logger.info(
                f"No RSS matches for '{query}', falling back to Bing search"
            )
            matching = await self._fallback_bing_search(
                f"{query} US news", num_results
            )

        return matching[:num_results]


# Global manager instance
_news_manager = None


def get_news_manager() -> NewsManager:
    """
    Gets the singleton instance of the news manager.
    """
    global _news_manager
    if _news_manager is None:
        _news_manager = NewsManager()
    return _news_manager


async def cleanup_news_manager():
    """
    Cleans up the news manager resources.
    """
    global _news_manager
    if _news_manager:
        await _news_manager.cleanup()
        _news_manager = None
