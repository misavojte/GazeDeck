#!/usr/bin/env python3
"""
Surface Layout Module

Minimal SurfaceLayout class for managing AprilTag surface configurations.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, List, Tuple, Optional

# Defer dependency imports until needed
_cv2 = None
_numpy = None
_marker_generator = None

def _ensure_dependencies():
    """Ensure required dependencies are available."""
    global _cv2, _numpy, _marker_generator
    if _cv2 is None:
        try:
            import cv2 as _cv2
            import numpy as _numpy
            from pupil_labs.real_time_screen_gaze import marker_generator as _marker_generator
        except ImportError as e:
            raise ImportError(f"Required dependencies missing: {e}. Install: pip install opencv-python numpy pupil-labs-realtime-screen-gaze")


class SurfaceLayout:
    """Minimal SurfaceLayout class for AprilTag surface configurations."""

    def __init__(self, width: int = 1920, height: int = 1080, tags: Dict[int, List[Tuple[int, int]]] = None):
        """Create SurfaceLayout with width, height, and tags dict."""
        if width <= 0 or height <= 0:
            raise ValueError("Width and height must be positive integers")
        if tags is None:
            raise ValueError("tags parameter is required")

        self.width = width
        self.height = height
        self.tags = tags

    @staticmethod
    def generate_from_rows_and_columns(width: int = 1920, height: int = 1080,
                                     tag_size: int = 100, rows: int = 2,
                                     columns: int = 5, margin: int = 50) -> 'SurfaceLayout':
        """Generate SurfaceLayout with tags positioned around screen edges."""
        if tag_size <= 0:
            raise ValueError("tag_size must be a positive integer")
        if rows < 2:
            raise ValueError("rows must be at least 2")
        if columns < 2:
            raise ValueError("columns must be at least 2")

        # Generate tags first
        tags = SurfaceLayout._calculate_tag_positions(width, height, tag_size, rows, columns, margin)

        # Create layout with generated tags
        layout = SurfaceLayout(width, height, tags)
        return layout

    @staticmethod
    def _calculate_tag_positions(width: int, height: int, tag_size: int, rows: int, columns: int, margin: int) -> Dict[int, List[Tuple[int, int]]]:
        """Calculate AprilTag positions around screen edges."""
        tags = {}

        # Calculate spacing
        available_width = width - 2 * margin
        spacing_x = (available_width - tag_size) / (columns - 1) if columns > 1 else 0

        tag_id = 0

        # Top and bottom edges
        for row in [0, 1]:
            y = margin if row == 0 else height - margin - tag_size
            for col in range(columns):
                x = margin + col * spacing_x
                tags[tag_id] = [
                    (int(x), int(y)),
                    (int(x + tag_size), int(y)),
                    (int(x + tag_size), int(y + tag_size)),
                    (int(x), int(y + tag_size))
                ]
                tag_id += 1

        # Left and right edges for additional rows
        if rows > 2:
            # Calculate Y positions for additional rows (evenly distributed)
            num_additional_rows = rows - 2
            top_edge_bottom = margin + tag_size
            bottom_edge_top = height - margin - tag_size
            available_vertical_space = bottom_edge_top - top_edge_bottom

            # Divide the available space into equal segments
            spacing_y = available_vertical_space / (num_additional_rows + 1) if num_additional_rows > 0 else 0

            for i in range(num_additional_rows):
                # Position each additional row at equal intervals
                y = top_edge_bottom + (i + 1) * spacing_y - tag_size // 2
                y = int(y)

                # Left edge
                x_left = margin
                tags[tag_id] = [
                    (int(x_left), int(y)),
                    (int(x_left + tag_size), int(y)),
                    (int(x_left + tag_size), int(y + tag_size)),
                    (int(x_left), int(y + tag_size))
                ]
                tag_id += 1

                # Right edge
                x_right = width - margin - tag_size
                tags[tag_id] = [
                    (int(x_right), int(y)),
                    (int(x_right + tag_size), int(y)),
                    (int(x_right + tag_size), int(y + tag_size)),
                    (int(x_right), int(y + tag_size))
                ]
                tag_id += 1

        return tags

    def get_tag(self, tag_id: int) -> Optional[List[Tuple[int, int]]]:
        """Get tag corners by ID."""
        return self.tags.get(tag_id)

    def save_config(self, path: str = "apriltag_config.yaml"):
        """Save configuration to YAML."""
        config = {
            'surface_width': self.width,
            'surface_height': self.height,
            'tags': {str(k): [[x, y] for x, y in v] for k, v in self.tags.items()}
        }
        try:
            Path(path).parent.mkdir(parents=True, exist_ok=True)
            with open(path, 'w', encoding='utf-8') as f:
                yaml.dump(config, f, default_flow_style=False, sort_keys=False)
        except (OSError, IOError, yaml.YAMLError) as e:
            raise OSError(f"Failed to save configuration to '{path}': {e}")

    @staticmethod
    def create_from_yaml(path: str) -> 'SurfaceLayout':
        """Create SurfaceLayout from YAML configuration file."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
        except (OSError, IOError) as e:
            raise OSError(f"Failed to read configuration file '{path}': {e}")
        except yaml.YAMLError as e:
            raise ValueError(f"Invalid YAML format in '{path}': {e}")

        if config is None:
            raise ValueError(f"Configuration file '{path}' is empty")

        required_fields = ['surface_width', 'surface_height', 'tags']
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            raise ValueError(f"Missing required fields in '{path}': {missing_fields}")

        # Load tags
        try:
            tags = {int(k): [(x, y) for x, y in v] for k, v in config['tags'].items()}
        except (ValueError, TypeError) as e:
            raise ValueError(f"Invalid tag data format in '{path}': {e}")

        layout = SurfaceLayout(
            width=config['surface_width'],
            height=config['surface_height'],
            tags=tags
        )

        return layout

    def generate_apriltags(self, output_path: str = "apriltags", config_filename: str = "apriltag_config.yaml"):
        """Generate AprilTag PNG images and save config in the same directory."""
        # Ensure dependencies are available
        _ensure_dependencies()

        # Calculate tag size from the first tag's dimensions
        if not self.tags:
            raise ValueError("No tags available to determine tag size")

        first_tag = next(iter(self.tags.values()))
        if len(first_tag) < 4:
            raise ValueError("Invalid tag format - expected 4 corners")

        # Calculate tag size from first tag's corners (bottom-right - top-left)
        top_left = first_tag[0]
        bottom_right = first_tag[2]
        tag_size = bottom_right[0] - top_left[0]  # width
        tag_height = bottom_right[1] - top_left[1]  # height

        if tag_size != tag_height:
            raise ValueError("Tags must be square")

        try:
            os.makedirs(output_path, exist_ok=True)
        except OSError as e:
            raise OSError(f"Failed to create output directory '{output_path}': {e}")

        # Save config in the same directory
        config_path = os.path.join(output_path, config_filename)
        try:
            self.save_config(config_path)
        except (OSError, IOError) as e:
            raise OSError(f"Failed to save config file '{config_path}': {e}")

        # Generate images
        for tag_id in self.tags.keys():
            try:
                marker_pixels = _marker_generator.generate_marker(marker_id=tag_id)
                marker_array = _numpy.array(marker_pixels, dtype=_numpy.uint8)
                if marker_array.ndim == 1:
                    side = int(_numpy.sqrt(marker_array.size))
                    marker_array = marker_array.reshape(side, side)
                scaled = _cv2.resize(marker_array, (tag_size, tag_size), interpolation=_cv2.INTER_NEAREST)
                _cv2.imwrite(f"{output_path}/apriltag_{tag_id}.png", scaled)
            except Exception as e:
                raise RuntimeError(f"Failed to generate AprilTag {tag_id}: {e}")

    def __len__(self):
        return len(self.tags)

    def __str__(self):
        return f"SurfaceLayout({self.width}x{self.height}, {len(self.tags)} tags)"


__version__ = "1.0.0"
__all__ = ['SurfaceLayout']
