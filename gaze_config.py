#!/usr/bin/env python3

from pupil_labs.real_time_screen_gaze import marker_generator
from pupil_labs.real_time_screen_gaze.gaze_mapper import GazeMapper
from config_utils import get_marker_vertices as get_marker_vertices_from_config, get_screen_size as get_screen_size_from_config, load_apriltag_config

def generate_markers(marker_id=0):
    """Generate AprilTag markers."""
    print("Generating markers...")
    marker_pixels = marker_generator.generate_marker(marker_id=marker_id)
    print(f"Generated marker with ID {marker_id}")
    return marker_pixels

def get_marker_vertices(config_path="apriltags/apriltag_config.yaml"):
    """Get marker positions on screen from configuration file.

    Args:
        config_path: Path to the YAML configuration file

    Returns:
        Dictionary mapping marker IDs to their corner coordinates
    """
    try:
        return get_marker_vertices_from_config(config_path)
    except Exception as e:
        print(f"Error loading marker vertices from config: {e}")
        print("Make sure 'apriltags/apriltag_config.yaml' exists and is properly formatted.")
        raise

def get_screen_size(config_path="apriltags/apriltag_config.yaml"):
    """Get the screen size for the gaze mapping surface from configuration file.

    Args:
        config_path: Path to the YAML configuration file

    Returns:
        Tuple of (width, height)
    """
    try:
        return get_screen_size_from_config(config_path)
    except Exception as e:
        print(f"Error loading screen size from config: {e}")
        print("Make sure 'apriltags/apriltag_config.yaml' exists and is properly formatted.")
        raise

def create_gaze_mapper(calibration):
    """Create and return a GazeMapper instance."""
    print("Creating GazeMapper...")
    gaze_mapper = GazeMapper(calibration)

    # Debug: Check calibration data
    print(f"Calibration data keys: {list(calibration.keys())}")

    return gaze_mapper

def add_surface(gaze_mapper, marker_verts=None, screen_size=None, config_path="apriltags/apriltag_config.yaml"):
    """Add a surface to the gaze mapper and return the surface."""
    if marker_verts is None:
        marker_verts = get_marker_vertices(config_path)
    if screen_size is None:
        screen_size = get_screen_size(config_path)

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

    def __init__(self, calibration, config_path="apriltags/apriltag_config.yaml"):
        self.gaze_mapper = create_gaze_mapper(calibration)
        self.screen_surface = None
        self.marker_pixels = None
        self.config_path = config_path

    def setup_surface(self):
        """Set up the screen surface for gaze mapping."""
        self.marker_pixels = generate_markers()
        self.screen_surface = add_surface(self.gaze_mapper, config_path=self.config_path)
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
