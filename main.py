#!/usr/bin/env python3

from pupil_labs.real_time_screen_gaze import marker_generator
from pupil_labs.realtime_api.simple import discover_one_device
from pupil_labs.real_time_screen_gaze.gaze_mapper import GazeMapper

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

# Define marker positions on screen (example with 4 markers)
marker_verts = {
    0: [  # marker id 0
        (32, 32),   # Top left marker corner
        (96, 32),   # Top right
        (96, 96),   # Bottom right
        (32, 96),   # Bottom left
    ],
    1: [  # marker id 1
        (1824, 32),   # Top left marker corner
        (1888, 32),   # Top right
        (1888, 96),   # Bottom right
        (1824, 96),   # Bottom left
    ],
    2: [  # marker id 2
        (32, 984),   # Top left marker corner
        (96, 984),   # Top right
        (96, 1048),  # Bottom right
        (32, 1048),  # Bottom left
    ],
    3: [  # marker id 3
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

# Main loop
print("Starting gaze tracking loop...")
device = discover_one_device(max_search_duration_seconds=10)

while True:
    frame, gaze = device.receive_matched_scene_video_frame_and_gaze()
    result = gaze_mapper.process_frame(frame, gaze)

    for surface_gaze in result.mapped_gaze[screen_surface.uid]:
        print(f"Gaze at {surface_gaze.x}, {surface_gaze.y}")
