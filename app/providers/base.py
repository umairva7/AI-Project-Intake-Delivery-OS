# app/providers/base.py
from abc import ABC, abstractmethod
from typing import Optional

from app.models import ExtractionResult


class BaseLLMProvider(ABC):
    """
    Abstract interface for LLM service providers.
    All providers (Groq, Ollama, future cloud providers) must implement this contract.
    """

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Name of the provider (e.g. 'groq', 'ollama')."""
        pass

    @abstractmethod
    def check_health(self) -> bool:
        """
        Check if the LLM provider service and credentials are reachable and healthy.
        Returns True if operational, False otherwise.
        """
        pass

    @abstractmethod
    def generate(
        self,
        prompt: str,
        format: Optional[str] = None,
        timeout: Optional[int] = None,
    ) -> str:
        """
        General-purpose prompt completion call.
        Returns raw string response.
        """
        pass

    @abstractmethod
    def extract_requirements(
        self,
        brief_text: str,
        retry_count: int = 0,
        last_error: Optional[str] = None,
    ) -> ExtractionResult:
        """
        Extract structured requirements from an unstructured brief.
        Returns an ExtractionResult model containing status, extraction, and review flags.
        """
        pass
