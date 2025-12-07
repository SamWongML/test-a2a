"""Shared configuration settings for all agents."""

from functools import lru_cache

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Base settings for all agents."""

    # Azure OpenAI settings (uses Entra ID auth)
    azure_openai_endpoint: str = ""
    azure_openai_deployment: str = ""
    azure_openai_api_version: str = "2024-02-15-preview"

    # Azure OpenAI Embedding settings
    azure_openai_embedding_deployment: str = "text-embedding-3-large"

    # Azure Entra ID credentials
    azure_tenant_id: str = ""
    azure_client_id: str = ""
    azure_client_secret: str = ""

    # Agent URLs
    research_agent_url: str = "http://localhost:8001"
    explainer_agent_url: str = "http://localhost:8002"
    knowledge_agent_url: str = "http://localhost:8003"

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
    azure_openai_deployment: str = "gpt-4o"


class ResearchSettings(Settings):
    """Settings for the Research agent."""

    port: int = 8001
    azure_openai_deployment: str = "gpt-4o"
    firecrawl_api_key: str
    github_token: str = ""


class ExplainerSettings(Settings):
    """Settings for the Explainer agent."""

    port: int = 8002
    azure_openai_deployment: str = "gpt-4o"
    context7_api_key: str


class KnowledgeSettings(Settings):
    """Settings for the Knowledge Manager agent."""

    port: int = 8003
    azure_openai_deployment: str = "gpt-4o"
    vector_db_path: str = "./data/knowledge.lance"


@lru_cache
def get_settings() -> Settings:
    """Get cached base settings."""
    return Settings()
