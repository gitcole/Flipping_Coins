"""
Mock implementation for WebSocket client.
"""
import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Callable, AsyncGenerator
from unittest.mock import Mock, AsyncMock
from dataclasses import dataclass
from enum import Enum


class WebSocketState(Enum):
    """WebSocket connection states."""
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"
    ERROR = "error"


@dataclass
class MockWebSocketMessage:
    """Represents a WebSocket message."""
    data: Any
    message_type: str = "message"
    timestamp: Optional[float] = None

    def __post_init__(self):
        if self.timestamp is None:
            self.timestamp = time.time()

    def to_dict(self) -> Dict[str, Any]:
        """Convert message to dictionary."""
        return {
            "data": self.data,
            "type": self.message_type,
            "timestamp": self.timestamp
        }

    def to_json(self) -> str:
        """Convert message to JSON string."""
        return json.dumps(self.to_dict())


class WebSocketMock:
    """Comprehensive mock for WebSocket client."""

    def __init__(self):
        self.state = WebSocketState.DISCONNECTED
        self.connected = False
        self.url = None

        # Message handling
        self.sent_messages = []
        self.received_messages = []
        self.message_handlers = {}

        # Connection control
        self.auto_connect = True
        self.connection_delay = 0.1
        self.disconnect_delay = 0.05
        self.error_on_connect = False

        # Message queue for simulating incoming messages
        self.message_queue = asyncio.Queue()
        self.message_processor_task = None

        # Statistics
        self.connection_attempts = 0
        self.messages_sent = 0
        self.messages_received = 0

    async def connect(self, url: str, **kwargs) -> bool:
        """Mock WebSocket connection."""
        self.url = url
        self.state = WebSocketState.CONNECTING
        self.connection_attempts += 1

        await self._simulate_delay(self.connection_delay)

        if self.error_on_connect:
            self.state = WebSocketState.ERROR
            raise Exception(f"Failed to connect to {url}")

        self.state = WebSocketState.CONNECTED
        self.connected = True

        # Start message processor if not running
        if self.message_processor_task is None:
            self.message_processor_task = asyncio.create_task(self._process_messages())

        return True

    async def disconnect(self, code: int = 1000, reason: str = "Normal closure"):
        """Mock WebSocket disconnection."""
        if not self.connected:
            return

        self.state = WebSocketState.DISCONNECTING
        await self._simulate_delay(self.disconnect_delay)

        self.state = WebSocketState.DISCONNECTED
        self.connected = False

        # Stop message processor
        if self.message_processor_task:
            self.message_processor_task.cancel()
            self.message_processor_task = None

    async def send(self, message: Any) -> bool:
        """Mock send message."""
        if not self.connected:
            raise Exception("WebSocket not connected")

        await self._simulate_delay(0.01)

        # Convert message to MockWebSocketMessage
        if not isinstance(message, MockWebSocketMessage):
            ws_message = MockWebSocketMessage(data=message)
        else:
            ws_message = message

        self.sent_messages.append(ws_message)
        self.messages_sent += 1

        return True

    async def send_json(self, data: Dict[str, Any]) -> bool:
        """Mock send JSON message."""
        json_message = MockWebSocketMessage(
            data=data,
            message_type="json"
        )
        return await self.send(json_message)

    async def recv(self) -> MockWebSocketMessage:
        """Mock receive message."""
        if not self.connected:
            raise Exception("WebSocket not connected")

        try:
            # Wait for message from queue with timeout
            message = await asyncio.wait_for(
                self.message_queue.get(),
                timeout=1.0
            )
            self.received_messages.append(message)
            self.messages_received += 1

            return message

        except asyncio.TimeoutError:
            # Return a heartbeat message if no messages
            heartbeat = MockWebSocketMessage(
                data={"type": "heartbeat"},
                message_type="heartbeat"
            )
            return heartbeat

    async def ping(self) -> bool:
        """Mock ping."""
        if not self.connected:
            return False

        await self._simulate_delay(0.01)
        return True

    async def pong(self) -> bool:
        """Mock pong."""
        if not self.connected:
            return False

        await self._simulate_delay(0.01)
        return True

    # Message queue management
    def queue_message(self, data: Any, message_type: str = "message"):
        """Add message to the incoming message queue."""
        message = MockWebSocketMessage(data=data, message_type=message_type)
        self.message_queue.put_nowait(message)

    def queue_json_message(self, data: Dict[str, Any]):
        """Add JSON message to the incoming message queue."""
        self.queue_message(data, "json")

    def queue_messages(self, messages: List[Dict[str, Any]]):
        """Add multiple messages to the incoming message queue."""
        for message_data in messages:
            self.queue_json_message(message_data)

    async def clear_message_queue(self):
        """Clear all queued messages."""
        while not self.message_queue.empty():
            try:
                self.message_queue.get_nowait()
            except asyncio.QueueEmpty:
                break

    # Event handling
    def add_message_handler(self, message_type: str, handler: Callable):
        """Add handler for specific message types."""
        if message_type not in self.message_handlers:
            self.message_handlers[message_type] = []

        self.message_handlers[message_type].append(handler)

    def remove_message_handler(self, message_type: str, handler: Callable):
        """Remove handler for specific message types."""
        if message_type in self.message_handlers:
            try:
                self.message_handlers[message_type].remove(handler)
            except ValueError:
                pass

    # Message processing
    async def _process_messages(self):
        """Process incoming messages and trigger handlers."""
        while self.connected:
            try:
                # Wait for message
                message = await self.recv()

                # Trigger handlers
                message_type = message.message_type
                if message_type in self.message_handlers:
                    for handler in self.message_handlers[message_type]:
                        try:
                            if asyncio.iscoroutinefunction(handler):
                                await handler(message)
                            else:
                                handler(message)
                        except Exception as e:
                            print(f"Error in message handler: {e}")

                await asyncio.sleep(0.01)  # Small delay between processing

            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error processing messages: {e}")
                await asyncio.sleep(0.1)

    # Simulation methods
    def simulate_disconnect(self):
        """Simulate unexpected disconnect."""
        if self.connected:
            asyncio.create_task(self.disconnect(1006, "Unexpected disconnect"))

    def simulate_error(self, error_message: str = "WebSocket error"):
        """Simulate WebSocket error."""
        self.state = WebSocketState.ERROR
        self.connected = False

        if self.message_processor_task:
            self.message_processor_task.cancel()
            self.message_processor_task = None

        raise Exception(error_message)

    def simulate_network_delay(self, delay: float):
        """Simulate network delay for next operation."""
        # This would be implemented to affect the next operation
        pass

    # Configuration methods
    def set_connection_delay(self, delay: float):
        """Set connection delay."""
        self.connection_delay = delay

    def set_disconnect_delay(self, delay: float):
        """Set disconnect delay."""
        self.disconnect_delay = delay

    def set_auto_connect(self, enabled: bool):
        """Enable/disable auto connect."""
        self.auto_connect = enabled

    def enable_connection_errors(self, enabled: bool = True):
        """Enable/disable connection errors."""
        self.error_on_connect = enabled

    # Statistics and monitoring
    def get_stats(self) -> Dict[str, Any]:
        """Get WebSocket statistics."""
        return {
            "state": self.state.value,
            "connected": self.connected,
            "url": self.url,
            "connection_attempts": self.connection_attempts,
            "messages_sent": self.messages_sent,
            "messages_received": self.messages_received,
            "queued_messages": self.message_queue.qsize(),
            "active_handlers": sum(len(handlers) for handlers in self.message_handlers.values())
        }

    def get_sent_messages(self) -> List[MockWebSocketMessage]:
        """Get all sent messages."""
        return self.sent_messages.copy()

    def get_received_messages(self) -> List[MockWebSocketMessage]:
        """Get all received messages."""
        return self.received_messages.copy()

    def reset_stats(self):
        """Reset statistics."""
        self.sent_messages.clear()
        self.received_messages.clear()
        self.connection_attempts = 0
        self.messages_sent = 0
        self.messages_received = 0

    async def _simulate_delay(self, seconds: float):
        """Simulate delay."""
        if seconds > 0:
            await asyncio.sleep(seconds)


class WebSocketMockBuilder:
    """Builder for creating customized WebSocket mocks."""

    def __init__(self):
        self.config = {
            "connection_delay": 0.1,
            "disconnect_delay": 0.05,
            "auto_connect": True,
            "error_on_connect": False,
            "initial_messages": [],
            "message_handlers": {}
        }

    def with_connection_delay(self, delay: float) -> 'WebSocketMockBuilder':
        """Configure connection delay."""
        self.config["connection_delay"] = delay
        return self

    def with_disconnect_delay(self, delay: float) -> 'WebSocketMockBuilder':
        """Configure disconnect delay."""
        self.config["disconnect_delay"] = delay
        return self

    def with_auto_connect(self, enabled: bool) -> 'WebSocketMockBuilder':
        """Configure auto connect."""
        self.config["auto_connect"] = enabled
        return self

    def with_connection_errors(self, enabled: bool = True) -> 'WebSocketMockBuilder':
        """Configure connection errors."""
        self.config["error_on_connect"] = enabled
        return self

    def with_initial_messages(self, messages: List[Dict[str, Any]]) -> 'WebSocketMockBuilder':
        """Configure initial messages to be queued."""
        self.config["initial_messages"] = messages
        return self

    def with_message_handler(self, message_type: str, handler: Callable) -> 'WebSocketMockBuilder':
        """Add message handler."""
        if message_type not in self.config["message_handlers"]:
            self.config["message_handlers"][message_type] = []

        self.config["message_handlers"][message_type].append(handler)
        return self

    def build(self) -> WebSocketMock:
        """Build the configured WebSocket mock."""
        mock = WebSocketMock()

        # Apply configuration
        mock.set_connection_delay(self.config["connection_delay"])
        mock.set_disconnect_delay(self.config["disconnect_delay"])
        mock.set_auto_connect(self.config["auto_connect"])
        mock.enable_connection_errors(self.config["error_on_connect"])

        # Add initial messages
        for message_data in self.config["initial_messages"]:
            mock.queue_json_message(message_data)

        # Add message handlers
        for message_type, handlers in self.config["message_handlers"].items():
            for handler in handlers:
                mock.add_message_handler(message_type, handler)

        return mock


# Convenience functions for common WebSocket scenarios
def create_trading_websocket_mock() -> WebSocketMock:
    """Create a WebSocket mock configured for trading scenarios."""
    return (WebSocketMockBuilder()
            .with_initial_messages([
                {"type": "subscription_success", "channel": "quotes"},
                {"type": "heartbeat"}
            ])
            .build())


def create_market_data_websocket_mock() -> WebSocketMock:
    """Create a WebSocket mock configured for market data."""
    return (WebSocketMockBuilder()
            .with_initial_messages([
                {"type": "market_data", "symbol": "BTC", "price": "50000.00"},
                {"type": "market_data", "symbol": "ETH", "price": "3000.00"}
            ])
            .build())


def create_error_prone_websocket_mock() -> WebSocketMock:
    """Create a WebSocket mock that simulates connection issues."""
    return (WebSocketMockBuilder()
            .with_connection_errors(True)
            .with_connection_delay(0.5)
            .build())