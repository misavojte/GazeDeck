# gazedeck/core/camera_distortion.py
# Simple camera undistortion utilities

import cv2
import numpy as np
import numpy.typing as npt

class CameraDistortion:
    """
    Simplified camera class for undistortion operations.

    Takes camera_distortion dict with 'scene_camera_matrix' and 'scene_distortion_coefficients'
    """

    def __init__(self, camera_distortion: dict):
        self._matrix = np.array(camera_distortion['scene_camera_matrix']).reshape(3, 3)
        self._distortion = np.array(camera_distortion['scene_distortion_coefficients']).reshape(1, 8)
        # Cache camera parameters for pose estimation [fx, fy, cx, cy]
        self._camera_params = [self._matrix[0,0], self._matrix[1,1], self._matrix[0,2], self._matrix[1,2]]

    def undistort_gaze(self, gaze: tuple[float, float]) -> tuple[float, float]:
        """
        Undistort a single gaze point.

        Args:
            gaze: (x, y) coordinates in distorted image space

        Returns:
            (x, y) coordinates in undistorted image space
        """
        # Optimized single-point undistortion - avoid list overhead
        undistorted = self.undistort_single_point(gaze)
        return undistorted

    def undistort_single_point(self, point: tuple[float, float]) -> tuple[float, float]:
        """
        Optimized undistortion for single point - avoids list creation and multiple reshapes.

        Args:
            point: (x, y) coordinates in distorted image space

        Returns:
            (x, y) coordinates in undistorted image space
        """
        # Create array directly for single point - more efficient than list conversion
        point_array = np.asarray([[point[0], point[1]]], dtype=np.float32).reshape(1, 1, 2)

        undistorted = cv2.undistortPoints(point_array, self._matrix, self._distortion, P=self._matrix)
        undistorted = undistorted.reshape(-1, 2)[0]  # Extract single point

        return tuple(undistorted)

    @property
    def camera_params(self) -> list[float]:
        """
        Get camera parameters for pose estimation [fx, fy, cx, cy].

        Returns:
            List of camera parameters [fx, fy, cx, cy]
        """
        return self._camera_params

    @property
    def matrix(self) -> npt.NDArray[np.float64]:
        """
        Get camera matrix.

        Returns:
            3x3 camera matrix
        """
        return self._matrix

    @property
    def distortion(self) -> npt.NDArray[np.float64]:
        """
        Get distortion coefficients.

        Returns:
            1x8 distortion coefficients
        """
        return self._distortion

    def undistort_points(self, points: list[tuple[float, float]]) -> npt.NDArray[np.float32]:
        """
        Undistort multiple points.

        Args:
            points: List of (x, y) tuples

        Returns:
            Array of undistorted points
        """
        return undistort_points(self._matrix, self._distortion, points)

def undistort_points(camera_matrix: npt.NDArray[np.float64],
                    distortion_coeffs: npt.NDArray[np.float64],
                    points: list[tuple[float, float]]) -> npt.NDArray[np.float32]:
    """
    Undistort points using camera distortion parameters.

    Args:
        camera_matrix: 3x3 camera matrix
        distortion_coeffs: 1x8 distortion coefficients
        points: List of (x, y) tuples

    Returns:
        Array of undistorted (x, y) coordinates
    """
    points_array = np.array(points, dtype=np.float32)

    if points_array.ndim == 1:
        points_array = points_array.reshape(-1, 2)
    if points_array.ndim == 2:
        points_array = points_array.reshape(-1, 1, 2)

    undistorted = cv2.undistortPoints(points_array, camera_matrix, distortion_coeffs, P=camera_matrix)
    undistorted = undistorted.reshape(-1, 2)
    return undistorted
