# gazedeck/cli/prompt_surface_layout_labeling.py

import asyncio
from typing import Optional
from gazedeck.core.surface_layout_discovery import SurfaceLayout


async def _describe(layout: SurfaceLayout) -> str:
    """
    Create a description of the surface layout.
    """
    return f"Layout {layout.id} ({len(layout.tags)} tags, size: {layout.size[0]:.1f}x{layout.size[1]:.1f})"


async def ask_label_cli(idx: int, layout: SurfaceLayout) -> Optional[str]:
    """
    Return label from stdin; blank → skip.
    Uses a thread to avoid blocking the asyncio loop.

    This is indented to be used with the label_surface_layouts function in gazedeck/core/surface_layout_labeling.py
    """
    # Get layout description
    description = await _describe(layout)

    def _prompt() -> str:
        try:
            result = input(f"[INPUT] Label for layout {idx} [{description}] (blank=skip): ")
            return result
        except EOFError:
            return ""  # skip on EOF
    return await asyncio.to_thread(_prompt)