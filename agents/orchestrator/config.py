"""Orchestrator configuration."""

import sys
from functools import lru_cache

sys.path.insert(0, "/app")

from shared.config import Settings


class OrchestratorSettings(Settings):
    """Settings for the Orchestrator agent."""

    port: int = 8000
    agent_name: str = "orchestrator-agent"
    agent_description: str = "Main orchestrator for multi-agent AI system"
    azure_openai_deployment: str = "gpt-4o"


@lru_cache
def get_settings() -> OrchestratorSettings:
    """Get cached orchestrator settings."""
    return OrchestratorSettings()
