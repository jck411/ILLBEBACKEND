"""MCP data models."""

from typing import Any

from pydantic import BaseModel, Field


class MCPTool(BaseModel):
    """MCP tool definition."""

    name: str = Field(..., description="Tool name")
    description: str = Field(..., description="Tool description")
    input_schema: dict[str, Any] = Field(..., description="JSON schema for tool input")


class MCPToolCall(BaseModel):
    """MCP tool call request."""

    id: str = Field(..., description="Tool call ID")
    name: str = Field(..., description="Tool name")
    arguments: dict[str, Any] = Field(..., description="Tool arguments")


class MCPToolResult(BaseModel):
    """MCP tool execution result."""

    tool_call_id: str = Field(..., description="Tool call ID")
    output: Any = Field(..., description="Tool output")
    error: str | None = Field(None, description="Error message if failed")


class MCPRequest(BaseModel):
    """MCP request format."""

    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    method: str = Field(..., description="Method name")
    params: dict[str, Any] | None = Field(None, description="Method parameters")
    id: str | None = Field(None, description="Request ID")


class MCPResponse(BaseModel):
    """MCP response format."""

    jsonrpc: str = Field(default="2.0", description="JSON-RPC version")
    result: Any | None = Field(None, description="Method result")
    error: dict[str, Any] | None = Field(None, description="Error details")
    id: str | None = Field(None, description="Request ID")


class MCPCapabilities(BaseModel):
    """MCP server capabilities."""

    tools: list[MCPTool] = Field(default_factory=list, description="Available tools")
    version: str = Field(..., description="MCP version")
