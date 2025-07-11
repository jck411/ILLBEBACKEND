"""OpenAI adapter implementation."""

import asyncio
import json
import time
from collections.abc import AsyncGenerator
from typing import Any

from openai import AsyncOpenAI
from pydantic import BaseModel

from src.adapters.base import LLMAdapter
from src.models.config import OpenAIConfig
from src.models.messages import ResponseChunk, ResponseStatus, ServerMessage
from src.utils.logging import get_logger


class ToolResult(BaseModel):
    """Model representing the result of a tool execution."""

    status: str
    result: Any = None
    error: str | None = None


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
        # Default timeout for tool execution
        self.tool_timeout: int = getattr(config, "tool_timeout", 30)

    async def execute_mcp_tool(self, tool_call: dict[str, Any]) -> ToolResult:
        """Execute a tool call via MCP.

        Args:
            tool_call: Tool call data from OpenAI

        Returns:
            ToolResult: Results from MCP tool execution
        """
        from src.mcp.models import MCPToolCall

        start_time = time.time()

        try:
            function_name = tool_call["function"]["name"]
            function_args = json.loads(tool_call["function"]["arguments"])

            # Create MCPToolCall from OpenAI format
            mcp_tool_call = MCPToolCall(
                id=tool_call.get("id", "unknown"),
                name=function_name,
                arguments=function_args,
            )

            # Get the MCP clients from the main module
            # This is a simple way to access the global clients
            try:
                from src.main import mcp_clients

                if mcp_clients:
                    # Try each MCP client until one succeeds
                    last_error = None
                    for client in mcp_clients:
                        try:
                            mcp_result = await client.execute_tool(mcp_tool_call)
                            if not mcp_result.error:
                                elapsed_ms = (time.time() - start_time) * 1000
                                self.logger.info(
                                    "mcp_tool_executed",
                                    module="openai_adapter",
                                    function_name=function_name,
                                    elapsed_ms=elapsed_ms,
                                )
                                return ToolResult(
                                    status="success", result=mcp_result.output
                                )
                            last_error = mcp_result.error
                        except Exception as e:
                            last_error = str(e)

                    # If we get here, all clients failed
                    return ToolResult(
                        status="error",
                        error=last_error or f"Tool '{function_name}' not found",
                    )
                else:
                    # No MCP clients available, try local tools directly
                    from src.mcp.tools import ToolRegistry

                    tool_handler = ToolRegistry.get_tool(function_name)
                    if tool_handler:
                        mcp_result = await tool_handler.execute(mcp_tool_call)
                        if not mcp_result.error:
                            elapsed_ms = (time.time() - start_time) * 1000
                            self.logger.info(
                                "mcp_tool_executed",
                                module="openai_adapter",
                                function_name=function_name,
                                elapsed_ms=elapsed_ms,
                            )
                            return ToolResult(
                                status="success", result=mcp_result.output
                            )
                        else:
                            return ToolResult(status="error", error=mcp_result.error)
                    else:
                        return ToolResult(
                            status="error", error=f"Tool '{function_name}' not found"
                        )

            except ImportError:
                # Fall back to local tools only if main module not available
                from src.mcp.tools import ToolRegistry

                tool_handler = ToolRegistry.get_tool(function_name)
                if tool_handler:
                    mcp_result = await tool_handler.execute(mcp_tool_call)
                    if not mcp_result.error:
                        elapsed_ms = (time.time() - start_time) * 1000
                        self.logger.info(
                            "mcp_tool_executed",
                            module="openai_adapter",
                            function_name=function_name,
                            elapsed_ms=elapsed_ms,
                        )
                        return ToolResult(status="success", result=mcp_result.output)
                    else:
                        return ToolResult(status="error", error=mcp_result.error)
                else:
                    return ToolResult(
                        status="error", error=f"Tool '{function_name}' not found"
                    )

        except TimeoutError:
            self.logger.error(
                "mcp_tool_timeout",
                module="openai_adapter",
                tool=tool_call.get("function", {}).get("name", "unknown"),
                elapsed_ms=(time.time() - start_time) * 1000,
            )
            return ToolResult(status="error", error="Tool execution timed out")

        except Exception as e:
            self.logger.error(
                "mcp_tool_error",
                module="openai_adapter",
                tool=tool_call.get("function", {}).get("name", "unknown"),
                error=str(e),
                elapsed_ms=(time.time() - start_time) * 1000,
                exc_info=True,
            )
            return ToolResult(status="error", error=str(e))

    async def generate_response(
        self,
        message: str,
        request_id: str,
        tools: list[dict[str, Any]] | None = None,
        use_mcp: bool = True,
        **kwargs: Any,
    ) -> AsyncGenerator[ServerMessage]:
        """Generate a response from OpenAI.

        Args:
            message: User message
            request_id: Unique request identifier
            tools: Optional list of available tools
            use_mcp: Whether to use MCP for tool execution (two-phase approach)
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

            # If MCP is not enabled or no tools are provided, use standard flow
            if not use_mcp or not tools:
                async for server_message in self._handle_standard_flow(
                    messages=messages,
                    tools=tools,
                    request_id=request_id,
                ):
                    yield server_message
            else:
                async for server_message in self._handle_mcp_flow(
                    messages=messages,
                    tools=tools,
                    request_id=request_id,
                    original_message=message,
                ):
                    yield server_message

            # Send completion status
            elapsed_ms = (time.time() - start_time) * 1000
            self.logger.info(
                "openai_response_complete",
                request_id=request_id,
                elapsed_ms=elapsed_ms,
                model=self.config.model,
                mcp_used=use_mcp,
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

    async def _handle_standard_flow(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]] | None,
        request_id: str,
    ) -> AsyncGenerator[ServerMessage]:
        """Handle standard OpenAI flow without MCP.

        Args:
            messages: List of messages to send to OpenAI
            tools: Optional list of tools
            request_id: Unique request identifier

        Yields:
            ServerMessage: Response chunks
        """
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

    async def _handle_mcp_flow(
        self,
        messages: list[dict[str, str]],
        tools: list[dict[str, Any]],
        request_id: str,
        original_message: str,
    ) -> AsyncGenerator[ServerMessage]:
        """Handle two-phase OpenAI flow with MCP.

        Args:
            messages: List of messages to send to OpenAI
            tools: List of tools to use with MCP
            request_id: Unique request identifier
            original_message: Original user message

        Yields:
            ServerMessage: Response chunks
        """
        # Notify client we're starting MCP flow
        yield ServerMessage(
            request_id=request_id,
            status=ResponseStatus.CHUNK,
            chunk=ResponseChunk(
                type="text",
                data="Starting two-phase OpenAI MCP interaction...",
                metadata={"phase": "start"},
            ),
            error=None,
        )

        # First phase: Get tool calls from OpenAI
        api_params = {
            "model": self.config.model,
            "messages": messages,
            "temperature": self.config.temperature,
            "tools": tools,
            "tool_choice": "auto",
            "stream": False,  # Two-phase works better with non-streaming first call
        }

        response = await self.client.chat.completions.create(**api_params)
        first_message = response.choices[0].message

        # If no tool calls, return the response directly
        if not first_message.tool_calls:
            yield ServerMessage(
                request_id=request_id,
                status=ResponseStatus.CHUNK,
                chunk=ResponseChunk(
                    type="text",
                    data=first_message.content or "No response generated",
                    metadata={},
                ),
                error=None,
            )
            return

        # Process tool calls
        yield ServerMessage(
            request_id=request_id,
            status=ResponseStatus.CHUNK,
            chunk=ResponseChunk(
                type="text",
                data=f"Executing {len(first_message.tool_calls)} tool calls...",
                metadata={
                    "phase": "tool_execution",
                    "count": len(first_message.tool_calls),
                },
            ),
            error=None,
        )

        # Prepare for second phase
        second_phase_messages = [
            {"role": "system", "content": self.config.system_prompt},
            {"role": "user", "content": original_message},
            first_message.model_dump(),  # Add the assistant's message with tool calls
        ]

        # Execute each tool call and add results
        for tool_call in first_message.tool_calls:
            # Execute the tool via MCP with timeout protection
            try:
                result = await asyncio.wait_for(
                    self.execute_mcp_tool(tool_call.model_dump()),
                    timeout=self.tool_timeout,
                )

                # Send tool execution progress to client
                yield ServerMessage(
                    request_id=request_id,
                    status=ResponseStatus.CHUNK,
                    chunk=ResponseChunk(
                        type="tool_result",
                        data=json.dumps(
                            {
                                "tool": tool_call.function.name,
                                "status": "complete",
                            }
                        ),
                        metadata={"tool_id": tool_call.id},
                    ),
                    error=None,
                )

                # Add tool result to messages for second phase
                second_phase_messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "content": json.dumps(result.model_dump()),
                    }
                )

            except Exception as e:
                self.logger.error(
                    "mcp_tool_error",
                    module="openai_adapter",
                    tool=tool_call.function.name,
                    error=str(e),
                    exc_info=True,
                )

                # Add error result to messages
                second_phase_messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "content": json.dumps({"error": str(e)}),
                    }
                )

        # Second phase: Get final response with tool outputs
        yield ServerMessage(
            request_id=request_id,
            status=ResponseStatus.CHUNK,
            chunk=ResponseChunk(
                type="text",
                data="Getting final response with tool results...",
                metadata={"phase": "final_response"},
            ),
            error=None,
        )

        second_params = {
            "model": self.config.model,
            "messages": second_phase_messages,
            "temperature": self.config.temperature,
            "stream": self.config.stream,
        }

        if self.config.stream:
            # Stream the final response
            stream = await self.client.chat.completions.create(**second_params)

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
        else:
            # Non-streaming final response
            final_response = await self.client.chat.completions.create(**second_params)

            if final_response.choices and final_response.choices[0].message.content:
                yield ServerMessage(
                    request_id=request_id,
                    status=ResponseStatus.CHUNK,
                    chunk=ResponseChunk(
                        type="text",
                        data=final_response.choices[0].message.content,
                        metadata={},
                    ),
                    error=None,
                )
