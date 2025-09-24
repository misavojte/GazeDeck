# gazedeck/core/surface_layout_labeling.py

# python
from __future__ import annotations
from typing import NamedTuple, Tuple
from typing import Awaitable, Callable, Dict, Optional
import numpy as np
import numpy.typing as npt

# internal
from gazedeck.core.surface_layout_discovery import SurfaceLayout, TagInfo

class SurfaceLayoutLabeled(NamedTuple):
    """
    Surface layout with user-provided label and discovery index.

    Notes:
        - Inherits id (str), tags, and size from SurfaceLayout (the actual surface identifier from YAML)
        - Adds label (str): User-provided descriptive label
        - Adds emission_id (int): Integer ID used for WebSocket transmission (avoids runtime int conversion)
    """
    id: str
    tags: Dict[int, TagInfo]  # Each tag has size and 4x2 corner array
    size: Tuple[float, float] # width, height
    label: str
    emission_id: int  # ID used for WebSocket transmission

async def label_surface_layouts(
    layouts: Dict[int, SurfaceLayout],
    ask_label: Callable[[int, SurfaceLayout], Awaitable[Optional[str]]],
) -> Dict[int, SurfaceLayoutLabeled]:
    """
    Ask the UI layer for labels per surface layout; return only those that were labeled.

    Args:
        layouts: {index -> SurfaceLayout} from discovery.
        ask_label: async function supplied by CLI/GUI that returns a label string
                   (or None / '' to skip this layout).

    Returns:
        {index -> SurfaceLayoutLabeled} containing only labeled entries.
    """
    labeled: Dict[int, SurfaceLayoutLabeled] = {}
    for idx, layout in layouts.items():
        raw = await ask_label(idx, layout)
        label = (raw or "").strip()
        if label:  # skip if user left it blank / None
            labeled[idx] = SurfaceLayoutLabeled(
                id=layout.id,
                tags=layout.tags,
                size=layout.size,
                label=label,
                emission_id=idx  # Use discovery index as emission ID (temporarily)
            )

    return labeled