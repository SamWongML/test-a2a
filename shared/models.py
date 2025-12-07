"""Model factory for Azure OpenAI LLM support.

Provides factory methods to create LLM instances for different frameworks
(PydanticAI, Agno, CrewAI, OpenAI client) using Azure OpenAI with Entra ID auth.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from shared.config import Settings


class ModelFactory:
    """Factory for creating Azure OpenAI LLM instances."""

    @staticmethod
    def _get_azure_credential(settings: Settings) -> Any:
        """Get Azure credential using Entra ID (service principal)."""
        from azure.identity import ClientSecretCredential

        return ClientSecretCredential(
            tenant_id=settings.azure_tenant_id,
            client_id=settings.azure_client_id,
            client_secret=settings.azure_client_secret,
        )

    @staticmethod
    def _get_azure_token_provider(settings: Settings) -> Any:
        """Get Azure token provider function for OpenAI client."""
        from azure.identity import get_bearer_token_provider

        credential = ModelFactory._get_azure_credential(settings)
        return get_bearer_token_provider(credential, "https://cognitiveservices.azure.com/.default")

    @staticmethod
    def create_genai_model(settings: Settings) -> Any:
        """Create Azure OpenAI client for chat completions.

        Returns an openai.AzureOpenAI client configured with Entra ID auth.
        """
        from openai import AzureOpenAI

        token_provider = ModelFactory._get_azure_token_provider(settings)
        return AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            azure_ad_token_provider=token_provider,
            api_version=settings.azure_openai_api_version,
        )

    @staticmethod
    def create_pydantic_ai_model(settings: Settings) -> Any:
        """Create model for PydanticAI (used by explainer agent).

        Returns pydantic_ai.models.openai.OpenAIModel with Azure config.
        """
        from openai import AzureOpenAI
        from pydantic_ai.models.openai import OpenAIModel

        azure_client = AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            azure_ad_token_provider=ModelFactory._get_azure_token_provider(settings),
            api_version=settings.azure_openai_api_version,
        )
        return OpenAIModel(
            settings.azure_openai_deployment,
            openai_client=azure_client,
        )

    @staticmethod
    def create_agno_model(settings: Settings) -> Any:
        """Create model for Agno (used by knowledge agent).

        Returns agno.models.azure.AzureOpenAI.
        """
        from agno.models.azure import AzureOpenAI

        return AzureOpenAI(
            id=settings.azure_openai_deployment,
            azure_endpoint=settings.azure_openai_endpoint,
            azure_ad_token_provider=ModelFactory._get_azure_token_provider(settings),
            api_version=settings.azure_openai_api_version,
        )

    @staticmethod
    def create_crewai_llm(settings: Settings) -> Any:
        """Create LLM for CrewAI (used by research agent).

        Returns langchain_openai.AzureChatOpenAI.
        """
        from langchain_openai import AzureChatOpenAI

        token_provider = ModelFactory._get_azure_token_provider(settings)
        return AzureChatOpenAI(
            azure_deployment=settings.azure_openai_deployment,
            azure_endpoint=settings.azure_openai_endpoint,
            azure_ad_token_provider=token_provider,
            api_version=settings.azure_openai_api_version,
        )

    @staticmethod
    def create_embedding_client(settings: Settings) -> Any:
        """Create Azure OpenAI client for embeddings.

        Returns an openai.AzureOpenAI client configured for embedding operations.
        """
        from openai import AzureOpenAI

        token_provider = ModelFactory._get_azure_token_provider(settings)
        return AzureOpenAI(
            azure_endpoint=settings.azure_openai_endpoint,
            azure_ad_token_provider=token_provider,
            api_version=settings.azure_openai_api_version,
        )

    @staticmethod
    def get_provider_info(settings: Settings) -> dict[str, str]:
        """Get human-readable info about the configured provider."""
        return {
            "provider": "Azure OpenAI",
            "model": settings.azure_openai_deployment,
            "endpoint": settings.azure_openai_endpoint,
            "embedding_model": settings.azure_openai_embedding_deployment,
        }
