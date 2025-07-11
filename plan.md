# Multi-Vendor LLM Backend Plan

## Current Status (2025-07-10)

✅ **COMPLETED - Core System Functional**
- WebSocket server fully implemented and tested
- OpenAI adapter with streaming support
- MCP integration for local tool servers
- Configuration management (YAML + environment variables)
- Type-safe Pydantic models for all messages
- Structured JSON logging with structlog
- Complete error handling and validation
- Pre-commit hooks and code quality tools (mypy, ruff)
- Unit tests for core message models

🚧 **IN PROGRESS**
- Integration tests for full WebSocket flow
- Performance optimization and profiling

📋 **TODO - Future Enhancements**
- Additional LLM vendor adapters (Anthropic, Google Gemini)
- More comprehensive test coverage
- Production deployment configuration

---

## Project Overview
A WebSocket-based backend that acts as an adapter between a frontend chat interface and multiple LLM providers, starting with OpenAI. The system will support MCP (Model Context Protocol) servers for local tool integration.

## Architecture

### Core Components

1. **WebSocket Server** (`src/server/websocket_server.py`)
   - Handles incoming WebSocket connections at ws://localhost:8000/ws/chat
   - Manages request/response lifecycle with unique request IDs
   - Streams responses back to the client

2. **Adapter Pattern** (`src/adapters/`)
   - Base adapter interface defining common methods
   - OpenAI adapter implementation (first vendor)
   - Future: Anthropic, Google Gemini adapters

3. **MCP Integration** (`src/mcp/`)
   - MCP client for connecting to local tool servers
   - HTTP transport implementation
   - Tool execution and response handling

4. **Configuration** (`config.yaml`)
   - OpenAI parameters (API key, model, temperature, top_p, system prompt)
   - MCP server configurations
   - WebSocket server settings

5. **Message Models** (`src/models/`)
   - Pydantic models for WebSocket messages
   - Request/response validation

## Implementation Phases

### Phase 1: Foundation (Current)
- [x] Project structure setup
- [x] WebSocket server implementation
- [x] Message models and validation
- [x] Configuration management
- [x] OpenAI adapter implementation
- [x] Basic error handling and logging
- [x] Type checking with mypy
- [x] Code formatting with ruff
- [x] Pre-commit hooks setup

### Phase 2: MCP Integration
- [x] MCP client implementation
- [x] HTTP transport for MCP
- [x] Tool discovery and execution
- [x] Tool response integration with LLM

### Phase 3: Testing & Refinement
- [x] Unit tests for core components (message models)
- [ ] Integration tests for WebSocket flow
- [x] Error handling improvements
- [ ] Performance optimization
- [x] Type safety with mypy
- [x] Code quality with ruff and pre-commit

### Phase 4: Multi-Vendor Support (Future)
- [ ] Anthropic adapter
- [ ] Google Gemini adapter
- [ ] Vendor selection logic
- [ ] Unified configuration format

## Technical Decisions

1. **Python 3.13.0** - Latest stable Python version
2. **FastAPI + WebSockets** - Modern async framework with WebSocket support
3. **Pydantic** - Data validation and settings management
4. **httpx** - Async HTTP client for OpenAI and MCP,
     __hybrid approach__:
      1. __Use httpx as the default__ for vendors without good async SDK support
      2. __Use official SDKs when they provide good async/streaming support__ (like OpenAI)
      3. __Wrap everything in a consistent adapter interface__ (which you already have!)

5. **uv** - Fast Python package manager
6. **structlog** - Structured JSON logging

## Message Flow

1. Client sends WebSocket message with action, payload, and request_id
2. Server validates message and extracts user text
3. Server sends "processing" status with metadata
4. Server queries MCP servers for available tools (if configured)
5. Server sends request to OpenAI with tools and user message
6. Server streams OpenAI response chunks back to client
7. Server sends "complete" status when finished
8. Error handling at each step with appropriate error messages

## Configuration Structure

```yaml
server:
  host: "0.0.0.0"
  port: 8000

openai:
  api_key: "${OPENAI_API_KEY}"  # From environment
  model: "gpt-4o-mini"
  temperature: 0.7
  top_p: 1.0
  max_tokens: 4096
  system_prompt: "You are a helpful assistant."

mcp:
  servers:
    - name: "example-server"
      url: "http://localhost:3000"
      transport: "http"

logging:
  level: "INFO"
  format: "json"
```

## Error Handling Strategy

1. **Connection Errors** - Graceful WebSocket disconnection handling
2. **Validation Errors** - Clear error messages for invalid requests
3. **API Errors** - Proper error propagation from OpenAI/MCP
4. **Timeout Errors** - Configurable timeouts with appropriate messages
5. **Rate Limiting** - Handle OpenAI rate limits with retries

## Security Considerations

1. API keys stored in environment variables
2. Input validation on all user messages
3. No logging of sensitive data
4. Secure WebSocket connections (WSS in production)

## Development Workflow

1. Use `uv` for dependency management
2. Pre-commit hooks for linting and formatting
3. Type checking with mypy
4. Testing with pytest
5. Structured JSON logging for debugging
