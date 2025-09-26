# gazedeck/cli/command_test_surface_layout_discovery.py

from __future__ import annotations

import argparse
from typing import Dict

from gazedeck.cli.setup_labeled_surface_layouts import setup_labeled_surface_layouts_cli
from gazedeck.core.surface_layout_labeling import SurfaceLayoutLabeled


def add_test_surface_layout_discovery_parser(subparsers) -> argparse.ArgumentParser:
    """
    Add the test-surface-layout-discovery subparser to the main parser.

    Args:
        subparsers: The subparsers object from the main argument parser

    Returns:
        The configured subparser for test-surface-layout-discovery command
    """
    test_discovery_parser = subparsers.add_parser(
        "test-surface-layout-discovery",
        help="Run test of surface layout discovery + labeling"
    )
    test_discovery_parser.add_argument(
        "--directory",
        type=str,
        default=".",
        help="Directory to search for surface layouts (default: current directory).",
    )
    return test_discovery_parser


async def run_discovery_and_label(directory: str = ".") -> Dict[int, SurfaceLayoutLabeled]:
    """
    Run surface layout discovery and labeling for the specified directory.

    Args:
        directory: Directory path to search for surface layouts

    Returns:
        Dictionary of labeled surface layouts indexed by their discovery order
    """
    labeled_layouts = await setup_labeled_surface_layouts_cli(directory)
    return labeled_layouts


async def cleanup_surface_layouts(layouts: Dict[int, SurfaceLayoutLabeled]):
    """
    Clean up all stored labeled surface layouts.
    """
    layouts.clear()



async def execute_test_surface_layout_discovery(args: argparse.Namespace):
    """
    Execute the test-surface-layout-discovery command with the parsed arguments.

    Args:
        args: Parsed command line arguments
    """
    labeled_layouts = await run_discovery_and_label(args.directory)

    if len(labeled_layouts) > 0:
        print(f"[INIT] Found {len(labeled_layouts)} labeled surface layout(s).")
    else:
        print("[ERR] No labeled surface layouts found.")

    print("Finishing the test. Cleaning up...")
    await cleanup_surface_layouts(labeled_layouts)