"""WebSocket sink for gaze events."""

import asyncio
import json
import logging
from typing import Set

import websockets
from websockets.exceptions import ConnectionClosedError

from ...core.types import GazeEvent
from ...ports.sink import ISink

logger = logging.getLogger(__name__)


class WebSocketSink(ISink):
    """WebSocket sink that broadcasts gaze events to connected clients."""

    def __init__(self, host: str = "localhost", port: int = 8765) -> None:
        """Initialize WebSocket sink.

        Args:
            host: Host to bind to
            port: Port to listen on
        """
        self._host = host
        self._port = port
        self._connected_clients: Set[websockets.WebSocketServerProtocol] = set()
        self._server: websockets.WebSocketServer | None = None
        self._running = False

    async def serve(self, host: str | None = None, port: int | None = None) -> None:
        """Start WebSocket server.

        Args:
            host: Override default host
            port: Override default port
        """
        if host is not None:
            self._host = host
        if port is not None:
            self._port = port

        self._running = True

        try:
            self._server = await websockets.serve(
                self._handle_connection,
                self._host,
                self._port,
            )
            logger.info(f"WebSocket server started on ws://{self._host}:{self._port}")

            # Keep the server running
            await self._server.wait_closed()
        except Exception as e:
            logger.error(f"WebSocket server error: {e}")
            raise
        finally:
            self._running = False

    async def emit(self, msg: GazeEvent) -> None:
        """Emit gaze event to all connected clients.

        Args:
            msg: Gaze event to emit
        """
        if not self._connected_clients:
            return

        # Convert to JSON
        try:
            json_data = msg.model_dump_json()
        except Exception as e:
            logger.error(f"Failed to serialize GazeEvent: {e}")
            return

        # Send to all clients, removing dead ones
        dead_clients = set()

        for client in self._connected_clients:
            try:
                await client.send(json_data)
            except ConnectionClosedError:
                dead_clients.add(client)
            except Exception as e:
                logger.warning(f"Failed to send to client: {e}")
                dead_clients.add(client)

        # Remove dead clients
        self._connected_clients -= dead_clients

        if dead_clients:
            logger.info(f"Removed {len(dead_clients)} dead clients")

    async def _handle_connection(
        self, websocket: websockets.WebSocketServerProtocol
    ) -> None:
        """Handle individual WebSocket connection.

        Args:
            websocket: WebSocket connection
        """
        logger.info(f"New client connected from {websocket.remote_address}")
        self._connected_clients.add(websocket)

        try:
            # Send periodic pings to keep connection alive
            while self._running and websocket in self._connected_clients:
                await asyncio.sleep(30)  # Ping every 30 seconds
                try:
                    await websocket.ping()
                except ConnectionClosedError:
                    break
        except Exception as e:
            logger.warning(f"Connection handler error: {e}")
        finally:
            self._connected_clients.discard(websocket)
            logger.info(f"Client disconnected: {websocket.remote_address}")

    async def close(self) -> None:
        """Close the WebSocket server."""
        self._running = False

        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()

        # Close all client connections
        close_tasks = []
        for client in self._connected_clients:
            close_tasks.append(client.close())

        if close_tasks:
            await asyncio.gather(*close_tasks, return_exceptions=True)

        self._connected_clients.clear()
        logger.info("WebSocket sink closed")
