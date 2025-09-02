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

# Tune these to your needs
CLIENT_QUEUE_MAX = 256       # per-client buffer; drop beyond this
BROADCAST_QUEUE_MAX = 1024   # global buffer; drop beyond this

_clients: Set[asyncio.Queue] = set()
_broadcast_q: asyncio.Queue = asyncio.Queue(maxsize=BROADCAST_QUEUE_MAX)

async def _client_handler(ws: WebSocketServerProtocol) -> None:
    """
    Registers a client with its own queue and streams messages to it.
    We don't read from ws; sending raises if the client disconnects.
    """
    q: asyncio.Queue = asyncio.Queue(maxsize=CLIENT_QUEUE_MAX)
    _clients.add(q)
    try:
        while True:
            msg = await q.get()
            await ws.send(msg)  # str or bytes
    except Exception:
        # ConnectionClosed or any send error → drop client
        pass
    finally:
        _clients.discard(q)

async def _broadcaster() -> None:
    """
    Fans out messages from the global queue to each client queue.
    Drops per-client if its queue is full (keeps fast clients fast).
    """
    while True:
        msg = await _broadcast_q.get()
        for q in tuple(_clients):
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
                print(f"ℹ️ Ignored HTTP request from {remote_addr} to WebSocket endpoint")
            except:
                print(f"ℹ️ Ignored invalid HTTP request to WebSocket endpoint")
        else:
            print(f"⚠️ WebSocket InvalidMessage error: {e}")

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

async def stop_ws_server(server: websockets.server.Serve, btask: asyncio.Task) -> None:
    """Graceful shutdown."""
    server.close()
    await server.wait_closed()
    btask.cancel()
    with contextlib.suppress(Exception):
        await btask
