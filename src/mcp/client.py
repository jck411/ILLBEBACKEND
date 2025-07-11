"""MCP client for connecting to MCP servers."""

import uuid
from typing import Any

import httpx

from src.mcp.models import (
    MCPCapabilities,
    MCPRequest,
    MCPResponse,
    MCPTool,
    MCPToolCall,
    MCPToolResult,
)
from src.models.config import MCPServerConfig
from src.utils.logging import get_logger


class MCPClient:
    """Client for interacting with MCP servers."""

    def __init__(self, server_config: MCPServerConfig) -> None:
        """Initialize MCP client.

        Args:
            server_config: MCP server configuration
        """
        self.config = server_config
        self.logger = get_logger(__name__)

        # Prepare headers for authentication and security
        headers = {"Content-Type": "application/json"}
        if server_config.auth_token:
            headers["Authorization"] = f"Bearer {server_config.auth_token}"

        # Validate URL for security
        if server_config.bind_localhost and not (
            server_config.url.startswith("http://127.0.0.1")
            or server_config.url.startswith("http://localhost")
            or server_config.url.startswith("https://127.0.0.1")
            or server_config.url.startswith("https://localhost")
        ):
            self.logger.warning(
                "mcp_security_warning",
                server=server_config.name,
                url=server_config.url,
                message="Non-localhost URL with bind_localhost=True",
            )

        self.client = httpx.AsyncClient(
            base_url=server_config.url,
            timeout=server_config.timeout,
            headers=headers,
        )
        self._capabilities: MCPCapabilities | None = None
        self._session_id: str | None = None

    async def initialize(self) -> None:
        """Initialize connection to MCP server."""
        try:
            # Send initialize request
            response = await self._send_request(
                method="initialize",
                params={
                    "protocolVersion": "2024-11-05",  # Updated to current MCP version
                    "clientInfo": {
                        "name": "llm-backend",
                        "version": "0.1.0",
                    },
                },
            )

            if response.result:
                # Get server capabilities
                caps_response = await self._send_request(method="tools/list")
                if caps_response.result:
                    tools = [
                        MCPTool(**tool)
                        for tool in caps_response.result.get("tools", [])
                    ]
                    self._capabilities = MCPCapabilities(
                        tools=tools,
                        version=response.result.get("protocolVersion", "1.0"),
                    )
                    self.logger.info(
                        "mcp_initialized",
                        server=self.config.name,
                        tools_count=len(tools),
                    )
        except Exception as e:
            self.logger.error(
                "mcp_init_failed",
                server=self.config.name,
                error=str(e),
                exc_info=True,
            )
            raise

    async def get_tools(self) -> list[MCPTool]:
        """Get available tools from the server.

        Returns:
            List of available tools
        """
        if not self._capabilities:
            await self.initialize()

        return self._capabilities.tools if self._capabilities else []

    async def call_tool(self, tool_call: MCPToolCall) -> MCPToolResult:
        """Execute a tool call.

        Args:
            tool_call: Tool call request

        Returns:
            Tool execution result
        """
        try:
            response = await self._send_request(
                method="tools/call",
                params={
                    "name": tool_call.name,
                    "arguments": tool_call.arguments,
                },
            )

            if response.error:
                return MCPToolResult(
                    tool_call_id=tool_call.id,
                    output=None,
                    error=response.error.get("message", "Unknown error"),
                )

            return MCPToolResult(
                tool_call_id=tool_call.id,
                output=response.result,
                error=None,
            )
        except Exception as e:
            self.logger.error(
                "mcp_tool_call_failed",
                tool=tool_call.name,
                error=str(e),
                exc_info=True,
            )
            return MCPToolResult(
                tool_call_id=tool_call.id,
                output=None,
                error=str(e),
            )

    async def _send_request(
        self,
        method: str,
        params: dict[str, Any] | None = None,
    ) -> MCPResponse:
        """Send JSON-RPC request to MCP server.

        Args:
            method: RPC method name
            params: Method parameters

        Returns:
            MCP response
        """
        request = MCPRequest(
            method=method,
            params=params,
            id=str(uuid.uuid4()),
        )

        # Prepare headers for session management
        headers = {"Content-Type": "application/json"}
        if self._session_id:
            headers["Mcp-Session-Id"] = self._session_id

        response = await self.client.post(
            "/",
            json=request.model_dump(exclude_none=True),
            headers=headers,
        )
        response.raise_for_status()

        # Check for session ID in response headers
        if "Mcp-Session-Id" in response.headers:
            self._session_id = response.headers["Mcp-Session-Id"]
            self.logger.info(
                "mcp_session_established",
                server=self.config.name,
                session_id=self._session_id,
            )

        return MCPResponse(**response.json())

    async def close(self) -> None:
        """Close the client connection."""
        await self.client.aclose()

    def to_openai_tools(self) -> list[dict[str, Any]]:
        """Convert MCP tools to OpenAI tool format.

        Returns:
            List of tools in OpenAI format
        """
        if not self._capabilities:
            return []

        openai_tools = []
        for tool in self._capabilities.tools:
            openai_tools.append(
                {
                    "type": "function",
                    "function": {
                        "name": f"{self.config.name}_{tool.name}",
                        "description": tool.description,
                        "parameters": tool.input_schema,
                    },
                }
            )

        return openai_tools
