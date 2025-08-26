"""AprilTag layout loader."""

import json
from pathlib import Path
from typing import Dict

import numpy as np


def load_markers(path: str | Path) -> Dict[int, np.ndarray]:
    """Load marker layout from JSON file.

    Args:
        path: Path to JSON file containing marker layout

    Returns:
        Dictionary mapping tag id to 4×2 numpy array of screen corners.
        Order is TL, TR, BR, BL.

    Raises:
        FileNotFoundError: If the layout file doesn't exist
        ValueError: If the layout format is invalid
    """
    path_obj = Path(path)

    if not path_obj.exists():
        raise FileNotFoundError(f"Marker layout file not found: {path}")

    with open(path_obj, "r") as f:
        data = json.load(f)

    if not isinstance(data, dict):
        raise ValueError("Marker layout must be a JSON object")

    markers = {}
    for tag_id_str, corners in data.items():
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
        raise ValueError("No valid markers found in layout file")

    return markers
