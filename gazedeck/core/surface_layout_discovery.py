# gazedeck/core/surface_layout_discovery.py

# python
from dataclasses import dataclass
from typing import Dict, Tuple, NamedTuple

# external
import yaml
import os

class TagInfo(NamedTuple):
    size: float  # Physical size in meters
    corners: Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float], Tuple[float, float]]  # Four corner coordinates

class SurfaceLayout(NamedTuple):
    id: str
    tags: Dict[int, TagInfo]  # Each tag has size and four corner coordinates
    size: Tuple[float, float] # width, height

    def to_dict(self) -> dict:
        """Convert the SurfaceLayout to a dictionary for serialization."""
        return {
            "id": self.id,
            "tags": {tag_id: {"size": tag_info.size, "corners": [list(corner) for corner in tag_info.corners]} for tag_id, tag_info in self.tags.items()},
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
            corners=tuple(tuple(corner) for corner in tag_data["corners"])
        )
    
    return SurfaceLayout(data["id"], tags, data["size"])

def discover_all_surface_layouts(directory: str) -> Dict[int, SurfaceLayout]:
    """
    Discover all surface layouts in a directory.
    It will inspect all subdirectories, search for surface_layout.yaml files
    and load them all.

    The keys are ids in which order they were discovered. This will be used for labeling purposes later.
    """
    found_layouts = {}
    layout_count = 0
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith("surface_layout.yaml"):
                file_path = os.path.join(root, file)
                found_layouts[layout_count] = load_surface_layout(file_path)
                layout_count += 1
    
    return found_layouts