# gazedeck/core/websocket_server.py

"""
Tiny high-throughput WebSocket broadcast server.

Design:
- Single asyncio loop (call start_ws_server() once from your app).
- Each client gets its own small queue to avoid head-of-line blocking.
- Producer pushes messages via broadcast_nowait(msg); slow clients drop.
- Outbound-only: we ignore incoming messages for max throughput.

Requires: websockets>=10  (pip install websockets)
"""

from __future__ import annotations

import asyncio
from typing import Set, Tuple
import websockets
from websockets.server import WebSocketServerProtocol
import contextlib

# Import binary message serialization
from .binary_messages import serialize_gaze_message

# Tune these to your needs
CLIENT_QUEUE_MAX = 256       # per-client buffer; drop beyond this
BROADCAST_QUEUE_MAX = 1024   # global buffer; drop beyond this

_clients: Set[asyncio.Queue] = set()
_broadcast_q: asyncio.Queue = asyncio.Queue(maxsize=BROADCAST_QUEUE_MAX)
_client_lock: asyncio.Lock = asyncio.Lock()

async def _client_handler(ws: WebSocketServerProtocol) -> None:
    """
    Registers a client with its own queue and streams messages to it.
    We don't read from ws; sending raises if the client disconnects.
    """
    q: asyncio.Queue = asyncio.Queue(maxsize=CLIENT_QUEUE_MAX)
    async with _client_lock:
        _clients.add(q)
    try:
        while True:
            msg = await q.get()
            await ws.send(msg)  # str or bytes
    except Exception as e:
        # ConnectionClosed or any send error → drop client
        pass
    finally:
        async with _client_lock:
            _clients.discard(q)

async def _broadcaster() -> None:
    """
    Fans out messages from the global queue to each client queue in parallel.
    Drops per-client if its queue is full (keeps fast clients fast).
    """
    try:
        while True:
            msg = await _broadcast_q.get()
            # Parallel fan-out: send to all clients simultaneously
            async with _client_lock:
                client_queues = _clients.copy()
            if client_queues:  # Only create tasks if we have clients
                tasks = []
                for q in client_queues:
                    tasks.append(_send_to_client(q, msg))
                await asyncio.gather(*tasks, return_exceptions=True)
    except asyncio.CancelledError:
        # This is expected during shutdown
        pass

async def _send_to_client(q: asyncio.Queue, msg: bytes) -> None:
    """Send message to a single client queue."""
    try:
        q.put_nowait(msg)
    except asyncio.QueueFull:
        # drop for this client; keeps overall throughput high
        pass

async def start_ws_server(host: str = "0.0.0.0", port: int = 8765) -> Tuple[websockets.server.Serve, asyncio.Task]:
    """
    Start the server and the broadcaster task.
    Returns (server, broadcaster_task). Keep them alive for the app lifetime.

    Usage:
        server, btask = await start_ws_server()
        # ... elsewhere: broadcast_nowait("hello")
    """
    server = await websockets.serve(
        _safe_client_handler, host, port,
        compression=None,   # save CPU; clients get raw speed
        max_size=None,      # allow large frames if needed
        ping_interval=20.0, # keep connections healthy
        ping_timeout=20.0,
    )
    btask = asyncio.create_task(_broadcaster())
    return server, btask

async def _safe_client_handler(ws: WebSocketServerProtocol) -> None:
    """
    Safe client handler that ignores invalid HTTP requests.
    (We don't want the server to crash for invalid HTTP requests)
    """
    try:
        await _client_handler(ws)
    except websockets.exceptions.InvalidMessage as e:
        if "did not receive a valid HTTP request" in str(e):
            # Try to get more info about the request
            try:
                remote_addr = ws.remote_address
                # Log without blocking (could use logging module if available)
            except:
                pass
        else:
            # Log without blocking (could use logging module if available)
            pass

def broadcast_nowait(msg: str | bytes) -> None:
    """
    Fast-path push from any coroutine/thread (thread-safe not guaranteed).
    Drops if the global queue is full to protect the event loop.
    """
    try:
        _broadcast_q.put_nowait(msg)
    except asyncio.QueueFull:
        # global pressure → drop newest; consider metrics if needed
        pass


def broadcast_gaze_data(device_id: int, surface_id: int, x: float, y: float, timestamp: float) -> None:
    """
    High-performance gaze data broadcast using binary serialization.

    Args:
        device_id: Stable integer device identifier
        surface_id: Stable integer surface identifier
        x: X coordinate (0.0-1.0 normalized on surface, can be higher or lower if the gaze is not on the surface, NaN if invalid)
        y: Y coordinate (0.0-1.0 normalized on surface, can be higher or lower if the gaze is not on the surface, NaN if invalid)
        timestamp: Gaze timestamp
    """
    message = serialize_gaze_message(device_id, surface_id, x, y, timestamp)
    broadcast_nowait(message)

async def stop_ws_server(server: websockets.server.Serve, btask: asyncio.Task) -> None:
    """Graceful shutdown with proper cancellation handling."""
    server.close()
    await server.wait_closed()
    btask.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await btask
