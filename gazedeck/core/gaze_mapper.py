# gazedeck/core/gaze_mapper.py
# Simplified gaze mapper using emission_ids and modular components

from typing import Dict, List, NamedTuple, Optional, Any    
from pupil_labs.realtime_api import GazeData
from pupil_labs.realtime_api.streaming import VideoFrame

from .camera_distortion import CameraDistortion
from .marker_detection import SimpleMarkerDetector, DetectedMarker
from .surface_tracking import track_surfaces, project_gaze_to_surface, SurfaceLocation

class MarkersToDetect(NamedTuple):
    """
    Representing markers of a specific size to detect.

    PERFORMANCE: Immutable for efficient caching and memory usage.
    """
    size: float  # Tag size in meters
    ids: tuple[int, ...]  # Tuple of tag IDs to detect for this size (no conversion needed)


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
        self._surface_locations = {}  # emission_id -> SurfaceLocation
        self._detected_markers: List[DetectedMarker] = []

        # PERFORMANCE: Pre-computed data structures for efficient processing
        # Updated during add_surface() - avoids expensive operations per frame
        self._markers_to_detect: List[MarkersToDetect] = []  # Markers grouped by size for detection

    def add_surface(self, tags: dict, surface_size: tuple[float, float],
                   emission_id: int) -> int:
        """
        Add surface using emission_id directly.

        Args:
            tags: Dict mapping tag_id -> TagInfo with size and corners
            surface_size: (width, height) in pixels
            emission_id: Integer surface ID for WebSocket transmission

        Returns:
            The emission_id used
        """
        # Convert TagInfo to the format expected by surface tracking
        converted_markers = {}
        tag_sizes = {}
        for tag_id, tag_info in tags.items():
            converted_markers[tag_id] = list(tag_info.corners)
            tag_sizes[tag_id] = tag_info.size

        self._surfaces[emission_id] = {
            'markers': converted_markers,
            'size': surface_size,
            'tag_sizes': tag_sizes
        }

        # PERFORMANCE: Update pre-computed data structures (construction-time optimization)
        # Group markers by size for efficient detection
        size_to_ids = {}
        for tag_id, tag_size in tag_sizes.items():
            if tag_size not in size_to_ids:
                size_to_ids[tag_size] = []
            size_to_ids[tag_size].append(tag_id)

        # Create MarkersToDetect objects and update the list
        for tag_size, tag_ids in size_to_ids.items():
            # Check if we already have this size
            existing_marker = None
            for marker in self._markers_to_detect:
                if marker.size == tag_size:
                    existing_marker = marker
                    break

            if existing_marker:
                # Update existing marker with additional IDs
                updated_ids = tuple(sorted(set(existing_marker.ids + tuple(tag_ids))))
                # Remove old and add updated
                self._markers_to_detect.remove(existing_marker)
                self._markers_to_detect.append(MarkersToDetect(size=tag_size, ids=updated_ids))
            else:
                # Add new marker
                self._markers_to_detect.append(MarkersToDetect(size=tag_size, ids=tuple(sorted(tag_ids))))

        return emission_id

    def process_scene(self, frame: VideoFrame):
        """Process video frame to detect markers and track surfaces"""
        if hasattr(frame, 'bgr_pixels'):
            frame_bgr = frame.bgr_pixels
        elif hasattr(frame, 'bgr_buffer'):
            frame_bgr = frame.bgr_buffer()

        # ULTRA OPTIMIZED: Multi-size detection with pre-computed data
        all_markers = []

        # Process each tag size with its specific IDs (pre-computed during construction)
        for markers_to_detect in self._markers_to_detect:
            try:
                # Detect markers for this specific size with immediate ID filtering
                size_markers = self._detector.detect_markers(
                    frame_bgr,
                    self._camera,
                    markers_to_detect.size,
                    markers_to_detect.ids  # Already a tuple, no conversion needed!
                )
                all_markers.extend(size_markers)
            except Exception:
                # If detection fails for a specific size, continue with others
                continue

        # Final deduplication by keeping highest confidence per tag ID
        unique_markers = {}
        for marker in all_markers:
            if marker.tag_id not in unique_markers or marker.confidence > unique_markers[marker.tag_id].confidence:
                unique_markers[marker.tag_id] = marker

        detected_markers = list(unique_markers.values())
        source_frame_timestamp = frame.timestamp_unix_seconds

        # Track surfaces using CV2 homography with pose validation
        self._surface_locations = track_surfaces(detected_markers, self._surfaces, source_frame_timestamp)

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
        for emission_id, surface_location in self._surface_locations.items():
            if surface_location.homography is None:
                mapped_gaze[emission_id] = []
                continue

            # Project gaze to surface using CV2 homography and normalize
            surface_data = self._surfaces[emission_id]
            x, y = project_gaze_to_surface(gaze_undistorted, surface_location.homography, surface_data['size'][0], surface_data['size'][1])

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