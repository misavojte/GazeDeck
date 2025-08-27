"""AprilTag layout loader."""

import json
from pathlib import Path
from typing import Dict, NamedTuple

import numpy as np


class ScreenConfig(NamedTuple):
    """Configuration for a screen plane with AprilTags."""
    plane_id: str
    screen_width: int
    screen_height: int
    markers: Dict[int, np.ndarray]


def load_screen_config(path: str | Path) -> ScreenConfig:
    """Load screen configuration from JSON file.

    Args:
        path: Path to JSON file containing screen configuration

    Returns:
        ScreenConfig object containing plane_id, screen dimensions, and markers

    Raises:
        FileNotFoundError: If the layout file doesn't exist
        ValueError: If the layout format is invalid
    """
    path_obj = Path(path)

    if not path_obj.exists():
        raise FileNotFoundError(f"Screen config file not found: {path}")

    with open(path_obj, "r") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Screen config must be a JSON object")

    # Parse required fields
    if "plane_id" not in data:
        raise ValueError("Screen config must contain 'plane_id'")
    if "screen_width" not in data:
        raise ValueError("Screen config must contain 'screen_width'")
    if "screen_height" not in data:
        raise ValueError("Screen config must contain 'screen_height'")
    if "markers" not in data:
        raise ValueError("Screen config must contain 'markers'")

    plane_id = str(data["plane_id"])
    screen_width = int(data["screen_width"])
    screen_height = int(data["screen_height"])

    if screen_width <= 0 or screen_height <= 0:
        raise ValueError("Screen dimensions must be positive integers")

    # Parse markers
    markers_data = data["markers"]
    if not isinstance(markers_data, dict):
        raise ValueError("Markers must be a JSON object")

    markers = {}
    for tag_id_str, corners in markers_data.items():
        try:
            tag_id = int(tag_id_str)
        except ValueError:
            raise ValueError(f"Tag ID must be an integer: {tag_id_str}")

        if not isinstance(corners, list) or len(corners) != 4:
            raise ValueError(f"Tag {tag_id} must have exactly 4 corners")

        # Convert to numpy array and validate each corner
        corners_array = []
        for i, corner in enumerate(corners):
            if not isinstance(corner, list) or len(corner) != 2:
                raise ValueError(f"Corner {i} of tag {tag_id} must be [x, y]")

            try:
                x, y = float(corner[0]), float(corner[1])
                corners_array.append([x, y])
            except (ValueError, TypeError):
                raise ValueError(f"Corner coordinates must be numbers: {corner}")

        markers[tag_id] = np.array(corners_array, dtype=np.float32)

    if not markers:
        raise ValueError("No valid markers found in config file")

    return ScreenConfig(
        plane_id=plane_id,
        screen_width=screen_width,
        screen_height=screen_height,
        markers=markers
    )



