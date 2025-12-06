"""Firecrawl web search tool for researching AI projects."""

from crewai.tools import BaseTool
from firecrawl import FirecrawlApp
from pydantic import BaseModel


class FirecrawlSearchInput(BaseModel):
    """Input for Firecrawl search."""

    query: str
    max_results: int = 5


class FirecrawlSearchTool(BaseTool):
    """Tool for searching the web using Firecrawl."""

    name: str = "firecrawl_search"
    description: str = """Search the web for information about AI projects, frameworks, and tools.
    Use this to find recent news, blog posts, documentation, and articles about AI/ML topics.
    Input should be a search query string."""
    args_schema: type[BaseModel] = FirecrawlSearchInput

    api_key: str
    _client: FirecrawlApp | None = None

    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        self._client = FirecrawlApp(api_key=api_key)

    def _run(self, query: str, max_results: int = 5) -> str:
        """Execute the web search."""
        try:
            # Use Firecrawl's search functionality
            results = self._client.search(
                query=query,
                limit=max_results,
            )

            if not results or not results.get("data"):
                return f"No results found for: {query}"

            # Format results
            formatted = []
            for item in results.get("data", [])[:max_results]:
                title = item.get("title", "No title")
                url = item.get("url", "")
                description = item.get("description", item.get("markdown", ""))[:300]
                formatted.append(f"**{title}**\nURL: {url}\n{description}\n")

            return "\n---\n".join(formatted)

        except Exception as e:
            return f"Search error: {str(e)}"


class FirecrawlScrapeTool(BaseTool):
    """Tool for scraping web pages using Firecrawl."""

    name: str = "firecrawl_scrape"
    description: str = """Scrape a specific URL to get its content in markdown format.
    Use this to get detailed information from a specific webpage.
    Input should be a valid URL."""

    api_key: str
    _client: FirecrawlApp | None = None

    def __init__(self, api_key: str, **kwargs):
        super().__init__(api_key=api_key, **kwargs)
        self._client = FirecrawlApp(api_key=api_key)

    def _run(self, url: str) -> str:
        """Scrape the URL content."""
        try:
            result = self._client.scrape_url(
                url=url,
                params={"formats": ["markdown"]},
            )

            if not result:
                return f"Could not scrape: {url}"

            content = result.get("markdown", "")
            # Truncate if too long
            if len(content) > 5000:
                content = content[:5000] + "\n\n[Content truncated...]"

            return content

        except Exception as e:
            return f"Scrape error: {str(e)}"
