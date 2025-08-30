#!/usr/bin/env python3
"""
Surface Configuration Generator

Generates apriltags_config.yaml with tags placed around screen edges
and automatically generates the corresponding AprilTag PNG images.
Tags are distributed evenly along the perimeter of the screen.

This module provides functions to:
- Generate AprilTag images using pupil_labs marker generator
- Calculate optimal tag positions around screen edges
- Generate and save configuration files
- Validate generated configurations
"""

import os
import yaml
from pathlib import Path
from typing import List, Tuple, Dict, Any
import cv2
import numpy as np
from pupil_labs.real_time_screen_gaze import marker_generator


def save_apriltag(marker_id: int, output_path: str = "apriltags", size: int = 100) -> bool:
    """Generate and save a single AprilTag as PNG using pupil_labs marker generator.

    Args:
        marker_id: Unique identifier for the AprilTag
        output_path: Directory path to save the PNG file
        size: Size of the generated image in pixels

    Returns:
        bool: True if successful, False otherwise
    """
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


def calculate_edge_positions(surface_width: int, surface_height: int, tag_size: int,
                           rows: int, columns: int, margin: int) -> Dict[int, List[Tuple[int, int]]]:
    """
    Calculate AprilTag positions around surface edges.

    For a 2x5 layout:
    - Top edge: 5 tags distributed evenly
    - Bottom edge: 5 tags distributed evenly
    - Total: 10 tags

    For layouts with more rows, additional tags are placed on left and right edges:
    - Row 0: Top edge tags (distributed across all columns)
    - Row 1: Bottom edge tags (distributed across all columns)
    - Rows 2+: Left edge tag in column 0 + Right edge tag in last column

    Inner positions (non-edge) are left empty.

    Args:
        surface_width: Surface width in pixels
        surface_height: Surface height in pixels
        tag_size: Size of each tag in pixels
        rows: Number of rows (minimum 2 for top/bottom edges)
        columns: Number of columns (minimum 2, tags per edge)
        margin: Margin from surface edges

    Returns:
        Dictionary mapping tag IDs to corner coordinates (only edge positions)
    """
    if rows < 2:
        raise ValueError("For edge placement, rows must be at least 2")
    if columns < 2:
        raise ValueError("For edge placement, columns must be at least 2")

    positions = {}

    # Calculate spacing for top and bottom edges
    available_width = surface_width - 2 * margin
    if columns > 1:
        spacing_x = (available_width - tag_size) / (columns - 1)
    else:
        spacing_x = 0

    tag_id = 0

    # Top edge tags (distributed across columns)
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

    # Bottom edge tags (distributed across columns)
    y_top = surface_height - margin - tag_size
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

    # For rows > 2, only add edge tags (left and right edges)
    if rows > 2:
        # Calculate vertical spacing for left and right edges
        available_height = surface_height - 2 * margin
        if rows > 3:
            spacing_y = (available_height - tag_size) / (rows - 3)
        else:
            spacing_y = 0

        # Left edge tags
        x_left = margin
        x_right = x_left + tag_size

        # Right edge tags
        x_left_right = surface_width - margin - tag_size
        x_right_right = x_left_right + tag_size

        for row in range(2, rows):
            # Calculate Y position for this row
            if rows == 3:
                # For 3 rows total, place middle row in center
                y_top = (surface_height - tag_size) // 2
            else:
                # For more rows, distribute evenly between top and bottom
                y_top = margin + (row - 1) * spacing_y

            y_bottom = y_top + tag_size

            # Left edge tag (only for column 0 of this row)
            left_tag_id = row * columns + 0
            positions[left_tag_id] = [
                (int(x_left), int(y_top)),      # Top-left
                (int(x_right), int(y_top)),     # Top-right
                (int(x_right), int(y_bottom)),  # Bottom-right
                (int(x_left), int(y_bottom))    # Bottom-left
            ]

            # Right edge tag (only for last column of this row)
            right_tag_id = row * columns + (columns - 1)
            positions[right_tag_id] = [
                (int(x_left_right), int(y_top)),      # Top-left
                (int(x_right_right), int(y_top)),     # Top-right
                (int(x_right_right), int(y_bottom)),  # Bottom-right
                (int(x_left_right), int(y_bottom))    # Bottom-left
            ]

    return positions


def get_edge_description(row: int, col: int, columns: int, rows: int) -> str:
    """Get description for edge-placed tag.

    Args:
        row: Row index of the tag
        col: Column index of the tag
        columns: Total number of columns
        rows: Total number of rows

    Returns:
        str: Human-readable description of the tag's position
    """
    if row == 0:  # Top edge
        if col == 0:
            return "Top-left corner"
        elif col == columns - 1:
            return "Top-right corner"
        else:
            return f"Top edge, position {col + 1}"
    elif row == 1:  # Bottom edge
        if col == 0:
            return "Bottom-left corner"
        elif col == columns - 1:
            return "Bottom-right corner"
        else:
            return f"Bottom edge, position {col + 1}"
    elif row >= 2:  # Left and right edges for additional rows
        if col == 0:
            return f"Left edge, row {row}"
        else:
            return f"Right edge, row {row}"


def generate_config(surface_width: int, surface_height: int, tag_size: int,
                   rows: int, columns: int, margin: int) -> Dict[str, Any]:
    """
    Generate complete configuration dictionary.

    Args:
        surface_width: Surface width in pixels
        surface_height: Surface height in pixels
        tag_size: Size of each tag in pixels
        rows: Number of rows around edges
        columns: Number of columns around edges
        margin: Margin from surface edges

    Returns:
        Complete configuration dictionary
    """
    # Calculate tag positions
    marker_positions = calculate_edge_positions(
        surface_width, surface_height, tag_size, rows, columns, margin
    )

    # Build configuration
    config = {
        'surface_width': surface_width,
        'surface_height': surface_height,
        'tag_size': tag_size,
        'rows': rows,
        'columns': columns,
        'margin': margin,
        'apriltags': {}
    }

    # Add each tag to config (only for positions that exist)
    for tag_id, corners in marker_positions.items():
        row = tag_id // columns
        col = tag_id % columns
        tag_name = f"tag_{tag_id}"
        config['apriltags'][tag_name] = {
            'id': tag_id,
            'description': get_edge_description(row, col, columns, rows),
            'corners': [list(corner) for corner in corners]  # Convert tuples to lists
        }

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
    """Validate the generated configuration.

    Args:
        config: Configuration dictionary to validate

    Returns:
        List of validation error messages (empty if valid)
    """
    errors = []

    # Check required fields
    required_fields = ['surface_width', 'surface_height', 'apriltags']
    for field in required_fields:
        if field not in config:
            errors.append(f"Missing required field: {field}")

    # Check surface dimensions
    if 'surface_width' in config and config['surface_width'] <= 0:
        errors.append("surface_width must be positive")
    if 'surface_height' in config and config['surface_height'] <= 0:
        errors.append("surface_height must be positive")

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
