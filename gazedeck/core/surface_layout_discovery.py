# gazedeck/core/surface_layout_discovery.py

# python
from dataclasses import dataclass
from typing import Dict, Tuple

# external
import yaml
import os

@dataclass(frozen=True)
class SurfaceLayout:
    id: str
    tags: Dict[int, Tuple[Tuple[float, float], Tuple[float, float], Tuple[float, float], Tuple[float, float]]]  # Each tag has four corner coordinates
    size: Tuple[float, float] # width, height

    def to_dict(self) -> dict:
        """Convert the SurfaceLayout to a dictionary for serialization."""
        return {
            "id": self.id,
            "tags": {tag_id: [list(corner) for corner in coords] for tag_id, coords in self.tags.items()},
            "size": list(self.size)
        }

def load_surface_layout(file_path: str) -> SurfaceLayout:
    """
    Load a surface layout from a yamlfile.
    """
    with open(file_path, "r") as f:
        data = yaml.load(f, Loader=yaml.FullLoader)
    return SurfaceLayout(data["id"], data["tags"], data["size"])

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
    
    print(f"Discovered {len(found_layouts)} surface layouts in directory {directory} (including subdirectories)")
    return found_layouts