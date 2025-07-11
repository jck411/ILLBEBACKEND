# Web Search Tool Fix Documentation

## Problem Summary

The web search tool was not working because:

1. **Missing `use_mcp` parameter**: The WebSocket server was not passing the `use_mcp=True` flag to the OpenAI adapter when tools were available.
2. **Empty MCP clients list**: Since no MCP servers were configured in `config.yaml`, the MCP clients list was empty, preventing local tools from being registered.
3. **Tool execution flow issue**: The OpenAI adapter requires the `use_mcp=True` flag to properly handle tool calls in the two-phase MCP flow.

## Fixes Applied

### 1. WebSocket Server Fix (`src/server/websocket_server.py`)

Added the `use_mcp` parameter when calling `generate_response`:

```python
# Generate response from LLM
async for response in self.llm_adapter.generate_response(
    message=message.payload.text,
    request_id=message.request_id,
    tools=tools if tools else None,
    use_mcp=bool(tools),  # Enable MCP if we have tools
):
```

### 2. Main Application Fix (`src/main.py`)

Created a dummy MCP client when no servers are configured to ensure local tools are available:

```python
# Initialize MCP clients
if config.mcp.enabled:
    # Always create at least one MCP client for local tools
    if not config.mcp.servers:
        # Create a dummy MCP client for local tools only
        from src.models.config import MCPServerConfig

        dummy_config = MCPServerConfig(
            name="local",
            url="http://localhost:0",  # Dummy URL, won't be used
            transport="http",
            timeout=30,
            auth_token=None,
            bind_localhost=True,
        )
        client = MCPClient(dummy_config)
        # Don't initialize the dummy client (no remote server)
        mcp_clients.append(client)
```

## How the Search Tool Works

1. **Tool Registration**: The `WebSearchTool` class in `src/mcp/tools/web_search.py` is automatically registered when the module is imported.

2. **Tool Discovery**: When a chat message is received, the WebSocket server:
   - Gets tools from MCP clients (including local tools)
   - Passes them to the OpenAI adapter in the correct format

3. **Tool Execution**: When OpenAI decides to use the search tool:
   - The adapter executes the tool via the MCP client
   - The tool uses DuckDuckGo to perform the search
   - Results are returned to OpenAI for final response generation

## Testing the Fix

### 1. Start the Server

```bash
python -m src.main
```

### 2. Run the Test Script

In another terminal:

```bash
python test_search.py
```

Or use any WebSocket client to send:

```json
{
  "request_id": "unique-id",
  "action": "chat",
  "payload": {
    "text": "search online for the latest news about musk"
  }
}
```

### 3. Expected Behavior

The system should:
1. Recognize the search intent
2. Call the `web_search` tool
3. Return search results from DuckDuckGo
4. Generate a summary of the findings

## MCP Protocol Compliance

The implementation follows the Model Context Protocol (MCP) specification:

- **Tool Definition**: Tools are defined with proper input schemas
- **Tool Execution**: Tools are executed asynchronously with proper error handling
- **Result Format**: Tool results follow the MCP result format
- **Two-Phase Flow**: The OpenAI adapter implements the two-phase flow for tool execution

## Future Improvements

1. **Add more local tools**: Implement additional tools following the same pattern as `WebSearchTool`
2. **Configure remote MCP servers**: Add actual MCP server configurations to `config.yaml`
3. **Enhanced error handling**: Add more detailed error messages and recovery mechanisms
4. **Tool result caching**: Cache search results to avoid redundant API calls
