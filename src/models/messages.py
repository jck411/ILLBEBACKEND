"""WebSocket message models for client-server communication."""

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class ResponseStatus(str, Enum):
    """Status of server response."""

    PROCESSING = "processing"
    CHUNK = "chunk"
    COMPLETE = "complete"
    ERROR = "error"


class ChatPayload(BaseModel):
    """Payload for chat action."""

    text: str = Field(..., description="User message text")


class ClientMessage(BaseModel):
    """Message sent from client to server."""

    action: Literal["chat"] = Field(..., description="Action to perform")
    payload: ChatPayload = Field(..., description="Action payload")
    request_id: str = Field(..., description="Unique request identifier")


class ResponseChunk(BaseModel):
    """Chunk of response data."""

    type: Literal["text", "tool_call", "tool_result"] | None = Field(
        None, description="Type of chunk"
    )
    data: str | None = Field(None, description="Chunk data")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class ServerMessage(BaseModel):
    """Message sent from server to client."""

    request_id: str = Field(..., description="Request identifier")
    status: ResponseStatus = Field(..., description="Response status")
    chunk: ResponseChunk | None = Field(None, description="Response chunk")
    error: str | None = Field(None, description="Error message if status is error")

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "request_id": "123e4567-e89b-12d3-a456-426614174000",
                    "status": "processing",
                    "chunk": {"metadata": {"user_message": "Hello"}},
                },
                {
                    "request_id": "123e4567-e89b-12d3-a456-426614174000",
                    "status": "chunk",
                    "chunk": {"type": "text", "data": "Hello! How can I help you?"},
                },
                {
                    "request_id": "123e4567-e89b-12d3-a456-426614174000",
                    "status": "complete",
                },
                {
                    "request_id": "123e4567-e89b-12d3-a456-426614174000",
                    "status": "error",
                    "error": "Invalid request",
                },
            ]
        }
    }
