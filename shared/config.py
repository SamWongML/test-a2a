"""Shared configuration settings for all agents."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Base settings for all agents."""

    # API Keys
    google_api_key: str

    # Agent URLs
    research_agent_url: str = "http://localhost:8001"
    explainer_agent_url: str = "http://localhost:8002"
    knowledge_agent_url: str = "http://localhost:8003"

    # LLM Settings
    gemini_model: str = "gemini-2.0-flash"

    # Server Settings
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "extra": "ignore",
    }


class OrchestratorSettings(Settings):
    """Settings for the Orchestrator agent."""

    port: int = 8000


class ResearchSettings(Settings):
    """Settings for the Research agent."""

    port: int = 8001
    firecrawl_api_key: str
    github_token: str = ""


class ExplainerSettings(Settings):
    """Settings for the Explainer agent."""

    port: int = 8002
    context7_api_key: str


class KnowledgeSettings(Settings):
    """Settings for the Knowledge Manager agent."""

    port: int = 8003
    vector_db_path: str = "./data/knowledge.lance"


@lru_cache
def get_settings() -> Settings:
    """Get cached base settings."""
    return Settings()
