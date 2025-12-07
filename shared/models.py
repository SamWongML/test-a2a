"""Model factory for multi-provider LLM support.

Provides factory methods to create LLM instances for different frameworks
(PydanticAI, Agno, CrewAI, raw google.generativeai) with support for
Gemini and Azure OpenAI providers.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from shared.config import Settings


class ModelFactory:
    """Factory for creating LLM instances across different providers."""

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
        """Create model for google.generativeai (used by orchestrator).

        For Gemini: returns google.generativeai.GenerativeModel
        For Azure: returns openai.AzureOpenAI client (different API!)
        """
        from shared.config import ModelProvider

        if settings.model_provider == ModelProvider.GEMINI:
            import google.generativeai as genai

            genai.configure(api_key=settings.google_api_key)
            return genai.GenerativeModel(settings.gemini_model)

        elif settings.model_provider == ModelProvider.AZURE_OPENAI:
            from openai import AzureOpenAI

            token_provider = ModelFactory._get_azure_token_provider(settings)
            return AzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                azure_ad_token_provider=token_provider,
                api_version=settings.azure_openai_api_version,
            )

        raise ValueError(f"Unsupported provider: {settings.model_provider}")

    @staticmethod
    def create_pydantic_ai_model(settings: Settings) -> Any:
        """Create model for PydanticAI (used by explainer agent).

        For Gemini: returns pydantic_ai.models.gemini.GeminiModel
        For Azure: returns pydantic_ai.models.openai.OpenAIModel with Azure config
        """
        from shared.config import ModelProvider

        if settings.model_provider == ModelProvider.GEMINI:
            import os

            from pydantic_ai.models.gemini import GeminiModel

            # Set the API key in env var as pydantic-ai expects
            os.environ["GEMINI_API_KEY"] = settings.google_api_key
            return GeminiModel(settings.gemini_model)

        elif settings.model_provider == ModelProvider.AZURE_OPENAI:
            from openai import AzureOpenAI
            from pydantic_ai.models.openai import OpenAIModel

            # Create Azure OpenAI client with Entra ID auth
            azure_client = AzureOpenAI(
                azure_endpoint=settings.azure_openai_endpoint,
                azure_ad_token_provider=ModelFactory._get_azure_token_provider(settings),
                api_version=settings.azure_openai_api_version,
            )
            return OpenAIModel(
                settings.azure_openai_deployment,
                openai_client=azure_client,
            )

        raise ValueError(f"Unsupported provider: {settings.model_provider}")

    @staticmethod
    def create_agno_model(settings: Settings) -> Any:
        """Create model for Agno (used by knowledge agent).

        For Gemini: returns agno.models.google.Gemini
        For Azure: returns agno.models.azure.AzureOpenAI
        """
        from shared.config import ModelProvider

        if settings.model_provider == ModelProvider.GEMINI:
            from agno.models.google import Gemini

            return Gemini(
                id=settings.gemini_model,
                api_key=settings.google_api_key,
            )

        elif settings.model_provider == ModelProvider.AZURE_OPENAI:
            from agno.models.azure import AzureOpenAI

            return AzureOpenAI(
                id=settings.azure_openai_deployment,
                azure_endpoint=settings.azure_openai_endpoint,
                azure_ad_token_provider=ModelFactory._get_azure_token_provider(settings),
                api_version=settings.azure_openai_api_version,
            )

        raise ValueError(f"Unsupported provider: {settings.model_provider}")

    @staticmethod
    def create_crewai_llm(settings: Settings) -> Any:
        """Create LLM for CrewAI (used by research agent).

        For Gemini: returns langchain_google_genai.ChatGoogleGenerativeAI
        For Azure: returns langchain_openai.AzureChatOpenAI
        """
        from shared.config import ModelProvider

        if settings.model_provider == ModelProvider.GEMINI:
            import os

            from crewai import LLM

            # Set API key in env var for CrewAI/LiteLLM
            os.environ["GEMINI_API_KEY"] = settings.google_api_key
            # CrewAI expects LiteLLM format: gemini/model-name
            return LLM(
                model=f"gemini/{settings.gemini_model}",
                temperature=0.7,
            )

        elif settings.model_provider == ModelProvider.AZURE_OPENAI:
            from langchain_openai import AzureChatOpenAI

            token_provider = ModelFactory._get_azure_token_provider(settings)
            return AzureChatOpenAI(
                azure_deployment=settings.azure_openai_deployment,
                azure_endpoint=settings.azure_openai_endpoint,
                azure_ad_token_provider=token_provider,
                api_version=settings.azure_openai_api_version,
            )

        raise ValueError(f"Unsupported provider: {settings.model_provider}")

    @staticmethod
    def get_provider_info(settings: Settings) -> dict[str, str]:
        """Get human-readable info about the configured provider."""
        from shared.config import ModelProvider

        if settings.model_provider == ModelProvider.GEMINI:
            return {
                "provider": "Google Gemini",
                "model": settings.gemini_model,
            }
        elif settings.model_provider == ModelProvider.AZURE_OPENAI:
            return {
                "provider": "Azure OpenAI",
                "model": settings.azure_openai_deployment,
                "endpoint": settings.azure_openai_endpoint,
            }
        return {"provider": "Unknown"}
