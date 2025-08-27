#!/usr/bin/env python3

from pupil_labs.real_time_screen_gaze import marker_generator
from pupil_labs.real_time_screen_gaze.gaze_mapper import GazeMapper

def generate_markers(marker_id=0):
    """Generate AprilTag markers."""
    print("Generating markers...")
    marker_pixels = marker_generator.generate_marker(marker_id=marker_id)
    print(f"Generated marker with ID {marker_id}")
    return marker_pixels

def get_marker_vertices():
    """Get marker positions on screen.

    IMPORTANT: Update these coordinates to match where you actually placed your printed AprilTags
    The coordinates are (x, y) where (0, 0) is top-left of your screen
    Each marker needs 4 corners: [top-left, top-right, bottom-right, bottom-left]
    Layout: 2x5 grid of 100x100px markers on 1020x780 screen
    """
    return {
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

def get_screen_size():
    """Get the screen size for the gaze mapping surface."""
    return (1020, 780)

def create_gaze_mapper(calibration):
    """Create and return a GazeMapper instance."""
    print("Creating GazeMapper...")
    gaze_mapper = GazeMapper(calibration)

    # Debug: Check calibration data
    print(f"Calibration data keys: {list(calibration.keys())}")

    return gaze_mapper

def add_surface(gaze_mapper, marker_verts=None, screen_size=None):
    """Add a surface to the gaze mapper and return the surface."""
    if marker_verts is None:
        marker_verts = get_marker_vertices()
    if screen_size is None:
        screen_size = get_screen_size()

    print("Adding surface...")
    screen_surface = gaze_mapper.add_surface(
        marker_verts,
        screen_size
    )
    print(f"Surface created with UID: {screen_surface.uid}")
    print(f"Marker vertices: {marker_verts}")

    return screen_surface

def remove_surface(gaze_mapper, surface_uid):
    """Remove a surface from the gaze mapper."""
    try:
        gaze_mapper.remove_surface(surface_uid)
        print("Surface removed successfully")
    except Exception as e:
        print(f"Error during surface cleanup: {e}")

class GazeConfig:
    """Configuration and setup for gaze mapping."""

    def __init__(self, calibration):
        self.gaze_mapper = create_gaze_mapper(calibration)
        self.screen_surface = None
        self.marker_pixels = None

    def setup_surface(self):
        """Set up the screen surface for gaze mapping."""
        self.marker_pixels = generate_markers()
        self.screen_surface = add_surface(self.gaze_mapper)
        return self.screen_surface

    def cleanup(self):
        """Clean up gaze mapping resources."""
        if self.screen_surface:
            remove_surface(self.gaze_mapper, self.screen_surface.uid)

    def __enter__(self):
        """Context manager entry."""
        self.setup_surface()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.cleanup()
