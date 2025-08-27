#!/usr/bin/env python3

import sys
import traceback
import signal
from pupil_labs.real_time_screen_gaze import marker_generator
from pupil_labs.realtime_api.simple import discover_one_device
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

# Generate AprilTag markers
print("Generating markers...")
marker_pixels = marker_generator.generate_marker(marker_id=0)
print(f"Generated marker with ID 0")

# Set up device and calibration
print("Discovering device...")
device = discover_one_device()
print("Getting calibration...")
calibration = device.get_calibration()

# Create GazeMapper
print("Creating GazeMapper...")
gaze_mapper = GazeMapper(calibration)

# Debug: Check calibration data
print(f"Calibration data keys: {list(calibration.keys())}")

# Define marker positions on screen (MUST match your actual printed AprilTag positions!)
# IMPORTANT: Update these coordinates to match where you actually placed your printed AprilTags
# The coordinates are (x, y) where (0, 0) is top-left of your screen
# Each marker needs 4 corners: [top-left, top-right, bottom-right, bottom-left]
marker_verts = {
    0: [  # marker id 0 - TOP-LEFT corner of screen
        (32, 32),   # Top left marker corner
        (96, 32),   # Top right
        (96, 96),   # Bottom right
        (32, 96),   # Bottom left
    ],
    1: [  # marker id 1 - TOP-RIGHT corner of screen
        (1824, 32),   # Top left marker corner
        (1888, 32),   # Top right
        (1888, 96),   # Bottom right
        (1824, 96),   # Bottom left
    ],
    2: [  # marker id 2 - BOTTOM-LEFT corner of screen
        (32, 984),   # Top left marker corner
        (96, 984),   # Top right
        (96, 1048),  # Bottom right
        (32, 1048),  # Bottom left
    ],
    3: [  # marker id 3 - BOTTOM-RIGHT corner of screen
        (1824, 984),   # Top left marker corner
        (1888, 984),   # Top right
        (1888, 1048),  # Bottom right
        (1824, 1048),  # Bottom left
    ],
}

screen_size = (1920, 1080)

print("Adding surface...")
screen_surface = gaze_mapper.add_surface(
    marker_verts,
    screen_size
)
print(f"Surface created with UID: {screen_surface.uid}")
print(f"Marker vertices: {marker_verts}")

# Main loop
print("Starting gaze tracking loop...")
print("Press Ctrl+C to stop gracefully...")
try:
    while running:
        try:
            frame, gaze = device.receive_matched_scene_video_frame_and_gaze()
            result = gaze_mapper.process_frame(frame, gaze)

            # Log only the mapped gaze coordinates
            if screen_surface.uid in result.mapped_gaze:
                surface_gazes = result.mapped_gaze[screen_surface.uid]
                for surface_gaze in surface_gazes:
                    print(f"{surface_gaze.x}, {surface_gaze.y}")

        except Exception as e:
            print(f"Error: {e}")
            continue
finally:
    # Cleanup resources
    print("Cleaning up resources...")
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
