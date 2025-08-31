# gazedeck/core/surface_layout_discovery.py

from dataclasses import dataclass
from typing import Dict, Tuple

@dataclass
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