#!/usr/bin/env python3
"""
AprilTags Configuration Generator

Generates apriltags_config.yaml with tags placed around screen edges
and automatically generates the corresponding AprilTag PNG images.
Tags are distributed evenly along the perimeter of the screen.

Usage:
    python apriltags_config_generator.py [options]

Options:
    --screen-width WIDTH     Screen width in pixels (default: 1020)
    --screen-height HEIGHT   Screen height in pixels (default: 780)
    --tag-size SIZE         Size of each tag in pixels (default: 100)
    --rows ROWS             Number of tag rows around edges (default: 2)
    --columns COLS          Number of tag columns around edges (default: 5)
    --margin MARGIN         Margin from screen edges in pixels (default: 10)
    --output DIR            Output directory for config.yaml and PNG files (default: apriltags)

Example:
    python apriltags_config_generator.py --screen-width 1920 --screen-height 1080 --output my_tags
"""

import argparse
import yaml
import os
import sys
from pathlib import Path
from typing import List, Tuple, Dict, Any
import cv2
import numpy as np
from pupil_labs.real_time_screen_gaze import marker_generator


def save_apriltag(marker_id: int, output_path: str = "apriltags", size: int = 100) -> bool:
    """Generate and save a single AprilTag as PNG using pupil_labs marker generator."""
    try:
        # Generate the marker using pupil_labs (this creates valid AprilTags)
        marker_pixels = marker_generator.generate_marker(marker_id=marker_id)

        # Convert to numpy array and ensure proper format
        marker_array = np.array(marker_pixels, dtype=np.uint8)

        # Ensure it's 2D
        if marker_array.ndim == 1:
            side_length = int(np.sqrt(marker_array.size))
            marker_array = marker_array.reshape(side_length, side_length)

        # Scale to desired size using nearest neighbor to preserve pattern
        scaled_marker = cv2.resize(marker_array, (size, size), interpolation=cv2.INTER_NEAREST)

        # Save using OpenCV
        os.makedirs(output_path, exist_ok=True)

        filename = f"{output_path}/apriltag_{marker_id}.png"
        cv2.imwrite(filename, scaled_marker)
        print(f"Saved AprilTag {marker_id} to {filename}")

        # Verify the saved image
        verify_img = cv2.imread(filename, cv2.IMREAD_GRAYSCALE)
        if verify_img is not None:
            print(f"Verification: saved image shape {verify_img.shape}, unique values: {np.unique(verify_img)}")
        else:
            print("Warning: Could not verify saved image")

        return True

    except Exception as e:
        print(f"Error generating AprilTag {marker_id}: {e}")
        import traceback
        traceback.print_exc()
        return False


def calculate_edge_positions(screen_width: int, screen_height: int, tag_size: int,
                           rows: int, columns: int, margin: int) -> Dict[int, List[Tuple[int, int]]]:
    """
    Calculate AprilTag positions around screen edges.

    For a 2x5 layout:
    - Top edge: 5 tags distributed evenly
    - Bottom edge: 5 tags distributed evenly
    - Total: 10 tags

    Args:
        screen_width: Screen width in pixels
        screen_height: Screen height in pixels
        tag_size: Size of each tag in pixels
        rows: Number of rows (should be 2 for top/bottom edges)
        columns: Number of columns (tags per edge)
        margin: Margin from screen edges

    Returns:
        Dictionary mapping tag IDs to corner coordinates
    """
    if rows != 2:
        raise ValueError("For edge placement, rows must be 2 (top and bottom edges)")

    positions = {}

    # Calculate spacing for top and bottom edges
    available_width = screen_width - 2 * margin
    if columns > 1:
        spacing_x = (available_width - tag_size) / (columns - 1)
    else:
        spacing_x = 0

    tag_id = 0

    # Top edge tags (row 0)
    y_top = margin
    for col in range(columns):
        x_left = margin + col * spacing_x
        x_right = x_left + tag_size
        y_bottom = y_top + tag_size

        positions[tag_id] = [
            (int(x_left), int(y_top)),      # Top-left
            (int(x_right), int(y_top)),     # Top-right
            (int(x_right), int(y_bottom)),  # Bottom-right
            (int(x_left), int(y_bottom))    # Bottom-left
        ]
        tag_id += 1

    # Bottom edge tags (row 1)
    y_top = screen_height - margin - tag_size
    for col in range(columns):
        x_left = margin + col * spacing_x
        x_right = x_left + tag_size
        y_bottom = y_top + tag_size

        positions[tag_id] = [
            (int(x_left), int(y_top)),      # Top-left
            (int(x_right), int(y_top)),     # Top-right
            (int(x_right), int(y_bottom)),  # Bottom-right
            (int(x_left), int(y_bottom))    # Bottom-left
        ]
        tag_id += 1

    return positions


def get_edge_description(row: int, col: int, columns: int) -> str:
    """Get description for edge-placed tag."""
    if row == 0:  # Top edge
        if col == 0:
            return "Top-left corner"
        elif col == columns - 1:
            return "Top-right corner"
        else:
            return f"Top edge, position {col + 1}"
    else:  # Bottom edge
        if col == 0:
            return "Bottom-left corner"
        elif col == columns - 1:
            return "Bottom-right corner"
        else:
            return f"Bottom edge, position {col + 1}"


def generate_config(screen_width: int, screen_height: int, tag_size: int,
                   rows: int, columns: int, margin: int) -> Dict[str, Any]:
    """
    Generate complete configuration dictionary.

    Args:
        screen_width: Screen width in pixels
        screen_height: Screen height in pixels
        tag_size: Size of each tag in pixels
        rows: Number of rows around edges
        columns: Number of columns around edges
        margin: Margin from screen edges

    Returns:
        Complete configuration dictionary
    """
    # Calculate tag positions
    marker_positions = calculate_edge_positions(
        screen_width, screen_height, tag_size, rows, columns, margin
    )

    # Build configuration
    config = {
        'screen_width': screen_width,
        'screen_height': screen_height,
        'tag_size': tag_size,
        'rows': rows,
        'columns': columns,
        'margin': margin,
        'apriltags': {}
    }

    # Add each tag to config
    tag_id = 0
    for row in range(rows):
        for col in range(columns):
            tag_name = f"tag_{tag_id}"
            config['apriltags'][tag_name] = {
                'id': tag_id,
                'description': get_edge_description(row, col, columns),
                'corners': [list(corner) for corner in marker_positions[tag_id]]  # Convert tuples to lists
            }
            tag_id += 1



    return config


def save_config(config: Dict[str, Any], output_path: str) -> None:
    """
    Save configuration to YAML file.

    Args:
        config: Configuration dictionary
        output_path: Path to save the config file
    """
    output_file = Path(output_path)

    # Create directory if it doesn't exist
    output_file.parent.mkdir(parents=True, exist_ok=True)

    # Save as YAML with cleaner formatting
    with open(output_file, 'w', encoding='utf-8') as f:
        yaml.dump(config, f, default_flow_style=False, sort_keys=False, allow_unicode=True)

    print(f"Configuration saved to: {output_file}")


def validate_config(config: Dict[str, Any]) -> List[str]:
    """Validate the generated configuration."""
    errors = []

    # Check required fields
    required_fields = ['screen_width', 'screen_height', 'apriltags']
    for field in required_fields:
        if field not in config:
            errors.append(f"Missing required field: {field}")

    # Check screen dimensions
    if 'screen_width' in config and config['screen_width'] <= 0:
        errors.append("screen_width must be positive")
    if 'screen_height' in config and config['screen_height'] <= 0:
        errors.append("screen_height must be positive")

    # Check tags
    if 'apriltags' in config:
        apriltags = config['apriltags']
        if not isinstance(apriltags, dict):
            errors.append("'apriltags' must be a dictionary")
        else:
            used_ids = set()
            for tag_name, tag_data in apriltags.items():
                if 'id' not in tag_data:
                    errors.append(f"Tag '{tag_name}' missing 'id' field")
                else:
                    tag_id = tag_data['id']
                    if tag_id in used_ids:
                        errors.append(f"Duplicate tag ID: {tag_id}")
                    used_ids.add(tag_id)

                if 'corners' not in tag_data:
                    errors.append(f"Tag '{tag_name}' missing 'corners' field")
                else:
                    corners = tag_data['corners']
                    if len(corners) != 4:
                        errors.append(f"Tag '{tag_name}' must have exactly 4 corners, got {len(corners)}")

    return errors


def main():
    """Main function to generate AprilTags configuration."""
    parser = argparse.ArgumentParser(
        description="Generate AprilTags configuration with edge placement",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )

    parser.add_argument('--screen-width', type=int, default=1020,
                       help='Screen width in pixels (default: 1020)')
    parser.add_argument('--screen-height', type=int, default=780,
                       help='Screen height in pixels (default: 780)')
    parser.add_argument('--tag-size', type=int, default=100,
                       help='Size of each tag in pixels (default: 100)')
    parser.add_argument('--rows', type=int, default=2,
                       help='Number of tag rows around edges (default: 2)')
    parser.add_argument('--columns', type=int, default=5,
                       help='Number of tag columns around edges (default: 5)')
    parser.add_argument('--margin', type=int, default=10,
                       help='Margin from screen edges in pixels (default: 10)')
    parser.add_argument('--output', type=str, default='apriltags',
                       help='Output directory for config.yaml and PNG files (default: apriltags)')

    args = parser.parse_args()

    try:
        # Generate configuration
        print("Generating AprilTags configuration...")
        print(f"Screen: {args.screen_width}x{args.screen_height}")
        print(f"Tags: {args.rows}x{args.columns} around edges")
        print(f"Tag size: {args.tag_size}x{args.tag_size}")
        print(f"Margin: {args.margin}px")
        print()

        config = generate_config(
            screen_width=args.screen_width,
            screen_height=args.screen_height,
            tag_size=args.tag_size,
            rows=args.rows,
            columns=args.columns,
            margin=args.margin
        )

        # Validate configuration
        errors = validate_config(config)
        if errors:
            print("Configuration validation errors:")
            for error in errors:
                print(f"  - {error}")
            return 1

        # Determine output directory and config file path
        output_dir = Path(args.output)
        config_file_path = output_dir / 'apriltag_config.yaml'
        png_output_dir = str(output_dir)

        # Save configuration
        save_config(config, str(config_file_path))

        # Generate PNG files for each tag
        print(f"\nGenerating AprilTag PNG files to: {png_output_dir}")
        png_success_count = 0
        total_tags = len(config['apriltags'])

        for tag_name, tag_data in config['apriltags'].items():
            tag_id = tag_data['id']
            if save_apriltag(tag_id, png_output_dir, args.tag_size):
                png_success_count += 1

        # Show summary
        print("\nConfiguration and PNG generation completed!")
        print(f"Total tags: {total_tags}")
        print(f"Layout: {args.rows}x{args.columns} around screen edges")
        print(f"Output directory: {args.output}")
        print(f"Files created: apriltag_config.yaml + {png_success_count} PNG files")

        if png_success_count != total_tags:
            print(f"Warning: {total_tags - png_success_count} PNG files failed to generate")
            return 1

        return 0

    except Exception as e:
        print(f"Error generating configuration: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
