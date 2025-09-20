# gazedeck/core/surface_tracking.py
# CV2-based surface tracking using homography

import cv2
import numpy as np
from typing import List, Dict, Optional

def calculate_surface_homography(detected_markers: List[Dict], surface_data: Dict) -> Optional[np.ndarray]:
    """
    Calculate homography matrix for surface using detected markers.

    Args:
        detected_markers: List of detected markers with 'id' and 'corners'
        surface_data: Surface definition with 'markers' mapping tag_id -> corners

    Returns:
        3x3 homography matrix or None if insufficient markers detected
    """
    # Extract marker corners for this surface
    # Collect all corresponding point pairs
    all_marker_points = []
    all_surface_points = []

    for marker in detected_markers:
        tag_id = marker['id']
        if tag_id in surface_data['markers']:
            # Get corresponding points for this marker
            marker_corners = marker['corners']  # List of (x, y) tuples
            surface_corners = surface_data['markers'][tag_id]  # List of (x, y) tuples

            if len(marker_corners) == len(surface_corners):
                all_marker_points.extend(marker_corners)
                all_surface_points.extend(surface_corners)

    if len(all_marker_points) < 1:  # Need at least 1 point
        return None

    # Convert to numpy arrays with correct shape for cv2.findHomography
    marker_points = np.array(all_marker_points, dtype=np.float32)  # Shape: (N, 2)
    surface_points = np.array(all_surface_points, dtype=np.float32)  # Shape: (N, 2)

    # Calculate homography matrix
    homography, mask = cv2.findHomography(marker_points, surface_points)
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
    if homography is None:
        return 0.5, 0.5  # Default to center

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

def track_surfaces(detected_markers: List[Dict], surface_definitions: Dict[int, Dict]) -> Dict[int, Optional[np.ndarray]]:
    """
    Track surfaces by calculating homography for each surface.

    Args:
        detected_markers: List of detected markers
        surface_definitions: Dict mapping emission_id -> surface_data

    Returns:
        Dict mapping emission_id -> homography_matrix (or None)
    """
    locations = {}
    for emission_id, surface_data in surface_definitions.items():
        homography = calculate_surface_homography(detected_markers, surface_data)
        locations[emission_id] = homography

    return locations
