"""Model factory for Azure OpenAI LLM support.

Provides factory methods to create LLM instances for different frameworks
(PydanticAI, Agno, CrewAI, OpenAI client) using Azure OpenAI with Entra ID auth.
All token management is handled by the centralized TokenManager.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from shared.config import Settings

# Set up module logger
logger = logging.getLogger("model-factory")


class ModelFactory:
    """Factory for creating Azure OpenAI LLM instances.

    All instances use the centralized TokenManager for authentication.
    Ensure TokenManager.initialize(settings) is called before using any
    factory methods.
    """

    @staticmethod
    def _get_token_manager():
        """Get the TokenManager singleton instance."""
        from shared.token_manager import TokenManager

        return TokenManager.get_instance()

    @staticmethod
    def create_genai_model(settings: Settings) -> Any:
        """Create Azure OpenAI client for chat completions.

        Returns an openai.AzureOpenAI client configured with Entra ID auth.
        """
        from openai import AzureOpenAI

        logger.info(f"Creating AzureOpenAI client for endpoint: {settings.azure_openai_endpoint}")
        try:
            token_provider = ModelFactory._get_token_manager().get_token_provider()
            client = AzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                azure_ad_token_provider=token_provider,
                api_version=settings.azure_openai_api_version,
            )
            logger.info("AzureOpenAI client created successfully")
            return client
        except Exception as e:
            logger.error(f"Failed to create AzureOpenAI client: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def create_pydantic_ai_model(settings: Settings) -> Any:
        """Create model for PydanticAI (used by explainer agent).

        Returns pydantic_ai.models.openai.OpenAIChatModel with Azure config.
        """
        from openai import AsyncAzureOpenAI
        from pydantic_ai.models.openai import OpenAIChatModel
        from pydantic_ai.providers.openai import OpenAIProvider

        logger.info(
            f"Creating PydanticAI model with deployment: {settings.azure_openai_deployment}"
        )
        try:
            token_provider = ModelFactory._get_token_manager().get_token_provider()
            azure_client = AsyncAzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                azure_ad_token_provider=token_provider,
                api_version=settings.azure_openai_api_version,
            )
            model = OpenAIChatModel(
                settings.azure_openai_deployment,
                provider=OpenAIProvider(openai_client=azure_client),
            )
            logger.info("PydanticAI model created successfully")
            return model
        except Exception as e:
            logger.error(f"Failed to create PydanticAI model: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def create_agno_model(settings: Settings) -> Any:
        """Create model for Agno (used by knowledge agent).

        Returns agno.models.azure.AzureOpenAI.
        """
        from agno.models.azure import AzureOpenAI

        logger.info(f"Creating Agno model with deployment: {settings.azure_openai_deployment}")
        try:
            token_provider = ModelFactory._get_token_manager().get_token_provider()
            model = AzureOpenAI(
                id=settings.azure_openai_deployment,
                azure_endpoint=settings.azure_openai_endpoint,
                azure_ad_token_provider=token_provider,
                api_version=settings.azure_openai_api_version,
            )
            logger.info("Agno model created successfully")
            return model
        except Exception as e:
            logger.error(f"Failed to create Agno model: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def create_crewai_llm(settings: Settings) -> Any:
        """Create LLM for CrewAI (used by research agent).

        Uses CrewAI's native LLM class with Azure OpenAI configuration.
        Sets AZURE_AD_TOKEN environment variable for authentication.
        """
        from crewai import LLM

        logger.info(
            f"Creating CrewAI LLM with deployment: azure/{settings.azure_openai_deployment}"
        )
        try:
            # Set environment variables for CrewAI's Azure provider
            ModelFactory._get_token_manager().set_environment_token()
            logger.debug("Environment variables set for CrewAI Azure provider")

            # Use CrewAI's native LLM with Azure
            llm = LLM(
                model=f"azure/{settings.azure_openai_deployment}",
            )
            logger.info("CrewAI LLM created successfully")
            return llm
        except Exception as e:
            logger.error(f"Failed to create CrewAI LLM: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def create_embedding_client(settings: Settings) -> Any:
        """Create Azure OpenAI client for embeddings.

        Returns an openai.AzureOpenAI client configured for embedding operations.
        """
        from openai import AzureOpenAI

        logger.info(
            f"Creating embedding client for model: {settings.azure_openai_embedding_deployment}"
        )
        try:
            token_provider = ModelFactory._get_token_manager().get_token_provider()
            client = AzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                azure_ad_token_provider=token_provider,
                api_version=settings.azure_openai_api_version,
            )
            logger.info("Embedding client created successfully")
            return client
        except Exception as e:
            logger.error(f"Failed to create embedding client: {str(e)}", exc_info=True)
            raise

    @staticmethod
    def get_provider_info(settings: Settings) -> dict[str, str]:
        """Get human-readable info about the configured provider."""
        return {
            "provider": "Azure OpenAI",
            "model": settings.azure_openai_deployment,
            "endpoint": settings.azure_openai_endpoint,
            "embedding_model": settings.azure_openai_embedding_deployment,
        }
