"""Simple test client for the WebSocket server."""

import asyncio
import json
import uuid

import websockets


async def test_chat() -> None:
    """Test the chat functionality."""
    uri = "ws://localhost:8000/ws/chat"

    async with websockets.connect(uri) as websocket:
        # Send a chat message
        request_id = str(uuid.uuid4())
        message = {
            "action": "chat",
            "payload": {"text": "Hello! Can you tell me a joke?"},
            "request_id": request_id,
        }

        print(f"Sending: {json.dumps(message, indent=2)}")
        await websocket.send(json.dumps(message))

        # Receive responses
        while True:
            response = await websocket.recv()
            data = json.loads(response)
            print(f"Received: {json.dumps(data, indent=2)}")

            # Check if response is complete
            if data.get("status") == "complete":
                print("Chat completed!")
                break
            elif data.get("status") == "error":
                print(f"Error: {data.get('error')}")
                break


async def main() -> None:
    """Run the test client."""
    print("Testing WebSocket connection...")
    try:
        await test_chat()
    except Exception as e:
        print(f"Connection failed: {e}")
        print("Make sure the server is running with: uv run python -m src.main")


if __name__ == "__main__":
    asyncio.run(main())
