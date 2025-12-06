"""Knowledge Manager Agent configuration."""

import sys
from functools import lru_cache

sys.path.insert(0, "/app")

from shared.config import Settings


class KnowledgeSettings(Settings):
    """Settings for the Knowledge Manager agent."""

    port: int = 8003
    agent_name: str = "knowledge-agent"
    agent_description: str = "Persistent memory and RAG for the multi-agent system"

    # Knowledge-specific settings
    vector_db_path: str = "./data/knowledge.lance"
    embedding_model: str = "models/text-embedding-004"
    max_search_results: int = 5


@lru_cache
def get_settings() -> KnowledgeSettings:
    """Get cached knowledge settings."""
    return KnowledgeSettings()
