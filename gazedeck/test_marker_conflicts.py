#!/usr/bin/env python3
"""Test script to verify marker layout conflicts are prevented."""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'config/generator/marker'))

from generator import _calculate_inside_positions, check_marker_conflicts

def test_marker_layout(screen_width: int, screen_height: int, marker_size_px: int, count: int):
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

    print("🔍 MARKER LAYOUT ANALYSIS - CONFLICT PREVENTION TEST")
    print("=" * 70)

    all_passed = True

    for screen_width, screen_height, marker_size, count in test_configs:
        result = test_marker_layout(screen_width, screen_height, marker_size, count)

        print(f"\n📐 {result['screen_size']} - {marker_size}px markers - {result['marker_count']} markers")
        print(f"   Coverage: {result['coverage_percentage']}%")
        print(f"   Conflicts: {result['conflict_count']}")

        if result['conflicts']:
            all_passed = False
            for conflict in result['conflicts']:
                print(f"   ❌ {conflict}")
        else:
            print("   ✅ NO CONFLICTS - Perfect layout!")

        # Show marker positions for first config
        if screen_width == 1080 and screen_height == 720 and marker_size == 150:
            print("   📍 Marker positions:")
            for i, pos in enumerate(result['positions']):
                x_coords = [p[0] for p in pos]
                y_coords = [p[1] for p in pos]
                x1, x2 = min(x_coords), max(x_coords)
                y1, y2 = min(y_coords), max(y_coords)
                print(f"      Marker {i}: ({x1},{y1}) to ({x2},{y2})")

    print("\n" + "=" * 70)
    if all_passed:
        print("🎉 SUCCESS: All marker layouts are conflict-free!")
        print("✅ The new algorithm properly distributes markers with pravidelné spacing!")
    else:
        print("❌ FAILURE: Some layouts still have conflicts that need to be fixed.")

    return all_passed

if __name__ == "__main__":
    success = print_marker_analysis()
    sys.exit(0 if success else 1)
