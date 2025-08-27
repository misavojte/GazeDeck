#!/usr/bin/env python3

import sys
import traceback
import signal
import asyncio
import json
import websockets
from pupil_labs.real_time_screen_gaze import marker_generator
from pupil_labs.realtime_api.simple import discover_one_device
from pupil_labs.real_time_screen_gaze.gaze_mapper import GazeMapper

# WebSocket server constants
HOST = "localhost"
PORT = 8765

# Global flag for graceful shutdown
running = True

# WebSocket clients storage
connected_clients = set()

def signal_handler(signum, frame):
    """Handle interrupt signal (Ctrl+C) for graceful shutdown."""
    global running
    print("\nReceived interrupt signal. Shutting down gracefully...")
    running = False

# Register signal handler for SIGINT (Ctrl+C)
signal.signal(signal.SIGINT, signal_handler)

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

# Set up device and calibration synchronously before entering async context
print("Discovering device...")
device = discover_one_device()
print("Getting calibration...")
calibration = device.get_calibration()

async def main():
    """Main async function that runs the gaze tracking with WebSocket server."""

    # Generate AprilTag markers
    print("Generating markers...")
    marker_pixels = marker_generator.generate_marker(marker_id=0)
    print("Generated marker with ID 0")

    # Create GazeMapper
    print("Creating GazeMapper...")
    gaze_mapper = GazeMapper(calibration)

    # Debug: Check calibration data
    print(f"Calibration data keys: {list(calibration.keys())}")

    # Define marker positions on screen (MUST match your actual printed AprilTag positions!)
    # IMPORTANT: Update these coordinates to match where you actually placed your printed AprilTags
    # The coordinates are (x, y) where (0, 0) is top-left of your screen
    # Each marker needs 4 corners: [top-left, top-right, bottom-right, bottom-left]
    # Layout: 2x5 grid of 100x100px markers on 1020x780 screen
    marker_verts = {
        0: [  # marker id 0 - Row 1, Col 1
            (65, 90),      # Top left marker corner
            (165, 90),     # Top right
            (165, 190),    # Bottom right
            (65, 190),     # Bottom left
        ],
        1: [  # marker id 1 - Row 1, Col 2
            (295, 90),     # Top left marker corner
            (395, 90),     # Top right
            (395, 190),    # Bottom right
            (295, 190),    # Bottom left
        ],
        2: [  # marker id 2 - Row 1, Col 3
            (525, 90),     # Top left marker corner
            (625, 90),     # Top right
            (625, 190),    # Bottom right
            (525, 190),    # Bottom left
        ],
        3: [  # marker id 3 - Row 1, Col 4
            (755, 90),     # Top left marker corner
            (855, 90),     # Top right
            (855, 190),    # Bottom right
            (755, 190),    # Bottom left
        ],
        4: [  # marker id 4 - Row 1, Col 5
            (985, 90),     # Top left marker corner
            (1085, 90),    # Top right
            (1085, 190),   # Bottom right
            (985, 190),    # Bottom left
        ],
        5: [  # marker id 5 - Row 2, Col 1
            (65, 590),     # Top left marker corner
            (165, 590),    # Top right
            (165, 690),    # Bottom right
            (65, 690),     # Bottom left
        ],
        6: [  # marker id 6 - Row 2, Col 2
            (295, 590),    # Top left marker corner
            (395, 590),    # Top right
            (395, 690),    # Bottom right
            (295, 690),    # Bottom left
        ],
        7: [  # marker id 7 - Row 2, Col 3
            (525, 590),    # Top left marker corner
            (625, 590),    # Top right
            (625, 690),    # Bottom right
            (525, 690),    # Bottom left
        ],
        8: [  # marker id 8 - Row 2, Col 4
            (755, 590),    # Top left marker corner
            (855, 590),    # Top right
            (855, 690),    # Bottom right
            (755, 690),    # Bottom left
        ],
        9: [  # marker id 9 - Row 2, Col 5
            (985, 590),    # Top left marker corner
            (1085, 590),   # Top right
            (1085, 690),   # Bottom right
            (985, 690),    # Bottom left
        ],
    }

    screen_size = (1020, 780)

    print("Adding surface...")
    screen_surface = gaze_mapper.add_surface(
        marker_verts,
        screen_size
    )
    print(f"Surface created with UID: {screen_surface.uid}")
    print(f"Marker vertices: {marker_verts}")

    # Start WebSocket server
    websocket_server = await start_websocket_server()

    # Main loop
    print("Starting gaze tracking loop...")
    print("Press Ctrl+C to stop gracefully...")
    try:
        while running:
            try:
                frame, gaze = device.receive_matched_scene_video_frame_and_gaze()
                result = gaze_mapper.process_frame(frame, gaze)

                # Log and send mapped gaze coordinates
                if screen_surface.uid in result.mapped_gaze:
                    surface_gazes = result.mapped_gaze[screen_surface.uid]
                    for surface_gaze in surface_gazes:
                        x, y = surface_gaze.x, surface_gaze.y
                        print(f"Server sending: {x:.3f}, {y:.3f}")
                        # Send gaze data to all connected WebSocket clients
                        await send_gaze_data(x, y)

                # Small delay to prevent overwhelming the clients
                await asyncio.sleep(0.01)

            except Exception as e:
                print(f"Error: {e}")
                continue
    finally:
        # Cleanup resources
        print("Cleaning up resources...")

        # Close WebSocket server
        websocket_server.close()
        await websocket_server.wait_closed()
        print("WebSocket server closed")

        try:
            # Remove the surface if it exists
            if 'screen_surface' in locals():
                gaze_mapper.remove_surface(screen_surface.uid)
                print("Surface removed successfully")
        except Exception as e:
            print(f"Error during surface cleanup: {e}")

        try:
            # Close device connection if it exists
            if 'device' in locals():
                device.close()
                print("Device connection closed successfully")
        except Exception as e:
            print(f"Error during device cleanup: {e}")

        print("Shutdown complete. Goodbye!")

if __name__ == "__main__":
    asyncio.run(main())