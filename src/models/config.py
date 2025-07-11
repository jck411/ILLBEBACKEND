"""Configuration models and settings management."""

import os

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load environment variables early
load_dotenv()


class ServerConfig(BaseModel):
    """Server configuration."""

    host: str = Field(default="0.0.0.0", description="Server host")
    port: int = Field(default=8000, description="Server port")
    cors_origins: list[str] = Field(
        default_factory=lambda: ["http://localhost:3000"],
        description="Allowed CORS origins",
    )


class OpenAIConfig(BaseModel):
    """OpenAI configuration."""

    api_key: str = Field(..., description="OpenAI API key")
    model: str = Field(default="gpt-4o-mini", description="Model to use")
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    max_tokens: int = Field(default=4096, gt=0)
    stream: bool = Field(default=True, description="Enable streaming")
    system_prompt: str = Field(
        default="You are a helpful AI assistant.",
        description="System prompt",
    )

    @field_validator("api_key")
    @classmethod
    def expand_env_vars(cls, v: str) -> str:
        """Expand environment variables in API key."""
        if v.startswith("${") and v.endswith("}"):
            env_var = v[2:-1]
            value = os.getenv(env_var)
            if not value:
                raise ValueError(f"Environment variable {env_var} not set")
            return value
        return v


class MCPServerConfig(BaseModel):
    """MCP server configuration."""

    name: str = Field(..., description="Server name")
    url: str = Field(..., description="Server URL")
    transport: str = Field(
        default="streamable-http",
        description="Transport protocol (streamable-http, stdio)",
    )
    timeout: int = Field(default=30, gt=0, description="Request timeout in seconds")
    auth_token: str | None = Field(None, description="Optional authentication token")
    bind_localhost: bool = Field(
        default=True, description="Bind to localhost only for security"
    )


class MCPConfig(BaseModel):
    """MCP configuration."""

    enabled: bool = Field(default=True, description="Enable MCP integration")
    servers: list[MCPServerConfig] = Field(
        default_factory=list, description="MCP servers"
    )


class LoggingConfig(BaseModel):
    """Logging configuration."""

    level: str = Field(default="INFO", description="Log level")
    format: str = Field(default="json", description="Log format")


class RequestConfig(BaseModel):
    """Request configuration."""

    timeout: int = Field(default=60, gt=0, description="Request timeout in seconds")
    max_retries: int = Field(default=3, ge=0, description="Maximum retries")
    retry_delay: float = Field(default=1.0, gt=0, description="Retry delay in seconds")


class Config(BaseModel):
    """Application configuration."""

    server: ServerConfig = Field(default_factory=ServerConfig)
    openai: OpenAIConfig
    mcp: MCPConfig = Field(default_factory=MCPConfig)
    logging: LoggingConfig = Field(default_factory=LoggingConfig)
    request: RequestConfig = Field(default_factory=RequestConfig)

    @classmethod
    def from_yaml(cls, path: str) -> "Config":
        """Load configuration from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)
        return cls(**data)


class Settings(BaseSettings):
    """Environment settings."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # Ignore extra fields in .env
        env_ignore_empty=True,  # Ignore empty environment variables
    )

    # Environment variables that can override config
    openai_api_key: str | None = None
    server_host: str | None = None
    server_port: int | None = None
    log_level: str | None = None
