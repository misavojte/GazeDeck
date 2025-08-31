# gazedeck/core/surface_layout_labeling.py

from dataclasses import dataclass
from gazedeck.core.surface_layout_discovery import SurfaceLayout

@dataclass
class SurfaceLayoutLabeled(SurfaceLayout):
    label: str