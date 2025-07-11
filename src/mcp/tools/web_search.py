"""Web search tool for MCP using DuckDuckGo."""

import asyncio
import time
from concurrent.futures import ThreadPoolExecutor

from ddgs import DDGS

from src.mcp.models import MCPTool, MCPToolCall, MCPToolResult
from src.mcp.tools.registry import MCPToolHandler, ToolRegistry
from src.utils.logging import get_logger

logger = get_logger(__name__)


@ToolRegistry.register
class WebSearchTool(MCPToolHandler):
    """Web search tool using DuckDuckGo."""

    @classmethod
    def get_definition(cls) -> MCPTool:
        """Get the tool definition.

        Returns:
            The web search tool definition
        """
        return MCPTool(
            name="web_search",
            description="Search the web for current information using DuckDuckGo",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search query",
                    },
                    "num_results": {
                        "type": "integer",
                        "description": "Number of results to return (1-10)",
                        "minimum": 1,
                        "maximum": 10,
                        "default": 5,
                    },
                },
                "required": ["query"],
            },
        )

    @classmethod
    async def execute(cls, tool_call: MCPToolCall) -> MCPToolResult:
        """Execute the web search.

        Args:
            tool_call: The tool call request

        Returns:
            The search results
        """
        start_time = time.time()
        query = tool_call.arguments.get("query", "")
        num_results = int(tool_call.arguments.get("num_results", 5))

        # Validate inputs
        if not query or not isinstance(query, str):
            return MCPToolResult(
                tool_call_id=tool_call.id,
                output=None,
                error="Query is required and must be a non-empty string",
            )

        # Clamp num_results to valid range
        num_results = max(1, min(10, num_results))

        try:
            logger.info(
                "web_search_started",
                query=query,
                num_results=num_results,
                tool_call_id=tool_call.id,
            )

            # Perform the search in a thread executor since DDGS.text is blocking
            def _search() -> list[dict[str, str]]:
                ddgs = DDGS()
                results = list(ddgs.text(query, max_results=num_results))
                logger.info("raw_search_results", count=len(results), query=query)
                return results

            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as executor:
                raw_results = await loop.run_in_executor(executor, _search)

            # Format results
            formatted_results = []
            for result in raw_results:
                formatted_results.append(
                    {
                        "title": result.get("title", ""),
                        "snippet": result.get("body", ""),
                        "url": result.get("href", ""),
                    }
                )

            elapsed_ms = (time.time() - start_time) * 1000
            logger.info(
                "web_search_completed",
                query=query,
                num_results=len(formatted_results),
                elapsed_ms=elapsed_ms,
                tool_call_id=tool_call.id,
            )

            return MCPToolResult(
                tool_call_id=tool_call.id,
                output={
                    "results": formatted_results,
                    "query": query,
                    "result_count": len(formatted_results),
                    "search_engine": "DuckDuckGo",
                },
                error=None,
            )

        except TimeoutError:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(
                "web_search_timeout",
                query=query,
                elapsed_ms=elapsed_ms,
                tool_call_id=tool_call.id,
            )
            return MCPToolResult(
                tool_call_id=tool_call.id,
                output=None,
                error="Web search timed out",
            )

        except Exception as e:
            elapsed_ms = (time.time() - start_time) * 1000
            logger.error(
                "web_search_failed",
                query=query,
                error=str(e),
                elapsed_ms=elapsed_ms,
                tool_call_id=tool_call.id,
                exc_info=True,
            )
            return MCPToolResult(
                tool_call_id=tool_call.id,
                output=None,
                error=f"Web search failed: {str(e)}",
            )
