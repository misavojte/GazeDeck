# gazedeck/cli/setup_labeled_surface_layouts.py

from __future__ import annotations

from typing import Dict
from gazedeck.core.surface_layout_discovery import SurfaceLayout, discover_all_surface_layouts
from gazedeck.core.surface_layout_labeling import SurfaceLayoutLabeled, label_surface_layouts
from gazedeck.cli.prompt_surface_layout_labeling import ask_label_cli


async def setup_labeled_surface_layouts_cli(directory: str) -> Dict[int, SurfaceLayoutLabeled]:
    """
    Discover surface layouts in directory, prompt labels (blank=skip),
    and return labeled surface layouts.
    """
    layouts: Dict[int, SurfaceLayout] = discover_all_surface_layouts(directory)

    if not layouts:
        print("No surface layouts found.")
        return {}

    labeled = await label_surface_layouts(layouts, ask_label_cli)

    if labeled:
        print("Labeled surface layouts:")
        for idx, ld in labeled.items():
            print(f"  [{idx}] {ld.label} -> {ld.id}")
    else:
        print("No surface layouts labeled.")

    return labeled