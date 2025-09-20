# gazedeck/core/marker_detection.py
# Simplified AprilTag detection

import cv2
import numpy as np
import numpy.typing as npt
import pupil_apriltags
from typing import List, Dict, Any, Optional

TAG_FAMILY = "tag36h11"

class SimpleMarkerDetector:
    """
    Simplified AprilTag detector that returns clean marker data.
    """

    def __init__(self, apriltag_params: Optional[Dict[str, Any]] = None):
        params = apriltag_params or {}
        self._detector = pupil_apriltags.Detector(
            families=TAG_FAMILY,
            nthreads=params.get('nthreads', 1),
            quad_decimate=params.get('quad_decimate', 0.5),
            decode_sharpening=params.get('decode_sharpening', 0.25),
            quad_sigma=params.get('quad_sigma', 0.5),
            debug=params.get('debug', 0),
            refine_edges=params.get('refine_edges', 1),
        )

    def detect_markers(self, image: npt.NDArray[np.uint8], camera_distortion) -> List[Dict]:
        """
        Detect AprilTag markers and return simplified format.

        Args:
            image: BGR image array
            camera_distortion: CameraDistortion instance for undistortion

        Returns:
            List of marker dictionaries with:
            - 'id': tag ID (int)
            - 'corners': list of (x, y) tuples (undistorted)
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return self.detect_from_gray(gray, camera_distortion)

    def detect_from_gray(self, gray: npt.NDArray[np.uint8], camera_distortion) -> List[Dict]:
        """
        Detect markers from grayscale image.

        Args:
            gray: Grayscale image array
            camera_distortion: CameraDistortion instance for undistortion

        Returns:
            List of marker dictionaries
        """
        markers = self._detector.detect(gray)

        # Deduplicate markers by ID, keeping the one with highest confidence
        unique_markers = {}
        for marker in markers:
            tag_id = marker.tag_id
            if tag_id not in unique_markers or marker.decision_margin > unique_markers[tag_id].decision_margin:
                unique_markers[tag_id] = marker

        # Convert to simple dict format
        result = []
        for marker in unique_markers.values():
            # Extract corners and undistort them
            corners = [[point[0], point[1]] for point in marker.corners]
            undistorted_corners = camera_distortion.undistort_points(corners)

            result.append({
                'id': marker.tag_id,
                'corners': undistorted_corners.tolist()
            })

        return result
