"""MCP tools registry and handlers."""

from .registry import MCPToolHandler, ToolRegistry

# Import tool implementations to trigger registration
from .web_search import WebSearchTool  # noqa: F401

__all__ = ["MCPToolHandler", "ToolRegistry"]
