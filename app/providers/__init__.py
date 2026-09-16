# app/providers/__init__.py
import logging
from typing import Optional, Union, Any

from app.config import settings
from app.providers.base import BaseLLMProvider
from app.providers.groq import (
    GroqProvider,
    GroqClient,
    GroqProviderError,
    GroqAuthenticationError,
    GroqConnectionError,
    GroqTimeoutError,
    GroqRateLimitError,
    GroqServerError,
)
from app.providers.ollama import (
    OllamaProvider,
    ExtractionResult,
    clean_and_parse_json,
    OllamaProviderError,
    OllamaConnectionError,
    OllamaTimeoutError,
)

logger = logging.getLogger(__name__)


def get_llm_provider(
    provider_name: Optional[str] = None,
    **kwargs: Any,
) -> BaseLLMProvider:
    """
    Factory function returning the configured LLM provider instance.
    Defaults to settings.LLM_PROVIDER (which defaults to 'groq').

    Args:
        provider_name: Optional provider override ('groq' or 'ollama').
        **kwargs: Optional configuration parameters forwarded to provider constructor.

    Returns:
        Configured BaseLLMProvider instance.
    """
    target = (provider_name or settings.LLM_PROVIDER).lower().strip()

    if target == "groq":
        logger.info("Initializing primary LLM provider: Groq (model=%s)", kwargs.get("model", settings.GROQ_MODEL))
        return GroqProvider(**kwargs)
    elif target == "ollama":
        logger.info("Initializing secondary LLM provider: Ollama (model=%s)", kwargs.get("model", settings.OLLAMA_MODEL))
        return OllamaProvider(**kwargs)
    else:
        logger.warning(
            "Unknown LLM provider '%s' requested; defaulting to primary provider (Groq)",
            target,
        )
        return GroqProvider(**kwargs)


__all__ = [
    "BaseLLMProvider",
    "GroqProvider",
    "GroqClient",
    "GroqProviderError",
    "GroqAuthenticationError",
    "GroqConnectionError",
    "GroqTimeoutError",
    "GroqRateLimitError",
    "GroqServerError",
    "OllamaProvider",
    "OllamaProviderError",
    "OllamaConnectionError",
    "OllamaTimeoutError",
    "ExtractionResult",
    "clean_and_parse_json",
    "get_llm_provider",
]
