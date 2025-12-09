"""Research Agent configuration."""

import sys
from functools import lru_cache

sys.path.insert(0, "/app")

from shared.config import Settings


class ResearchSettings(Settings):
    """Settings for the Research agent."""

    port: int = 8001
    agent_name: str = "research-agent"
    agent_description: str = "Researches AI projects with Firecrawl and GitHub MCP"
    azure_openai_deployment: str = "gpt-4o"

    # Research-specific settings
    firecrawl_api_key: str
    github_token: str = ""
    max_results: int = 10


@lru_cache
def get_settings() -> ResearchSettings:
    """Get cached research settings."""
    return ResearchSettings()
