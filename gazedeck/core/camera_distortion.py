# gazedeck/core/camera_distortion.py
# Simple camera undistortion utilities

import cv2
import numpy as np
import numpy.typing as npt

class SimpleCamera:
    """
    Simplified camera class for undistortion operations.

    Takes camera_distortion dict with 'scene_camera_matrix' and 'scene_distortion_coefficients'
    """

    def __init__(self, camera_distortion: dict):
        self._matrix = np.array(camera_distortion['scene_camera_matrix']).reshape(3, 3)
        self._distortion = np.array(camera_distortion['scene_distortion_coefficients']).reshape(1, 8)

    def undistort_gaze(self, gaze: tuple[float, float]) -> tuple[float, float]:
        """
        Undistort a single gaze point.

        Args:
            gaze: (x, y) coordinates in distorted image space

        Returns:
            (x, y) coordinates in undistorted image space
        """
        undistorted = undistort_points(self._matrix, self._distortion, [gaze])
        return tuple(undistorted[0])

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
