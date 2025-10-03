# gazedeck/core/surface_layout_discovery.py

# python
from dataclasses import dataclass
from typing import Dict, Tuple, NamedTuple
import numpy as np
import numpy.typing as npt

# external
import yaml
import os

class TagInfo(NamedTuple):
    size: float  # Physical size in meters
    corners: npt.NDArray[np.float32]  # 4x2 array of corner coordinates

class SurfaceLayout(NamedTuple):
    id: str
    tags: Dict[int, TagInfo]  # Each tag has size and four corner coordinates
    size: Tuple[float, float] # width, height

    def to_dict(self) -> dict:
        """Convert the SurfaceLayout to a dictionary for serialization."""
        return {
            "id": self.id,
            "tags": {tag_id: {"size": tag_info.size, "corners": tag_info.corners.tolist()} for tag_id, tag_info in self.tags.items()},
            "size": list(self.size)
        }

def load_surface_layout(file_path: str) -> SurfaceLayout:
    """
    Load a surface layout from a yamlfile.
    """
    with open(file_path, "r") as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
    
    # Convert tags data to TagInfo objects
    tags = {}
    for tag_id, tag_data in data["tags"].items():
        tags[int(tag_id)] = TagInfo(
            size=tag_data["size"],
            corners=np.asarray(tag_data["corners"], dtype=np.float32)  # Use asarray to avoid unnecessary copy
        )
    
    return SurfaceLayout(data["id"], tags, data["size"])

def discover_all_surface_layouts(directory: str) -> Dict[int, SurfaceLayout]:
    """
    Discover all surface layouts in a directory.
    It will inspect all subdirectories, search for surface_layout.yaml files
    and load them all.

    The keys are ids in which order they were discovered. This will be used for labeling purposes later.
    """
    import os
    import sys

    # Try to determine the console executable location for better path resolution
    console_base_dir = None

    # Check if we're running from a PyInstaller bundle (standalone executable)
    if hasattr(sys, '_MEIPASS'):
        # We're in a PyInstaller bundle, get the executable directory
        console_base_dir = os.path.dirname(sys.executable)
    else:
        # We're running from source, use current working directory
        console_base_dir = os.getcwd()

    # Convert to absolute path and validate
    abs_directory = os.path.abspath(directory)

    # Check if the directory exists
    if not os.path.exists(abs_directory):
        print(f"[ERR] Directory does not exist: {abs_directory}")
        return {}

    # Check if it's a directory
    if not os.path.isdir(abs_directory):
        print(f"[ERR] Path is not a directory: {abs_directory}")
        return {}


    found_layouts = {}
    layout_count = 0

    # Use os.walk for better control and to avoid infinite recursion
    for root, dirs, files in os.walk(abs_directory):
        # Limit search depth to prevent excessive recursion
        depth = root[len(abs_directory):].count(os.sep)
        if depth > 5:  # Reduced to 5 levels for safety
            dirs.clear()  # Don't recurse deeper
            continue

        for file in files:
            if file == "surface_layout.yaml":
                yaml_file = os.path.join(root, file)
                try:
                    found_layouts[layout_count] = load_surface_layout(yaml_file)
                    layout_count += 1
                except Exception as e:
                    print(f"[WARN] Error loading {yaml_file}: {e}")

    return found_layouts