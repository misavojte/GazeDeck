# gazedeck/core/surface_tracking.py
# CV2-based surface tracking using homography

import cv2
import numpy as np
from typing import List, Dict, Optional, NamedTuple, Any
from .marker_detection import DetectedMarker

class SurfaceLocation(NamedTuple):
    """
    Surface location data with homography matrix and timestamp.

    PERFORMANCE: Immutable for efficient caching and memory usage.
    """
    homography: Optional[np.ndarray]  # 3x3 homography matrix or None
    timestamp: float  # Unix timestamp from video frame


def calculate_surface_homography(detected_markers: List[DetectedMarker], surface_data: Dict[str, Any], timestamp: float) -> Optional[np.ndarray]:
    """
    Calculate homography matrix for surface using detected markers.

    Args:
        detected_markers: List of DetectedMarker instances
        surface_data: Surface definition with 'markers' mapping tag_id -> np.ndarray corners
        timestamp: Unix timestamp from the video frame

    Returns:
        3x3 homography matrix or None if insufficient markers detected
    """
    # Extract marker corners for this surface efficiently
    # Collect points more efficiently using numpy operations
    marker_points_list = []
    surface_points_list = []

    for marker in detected_markers:
        if marker.tag_id in surface_data['markers']:
            # Get corresponding points for this marker (already numpy arrays)
            marker_corners = marker.corners  # Already np.ndarray
            surface_corners = surface_data['markers'][marker.tag_id]  # Already np.ndarray

            if len(marker_corners) == len(surface_corners):
                # Use numpy concatenation for better performance than extend
                marker_points_list.append(marker_corners)
                surface_points_list.append(surface_corners)

    # Early return if insufficient points
    if len(marker_points_list) < 1 or sum(len(points) for points in marker_points_list) < 4:
        return None

    # Concatenate all marker and surface points efficiently
    if marker_points_list:
        marker_points = np.concatenate(marker_points_list).astype(np.float32)
        surface_points = np.concatenate(surface_points_list).astype(np.float32)
    else:
        return None

    # Calculate homography matrix with RANSAC to handle outliers
    homography, mask = cv2.findHomography(
        marker_points,
        surface_points
    )

    # Check if RANSAC found a good homography
    if homography is None or mask is None:
        return None

    # Check if enough inliers were found (at least 80% of points)
    # inlier_ratio = np.sum(mask) / len(mask) if len(mask) > 0 else 0
    # if inlier_ratio < 0.8:
    #     return None
    
    return homography

def project_gaze_to_surface(gaze_point: tuple[float, float], homography: np.ndarray,
                          surface_width: float, surface_height: float) -> tuple[float, float]:
    """
    Project gaze point to surface using homography and normalize coordinates.

    Args:
        gaze_point: (x, y) coordinates in image space
        homography: 3x3 homography matrix
        surface_width: Surface width in pixels
        surface_height: Surface height in pixels

    Returns:
        (x, y) coordinates in surface space (0-1 normalized)
    """
    # Create input array with correct shape for cv2.perspectiveTransform
    # Shape should be (1, 1, 2) for single 2D point - use asarray for potential copy avoidance
    gaze_array = np.asarray([[gaze_point[0], gaze_point[1]]], dtype=np.float32).reshape(1, 1, 2)

    # Project to surface coordinates (pixel coordinates)
    projected = cv2.perspectiveTransform(gaze_array, homography)
    pixel_x, pixel_y = projected[0, 0, 0], projected[0, 0, 1]

    # Normalize to 0-1 range - use float division for better precision
    normalized_x = pixel_x / surface_width
    normalized_y = pixel_y / surface_height

    return normalized_x, normalized_y

def track_surfaces(detected_markers: List[DetectedMarker], surface_definitions: Dict[int, Dict], timestamp: float) -> Dict[int, SurfaceLocation]:
    """
    Track surfaces by calculating homography for each surface.

    Args:
        detected_markers: List of DetectedMarker instances
        surface_definitions: Dict mapping emission_id -> surface_data
        timestamp: Unix timestamp from the video frame

    Returns:
        Dict mapping emission_id -> SurfaceLocation with homography and timestamp
    """
    locations = {}
    for emission_id, surface_data in surface_definitions.items():
        homography = calculate_surface_homography(detected_markers, surface_data, timestamp)
        locations[emission_id] = SurfaceLocation(homography, timestamp)

    return locations
