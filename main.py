#!/usr/bin/env python3

import signal
import asyncio

from device_manager import DeviceManager
from websocket_server import start_websocket_server, send_gaze_data
from gaze_config import GazeConfig

# Global flag for graceful shutdown
running = True

def signal_handler(signum, frame):
    """Handle interrupt signal (Ctrl+C) for graceful shutdown."""
    global running
    print("\nReceived interrupt signal. Shutting down gracefully...")
    running = False

# Register signal handler for SIGINT (Ctrl+C)
signal.signal(signal.SIGINT, signal_handler)

async def main():
    """Main async function that runs the gaze tracking with WebSocket server."""

    # Initialize device and calibration
    device_manager = DeviceManager()
    device, calibration = device_manager.initialize()

    # Set up gaze mapping configuration
    gaze_config = GazeConfig(calibration)
    screen_surface = gaze_config.setup_surface()

    # Start WebSocket server
    websocket_server = await start_websocket_server()

    # Main loop
    print("Starting gaze tracking loop...")
    print("Press Ctrl+C to stop gracefully...")
    try:
        while running:
            try:
                frame, gaze = device.receive_matched_scene_video_frame_and_gaze()
                result = gaze_config.gaze_mapper.process_frame(frame, gaze)

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

        # Clean up gaze configuration
        gaze_config.cleanup()

        # Clean up device connection
        device_manager.cleanup()

        print("Shutdown complete. Goodbye!")

if __name__ == "__main__":
    asyncio.run(main())