"""AprilTag marker generator for GazeDeck."""

import json
import cv2
from pathlib import Path
from typing import Dict, List, Tuple


def check_marker_conflicts(positions: List[List[Tuple[int, int]]], marker_size_px: int) -> List[str]:
    """Check for marker overlaps and return conflict descriptions."""
    conflicts = []

    for i, marker_a in enumerate(positions):
        # Get bounding box for marker A
        ax_coords = [p[0] for p in marker_a]
        ay_coords = [p[1] for p in marker_a]
        ax1, ax2 = min(ax_coords), max(ax_coords)
        ay1, ay2 = min(ay_coords), max(ay_coords)

        for j, marker_b in enumerate(positions):
            if i >= j:  # Skip self-comparison and duplicate checks
                continue

            # Get bounding box for marker B
            bx_coords = [p[0] for p in marker_b]
            by_coords = [p[1] for p in marker_b]
            bx1, bx2 = min(bx_coords), max(bx_coords)
            by1, by2 = min(by_coords), max(by_coords)

            # Check for overlap (with small tolerance for edge touching)
            tolerance = 2
            if not (ax2 + tolerance < bx1 or bx2 + tolerance < ax1 or
                    ay2 + tolerance < by1 or by2 + tolerance < ay1):
                conflicts.append(f"Markers {i} and {j} overlap! "
                               f"Marker {i}: ({ax1},{ay1}) to ({ax2},{ay2}), "
                               f"Marker {j}: ({bx1},{by1}) to ({bx2},{by2})")

    return conflicts


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

    # Check for marker conflicts before generating
    conflicts = check_marker_conflicts(marker_positions, marker_size_px)
    if conflicts:
        conflict_msg = f"❌ MARKER CONFLICTS DETECTED ({len(conflicts)} conflicts):\n" + "\n".join(conflicts)
        raise ValueError(f"Cannot generate markers due to conflicts:\n{conflict_msg}")

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
    """Calculate positions for markers INSIDE bounds but ALONG EDGES, evenly spaced, no overlaps.

    Layout rules (edge-only):
      - 4: corners
      - 6: corners + centers on the two shorter-side edges
      - 8: (6-layout) + centers on the two longer-side edges
      - 10: (8-layout) + one extra on each longer-side edge between corner and center, with equal gaps
    """

    def rect(x: int, y: int) -> List[Tuple[int, int]]:
        return [
            (x, y),
            (x + marker_size_px, y),
            (x + marker_size_px, y + marker_size_px),
            (x, y + marker_size_px),
        ]

    # Determine which side is longer
    is_width_longer = screen_width >= screen_height

    positions: List[List[Tuple[int, int]]] = []

    # 1) Corners
    positions.extend([
        rect(0, 0),  # top-left
        rect(screen_width - marker_size_px, 0),  # top-right
        rect(0, screen_height - marker_size_px),  # bottom-left
        rect(screen_width - marker_size_px, screen_height - marker_size_px),  # bottom-right
    ])

    if count <= 4:
        return positions[:count]

    # Helper: place centers on a pair of opposite edges
    def place_centers_on_horizontal_edges():
        cx = screen_width // 2 - marker_size_px // 2
        positions.append(rect(cx, 0))  # top-center
        positions.append(rect(cx, screen_height - marker_size_px))  # bottom-center

    def place_centers_on_vertical_edges():
        cy = screen_height // 2 - marker_size_px // 2
        positions.append(rect(0, cy))  # left-center
        positions.append(rect(screen_width - marker_size_px, cy))  # right-center

    # 2) Add centers on shorter-side edges for 6
    if count >= 6:
        if is_width_longer:
            # Shorter side is height -> LEFT and RIGHT centers
            place_centers_on_vertical_edges()
        else:
            # Shorter side is width -> TOP and BOTTOM centers
            place_centers_on_horizontal_edges()

    # 3) Add centers on longer-side edges for 8
    if count >= 8:
        if is_width_longer:
            # Longer side is width -> TOP and BOTTOM centers
            place_centers_on_horizontal_edges()
        else:
            # Longer side is height -> LEFT and RIGHT centers
            place_centers_on_vertical_edges()

    # 4) For 10, place TWO markers per longer edge with equal gaps to corners and between them
    if count >= 10:
        if is_width_longer:
            # Longer edges are TOP and BOTTOM.
            # Remove the top/bottom centers added at the 8-markers step (last two entries)
            positions = positions[:-2]

            # Within the interval between corner markers along top/bottom edges (length = W - 2*msz),
            # place 2 markers with 3 equal gaps (edge-to-first, between, second-to-edge)
            LA = screen_width - 2 * marker_size_px
            if LA < 2 * marker_size_px:
                raise ValueError("Screen too small for any markers along horizontal edges.")
            # Need space for 2 markers and 3 gaps: 2*msz + 3*g = LA
            remaining = LA - 2 * marker_size_px
            if remaining < 0:
                raise ValueError("Markers too large for horizontal edge placement.")
            gap = remaining // 3
            if gap <= 0:
                raise ValueError("Markers too large or screen too small to evenly place 2 per horizontal edge.")
            x_left = marker_size_px + gap
            x_right = x_left + marker_size_px + gap

            # Top edge extras
            positions.append(rect(x_left, 0))
            positions.append(rect(x_right, 0))
            # Bottom edge extras
            positions.append(rect(x_left, screen_height - marker_size_px))
            positions.append(rect(x_right, screen_height - marker_size_px))
        else:
            # Longer edges are LEFT and RIGHT.
            # Remove the left/right centers added at the 8-markers step (last two entries)
            positions = positions[:-2]

            LA = screen_height - 2 * marker_size_px
            if LA < 2 * marker_size_px:
                raise ValueError("Screen too small for any markers along vertical edges.")
            remaining = LA - 2 * marker_size_px
            if remaining < 0:
                raise ValueError("Markers too large for vertical edge placement.")
            gap = remaining // 3
            if gap <= 0:
                raise ValueError("Markers too large or screen too small to evenly place 2 per vertical edge.")
            y_top = marker_size_px + gap
            y_bottom = y_top + marker_size_px + gap

            # Left edge extras
            positions.append(rect(0, y_top))
            positions.append(rect(0, y_bottom))
            # Right edge extras
            positions.append(rect(screen_width - marker_size_px, y_top))
            positions.append(rect(screen_width - marker_size_px, y_bottom))

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


def test_marker_layout(screen_width: int, screen_height: int, marker_size_px: int, count: int) -> Dict:
    """Test marker layout and return detailed information."""
    marker_positions = _calculate_inside_positions(screen_width, screen_height, marker_size_px, count)
    conflicts = check_marker_conflicts(marker_positions, marker_size_px)

    # Calculate coverage and spacing
    total_area = screen_width * screen_height
    marker_area = marker_size_px * marker_size_px * len(marker_positions)
    coverage_percentage = (marker_area / total_area) * 100

    return {
        "screen_size": f"{screen_width}x{screen_height}",
        "marker_size": marker_size_px,
        "marker_count": len(marker_positions),
        "conflicts": conflicts,
        "conflict_count": len(conflicts),
        "coverage_percentage": round(coverage_percentage, 2),
        "positions": marker_positions
    }


def print_marker_analysis():
    """Print analysis of marker layouts for different configurations."""
    test_configs = [
        (1080, 720, 150, 10),   # Original config
        (1920, 1080, 150, 10),  # Full HD
        (2560, 1440, 200, 10),  # Wide screen
        (720, 1080, 150, 10),   # Portrait
        (1080, 720, 100, 10),   # Smaller markers
        (1080, 720, 200, 8),    # Larger markers, fewer count
    ]

    print("🔍 MARKER LAYOUT ANALYSIS")
    print("=" * 60)

    for screen_width, screen_height, marker_size, count in test_configs:
        result = test_marker_layout(screen_width, screen_height, marker_size, count)

        print(f"\n📐 {result['screen_size']} - {marker_size}px markers - {result['marker_count']} markers")
        print(f"   Coverage: {result['coverage_percentage']}%")
        print(f"   Conflicts: {result['conflict_count']}")

        if result['conflicts']:
            for conflict in result['conflicts']:
                print(f"   ❌ {conflict}")
        else:
            print("   ✅ NO CONFLICTS - Perfect layout!")


if __name__ == "__main__":
    print_marker_analysis()
