"""Explainer Agent configuration."""

import sys
from functools import lru_cache

sys.path.insert(0, "/app")

from shared.config import Settings


class ExplainerSettings(Settings):
    """Settings for the Explainer agent."""

    port: int = 8002
    agent_name: str = "explainer-agent"
    agent_description: str = "Explains technologies with detailed code snippets"

    # Explainer-specific settings
    context7_api_key: str


@lru_cache
def get_settings() -> ExplainerSettings:
    """Get cached explainer settings."""
    return ExplainerSettings()
