#!/usr/bin/env python3

import asyncio
import json
import websockets

# WebSocket server constants
HOST = "localhost"
PORT = 8765

# WebSocket clients storage
connected_clients = set()

async def websocket_handler(websocket, path=None):
    """Handle WebSocket connections. This server is JUST FOR SENDING data."""
    # Add new client to the set
    connected_clients.add(websocket)
    print(f"New client connected from {websocket.remote_address}. Total clients: {len(connected_clients)}")

    try:
        # Keep connection alive but don't expect to receive data
        # Send a welcome message to confirm connection
        await websocket.send(json.dumps({
            "type": "connection_established",
            "message": "Connected to GazeDeck WebSocket server",
            "timestamp": asyncio.get_event_loop().time()
        }))
        await websocket.wait_closed()
    except Exception as e:
        print(f"WebSocket error: {e}")
    finally:
        # Remove client when they disconnect
        connected_clients.discard(websocket)
        print(f"Client disconnected. Total clients: {len(connected_clients)}")

async def send_gaze_data(x, y):
    """Send gaze coordinates to all connected WebSocket clients."""
    if not connected_clients:
        return

    message = json.dumps({
        "type": "gaze_data",
        "x": x,
        "y": y,
        "timestamp": asyncio.get_event_loop().time()
    })

    # Send to all connected clients
    disconnected_clients = set()
    for client in connected_clients:
        try:
            await client.send(message)
        except Exception as e:
            print(f"Failed to send data to client: {e}")
            disconnected_clients.add(client)

    # Remove disconnected clients
    for client in disconnected_clients:
        connected_clients.discard(client)

async def start_websocket_server():
    """Start the WebSocket server."""
    try:
        server = await websockets.serve(websocket_handler, HOST, PORT)
        print(f"WebSocket server started on ws://{HOST}:{PORT}")
        print(f"Connect your client to: ws://{HOST}:{PORT}")
        return server
    except Exception as e:
        print(f"Failed to start WebSocket server: {e}")
        raise

def get_websocket_info():
    """Get WebSocket server information."""
    return {
        "host": HOST,
        "port": PORT,
        "url": f"ws://{HOST}:{PORT}"
    }
