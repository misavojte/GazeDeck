# gazedeck/core/marker_detection.py
# Simplified AprilTag detection

import cv2
import numpy as np
import numpy.typing as npt
import pupil_apriltags
from typing import List, Dict, Any, Optional
from typing import Tuple, NamedTuple

class DetectedMarker(NamedTuple):
    """
   Detected marker results with type safety and mandatory 3D pose.

    Args:
        tag_id: Unique marker ID
        corners: List of (x, y) corner coordinates (undistorted)
        confidence: Detection confidence score (decision_margin from AprilTag)
        pose_R: Rotation matrix (3x3)
        pose_t: Translation vector (3x1)
        pose_err: Pose estimation error
    """
    tag_id: int
    corners: Tuple[Tuple[float, float], ...]
    confidence: float
    pose_R: np.ndarray
    pose_t: np.ndarray
    pose_err: float

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
            quad_sigma=params.get('quad_sigma', 0.0),
            debug=params.get('debug', 0),
            refine_edges=params.get('refine_edges', 1),
        )

    def detect_markers(self, image: npt.NDArray[np.uint8], camera_distortion, tag_size: float, expected_tag_ids: Optional[tuple[int, ...]] = None) -> List[DetectedMarker]:
        """
        Detect AprilTag markers for a specific tag size, filtering by expected IDs.

        PERFORMANCE OPTIMIZED: Only detects markers of specified size and filters by expected IDs immediately.

        Args:
            image: BGR image array
            camera_distortion: CameraDistortion instance for undistortion
            tag_size: Tag size in meters for detection (REQUIRED)
            expected_tag_ids: Optional tuple of expected tag IDs to filter immediately (no conversion needed)

        Returns:
            List of DetectedMarker instances with mandatory pose data for expected IDs only
        """
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return self.detect_from_gray(gray, camera_distortion, tag_size, expected_tag_ids)

    def detect_from_gray(self, gray: npt.NDArray[np.uint8], camera_distortion, tag_size: float, expected_tag_ids: Optional[tuple[int, ...]] = None) -> List[DetectedMarker]:
        """
        Detect markers from grayscale image with mandatory 3D pose estimation.

        PERFORMANCE OPTIMIZED: Filters by expected tag IDs immediately and only processes relevant markers.

        Args:
            gray: Grayscale image array
            camera_distortion: CameraDistortion instance for undistortion
            tag_size: Tag size in meters for detection (REQUIRED)
            expected_tag_ids: Optional tuple of expected tag IDs to filter immediately (no conversion needed)

        Returns:
            List of DetectedMarker instances with mandatory pose data for expected IDs only
        """
        # Convert expected_tag_ids to set for O(1) lookup (one-time conversion)
        expected_ids_set = set(expected_tag_ids) if expected_tag_ids else None

        # Get cached camera parameters for pose estimation [fx, fy, cx, cy]
        camera_params = camera_distortion.camera_params

        # PERFORMANCE: Detect with specific tag size and filter immediately
        markers = self._detector.detect(gray, estimate_tag_pose=True, camera_params=camera_params, tag_size=tag_size)

        # PERFORMANCE: Process markers in place, filter early
        result = []
        for marker in markers:
            tag_id = marker.tag_id

            # EARLY EXIT: Skip markers not in expected IDs
            if expected_ids_set is not None and tag_id not in expected_ids_set:
                continue

            # Skip markers without valid pose estimation
            if not hasattr(marker, 'pose_R') or marker.pose_R is None:
                continue

            # Extract corners and undistort them
            corners = [[point[0], point[1]] for point in marker.corners]
            undistorted_corners = camera_distortion.undistort_points(corners)

            result.append(DetectedMarker(
                tag_id=marker.tag_id,
                corners=tuple(tuple(corner) for corner in undistorted_corners.tolist()),
                confidence=marker.decision_margin,
                pose_R=marker.pose_R,
                pose_t=marker.pose_t,
                pose_err=marker.pose_err
            ))

        return result
