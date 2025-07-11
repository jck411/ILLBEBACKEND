"""Main application entry point."""

import os
import sys
import uuid
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware

from src.adapters import OpenAIAdapter
from src.mcp import MCPClient
from src.models.config import Config, Settings
from src.server import WebSocketServer
from src.utils.logging import setup_logging

# Load environment variables early
load_dotenv()

# Global variables for lifecycle management
config: Config
ws_server: WebSocketServer
mcp_clients: list[MCPClient] = []


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None]:
    """Application lifespan manager."""
    global config, ws_server, mcp_clients

    # Load configuration
    config_path = os.getenv("CONFIG_PATH", "config.yaml")
    config = Config.from_yaml(config_path)

    # Load environment settings
    settings = Settings()

    # Apply environment overrides
    if settings.openai_api_key:
        config.openai.api_key = settings.openai_api_key
    if settings.server_host:
        config.server.host = settings.server_host
    if settings.server_port:
        config.server.port = settings.server_port
    if settings.log_level:
        config.logging.level = settings.log_level

    # Setup logging
    setup_logging(config.logging.level, config.logging.format)

    # Initialize OpenAI adapter
    openai_adapter = OpenAIAdapter(config.openai)

    # Validate adapter configuration
    if not await openai_adapter.validate_config():
        print("Failed to validate OpenAI configuration. Check your API key.")
        sys.exit(1)

    # Initialize MCP clients
    if config.mcp.enabled:
        for server_config in config.mcp.servers:
            try:
                client = MCPClient(server_config)
                await client.initialize()
                mcp_clients.append(client)
            except Exception as e:
                print(f"Failed to initialize MCP server {server_config.name}: {e}")

    # Initialize WebSocket server
    ws_server = WebSocketServer(config, openai_adapter, mcp_clients)

    yield

    # Cleanup
    for client in mcp_clients:
        await client.close()


# Create FastAPI app
app = FastAPI(
    title="Multi-Vendor LLM Backend",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Will be configured from config
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root() -> dict:
    """Root endpoint."""
    return {
        "name": "Multi-Vendor LLM Backend",
        "version": "0.1.0",
        "status": "running",
    }


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {
        "status": "healthy",
        "mcp_servers": len(mcp_clients),
        "adapter": "openai",
    }


@app.websocket("/ws/chat")
async def websocket_endpoint(websocket: WebSocket) -> None:
    """WebSocket endpoint for chat."""
    client_id = str(uuid.uuid4())
    await ws_server.connect(websocket, client_id)
    await ws_server.handle_message(websocket, client_id)


def main() -> None:
    """Run the application."""
    import uvicorn

    # Get configuration
    config_path = os.getenv("CONFIG_PATH", "config.yaml")
    config = Config.from_yaml(config_path)

    # Apply environment overrides
    settings = Settings()
    host = settings.server_host or config.server.host
    port = settings.server_port or config.server.port

    # Update CORS origins
    app.add_middleware(
        CORSMiddleware,
        allow_origins=config.server.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Run server
    uvicorn.run(
        "src.main:app",
        host=host,
        port=port,
        reload=True,
        log_level=config.logging.level.lower(),
    )


if __name__ == "__main__":
    main()
