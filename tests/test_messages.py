"""Tests for message models."""

import pytest
from pydantic import ValidationError

from src.models.messages import (
    ChatPayload,
    ClientMessage,
    ResponseChunk,
    ResponseStatus,
    ServerMessage,
)


def test_chat_payload_valid() -> None:
    """Test valid ChatPayload creation."""
    payload = ChatPayload(text="Hello, world!")
    assert payload.text == "Hello, world!"


def test_chat_payload_invalid() -> None:
    """Test invalid ChatPayload creation."""
    with pytest.raises(ValidationError):
        ChatPayload(text="")  # Empty field should fail validation


def test_client_message_valid() -> None:
    """Test valid ClientMessage creation."""
    message = ClientMessage(
        action="chat",
        payload=ChatPayload(text="Test message"),
        request_id="test-123",
    )
    assert message.action == "chat"
    assert message.payload.text == "Test message"
    assert message.request_id == "test-123"


def test_server_message_processing() -> None:
    """Test ServerMessage with processing status."""
    message = ServerMessage(
        request_id="test-123",
        status=ResponseStatus.PROCESSING,
        chunk=ResponseChunk(type=None, data=None, metadata={"user_message": "Hello"}),
        error=None,
    )
    assert message.status == ResponseStatus.PROCESSING
    assert message.chunk is not None  # Verify chunk exists before accessing properties
    if message.chunk:  # Type narrowing for static analysis
        assert message.chunk.metadata is not None
        assert message.chunk.metadata.get("user_message") == "Hello"


def test_server_message_chunk() -> None:
    """Test ServerMessage with text chunk."""
    message = ServerMessage(
        request_id="test-123",
        status=ResponseStatus.CHUNK,
        chunk=ResponseChunk(type="text", data="Response text", metadata={}),
        error=None,
    )
    assert message.status == ResponseStatus.CHUNK
    assert message.chunk is not None  # Verify chunk exists before accessing properties
    if message.chunk:  # Type narrowing for static analysis
        assert message.chunk.type == "text"
        assert message.chunk.data == "Response text"


def test_server_message_error() -> None:
    """Test ServerMessage with error."""
    message = ServerMessage(
        request_id="test-123",
        status=ResponseStatus.ERROR,
        error="Something went wrong",
        chunk=None,
    )
    assert message.status == ResponseStatus.ERROR
    assert message.error == "Something went wrong"
    assert message.chunk is None
