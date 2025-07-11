"""Base adapter interface for LLM providers."""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from typing import Any

from src.models.messages import ServerMessage


class LLMAdapter(ABC):
    """Abstract base class for LLM provider adapters."""

    @abstractmethod
    def generate_response(
        self,
        message: str,
        request_id: str,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[ServerMessage]:
        """Generate a response from the LLM provider.

        Args:
            message: User message
            request_id: Unique request identifier
            tools: Optional list of available tools
            **kwargs: Additional provider-specific parameters

        Yields:
            ServerMessage: Response chunks from the provider
        """
        ...

    @abstractmethod
    async def validate_config(self) -> bool:
        """Validate the adapter configuration.

        Returns:
            bool: True if configuration is valid
        """
        pass
