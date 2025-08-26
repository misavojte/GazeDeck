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
    screen_x = screen_point[0, 0] / screen_point[2, 0]
    screen_y = screen_point[1, 0] / screen_point[2, 0]

    return (screen_x, screen_y)
