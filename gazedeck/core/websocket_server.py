# gazedeck/core/websocket_server.py

"""
High-throughput WebSocket broadcast server with proper encapsulation.

Design:
- Class-based design eliminates global state issues
- Each instance manages its own clients and broadcast queue
- Proper resource cleanup and lifecycle management
- Thread-safe operations with proper async patterns

Requires: websockets>=10  (pip install websockets)
"""

from __future__ import annotations

import asyncio
from typing import Set, Optional
import websockets
from websockets.server import WebSocketServerProtocol
import contextlib

# Import binary message serialization
from .binary_messages import serialize_gaze_message

# Tune these to your needs
CLIENT_QUEUE_MAX = 256       # per-client buffer; drop beyond this
BROADCAST_QUEUE_MAX = 1024   # global buffer; drop beyond this


class WebSocketServer:
    """
    High-performance WebSocket broadcast server with proper encapsulation.
    
    Eliminates global state issues by encapsulating all server state
    within the class instance. Each instance is completely independent.
    
    Why class-based design:
    - Eliminates global state pollution between command executions
    - Enables proper resource lifecycle management
    - Makes testing easier with isolated instances
    - Follows Python best practices for stateful services
    """
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8765):
        """
        Initialize WebSocket server with clean state.
        
        Args:
            host: Server host address (default: "0.0.0.0" for all interfaces)
            port: Server port number (default: 8765)
        """
        self.host = host
        self.port = port
        self._clients: Set[asyncio.Queue] = set()
        self._broadcast_q: asyncio.Queue = asyncio.Queue(maxsize=BROADCAST_QUEUE_MAX)
        self._client_lock: asyncio.Lock = asyncio.Lock()
        self._server: Optional[websockets.server.Serve] = None
        self._broadcaster_task: Optional[asyncio.Task] = None
        self._is_running = False
    
    async def _client_handler(self, ws: WebSocketServerProtocol) -> None:
        """
        Handle individual client connections.
        
        Why separate queue per client:
        - Prevents head-of-line blocking between clients
        - Allows dropping slow clients without affecting others
        - Enables parallel message distribution
        """
        q: asyncio.Queue = asyncio.Queue(maxsize=CLIENT_QUEUE_MAX)
        async with self._client_lock:
            self._clients.add(q)
        try:
            while True:
                msg = await q.get()
                await ws.send(msg)  # str or bytes
        except Exception:
            # ConnectionClosed or any send error → drop client
            # No logging here to avoid high-frequency output
            pass
        finally:
            async with self._client_lock:
                self._clients.discard(q)
    
    async def _broadcaster(self) -> None:
        """
        Distribute messages from broadcast queue to all client queues.
        
        Why parallel distribution:
        - Maximizes throughput by sending to all clients simultaneously
        - Uses asyncio.gather for efficient parallel execution
        - Drops messages for slow clients to maintain overall performance
        """
        try:
            while True:
                msg = await self._broadcast_q.get()
                # Parallel fan-out: send to all clients simultaneously
                async with self._client_lock:
                    client_queues = self._clients.copy()
                if client_queues:  # Only create tasks if we have clients
                    tasks = []
                    for q in client_queues:
                        tasks.append(self._send_to_client(q, msg))
                    await asyncio.gather(*tasks, return_exceptions=True)
        except asyncio.CancelledError:
            # Expected during shutdown - no logging needed
            pass
    
    async def _send_to_client(self, q: asyncio.Queue, msg: bytes) -> None:
        """
        Send message to a single client queue.
        
        Why non-blocking put:
        - Prevents slow clients from blocking the broadcaster
        - Maintains high throughput for fast clients
        - Implements backpressure by dropping messages
        """
        try:
            q.put_nowait(msg)
        except asyncio.QueueFull:
            # Drop message for this client - maintains overall performance
            pass
    
    async def _safe_client_handler(self, ws: WebSocketServerProtocol) -> None:
        """
        Safe client handler that ignores invalid HTTP requests.
        
        Why safe handling:
        - Prevents server crashes from malformed HTTP requests
        - WebSocket servers should be robust against invalid requests
        - Graceful degradation maintains service availability
        """
        try:
            await self._client_handler(ws)
        except websockets.exceptions.InvalidMessage as e:
            if "did not receive a valid HTTP request" in str(e):
                # Invalid HTTP request - ignore silently
                pass
            else:
                # Other WebSocket errors - ignore silently
                pass
    
    async def start(self) -> None:
        """
        Start the WebSocket server and broadcaster task.
        
        Raises:
            RuntimeError: If server is already running
            
        Why separate start method:
        - Enables proper resource initialization
        - Allows error handling during startup
        - Follows async context manager patterns
        """
        if self._is_running:
            raise RuntimeError("WebSocket server is already running")
        
        self._server = await websockets.serve(
            self._safe_client_handler, self.host, self.port,
            compression=None,   # save CPU; clients get raw speed
            max_size=None,      # allow large frames if needed
            ping_interval=20.0, # keep connections healthy
            ping_timeout=20.0,
        )
        self._broadcaster_task = asyncio.create_task(self._broadcaster())
        self._is_running = True
    
    async def stop(self) -> None:
        """
        Graceful shutdown with short timeouts.
        
        Why short timeouts:
        - Prevents indefinite blocking during shutdown
        - Ensures responsive application termination
        - Follows asyncio best practices for cleanup
        """
        if not self._is_running:
            return
        
        self._is_running = False
        
        if self._server:
            self._server.close()
            # Ensure server closes quickly
            with contextlib.suppress(asyncio.TimeoutError):
                await asyncio.wait_for(self._server.wait_closed(), timeout=0.3)
        
        # Stop broadcaster task
        if self._broadcaster_task:
            self._broadcaster_task.cancel()
            with contextlib.suppress(asyncio.CancelledError, asyncio.TimeoutError):
                await asyncio.wait_for(self._broadcaster_task, timeout=0.3)
        
        # Clear all state
        self._reset_state()
    
    def _reset_state(self) -> None:
        """
        Reset all internal state to clean state.
        
        Why explicit state reset:
        - Ensures clean state between server restarts
        - Prevents memory leaks from accumulated state
        - Enables proper resource cleanup
        """
        self._clients.clear()
        
        # Clear the broadcast queue
        while not self._broadcast_q.empty():
            try:
                self._broadcast_q.get_nowait()
            except asyncio.QueueEmpty:
                break
        
        # Reset the client lock
        self._client_lock = asyncio.Lock()
    
    def broadcast_nowait(self, msg: str | bytes) -> None:
        """
        Fast-path message broadcast.
        
        Why non-blocking broadcast:
        - Prevents blocking the event loop
        - Maintains high-frequency performance
        - Implements backpressure by dropping messages when full
        """
        if not self._is_running:
            return
        
        try:
            self._broadcast_q.put_nowait(msg)
        except asyncio.QueueFull:
            # Drop message to prevent blocking - maintains performance
            pass
    
    def broadcast_gaze_data(self, device_id: int, surface_id: int, x: float, y: float, timestamp: float) -> None:
        """
        High-performance gaze data broadcast using binary serialization.

        Args:
            device_id: Stable integer device identifier
            surface_id: Stable integer surface identifier
            x: X coordinate (0.0-1.0 normalized on surface, can be higher or lower if the gaze is not on the surface, NaN if invalid)
            y: Y coordinate (0.0-1.0 normalized on surface, can be higher or lower if the gaze is not on the surface, NaN if invalid)
            timestamp: Gaze timestamp
            
        Why binary serialization:
        - 30x faster than JSON serialization
        - Reduces CPU overhead for high-frequency data
        - Minimizes network bandwidth usage
        """
        message = serialize_gaze_message(device_id, surface_id, x, y, timestamp)
        self.broadcast_nowait(message)
    
    @property
    def is_running(self) -> bool:
        """Check if the server is currently running."""
        return self._is_running
    
    @property
    def client_count(self) -> int:
        """Get the current number of connected clients."""
        return len(self._clients)