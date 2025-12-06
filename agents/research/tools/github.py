"""GitHub search tool for finding AI projects."""

import httpx
from crewai.tools import BaseTool
from pydantic import BaseModel


class GitHubSearchInput(BaseModel):
    """Input for GitHub search."""

    query: str
    max_results: int = 10
    sort: str = "stars"  # stars, forks, updated


class GitHubSearchTool(BaseTool):
    """Tool for searching GitHub repositories."""

    name: str = "github_search"
    description: str = """Search GitHub for repositories related to AI, machine learning, 
    and open source projects. Returns repository names, descriptions, stars, and URLs.
    Use this to find popular and trending AI projects on GitHub.
    Input should be a search query for repositories."""
    args_schema: type[BaseModel] = GitHubSearchInput

    token: str = ""

    def __init__(self, token: str = "", **kwargs):
        super().__init__(token=token, **kwargs)

    def _run(self, query: str, max_results: int = 10, sort: str = "stars") -> str:
        """Search GitHub repositories."""
        try:
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "AI-Research-Agent",
            }
            if self.token:
                headers["Authorization"] = f"token {self.token}"

            # Search for repositories
            params = {
                "q": f"{query} language:python",
                "sort": sort,
                "order": "desc",
                "per_page": max_results,
            }

            with httpx.Client() as client:
                response = client.get(
                    "https://api.github.com/search/repositories",
                    headers=headers,
                    params=params,
                    timeout=30.0,
                )
                response.raise_for_status()
                data = response.json()

            if not data.get("items"):
                return f"No repositories found for: {query}"

            # Format results
            formatted = []
            for repo in data["items"][:max_results]:
                name = repo.get("full_name", "Unknown")
                description = repo.get("description", "No description")[:200]
                stars = repo.get("stargazers_count", 0)
                forks = repo.get("forks_count", 0)
                url = repo.get("html_url", "")
                updated = repo.get("updated_at", "")[:10]
                topics = ", ".join(repo.get("topics", [])[:5])

                formatted.append(
                    f"**{name}** ⭐ {stars:,} | 🍴 {forks:,}\n"
                    f"URL: {url}\n"
                    f"Description: {description}\n"
                    f"Topics: {topics}\n"
                    f"Last Updated: {updated}"
                )

            return "\n\n---\n\n".join(formatted)

        except Exception as e:
            return f"GitHub search error: {str(e)}"


class GitHubRepoDetailsTool(BaseTool):
    """Tool for getting detailed information about a GitHub repository."""

    name: str = "github_repo_details"
    description: str = """Get detailed information about a specific GitHub repository.
    Input should be the full repository name (e.g., 'langchain-ai/langchain')."""

    token: str = ""

    def __init__(self, token: str = "", **kwargs):
        super().__init__(token=token, **kwargs)

    def _run(self, repo_name: str) -> str:
        """Get repository details."""
        try:
            headers = {
                "Accept": "application/vnd.github.v3+json",
                "User-Agent": "AI-Research-Agent",
            }
            if self.token:
                headers["Authorization"] = f"token {self.token}"

            with httpx.Client() as client:
                # Get repo info
                response = client.get(
                    f"https://api.github.com/repos/{repo_name}",
                    headers=headers,
                    timeout=30.0,
                )
                response.raise_for_status()
                repo = response.json()

                # Get README
                try:
                    readme_response = client.get(
                        f"https://api.github.com/repos/{repo_name}/readme",
                        headers={**headers, "Accept": "application/vnd.github.raw+json"},
                        timeout=30.0,
                    )
                    readme = (
                        readme_response.text[:2000] if readme_response.status_code == 200 else ""
                    )
                except Exception:
                    readme = ""

            # Format result
            result = f"""# {repo.get("full_name", repo_name)}

**Description:** {repo.get("description", "No description")}

**Stats:**
- ⭐ Stars: {repo.get("stargazers_count", 0):,}
- 🍴 Forks: {repo.get("forks_count", 0):,}
- 👁️ Watchers: {repo.get("watchers_count", 0):,}
- 🐛 Open Issues: {repo.get("open_issues_count", 0):,}

**Info:**
- Language: {repo.get("language", "Unknown")}
- License: {repo.get("license", {}).get("name", "Unknown") if repo.get("license") else "Unknown"}
- Created: {repo.get("created_at", "")[:10]}
- Last Updated: {repo.get("updated_at", "")[:10]}

**Topics:** {", ".join(repo.get("topics", []))}

**README Preview:**
{readme[:1500]}{"..." if len(readme) > 1500 else ""}
"""
            return result

        except Exception as e:
            return f"Error getting repo details: {str(e)}"
