# gazedeck/core/surface_tracking.py
# CV2-based surface tracking using homography

import cv2
import numpy as np
from typing import List, Dict, Optional, NamedTuple
from .marker_detection import DetectedMarker

class SurfaceLocation(NamedTuple):
    """
    Surface location data with homography matrix and timestamp.

    PERFORMANCE: Immutable for efficient caching and memory usage.
    """
    homography: Optional[np.ndarray]  # 3x3 homography matrix or None
    timestamp: float  # Unix timestamp from video frame

def _reorder_corners_top_left_ccw(corners: list) -> list:
    """
    Ensure corners start at top-left and are ordered counter-clockwise.
    This makes detected and defined corners comparable regardless of rotation.
    """
    if len(corners) != 4:
        return corners
    # Compute centroid
    cx = sum(p[0] for p in corners) / 4.0
    cy = sum(p[1] for p in corners) / 4.0
    # Compute angles from centroid
    pts_with_angle = []
    for (x, y) in corners:
        angle = np.arctan2(y - cy, x - cx)
        pts_with_angle.append(((x, y), angle))
    # Sort CCW by angle
    pts_with_angle.sort(key=lambda t: t[1])
    ccw = [p for (p, _) in pts_with_angle]
    # Find top-left (min y, then min x)
    top_left_idx = min(range(4), key=lambda i: (ccw[i][1], ccw[i][0]))
    # Rotate so it starts at top-left
    ordered = ccw[top_left_idx:] + ccw[:top_left_idx]
    return ordered

def calculate_surface_homography(detected_markers: List[DetectedMarker], surface_data: Dict, timestamp: float) -> Optional[np.ndarray]:
    """
    Calculate homography matrix for surface using detected markers.

    Args:
        detected_markers: List of DetectedMarker instances
        surface_data: Surface definition with 'markers' mapping tag_id -> corners
        timestamp: Unix timestamp from the video frame

    Returns:
        3x3 homography matrix or None if insufficient markers detected
    """
    # Extract marker corners for this surface
    all_marker_points = []
    all_surface_points = []

    for marker in detected_markers:
        if marker.tag_id in surface_data['markers']:
            # Get corresponding points for this marker
            marker_corners = _reorder_corners_top_left_ccw(list(marker.corners))
            surface_corners = _reorder_corners_top_left_ccw(list(surface_data['markers'][marker.tag_id]))

            if len(marker_corners) == len(surface_corners):
                all_marker_points.extend(marker_corners)
                all_surface_points.extend(surface_corners)

    # STRICT: Need at least 4 corresponding point pairs for reliable homography
    if len(all_marker_points) < 4:
        return None

    # Convert to numpy arrays with correct shape for cv2.findHomography
    marker_points = np.array(all_marker_points, dtype=np.float32)  # Shape: (N, 2)
    surface_points = np.array(all_surface_points, dtype=np.float32)  # Shape: (N, 2)

    # Calculate homography matrix with RANSAC to handle outliers
    homography, mask = cv2.findHomography(
        marker_points,
        surface_points,
        method=cv2.RANSAC,
        ransacReprojThreshold=2.0,
        maxIters=1000,
        confidence=0.995
    )

    # Check if RANSAC found a good homography
    if homography is None or mask is None:
        return None

    # Check if enough inliers were found (at least 80% of points)
    inlier_ratio = np.sum(mask) / len(mask) if len(mask) > 0 else 0
    if inlier_ratio < 0.8:
        return None
    
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
    # Shape should be (1, 1, 2) for single 2D point
    gaze_array = np.array([[gaze_point[0], gaze_point[1]]], dtype=np.float32).reshape(1, 1, 2)

    # Project to surface coordinates (pixel coordinates)
    projected = cv2.perspectiveTransform(gaze_array, homography)
    pixel_x, pixel_y = projected[0, 0, 0], projected[0, 0, 1]

    # Normalize to 0-1 range
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
