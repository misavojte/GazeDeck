# gazedeck/core/surface_layout_labeling.py

# python
from __future__ import annotations
from dataclasses import dataclass
from typing import Awaitable, Callable, Dict, Optional

# internal
from gazedeck.core.surface_layout_discovery import SurfaceLayout

@dataclass(frozen=True)
class SurfaceLayoutLabeled(SurfaceLayout):
    label: str

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
                label=label
            )

    return labeled