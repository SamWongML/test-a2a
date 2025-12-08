"""Centralized Azure AD Token Manager with automatic refresh.

Provides a thread-safe singleton for managing Azure AD tokens used across
all agents in the multi-agent system. Automatically refreshes tokens
10 minutes before expiration to prevent authentication failures.
"""

from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from azure.core.credentials import AccessToken

    from shared.config import Settings

# Set up module logger
logger = logging.getLogger("token-manager")

# Refresh token 10 minutes before expiration
TOKEN_REFRESH_BUFFER_SECONDS = 600


@dataclass
class CachedToken:
    """Cached token with expiration tracking."""

    token: str
    expires_at: float  # Unix timestamp


class TokenManager:
    """Thread-safe singleton for Azure AD token management.

    Automatically refreshes tokens 10 minutes before expiration.
    Provides both raw tokens and token provider functions for different
    frameworks (OpenAI, PydanticAI, Agno, CrewAI, LangChain).

    Usage:
        # Initialize once at application startup
        settings = get_settings()
        TokenManager.initialize(settings)

        # Get token provider for OpenAI clients
        token_provider = TokenManager.get_instance().get_token_provider()

        # Get raw token for CrewAI/environment variables
        token = TokenManager.get_instance().get_token()
    """

    _instance: TokenManager | None = None
    _lock = threading.Lock()

    def __new__(cls, settings: Settings | None = None) -> TokenManager:
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    instance = super().__new__(cls)
                    instance._initialized = False
                    cls._instance = instance
        return cls._instance

    def __init__(self, settings: Settings | None = None) -> None:
        if self._initialized:
            return
        if settings is None:
            raise ValueError("Settings required for first TokenManager initialization")

        self._settings = settings
        self._cached_token: CachedToken | None = None
        self._token_lock = threading.Lock()
        self._credential = None
        self._initialized = True
        logger.info("TokenManager initialized")

    def _get_credential(self):
        """Lazily initialize Azure credential."""
        if self._credential is None:
            from azure.identity import ClientSecretCredential

            logger.debug("Creating Azure ClientSecretCredential")
            self._credential = ClientSecretCredential(
                tenant_id=self._settings.azure_tenant_id,
                client_id=self._settings.azure_client_id,
                client_secret=self._settings.azure_client_secret,
            )
        return self._credential

    def _is_token_valid(self) -> bool:
        """Check if cached token is valid (not expired + buffer)."""
        if self._cached_token is None:
            return False
        return time.time() < (self._cached_token.expires_at - TOKEN_REFRESH_BUFFER_SECONDS)

    def _refresh_token(self) -> AccessToken:
        """Get a fresh token from Azure AD."""
        logger.info("Refreshing Azure AD token...")
        try:
            credential = self._get_credential()
            token = credential.get_token("https://cognitiveservices.azure.com/.default")
            logger.info("Successfully acquired Azure AD token")
            return token
        except Exception as e:
            logger.error(f"Failed to refresh Azure AD token: {str(e)}", exc_info=True)
            raise

    def get_token(self) -> str:
        """Get a valid Azure AD token, refreshing if necessary.

        Thread-safe method that returns a valid token. If the cached token
        is expired or will expire within 10 minutes, a new token is fetched.

        Returns:
            str: A valid Azure AD access token.
        """
        with self._token_lock:
            if not self._is_token_valid():
                access_token = self._refresh_token()
                self._cached_token = CachedToken(
                    token=access_token.token,
                    expires_at=access_token.expires_on,
                )
            return self._cached_token.token

    def get_token_provider(self) -> Callable[[], str]:
        """Get a token provider function for Azure OpenAI clients.

        Returns a callable that can be passed to Azure OpenAI clients
        as the `azure_ad_token_provider` parameter. The callable returns
        a fresh token on each call if the cached token is expired.

        Returns:
            Callable[[], str]: A function that returns a valid token.
        """
        return self.get_token

    def set_environment_token(self) -> None:
        """Set Azure token environment variables for libraries that need them.

        Sets the following environment variables:
        - AZURE_API_KEY: For CrewAI and LiteLLM (uses Azure AD token as API key)
        - AZURE_API_BASE: Azure OpenAI endpoint
        - AZURE_API_VERSION: API version
        """
        os.environ["AZURE_API_KEY"] = self.get_token()
        os.environ["AZURE_API_BASE"] = self._settings.azure_openai_endpoint
        os.environ["AZURE_API_VERSION"] = self._settings.azure_openai_api_version

    def get_token_expiry(self) -> float | None:
        """Get the expiration timestamp of the current cached token.

        Returns:
            float | None: Unix timestamp of token expiration, or None if no token cached.
        """
        if self._cached_token is None:
            return None
        return self._cached_token.expires_at

    def get_time_until_refresh(self) -> float | None:
        """Get seconds until the next token refresh is needed.

        Returns:
            float | None: Seconds until refresh, or None if no token cached.
                         Returns 0 if refresh is already needed.
        """
        if self._cached_token is None:
            return None
        time_until_refresh = (
            self._cached_token.expires_at - TOKEN_REFRESH_BUFFER_SECONDS - time.time()
        )
        return max(0, time_until_refresh)

    @classmethod
    def initialize(cls, settings: Settings) -> TokenManager:
        """Initialize the singleton with settings.

        Must be called once at application startup before any token operations.

        Args:
            settings: Application settings with Azure credentials.

        Returns:
            TokenManager: The initialized singleton instance.
        """
        return cls(settings)

    @classmethod
    def get_instance(cls) -> TokenManager:
        """Get the initialized singleton instance.

        Raises:
            RuntimeError: If TokenManager was not initialized.

        Returns:
            TokenManager: The singleton instance.
        """
        if cls._instance is None:
            raise RuntimeError("TokenManager not initialized. Call initialize() first.")
        return cls._instance

    @classmethod
    def reset(cls) -> None:
        """Reset the singleton instance. Primarily for testing."""
        with cls._lock:
            cls._instance = None
