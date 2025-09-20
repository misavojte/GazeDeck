# gazedeck/core/gaze_mapper.py
# Simplified gaze mapper using emission_ids and modular components

from typing import Dict, List, NamedTuple, Optional, Any
import numpy as np
from pupil_labs.realtime_api import GazeData

from .camera_distortion import CameraDistortion
from .marker_detection import SimpleMarkerDetector, DetectedMarker
from .surface_tracking import track_surfaces, project_gaze_to_surface

class SimpleMappedGaze(NamedTuple):
    """Simple gaze mapping result"""
    surface_id: int  # emission_id
    x: float
    y: float
    base_datum: GazeData

class SimpleMapperResult(NamedTuple):
    """Simple gaze mapping result"""
    mapped_gaze: Dict[int, List[SimpleMappedGaze]]  # emission_id -> gaze data

class GazeMapper:
    """
    Simplified gaze mapper using emission_ids and CV2 homography.

    No surface_tracker dependency, no complex coordinate spaces.
    """

    def __init__(self, camera_distortion: dict, apriltag_params: Optional[Dict[str, Any]] = None):
        self._camera = CameraDistortion(camera_distortion)
        self._detector = SimpleMarkerDetector(apriltag_params)
        self._surfaces = {}  # emission_id -> surface_data
        self._surface_locations = {}  # emission_id -> homography_matrix
        self._detected_markers: List[DetectedMarker] = []

    def add_surface(self, markers_verts: dict, surface_size: tuple[float, float],
                   emission_id: int) -> int:
        """
        Add surface using emission_id directly.

        Args:
            markers_verts: Dict mapping tag_id -> tuple of (x, y) surface coordinates
            surface_size: (width, height) in pixels
            emission_id: Integer surface ID for WebSocket transmission

        Returns:
            The emission_id used
        """
        # Convert markers_verts from tuple-of-tuples to list-of-tuples for easier processing
        converted_markers = {}
        for tag_id, corners_tuple in markers_verts.items():
            converted_markers[tag_id] = list(corners_tuple)

        self._surfaces[emission_id] = {
            'markers': converted_markers,
            'size': surface_size
        }
        return emission_id

    def process_scene(self, frame):
        """Process video frame to detect markers and track surfaces"""
        if hasattr(frame, 'bgr_pixels'):
            frame = frame.bgr_pixels
        elif hasattr(frame, 'bgr_buffer'):
            frame = frame.bgr_buffer()

        # Detect markers and undistort corners
        self._detected_markers = self._detector.detect_markers(frame, self._camera)

        # Track surfaces using CV2 homography
        self._surface_locations = track_surfaces(self._detected_markers, self._surfaces)

    def process_gaze(self, gaze: GazeData) -> SimpleMapperResult:
        """
        Process gaze data using latest surface locations.

        Args:
            gaze: GazeData from Pupil Labs

        Returns:
            SimpleMapperResult with mapped gaze data
        """
        if len(self._surface_locations) == 0:
            return SimpleMapperResult({})

        # Undistort gaze point
        gaze_undistorted = self._camera.undistort_gaze((gaze.x, gaze.y))

        # Map gaze to each surface using homography
        mapped_gaze = {}
        for emission_id, homography in self._surface_locations.items():
            if homography is None:
                mapped_gaze[emission_id] = []
                continue

            # Project gaze to surface using CV2 homography and normalize
            surface_data = self._surfaces[emission_id]
            x, y = project_gaze_to_surface(gaze_undistorted, homography, surface_data['size'][0], surface_data['size'][1])

            mapped_gaze[emission_id] = [SimpleMappedGaze(emission_id, x, y, gaze)]

        return SimpleMapperResult(mapped_gaze)

    def clear_surfaces(self):
        """Clear all surfaces"""
        self._surfaces = {}
        self._surface_locations = {}

    def replace_surface(self, emission_id: int, new_marker_verts: dict, new_surface_size: tuple[float, float]) -> int:
        """Replace surface definition"""
        if emission_id in self._surfaces:
            self._surfaces[emission_id]['markers'] = new_marker_verts
            self._surfaces[emission_id]['size'] = new_surface_size
            # Clear cached location to force recalculation
            self._surface_locations.pop(emission_id, None)
            return emission_id
        return None

    @property
    def surfaces(self) -> Dict[int, dict]:
        """Get copy of surfaces dict"""
        return self._surfaces.copy()

    @property
    def detected_markers(self) -> List[DetectedMarker]:
        """Get detected markers"""
        return self._detected_markers.copy()