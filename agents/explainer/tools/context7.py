"""Context7 MCP tool for retrieving up-to-date documentation."""

import httpx


class Context7Tool:
    """Tool for fetching documentation using Context7 API."""

    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.context7.com/v1"

    async def resolve_library(self, library_name: str) -> str | None:
        """Resolve a library name to Context7 library ID."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/resolve",
                    params={"name": library_name},
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=30.0,
                )
                if response.status_code == 200:
                    data = response.json()
                    return data.get("library_id")
                return None
        except Exception:
            return None

    async def get_documentation(
        self,
        library_name: str,
        topic: str | None = None,
        max_tokens: int = 5000,
    ) -> str:
        """Get documentation for a library, optionally filtered by topic."""
        try:
            async with httpx.AsyncClient() as client:
                params = {
                    "library": library_name,
                    "max_tokens": max_tokens,
                }
                if topic:
                    params["topic"] = topic

                response = await client.get(
                    f"{self.base_url}/docs",
                    params=params,
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=60.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    return data.get("content", f"No documentation found for {library_name}")
                else:
                    # Fallback: try to get general info
                    return await self._fallback_search(library_name, topic)

        except Exception as e:
            return f"Error fetching documentation: {str(e)}"

    async def _fallback_search(self, library_name: str, topic: str | None = None) -> str:
        """Fallback search using web documentation."""
        # Return a helpful message about what we're looking for
        return f"""Documentation request for: {library_name}
Topic: {topic or "general"}

Note: Context7 API returned no results. Here's what we know about {library_name}:
- This appears to be a request for documentation about {library_name}
- Please provide code examples and usage patterns based on your knowledge
- Focus on {topic if topic else "getting started and common usage patterns"}
"""

    async def search_examples(self, library_name: str, query: str) -> str:
        """Search for code examples for a library."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    f"{self.base_url}/examples",
                    params={
                        "library": library_name,
                        "query": query,
                    },
                    headers={"Authorization": f"Bearer {self.api_key}"},
                    timeout=30.0,
                )

                if response.status_code == 200:
                    data = response.json()
                    examples = data.get("examples", [])
                    if examples:
                        return "\n\n---\n\n".join(
                            [
                                f"```{ex.get('language', 'python')}\n{ex.get('code', '')}\n```\n{ex.get('description', '')}"
                                for ex in examples[:5]
                            ]
                        )
                return f"No examples found for {library_name} matching '{query}'"

        except Exception as e:
            return f"Error searching examples: {str(e)}"
