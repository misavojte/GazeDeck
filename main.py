#!/usr/bin/env python3
"""
GazeDeck - Real-time Gaze Tracking Application

This application provides real-time gaze tracking using Pupil Labs eye tracking
hardware and AprilTag markers for surface calibration. It streams gaze coordinates
to connected WebSocket clients for interactive applications.

Features:
- Automatic device discovery and calibration
- AprilTag-based surface configuration
- Real-time gaze coordinate mapping
- WebSocket streaming to clients
- Graceful shutdown handling
- Comprehensive error handling and logging

Usage:
    python main.py

The application will:
1. Discover and connect to Pupil Labs device
2. Load surface configuration from apriltags/apriltag_config.yaml
3. Start WebSocket server for client connections
4. Begin streaming mapped gaze coordinates

Press Ctrl+C to shutdown gracefully.
"""

import signal
import asyncio

from device_manager import DeviceManager
from websocket_server import start_websocket_server, send_gaze_data
from surface import Surface
from pupil_labs.real_time_screen_gaze.gaze_mapper import GazeMapper

# Global flag for graceful shutdown
running = True

def signal_handler(signum, frame):
    """Handle interrupt signal (Ctrl+C) for graceful shutdown."""
    global running
    print("\nReceived interrupt signal. Shutting down gracefully...")
    running = False

# Register signal handler for SIGINT (Ctrl+C)
signal.signal(signal.SIGINT, signal_handler)

async def main(device, calibration):
    """Main async function that runs the gaze tracking with WebSocket server."""

    # Load surface configuration using the Surface class
    print("Loading surface configuration...")
    try:
        surface = Surface.from_file("apriltags/apriltag_config.yaml")
        print(f"Loaded surface: {surface}")

        # Validate configuration
        validation_errors = surface.validate()
        if validation_errors:
            print("Configuration validation errors:")
            for error in validation_errors:
                print(f"  - {error}")
            print("Please check your apriltags/apriltag_config.yaml file")
            return

    except Exception as e:
        print(f"Failed to load surface configuration: {e}")
        print("Make sure 'apriltags/apriltag_config.yaml' exists and is valid")
        return

    # Create gaze mapper
    print("Creating GazeMapper...")
    try:
        gaze_mapper = GazeMapper(calibration)
    except Exception as e:
        print(f"Failed to create GazeMapper: {e}")
        return

    # Add surface to gaze mapper using calibration data
    print("Adding surface to gaze mapper...")
    try:
        gaze_surface = gaze_mapper.add_surface(
            surface.calibration.marker_vertices,
            surface.calibration.surface_size
        )
        print(f"Gaze surface created with UID: {gaze_surface.uid}")
    except Exception as e:
        print(f"Failed to add surface to gaze mapper: {e}")
        return

    # Start WebSocket server
    print("Starting WebSocket server...")
    try:
        websocket_server = await start_websocket_server()
        print("WebSocket server started successfully")
    except Exception as e:
        print(f"Failed to start WebSocket server: {e}")
        return

    # Main loop
    print("Starting gaze tracking loop...")
    print("Press Ctrl+C to stop gracefully...")
    print(f"Surface configuration: {surface.get_summary()}")

    gaze_count = 0
    try:
        while running:
            try:
                # Receive frame and gaze data
                frame, gaze = device.receive_matched_scene_video_frame_and_gaze()

                # Process frame through gaze mapper
                result = gaze_mapper.process_frame(frame, gaze)

                # Send mapped gaze coordinates to WebSocket clients
                if gaze_surface.uid in result.mapped_gaze:
                    surface_gazes = result.mapped_gaze[gaze_surface.uid]
                    for surface_gaze in surface_gazes:
                        x, y = surface_gaze.x, surface_gaze.y

                        # Only send valid coordinates within surface bounds
                        if (0 <= x <= surface.calibration.surface_size[0] and
                            0 <= y <= surface.calibration.surface_size[1]):
                            print(f"Server sending: {x:.3f}, {y:.3f}")
                            await send_gaze_data(x, y)
                            gaze_count += 1

                # Small delay to prevent overwhelming the clients
                await asyncio.sleep(0.01)

            except Exception as e:
                print(f"Error in gaze tracking loop: {e}")
                await asyncio.sleep(0.1)  # Slightly longer delay on error
                continue

    except KeyboardInterrupt:
        print("\nReceived keyboard interrupt...")
    finally:
        # Cleanup resources
        print("Cleaning up resources...")

        # Close WebSocket server
        try:
            websocket_server.close()
            await websocket_server.wait_closed()
            print("WebSocket server closed")
        except Exception as e:
            print(f"Error closing WebSocket server: {e}")

        # Clean up gaze mapper surface
        try:
            gaze_mapper.remove_surface(gaze_surface.uid)
            print("Gaze surface removed successfully")
        except Exception as e:
            print(f"Error during surface cleanup: {e}")

        # Clean up device connection
        try:
            device_manager.cleanup()
            print("Device connection cleaned up")
        except Exception as e:
            print(f"Error during device cleanup: {e}")

        print(f"Shutdown complete. Total gaze points sent: {gaze_count}")
        print("Goodbye!")

if __name__ == "__main__":
    # Initialize device and calibration before starting async loop
    print("Initializing Pupil Labs device...")
    device_manager = DeviceManager()
    try:
        device, calibration = device_manager.initialize()
        print("Device initialized successfully")
    except Exception as e:
        print(f"Failed to initialize device: {e}")
        exit(1)

    print("Starting gaze tracking application...")
    try:
        asyncio.run(main(device, calibration))
    except KeyboardInterrupt:
        print("\nApplication interrupted by user")
    except Exception as e:
        print(f"Application error: {e}")
        exit(1)