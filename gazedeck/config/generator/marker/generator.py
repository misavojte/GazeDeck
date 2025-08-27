"""AprilTag marker generator for GazeDeck."""

import json
import cv2
from pathlib import Path
from typing import Dict, List, Tuple


def generate_apriltag_markers(
    screen_width: int,
    screen_height: int,
    output_dir: Path,
    marker_size_px: int = 200,
    position: str = "inside",
    count: int = 4
) -> Dict:
    """Generate AprilTag markers and config for GazeDeck.

    Args:
        screen_width: Screen width in pixels
        screen_height: Screen height in pixels
        output_dir: Output directory for markers and config
        marker_size_px: Size of each marker in pixels
        position: "inside" for markers within screen bounds,
                 "outside" for markers adjacent to screen edges
        count: Number of markers to generate (4, 6, 8, or 10)

    Returns:
        Config dictionary compatible with GazeDeck's marker format
    """

    # Create output directory
    markers_dir = output_dir / "markers"
    markers_dir.mkdir(parents=True, exist_ok=True)

    # Get AprilTag dictionary
    apriltag_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)

    # Validate marker count
    if count not in [4, 6, 8, 10]:
        raise ValueError(f"Marker count must be 4, 6, 8, or 10. Got: {count}")

    # Calculate marker positions
    marker_positions = _calculate_marker_positions(
        screen_width, screen_height, marker_size_px, position, count
    )

    # Generate config
    config = {
        "plane_id": f"screen_{count}apriltag_{screen_width}x{screen_height}_{position}",
        "screen_width": screen_width,
        "screen_height": screen_height,
        "markers": {}
    }

    # Generate each marker
    for marker_id, corners in enumerate(marker_positions):
        # Generate AprilTag marker image
        marker_img = cv2.aruco.generateImageMarker(apriltag_dict, marker_id, marker_size_px)

        # Save as PNG
        output_path = markers_dir / f"{marker_id}.png"
        cv2.imwrite(str(output_path), marker_img)

        # Add to config (corners are already tuples)
        config["markers"][str(marker_id)] = list(corners)

    return config


def _calculate_marker_positions(
    screen_width: int,
    screen_height: int,
    marker_size_px: int,
    position: str,
    count: int
) -> List[List[Tuple[int, int]]]:
    """Calculate pixel positions for markers in logical layouts."""

    if position == "inside":
        return _calculate_inside_positions(screen_width, screen_height, marker_size_px, count)
    elif position == "outside":
        return _calculate_outside_positions(screen_width, screen_height, marker_size_px, count)
    else:
        raise ValueError(f"Invalid position: {position}. Must be 'inside' or 'outside'")


def _calculate_inside_positions(
    screen_width: int,
    screen_height: int,
    marker_size_px: int,
    count: int
) -> List[List[Tuple[int, int]]]:
    """Calculate positions for markers inside screen bounds."""

    positions = []

    # Always include corners (first 4 markers)
    positions.extend([
        # Top-left
        [(0, 0), (marker_size_px, 0), (marker_size_px, marker_size_px), (0, marker_size_px)],
        # Top-right
        [(screen_width - marker_size_px, 0), (screen_width, 0),
         (screen_width, marker_size_px), (screen_width - marker_size_px, marker_size_px)],
        # Bottom-left
        [(0, screen_height - marker_size_px), (marker_size_px, screen_height - marker_size_px),
         (marker_size_px, screen_height), (0, screen_height)],
        # Bottom-right
        [(screen_width - marker_size_px, screen_height - marker_size_px),
         (screen_width, screen_height - marker_size_px),
         (screen_width, screen_height), (screen_width - marker_size_px, screen_height)]
    ])

    if count >= 6:
        # Add top and bottom center markers
        positions.extend([
            # Top-center
            [(screen_width // 2 - marker_size_px // 2, 0),
             (screen_width // 2 + marker_size_px // 2, 0),
             (screen_width // 2 + marker_size_px // 2, marker_size_px),
             (screen_width // 2 - marker_size_px // 2, marker_size_px)],
            # Bottom-center
            [(screen_width // 2 - marker_size_px // 2, screen_height - marker_size_px),
             (screen_width // 2 + marker_size_px // 2, screen_height - marker_size_px),
             (screen_width // 2 + marker_size_px // 2, screen_height),
             (screen_width // 2 - marker_size_px // 2, screen_height)]
        ])

    if count >= 8:
        # Add left and right center markers
        positions.extend([
            # Left-center
            [(0, screen_height // 2 - marker_size_px // 2),
             (marker_size_px, screen_height // 2 - marker_size_px // 2),
             (marker_size_px, screen_height // 2 + marker_size_px // 2),
             (0, screen_height // 2 + marker_size_px // 2)],
            # Right-center
            [(screen_width - marker_size_px, screen_height // 2 - marker_size_px // 2),
             (screen_width, screen_height // 2 - marker_size_px // 2),
             (screen_width, screen_height // 2 + marker_size_px // 2),
             (screen_width - marker_size_px, screen_height // 2 + marker_size_px // 2)]
        ])

    if count >= 10:
        # Add diagonal markers in corners of center area
        center_margin = marker_size_px * 2
        positions.extend([
            # Top-left inner
            [(center_margin, center_margin),
             (center_margin + marker_size_px, center_margin),
             (center_margin + marker_size_px, center_margin + marker_size_px),
             (center_margin, center_margin + marker_size_px)],
            # Bottom-right inner
            [(screen_width - center_margin - marker_size_px, screen_height - center_margin - marker_size_px),
             (screen_width - center_margin, screen_height - center_margin - marker_size_px),
             (screen_width - center_margin, screen_height - center_margin),
             (screen_width - center_margin - marker_size_px, screen_height - center_margin)]
        ])

    return positions[:count]


def _calculate_outside_positions(
    screen_width: int,
    screen_height: int,
    marker_size_px: int,
    count: int
) -> List[List[Tuple[int, int]]]:
    """Calculate positions for markers outside screen bounds."""

    positions = []

    # Always include 4 edge markers
    positions.extend([
        # Top-center
        [(screen_width // 2 - marker_size_px // 2, -marker_size_px),
         (screen_width // 2 + marker_size_px // 2, -marker_size_px),
         (screen_width // 2 + marker_size_px // 2, 0),
         (screen_width // 2 - marker_size_px // 2, 0)],
        # Bottom-center
        [(screen_width // 2 - marker_size_px // 2, screen_height),
         (screen_width // 2 + marker_size_px // 2, screen_height),
         (screen_width // 2 + marker_size_px // 2, screen_height + marker_size_px),
         (screen_width // 2 - marker_size_px // 2, screen_height + marker_size_px)],
        # Left-center
        [(-marker_size_px, screen_height // 2 - marker_size_px // 2),
         (0, screen_height // 2 - marker_size_px // 2),
         (0, screen_height // 2 + marker_size_px // 2),
         (-marker_size_px, screen_height // 2 + marker_size_px // 2)],
        # Right-center
        [(screen_width, screen_height // 2 - marker_size_px // 2),
         (screen_width + marker_size_px, screen_height // 2 - marker_size_px // 2),
         (screen_width + marker_size_px, screen_height // 2 + marker_size_px // 2),
         (screen_width, screen_height // 2 + marker_size_px // 2)]
    ])

    if count >= 6:
        # Add corner markers outside screen
        positions.extend([
            # Top-left outside
            [(-marker_size_px, -marker_size_px), (0, -marker_size_px),
             (0, 0), (-marker_size_px, 0)],
            # Top-right outside
            [(screen_width, -marker_size_px), (screen_width + marker_size_px, -marker_size_px),
             (screen_width + marker_size_px, 0), (screen_width, 0)]
        ])

    if count >= 8:
        # Add bottom corner markers outside screen
        positions.extend([
            # Bottom-left outside
            [(-marker_size_px, screen_height), (0, screen_height),
             (0, screen_height + marker_size_px), (-marker_size_px, screen_height + marker_size_px)],
            # Bottom-right outside
            [(screen_width, screen_height), (screen_width + marker_size_px, screen_height),
             (screen_width + marker_size_px, screen_height + marker_size_px),
             (screen_width, screen_height + marker_size_px)]
        ])

    if count >= 10:
        # Add diagonal markers further out
        offset = marker_size_px * 2
        positions.extend([
            # Far top-left
            [(-offset - marker_size_px, -offset - marker_size_px),
             (-offset, -offset - marker_size_px),
             (-offset, -offset), (-offset - marker_size_px, -offset)],
            # Far bottom-right
            [(screen_width + offset, screen_height + offset),
             (screen_width + offset + marker_size_px, screen_height + offset),
             (screen_width + offset + marker_size_px, screen_height + offset + marker_size_px),
             (screen_width + offset, screen_height + offset + marker_size_px)]
        ])

    return positions[:count]


def save_config(config: Dict, output_path: Path) -> None:
    """Save marker config as JSON."""
    with open(output_path, 'w') as f:
        json.dump(config, f, indent=2)
