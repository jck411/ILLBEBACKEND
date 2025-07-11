"""MCP tools registry and base handler."""

from typing import ClassVar

from src.mcp.models import MCPTool, MCPToolCall, MCPToolResult
from src.utils.logging import get_logger

logger = get_logger(__name__)


class ToolRegistry:
    """Registry for MCP tools."""

    _tools: ClassVar[dict[str, type["MCPToolHandler"]]] = {}

    @classmethod
    def register(cls, tool_handler: type["MCPToolHandler"]) -> type["MCPToolHandler"]:
        """Register a tool handler.

        Args:
            tool_handler: The tool handler class to register

        Returns:
            The registered tool handler class (for decorator usage)
        """
        tool_def = tool_handler.get_definition()
        cls._tools[tool_def.name] = tool_handler
        logger.info("mcp_tool_registered", tool=tool_def.name)
        return tool_handler

    @classmethod
    def get_tool(cls, name: str) -> type["MCPToolHandler"] | None:
        """Get a tool handler by name.

        Args:
            name: The tool name

        Returns:
            The tool handler class if found, None otherwise
        """
        return cls._tools.get(name)

    @classmethod
    def get_tools(cls) -> list[MCPTool]:
        """Get all registered tool definitions.

        Returns:
            List of all registered tool definitions
        """
        return [handler.get_definition() for handler in cls._tools.values()]


class MCPToolHandler:
    """Base class for MCP tool handlers."""

    @classmethod
    def get_definition(cls) -> MCPTool:
        """Get the tool definition.

        Returns:
            The tool definition

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Tool handlers must implement get_definition")

    @classmethod
    async def execute(cls, tool_call: MCPToolCall) -> MCPToolResult:
        """Execute the tool.

        Args:
            tool_call: The tool call request

        Returns:
            The tool execution result

        Raises:
            NotImplementedError: If not implemented by subclass
        """
        raise NotImplementedError("Tool handlers must implement execute")
