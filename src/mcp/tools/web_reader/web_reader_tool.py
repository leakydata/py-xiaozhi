from typing import Any, Dict, List, Type

from src.mcp.tools.search.client import SearchClient

from ..tool_base import ToolBase
from .models import WebReaderQuery, WebReaderResult


class WebReaderTool(ToolBase):
    """
    Web Reader tool.
    """

    name: str = "web_reader"
    description: str = "Reads the content of a webpage from a URL."
    args_schema: Type[WebReaderQuery] = WebReaderQuery
    results_schema: Type[WebReaderResult] = WebReaderResult

    async def _run(self, query: WebReaderQuery) -> WebReaderResult:
        """
        Reads the content of a webpage.
        """
        async with SearchClient() as client:
            content = await client.fetch_webpage_content(query.url, query.max_length)
            return WebReaderResult(content=content)
