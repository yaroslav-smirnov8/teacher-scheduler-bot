"""Abstract base class for AI providers"""
from abc import ABC, abstractmethod


class AIProvider(ABC):
    """Base class for AI homework generation providers."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        temperature: float = 0.3,
    ) -> tuple[str | None, str | None]:
        """Send a prompt to the provider and return the response.

        Args:
            prompt: The full prompt to send.
            temperature: Model temperature (0.0-1.0).

        Returns:
            Tuple of (response_text, error_message).
            On success: (response_text, None).
            On failure: (None, error_message).
        """
        ...

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable provider name for logging."""
        ...

    @property
    @abstractmethod
    def model_name(self) -> str:
        """Model identifier for logging."""
        ...
