# Multi-Vendor LLM Backend

A WebSocket-based backend that acts as an adapter between a frontend chat interface and multiple LLM providers. Currently supports OpenAI with MCP (Model Context Protocol) integration for local tools.

**Status: ✅ Core functionality complete and working** (as of 2025-07-10)

## Features

- ✅ WebSocket server for real-time chat
- ✅ Streaming responses from LLM providers
- ✅ OpenAI adapter with full configuration support
- ✅ MCP (Model Context Protocol) integration for local tools
- ✅ Structured JSON logging
- ✅ Configuration via YAML and environment variables
- ✅ Type-safe with Pydantic models
- ✅ Full test coverage for message models
- ✅ Pre-commit hooks and code quality tools
- 🚧 Multi-vendor support (coming soon)

## Prerequisites

- Python 3.13.0 (exact version required)
- uv package manager
- OpenAI API key

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd llm-backend
```

2. Install uv if you haven't already:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. Run the setup script (recommended):
```bash
chmod +x setup.sh
./setup.sh
```

Or manually set up the environment:

```bash
# Create and activate virtual environment
uv venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies
uv sync

# Set up pre-commit hooks
uv run pre-commit install

# Copy environment file
cp .env.example .env
# Edit .env and add your OpenAI API key
```

4. Configure VS Code (optional but recommended):
```bash
mkdir -p .vscode
cat > .vscode/settings.json << 'EOF'
{
    "python.defaultInterpreterPath": "${workspaceFolder}/.venv/bin/python",
    "python.analysis.extraPaths": [
        "${workspaceFolder}"
    ],
    "python.linting.enabled": true,
    "python.linting.mypyEnabled": true,
    "python.linting.mypyPath": "${workspaceFolder}/.venv/bin/mypy",
    "python.linting.ruffEnabled": true,
    "python.linting.ruffPath": "${workspaceFolder}/.venv/bin/ruff",
    "[python]": {
        "editor.formatOnSave": true,
        "editor.defaultFormatter": "charliermarsh.ruff"
    },
    "python.analysis.typeCheckingMode": "basic",
    "python.analysis.autoImportCompletions": true
}
EOF
```

## Troubleshooting

### Import Issues
If VS Code's Pylance shows "Import could not be resolved" errors:
- Ensure the virtual environment is activated
- Configure VS Code to use the correct Python interpreter (step 8 above)
- Try restarting VS Code

### Type Errors
If you encounter mypy errors related to missing type stubs:
```bash
# Install additional type stubs as needed
uv add --dev types-PyYAML
```

### Async Iterator Errors
If you see errors like `"Coroutine[Any, Any, AsyncIterator[ServerMessage]]" has no attribute "__aiter__"`:
- In `websocket_server.py`, ensure you're awaiting the async generator before iterating:
```python
# Incorrect:
async for response in self.llm_adapter.generate_response(...):
    # ...

# Correct:
response_generator = await self.llm_adapter.generate_response(...)
async for response in response_generator:
    # ...
```

### Missing Required Constructor Arguments
If you see errors about missing required arguments for `ServerMessage` or `ResponseChunk`:
- Ensure all required parameters are provided, including ones with default values:
```python
# Example with all required parameters:
server_message = ServerMessage(
    request_id="some-id",
    status=ResponseStatus.CHUNK,
    chunk=ResponseChunk(type="text", data="data", metadata={}),
    error=None,
)
```

### Indentation and Syntax Errors
If you see indentation errors in the code:
```bash
# Run ruff to auto-fix formatting issues
uv run ruff format src
```

### Build Errors
If you encounter build errors with hatchling:
- Ensure the `[tool.hatch.build.targets.wheel]` section is added to pyproject.toml (step 4)
- You may need to remove and recreate the virtual environment if persistent issues occur

## Configuration

Edit `config.yaml` to customize:
- Server settings (host, port, CORS)
- OpenAI parameters (model, temperature, system prompt)
- MCP server configurations
- Logging preferences

## Running the Server

```bash
# Using uv (recommended)
uv run python -m src.main

# Or activate the environment first
source .venv/bin/activate
python -m src.main
```

For testing purposes without a real OpenAI API key, you can use a placeholder in your .env file:
```
OPENAI_API_KEY=sk-placeholder-key
```
Note: With a placeholder key, the server will start but actual API requests to OpenAI will fail.

The WebSocket server will start at `ws://localhost:8000/ws/chat`

## WebSocket Message Format

### Client → Server
```json
{
  "action": "chat",
  "payload": {"text": "user message"},
  "request_id": "unique-uuid-v4"
}
```

### Server → Client

**Processing Started:**
```json
{
  "request_id": "uuid",
  "status": "processing",
  "chunk": {"metadata": {"user_message": "..."}}
}
```

**Text Chunk (Streaming):**
```json
{
  "request_id": "uuid",
  "status": "chunk",
  "chunk": {"type": "text", "data": "content"}
}
```

**Response Completed:**
```json
{
  "request_id": "uuid",
  "status": "complete"
}
```

**Error:**
```json
{
  "request_id": "uuid",
  "status": "error",
  "error": "error message"
}
```

## Development

### Development Dependencies
If not using the setup script, you can install development dependencies manually:
```bash
uv add --dev mypy pre-commit types-PyYAML pytest pytest-asyncio pytest-cov ruff
uv run pre-commit install
```

### Run tests:
```bash
uv run pytest
```

### Type checking:
```bash
uv run mypy src
```

If you encounter typing issues with specific imports, create or update the mypy.ini file:
```ini
[mypy]
python_version = 3.13
warn_return_any = true
warn_unused_configs = true
disallow_untyped_defs = true
disallow_incomplete_defs = true
check_untyped_defs = true
disallow_untyped_decorators = true
no_implicit_optional = true
warn_redundant_casts = true
warn_unused_ignores = true
warn_no_return = true
warn_unreachable = true
strict_equality = true

# Ignore missing imports for modules without type stubs
[mypy.structlog]
ignore_missing_imports = True

[mypy.openai]
ignore_missing_imports = True

[mypy.websockets]
ignore_missing_imports = True

[mypy.pydantic_settings]
ignore_missing_imports = True

[mypy.uvicorn]
ignore_missing_imports = True
```

### Linting and Formatting:
```bash
# Check for linting issues
uv run ruff check src

# Auto-fix formatting issues
uv run ruff format src
```

### Resolving Common Type Errors:
- Use modern type annotations: `list[str]` instead of `List[str]`
- Use union syntax: `str | None` instead of `Optional[str]`
- Properly handle `None` values: `if value is not None: ...`
- Set proper defaults: `error: str | None = None`

## Project Structure

```
.
├── config.yaml          # Main configuration file
├── src/
│   ├── main.py         # Application entry point
│   ├── server/         # WebSocket server implementation
│   ├── adapters/       # LLM provider adapters
│   ├── mcp/           # MCP client and integration
│   ├── models/        # Pydantic models
│   └── utils/         # Utility functions
├── tests/             # Test suite
├── pyproject.toml     # Project dependencies and tools
└── plan.md           # Development plan and architecture
```

## MCP Integration

To add an MCP server, update the `mcp.servers` section in `config.yaml`:

```yaml
mcp:
  servers:
    - name: "my-tool-server"
      url: "http://localhost:3000"
      transport: "http"
      timeout: 30
```

## License

[Your License Here]
