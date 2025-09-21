# gazedeck/core/marker_detection.py
# Simplified AprilTag detection

import cv2
import numpy as np
import numpy.typing as npt
import pupil_apriltags
from typing import List, Dict, Any, Optional
from typing import Tuple, NamedTuple

from gazedeck.core.camera_distortion import CameraDistortion

class DetectedMarker(NamedTuple):
    """
    Detected marker results with type safety, no pose or size data.
    Pose will be computed in the next dev step.
    Args:
        tag_id: Unique marker ID
        corners: List of (x, y) corner coordinates (undistorted)
        confidence: Detection confidence score (decision_margin from AprilTag)
        original_corners: List of (x, y) corner coordinates (original distorted) for visualization
    """
    tag_id: int
    corners: Tuple[Tuple[float, float], ...]
    confidence: float
    original_corners: Tuple[Tuple[float, float], ...]

TAG_FAMILY = "tag36h11"

class SimpleMarkerDetector:
    """
    Simplified AprilTag detector that returns clean marker data without pose, size, or ID filtering.
    """

    def __init__(self, apriltag_params: Optional[Dict[str, Any]] = None):
        params = apriltag_params or {}
        self._detector = pupil_apriltags.Detector(
            families=TAG_FAMILY,
            nthreads=params.get('nthreads', 1),
            quad_decimate=params.get('quad_decimate', 0.5),
            decode_sharpening=params.get('decode_sharpening', 0.25),
            quad_sigma=params.get('quad_sigma', 0.0),
            debug=params.get('debug', 0),
            refine_edges=params.get('refine_edges', 1),
        )

    def detect_markers(self, image: npt.NDArray[np.uint8], camera_distortion) -> List[DetectedMarker]:
        """
        Detect AprilTag markers.

        Args:
            image: BGR image array
            camera_distortion: CameraDistortion instance for undistortion

        Returns:
            List of DetectedMarker instances
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return self.detect_from_gray(gray, camera_distortion)

    def detect_from_gray(self, gray: npt.NDArray[np.uint8], camera_distortion: CameraDistortion) -> List[DetectedMarker]:
        """
        Detect markers from grayscale image.

        Args:
            gray: Grayscale image array
            camera_distortion: CameraDistortion instance for undistortion

        Returns:
            List of DetectedMarker instances
        """
        # Detect markers
        markers = self._detector.detect(gray)
        
        if not markers:
            return []

        # Batch undistort all corners at once for better performance
        all_corners = [marker.corners for marker in markers]
        all_undistorted = camera_distortion.undistort_points(all_corners)
        
        # Process all detected markers
        result = []
        for i, marker in enumerate(markers):
            # Extract corners and undistort them
            # IMPORTANT!!!
            # AprilTag detectors return corners that wrap counter-clock wise around the tag.
            # 0 bottom-left
            # 1 bottom-right
            # 2 top-right
            # 3 top-left
            # no need to reorder them!!!
            undistorted_corners = all_undistorted[i * 4:(i + 1) * 4]

            result.append(DetectedMarker(
                tag_id=marker.tag_id,
                corners=tuple(tuple(corner) for corner in undistorted_corners),
                confidence=marker.decision_margin,
                original_corners=tuple(tuple(corner) for corner in marker.corners)
            ))

        return result
