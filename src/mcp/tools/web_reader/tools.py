from src.mcp.tools.search.client import SearchClient


async def read_webpage(url: str, max_length: int = 8000) -> str:
    """
    Reads the content of a webpage.
    """
    async with SearchClient() as client:
        content = await client.fetch_webpage_content(url, max_length)
        return content
