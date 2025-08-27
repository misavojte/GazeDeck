"""Geometry utilities for homography transformations."""

import cv2
import numpy as np


def apply_homography(img_xy: tuple[float, float], H: list[list[float]]) -> tuple[float, float]:
    """Apply homography transformation to convert image coordinates to screen coordinates.

    Args:
        img_xy: Image coordinates (x, y) in pixels
        H: 3x3 homography matrix as list of lists

    Returns:
        Screen coordinates (x, y) in pixels
    """
    x, y = img_xy

    # Convert to homogeneous coordinates
    img_point = np.array([[x], [y], [1]], dtype=np.float32)

    # Convert H to numpy array
    H_np = np.array(H, dtype=np.float32)

    # Apply homography transformation
    screen_point = H_np @ img_point

    # Convert back from homogeneous coordinates
    screen_x = float(screen_point[0, 0] / screen_point[2, 0])
    screen_y = float(screen_point[1, 0] / screen_point[2, 0])

    return (screen_x, screen_y)


def undistort_points(
    points_xy: list[tuple[float, float]] | np.ndarray,
    K: list[list[float]] | np.ndarray,
    D: list[float] | np.ndarray,
) -> np.ndarray:
    """Undistort 2D points given camera intrinsics and distortion coefficients.

    Args:
        points_xy: List/array of (x, y) image points in pixels
        K: 3x3 camera intrinsic matrix
        D: Distortion coefficients (OpenCV order: k1,k2,p1,p2,k3,k4,k5,k6,...) 

    Returns:
        Array of undistorted points in pixels with shape (N, 2)
    """
    pts = np.asarray(points_xy, dtype=np.float32).reshape(-1, 1, 2)
    K_np = np.asarray(K, dtype=np.float32).reshape(3, 3)
    D_np = np.asarray(D, dtype=np.float32).reshape(-1)

    # Use the same K for output to keep pixel coordinates
    undistorted = cv2.undistortPoints(pts, K_np, D_np, P=K_np)
    return undistorted.reshape(-1, 2)