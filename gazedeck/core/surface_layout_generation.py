# gazedeck/core/surface_layout_generation.py

import cv2
import os
from gazedeck.core.surface_layout_discovery import SurfaceLayout
from typing import Dict, Tuple
import yaml

# we are using AprilTag 36h11
apriltag_dict = cv2.aruco.getPredefinedDictionary(cv2.aruco.DICT_APRILTAG_36h11)

def generate_marker(marker_id, side_pixels=8, flip_x=False, flip_y=False):
	image_data = apriltag_dict.generateImageMarker(marker_id, side_pixels, 0)

	flip_code = None
	if flip_x and not flip_y:
		flip_code = 1
	elif not flip_x and flip_y:
		flip_code = 0
	elif flip_x and flip_y:
		flip_code = -1

	if flip_code is not None:
		image_data = cv2.flip(image_data, flip_code)

	return image_data


def generate_surface_layout(id: str, tags: Dict[int, Tuple[float, float]], surface_size: Tuple[float, float]) -> SurfaceLayout:
    """
    Generate a surface layout from a dictionary of tags and their coordinates.
    """
    if len(tags) == 0:
        raise ValueError("Tags must be a non-empty dictionary")
    if len(tags) != len(set(tags.keys())):
        raise ValueError("Tags must be a dictionary with unique keys")
    return SurfaceLayout(id, tags, surface_size)

def generate_surface_layout_from_rows_and_columns(id: str, rows: int, columns: int, surface_size: Tuple[float, float], tag_size: float, margin: float = 0.0, starting_tag_id: int = 0) -> SurfaceLayout:
    """
    Generate a surface layout from a number of rows and columns.
    While generating the tags only around the edges of the surface.]
    Effectively, every inner col or row is skipped.

    Tags' coordinates are (x, y) starting from the top left corner of the surface, calculated in the unit of the provided size.

    Margin is the distance from the edge of the surface to the first tag.
    It can be negative, in which case the tags will be closer to the edge of the surface.
    If more negative than their size, the tags will be outside the surface.
    """
    if rows < 2 or columns < 2:
        raise ValueError("Rows and columns must be at least 2")
    if tag_size <= 0:
        raise ValueError("Tag size must be a positive number")
    tags = {}
    tag_id = starting_tag_id
    spacing_x = (surface_size[0] - tag_size - 2 * margin) / (columns - 1)
    spacing_y = (surface_size[1] - tag_size - 2 * margin) / (rows - 1)
    for row in range(rows):
        for col in range(columns):
            if row == 0 or row == rows - 1 or col == 0 or col == columns - 1:
                TOP_LEFT_COORD = (col * spacing_x + margin, row * spacing_y + margin)
                TOP_RIGHT_COORD = (col * spacing_x + tag_size + margin, row * spacing_y + margin)
                BOTTOM_LEFT_COORD = (col * spacing_x + margin, row * spacing_y + tag_size + margin)
                BOTTOM_RIGHT_COORD = (col * spacing_x + tag_size + margin, row * spacing_y + tag_size + margin)

                # Bottom right precedes the bottom left because of the convention of using AprilTag coordinates.
                tags[tag_id] = (TOP_LEFT_COORD, TOP_RIGHT_COORD, BOTTOM_RIGHT_COORD, BOTTOM_LEFT_COORD)
                tag_id += 1

    return SurfaceLayout(id, tags, surface_size)

def save_surface_layout(layout: SurfaceLayout, output_dir: str):
    """
    Save the surface layout to a directory.
    The directory will contain the AprilTag images for each tag.
    And it will also contain the yaml configuration file.

    Example:
    >>> save_surface_layout(generate_surface_layout_from_rows_and_columns("surface_1", 3, 3, (100, 100), 10), "output_dir")
    >>> This will save the surface layout to the directory "output_dir/surface_1"
    >>> And it will also save the AprilTag images for each tag to the directory "output_dir/surface_1/tag_{tag_id}.png"
    >>> And it will also save the yaml configuration file to the directory "output_dir/surface_1/surface_layout.yaml"
    """
    os.makedirs(output_dir, exist_ok=True)
    # make subfolder for this surface id
    output_dir = os.path.join(output_dir, layout.id)
    os.makedirs(output_dir, exist_ok=True)

    # Generate and save AprilTag images
    for tag_id in layout.tags.keys():
        image_data = generate_marker(tag_id)
        cv2.imwrite(os.path.join(output_dir, f"tag_{tag_id}.png"), image_data)

    # Save configuration
    with open(os.path.join(output_dir, "surface_layout.yaml"), "w") as f:
        yaml.dump(layout.to_dict(), f)