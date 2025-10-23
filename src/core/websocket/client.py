"""WebSocket client for real-time market data streaming."""

from __future__ import annotations

import asyncio
import json
from typing import Any, Callable, Dict, List, Optional, Set

import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from src.utils.logging import get_logger
from src.core.config import get_settings


class WebSocketClientError(Exception):
    """Base exception for WebSocket client errors."""
    pass


class WebSocketConnectionError(WebSocketClientError):
    """Raised when WebSocket connection fails."""
    pass


class WebSocketClient:
    """WebSocket client for real-time market data streaming."""

    def __init__(
        self,
        uri: Optional[str] = None,
        subscriptions: Optional[List[str]] = None,
        ping_interval: int = 20,
        timeout: int = 10,
        max_reconnects: int = 5,
    ):
        """Initialize WebSocket client.

        Args:
            uri: WebSocket server URI
            subscriptions: List of subscription channels/topics
            ping_interval: Ping interval in seconds
            timeout: Connection timeout in seconds
            max_reconnects: Maximum reconnection attempts
        """
        self.settings = get_settings()
        self.logger = get_logger("websocket.client")

        self.uri = uri or self.settings.websocket.uri
        self.subscriptions = subscriptions or []
        self.ping_interval = ping_interval
        self.timeout = timeout
        self.max_reconnects = max_reconnects

        # Connection state
        self.websocket: Optional[websockets.WebSocketServerProtocol] = None
        self.is_connected = False
        self.is_running = False
        self._shutdown_event = asyncio.Event()

        # Message handlers
        self.message_handlers: Dict[str, List[Callable]] = {}
        self.error_handlers: List[Callable[[Exception], None]] = []

        # Subscription management
        self.subscribed_channels: Set[str] = set()

        # Connection statistics
        self.stats = {
            'messages_received': 0,
            'messages_sent': 0,
            'reconnections': 0,
            'errors': 0,
            'start_time': None,
        }

    async def connect(self) -> None:
        """Connect to WebSocket server."""
        if self.is_connected:
            self.logger.warning("WebSocket client is already connected")
            return

        # Skip connection if no URI is provided (WebSocket disabled)
        if not self.uri or self.uri.strip() == "":
            self.logger.info("WebSocket URI not configured - skipping WebSocket connection")
            return

        retry_count = 0
        while retry_count <= self.max_reconnects:
            try:
                self.logger.info(f"Connecting to WebSocket server: {self.uri}")

                # Connect with timeout using asyncio.wait_for
                self.websocket = await asyncio.wait_for(
                    websockets.connect(
                        self.uri,
                        ping_interval=self.ping_interval,
                    ),
                    timeout=self.timeout,
                )

                self.is_connected = True
                self.stats['start_time'] = asyncio.get_event_loop().time()

                self.logger.info("WebSocket connection established")

                # Subscribe to channels
                await self._subscribe_to_channels()

                return

            except Exception as e:
                retry_count += 1
                self.stats['errors'] += 1
                self.is_connected = False

                if retry_count <= self.max_reconnects:
                    self.logger.warning(f"Connection attempt {retry_count} failed: {str(e)}")
                    await asyncio.sleep(2 ** retry_count)  # Exponential backoff
                else:
                    self.logger.error(f"Failed to connect after {self.max_reconnects} attempts")
                    raise WebSocketConnectionError(f"Failed to connect: {str(e)}")

    async def disconnect(self) -> None:
        """Disconnect from WebSocket server."""
        if not self.is_connected:
            return

        self.logger.info("Disconnecting from WebSocket server...")

        self.is_connected = False

        if self.websocket:
            await self.websocket.close()
            self.websocket = None

        self.logger.info("WebSocket disconnected")

    async def start(self) -> None:
        """Start the WebSocket client."""
        if self.is_running:
            self.logger.warning("WebSocket client is already running")
            return

        self.is_running = True
        self._shutdown_event.clear()

        self.logger.info("Starting WebSocket client...")

        try:
            # Connect to server
            await self.connect()

            # Start message handling loop
            await self._message_loop()

        except asyncio.CancelledError:
            self.logger.info("WebSocket client shutdown requested")
        except Exception as e:
            self.logger.error(f"WebSocket client error: {str(e)}")
            # Notify error handlers
            for handler in self.error_handlers:
                try:
                    handler(e)
                except Exception as handler_error:
                    self.logger.error(f"Error in error handler: {str(handler_error)}")
        finally:
            self.is_running = False
            await self.disconnect()

    async def stop(self) -> None:
        """Stop the WebSocket client."""
        if not self.is_running:
            return

        self.logger.info("Stopping WebSocket client...")
        self._shutdown_event.set()

        # Wait for message loop to finish
        await asyncio.sleep(0.1)

    async def _message_loop(self) -> None:
        """Main message handling loop."""
        while not self._shutdown_event.is_set() and self.is_connected:
            try:
                # Receive message with timeout
                message = await asyncio.wait_for(
                    self.websocket.recv(),
                    timeout=self.timeout
                )

                self.stats['messages_received'] += 1

                # Parse and handle message
                await self._handle_message(message)

            except asyncio.TimeoutError:
                # Send ping to keep connection alive
                await self._send_ping()

            except ConnectionClosed:
                self.logger.warning("WebSocket connection closed by server")
                self.is_connected = False
                await self._handle_reconnection()

            except Exception as e:
                self.stats['errors'] += 1
                self.logger.error(f"Error in message loop: {str(e)}")

                # Notify error handlers
                for handler in self.error_handlers:
                    try:
                        handler(e)
                    except Exception as handler_error:
                        self.logger.error(f"Error in error handler: {str(handler_error)}")

                if not self._shutdown_event.is_set():
                    await self._handle_reconnection()

    async def _handle_message(self, message: str) -> None:
        """Handle incoming WebSocket message.

        Args:
            message: Raw message string
        """
        try:
            # Parse JSON message
            data = json.loads(message)

            # Extract channel/topic from message
            channel = self._extract_channel(data)

            # Call registered handlers for this channel
            if channel in self.message_handlers:
                for handler in self.message_handlers[channel]:
                    try:
                        await handler(data)
                    except Exception as e:
                        self.logger.error(f"Error in message handler for {channel}: {str(e)}")

        except json.JSONDecodeError as e:
            self.logger.error(f"Invalid JSON message: {str(e)}")
        except Exception as e:
            self.logger.error(f"Error handling message: {str(e)}")

    def _extract_channel(self, data: Dict[str, Any]) -> str:
        """Extract channel/topic from message data.

        Args:
            data: Parsed message data

        Returns:
            Channel/topic identifier
        """
        # This is a generic implementation - override for specific exchange formats
        if 'channel' in data:
            return data['channel']
        elif 'topic' in data:
            return data['topic']
        elif 'type' in data:
            return data['type']
        else:
            return 'default'

    async def _send_ping(self) -> None:
        """Send ping frame to keep connection alive."""
        if self.websocket and self.is_connected:
            try:
                await self.websocket.ping()
            except Exception as e:
                self.logger.error(f"Error sending ping: {str(e)}")
                self.is_connected = False

    async def _handle_reconnection(self) -> None:
        """Handle reconnection logic."""
        if self._shutdown_event.is_set():
            return

        self.stats['reconnections'] += 1

        self.logger.info(f"Attempting reconnection ({self.stats['reconnections']})...")

        # Wait before reconnection attempt
        await asyncio.sleep(min(2 ** self.stats['reconnections'], 30))

        try:
            await self.connect()
        except Exception as e:
            self.logger.error(f"Reconnection failed: {str(e)}")

    async def _subscribe_to_channels(self) -> None:
        """Subscribe to configured channels."""
        for channel in self.subscriptions:
            if channel not in self.subscribed_channels:
                await self.subscribe(channel)
                self.subscribed_channels.add(channel)

    async def subscribe(self, channel: str) -> None:
        """Subscribe to a channel.

        Args:
            channel: Channel to subscribe to
        """
        if not self.is_connected:
            self.logger.warning("Cannot subscribe: not connected")
            return

        try:
            # Create subscription message (override for specific exchange format)
            subscription_message = self._create_subscription_message(channel)

            await self.send_message(subscription_message)

            self.logger.info(f"Subscribed to channel: {channel}")

        except Exception as e:
            self.logger.error(f"Error subscribing to {channel}: {str(e)}")

    async def unsubscribe(self, channel: str) -> None:
        """Unsubscribe from a channel.

        Args:
            channel: Channel to unsubscribe from
        """
        if not self.is_connected:
            self.logger.warning("Cannot unsubscribe: not connected")
            return

        try:
            # Create unsubscription message
            unsubscription_message = self._create_unsubscription_message(channel)

            await self.send_message(unsubscription_message)

            self.subscribed_channels.discard(channel)
            self.logger.info(f"Unsubscribed from channel: {channel}")

        except Exception as e:
            self.logger.error(f"Error unsubscribing from {channel}: {str(e)}")

    def _create_subscription_message(self, channel: str) -> Dict[str, Any]:
        """Create subscription message for channel.

        Args:
            channel: Channel to subscribe to

        Returns:
            Subscription message dictionary
        """
        # Generic subscription message - override for specific exchange formats
        return {
            'method': 'SUBSCRIBE',
            'params': [channel],
            'id': f'sub_{channel}_{asyncio.get_event_loop().time()}'
        }

    def _create_unsubscription_message(self, channel: str) -> Dict[str, Any]:
        """Create unsubscription message for channel.

        Args:
            channel: Channel to unsubscribe from

        Returns:
            Unsubscription message dictionary
        """
        # Generic unsubscription message - override for specific exchange formats
        return {
            'method': 'UNSUBSCRIBE',
            'params': [channel],
            'id': f'unsub_{channel}_{asyncio.get_event_loop().time()}'
        }

    async def send_message(self, message: Dict[str, Any]) -> None:
        """Send message to WebSocket server.

        Args:
            message: Message to send
        """
        if not self.is_connected or not self.websocket:
            raise WebSocketClientError("Not connected")

        try:
            message_str = json.dumps(message)
            await self.websocket.send(message_str)
            self.stats['messages_sent'] += 1

        except Exception as e:
            self.logger.error(f"Error sending message: {str(e)}")
            raise

    def add_message_handler(self, channel: str, handler: Callable) -> None:
        """Add message handler for a channel.

        Args:
            channel: Channel to handle messages for
            handler: Async handler function
        """
        if channel not in self.message_handlers:
            self.message_handlers[channel] = []

        self.message_handlers[channel].append(handler)
        self.logger.debug(f"Added message handler for channel: {channel}")

    def remove_message_handler(self, channel: str, handler: Callable) -> None:
        """Remove message handler for a channel.

        Args:
            channel: Channel to remove handler from
            handler: Handler function to remove
        """
        if channel in self.message_handlers:
            try:
                self.message_handlers[channel].remove(handler)
                self.logger.debug(f"Removed message handler for channel: {channel}")
            except ValueError:
                self.logger.warning(f"Handler not found for channel: {channel}")

    def add_error_handler(self, handler: Callable[[Exception], None]) -> None:
        """Add error handler.

        Args:
            handler: Error handler function
        """
        self.error_handlers.append(handler)
        self.logger.debug("Added error handler")

    def remove_error_handler(self, handler: Callable[[Exception], None]) -> None:
        """Remove error handler.

        Args:
            handler: Error handler function to remove
        """
        try:
            self.error_handlers.remove(handler)
            self.logger.debug("Removed error handler")
        except ValueError:
            self.logger.warning("Error handler not found")

    def get_stats(self) -> Dict[str, Any]:
        """Get client statistics.

        Returns:
            Dictionary with client statistics
        """
        uptime = None
        if self.stats['start_time']:
            uptime = asyncio.get_event_loop().time() - self.stats['start_time']

        return {
            'is_connected': self.is_connected,
            'is_running': self.is_running,
            'messages_received': self.stats['messages_received'],
            'messages_sent': self.stats['messages_sent'],
            'reconnections': self.stats['reconnections'],
            'errors': self.stats['errors'],
            'uptime_seconds': uptime,
            'subscribed_channels': list(self.subscribed_channels),
        }