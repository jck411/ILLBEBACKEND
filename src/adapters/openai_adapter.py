"""OpenAI adapter implementation."""

import time
from collections.abc import AsyncGenerator
from typing import Any

from openai import AsyncOpenAI

from src.adapters.base import LLMAdapter
from src.models.config import OpenAIConfig
from src.models.messages import ResponseChunk, ResponseStatus, ServerMessage
from src.utils.logging import get_logger


class OpenAIAdapter(LLMAdapter):
    """OpenAI API adapter."""

    def __init__(self, config: OpenAIConfig) -> None:
        """Initialize OpenAI adapter.

        Args:
            config: OpenAI configuration
        """
        self.config = config
        self.client = AsyncOpenAI(api_key=config.api_key)
        self.logger = get_logger(__name__)

    async def generate_response(
        self,
        message: str,
        request_id: str,
        tools: list[dict[str, Any]] | None = None,
        **kwargs: Any,
    ) -> AsyncGenerator[ServerMessage]:
        """Generate a response from OpenAI.

        Args:
            message: User message
            request_id: Unique request identifier
            tools: Optional list of available tools
            **kwargs: Additional parameters

        Yields:
            ServerMessage: Response chunks from OpenAI
        """
        start_time = time.time()

        # Send processing status
        yield ServerMessage(
            request_id=request_id,
            status=ResponseStatus.PROCESSING,
            chunk=ResponseChunk(
                type=None, data=None, metadata={"user_message": message}
            ),
            error=None,
        )

        try:
            # Prepare messages
            messages = [
                {"role": "system", "content": self.config.system_prompt},
                {"role": "user", "content": message},
            ]

            # Prepare API call parameters
            api_params = {
                "model": self.config.model,
                "messages": messages,
                "temperature": self.config.temperature,
                "top_p": self.config.top_p,
                "max_tokens": self.config.max_tokens,
                "stream": self.config.stream,
            }

            # Add tools if provided
            if tools:
                api_params["tools"] = tools
                api_params["tool_choice"] = "auto"

            # Make API call
            if self.config.stream:
                # Streaming response
                stream = await self.client.chat.completions.create(**api_params)

                async for chunk in stream:
                    if chunk.choices and chunk.choices[0].delta.content:
                        yield ServerMessage(
                            request_id=request_id,
                            status=ResponseStatus.CHUNK,
                            chunk=ResponseChunk(
                                type="text",
                                data=chunk.choices[0].delta.content,
                                metadata={},
                            ),
                            error=None,
                        )

                    # Handle tool calls if present
                    if chunk.choices and chunk.choices[0].delta.tool_calls:
                        for tool_call in chunk.choices[0].delta.tool_calls:
                            yield ServerMessage(
                                request_id=request_id,
                                status=ResponseStatus.CHUNK,
                                chunk=ResponseChunk(
                                    type="tool_call",
                                    data=tool_call.model_dump_json(),
                                    metadata={},
                                ),
                                error=None,
                            )
            else:
                # Non-streaming response
                response = await self.client.chat.completions.create(**api_params)

                if response.choices and response.choices[0].message.content:
                    yield ServerMessage(
                        request_id=request_id,
                        status=ResponseStatus.CHUNK,
                        chunk=ResponseChunk(
                            type="text",
                            data=response.choices[0].message.content,
                            metadata={},
                        ),
                        error=None,
                    )

            # Send completion status
            elapsed_ms = (time.time() - start_time) * 1000
            self.logger.info(
                "openai_response_complete",
                request_id=request_id,
                elapsed_ms=elapsed_ms,
                model=self.config.model,
            )

            yield ServerMessage(
                request_id=request_id,
                status=ResponseStatus.COMPLETE,
                chunk=None,
                error=None,
            )

        except Exception as e:
            self.logger.error(
                "openai_error",
                request_id=request_id,
                error=str(e),
                exc_info=True,
            )
            yield ServerMessage(
                request_id=request_id,
                status=ResponseStatus.ERROR,
                error=f"OpenAI error: {str(e)}",
                chunk=None,
            )

    async def validate_config(self) -> bool:
        """Validate OpenAI configuration.

        Returns:
            bool: True if configuration is valid
        """
        try:
            # Test API key by listing models
            await self.client.models.list()
            self.logger.info("openai_config_valid")
            return True
        except Exception as e:
            self.logger.error("openai_config_invalid", error=str(e))
            return False
