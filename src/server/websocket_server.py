"""WebSocket server for handling chat connections."""

import json

from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from src.adapters.base import LLMAdapter
from src.mcp.client import MCPClient
from src.mcp.models import MCPToolCall
from src.models.config import Config
from src.models.messages import (
    ClientMessage,
    ResponseChunk,
    ResponseStatus,
    ServerMessage,
)
from src.utils.logging import get_logger


class WebSocketServer:
    """WebSocket server for handling chat connections."""

    def __init__(
        self,
        config: Config,
        llm_adapter: LLMAdapter,
        mcp_clients: list[MCPClient] | None = None,
    ) -> None:
        """Initialize WebSocket server.

        Args:
            config: Application configuration
            llm_adapter: LLM provider adapter
            mcp_clients: Optional list of MCP clients
        """
        self.config = config
        self.llm_adapter = llm_adapter
        self.mcp_clients = mcp_clients or []
        self.logger = get_logger(__name__)
        self.active_connections: dict[str, WebSocket] = {}

    async def connect(self, websocket: WebSocket, client_id: str) -> None:
        """Accept WebSocket connection.

        Args:
            websocket: WebSocket connection
            client_id: Unique client identifier
        """
        await websocket.accept()
        self.active_connections[client_id] = websocket
        self.logger.info("websocket_connected", client_id=client_id)

    async def disconnect(self, client_id: str) -> None:
        """Handle WebSocket disconnection.

        Args:
            client_id: Client identifier
        """
        if client_id in self.active_connections:
            del self.active_connections[client_id]
            self.logger.info("websocket_disconnected", client_id=client_id)

    async def handle_message(
        self,
        websocket: WebSocket,
        client_id: str,
    ) -> None:
        """Handle incoming WebSocket messages.

        Args:
            websocket: WebSocket connection
            client_id: Client identifier
        """
        try:
            while True:
                # Receive message
                data = await websocket.receive_text()

                try:
                    # Parse and validate message
                    message_data = json.loads(data)
                    client_message = ClientMessage(**message_data)

                    self.logger.info(
                        "message_received",
                        client_id=client_id,
                        request_id=client_message.request_id,
                        action=client_message.action,
                    )

                    # Handle chat action
                    if client_message.action == "chat":
                        await self._handle_chat(
                            websocket,
                            client_message,
                            client_id,
                        )
                    else:
                        # Unsupported action
                        error_response = ServerMessage(  # type: ignore[unreachable]
                            request_id=client_message.request_id,
                            status=ResponseStatus.ERROR,
                            error=f"Unsupported action: {client_message.action}",
                            chunk=None,
                        )
                        await websocket.send_text(error_response.model_dump_json())

                except ValidationError as e:
                    # Invalid message format
                    self.logger.error(
                        "invalid_message",
                        client_id=client_id,
                        error=str(e),
                    )
                    error_response = {
                        "status": "error",
                        "error": f"Invalid message format: {str(e)}",
                    }
                    await websocket.send_text(json.dumps(error_response))

                except json.JSONDecodeError as e:
                    # Invalid JSON
                    self.logger.error(
                        "invalid_json",
                        client_id=client_id,
                        error=str(e),
                    )
                    error_response = {
                        "status": "error",
                        "error": f"Invalid JSON: {str(e)}",
                    }
                    await websocket.send_text(json.dumps(error_response))

        except WebSocketDisconnect:
            await self.disconnect(client_id)
        except Exception as e:
            self.logger.error(
                "websocket_error",
                client_id=client_id,
                error=str(e),
                exc_info=True,
            )
            await self.disconnect(client_id)

    async def _handle_chat(
        self,
        websocket: WebSocket,
        message: ClientMessage,
        client_id: str,
    ) -> None:
        """Handle chat message.

        Args:
            websocket: WebSocket connection
            message: Client message
            client_id: Client identifier
        """
        try:
            # Get available tools from MCP servers and local tools
            tools = []
            if self.config.mcp.enabled:
                # Get tools from remote MCP servers
                for client in self.mcp_clients:
                    tools.extend(client.to_openai_tools())

                # Get local tools and add them to the tools list
                if self.mcp_clients:
                    # Use the first client to get combined tools (includes local)
                    combined_tools = await self.mcp_clients[0].get_tools()
                    for tool in combined_tools:
                        # Check if this is a local tool
                        # (not already added by to_openai_tools)
                        if not any(
                            openai_tool["function"]["name"].endswith(f"_{tool.name}")
                            for openai_tool in tools
                        ):
                            # Add local tool directly
                            tools.append(
                                {
                                    "type": "function",
                                    "function": {
                                        "name": tool.name,
                                        "description": tool.description,
                                        "parameters": tool.input_schema,
                                    },
                                }
                            )
                else:
                    # No MCP clients, get local tools directly
                    from src.mcp.tools import ToolRegistry

                    local_tools = ToolRegistry.get_tools()
                    for tool in local_tools:
                        tools.append(
                            {
                                "type": "function",
                                "function": {
                                    "name": tool.name,
                                    "description": tool.description,
                                    "parameters": tool.input_schema,
                                },
                            }
                        )

            # Generate response from LLM
            async for response in self.llm_adapter.generate_response(
                message=message.payload.text,
                request_id=message.request_id,
                tools=tools if tools else None,
                use_mcp=bool(tools),  # Enable MCP if we have tools
            ):
                # Send response chunk
                await websocket.send_text(response.model_dump_json())

                # Handle tool calls if present
                if (
                    response.status == ResponseStatus.CHUNK
                    and response.chunk
                    and response.chunk.type == "tool_call"
                ):
                    # Parse tool call
                    if response.chunk and response.chunk.data:
                        tool_call_data = json.loads(response.chunk.data)

                        # Find the appropriate MCP client
                        for mcp_client in self.mcp_clients:
                            if tool_call_data["name"].startswith(
                                f"{mcp_client.config.name}_"
                            ):
                                # Execute tool
                                tool_name = tool_call_data["name"].replace(
                                    f"{mcp_client.config.name}_", ""
                                )
                                tool_call = MCPToolCall(
                                    id=tool_call_data.get("id", ""),
                                    name=tool_name,
                                    arguments=tool_call_data.get("arguments", {}),
                                )

                            result = await mcp_client.call_tool(tool_call)

                            # Send tool result
                            tool_result_response = ServerMessage(
                                request_id=message.request_id,
                                status=ResponseStatus.CHUNK,
                                chunk=ResponseChunk(
                                    type="tool_result",
                                    data=json.dumps(
                                        {
                                            "tool_call_id": result.tool_call_id,
                                            "output": result.output,
                                            "error": result.error,
                                        }
                                    ),
                                    metadata={},
                                ),
                                error=None,
                            )
                            await websocket.send_text(
                                tool_result_response.model_dump_json()
                            )
                            break

        except Exception as e:
            self.logger.error(
                "chat_error",
                client_id=client_id,
                request_id=message.request_id,
                error=str(e),
                exc_info=True,
            )
            error_response = ServerMessage(
                request_id=message.request_id,
                status=ResponseStatus.ERROR,
                error=f"Chat error: {str(e)}",
                chunk=None,
            )
            await websocket.send_text(error_response.model_dump_json())
