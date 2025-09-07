# gazedeck/cli/command_mock.py

# python
from __future__ import annotations

# external
import argparse
import asyncio
from typing import Dict, Any
from dataclasses import dataclass

from gazedeck.cli.setup_labeled_surface_layouts import setup_labeled_surface_layouts_cli
from gazedeck.core.surface_layout_labeling import SurfaceLayoutLabeled
from gazedeck.core.surface_layout_discovery import discover_all_surface_layouts, SurfaceLayout
from gazedeck.core.websocket_server import start_ws_server, stop_ws_server, broadcast_nowait
from gazedeck.core.device_mocking import start_mock_tracking, stop_mock_tracking


@dataclass(frozen=True)
class MockLabeledDevice:
    """
    Mock device equivalent to LabeledDevice for testing purposes.
    """
    label: str
    name: str
    ip: str

    @property
    def device_label(self) -> str:
        """Return the device label for consistency."""
        return self.label


async def setup_mock_device_cli() -> Dict[int, MockLabeledDevice]:
    """
    Present a mock device for labeling using the same interface as real devices.
    """
    print("🎭 Setting up mock device...")

    # Create a mock device description
    mock_device_description = "Mock Tracker Device (Cursor-based) | IP: 127.0.0.1 | Battery: 100% | Sensors: ✓"

    def _prompt() -> str:
        try:
            import sys

            # Check if we have a TTY (interactive terminal)
            if not sys.stdin.isatty():
                print("⚠️  Non-interactive terminal detected, auto-labeling as 'mock_tracker'...")
                return "mock_tracker"

            # Simple input with basic timeout handling
            try:
                result = input(f"Label for mock device [0] [{mock_device_description}] (blank=skip): ")
                return result or "mock_tracker"  # Default to mock_tracker if blank
            except EOFError:
                print("\n❌ EOF detected, using default label 'mock_tracker'...")
                return "mock_tracker"
            except KeyboardInterrupt:
                print("\n❌ Keyboard interrupt, using default label 'mock_tracker'...")
                return "mock_tracker"

        except Exception as e:
            print(f"\n❌ Error getting input: {e}, using default label 'mock_tracker'...")
            return "mock_tracker"

    try:
        label = await asyncio.wait_for(asyncio.to_thread(_prompt), timeout=30.0)
    except asyncio.TimeoutError:
        print("\n⏰ Timeout, using default label 'mock_tracker'...")
        label = "mock_tracker"

    if not label.strip():
        label = "mock_tracker"

    # Create the mock labeled device
    mock_device = MockLabeledDevice(
        label=label.strip(),
        name="Mock Cursor Tracker",
        ip="127.0.0.1"
    )

    labeled = {0: mock_device}

    print("Labeled mock device:")
    print(f"  [0] {mock_device.label} -> {mock_device.name} ({mock_device.ip})")

    return labeled


def add_mock_parser(subparsers) -> argparse.ArgumentParser:
    """
    Add the mock subparser to the main parser.
    """
    mock_parser = subparsers.add_parser(
        "mock",
        help="Stream mock gaze data using cursor position with random noise."
    )

    # Surface layouts arguments
    mock_parser.add_argument(
        "--directory",
        type=str,
        default=".",
        help="Directory to search for surface layouts (default: current directory).",
    )

    # Noise level argument
    mock_parser.add_argument(
        "--noise-level",
        type=float,
        default=20.0,
        help="Maximum random noise in pixels (±noise_level, default: 20.0).",
    )

    # Frequency argument
    mock_parser.add_argument(
        "--frequency",
        type=float,
        default=200.0,
        help="Tracking frequency in Hz (default: 200.0).",
    )

    # Auto-label surface layouts
    mock_parser.add_argument(
        "--auto-label-surface",
        action="store_true",
        help="Automatically label surfaces based on their IDs instead of prompting for labels.",
    )

    return mock_parser


async def auto_label_surface_layouts(layouts: Dict[int, SurfaceLayout]) -> Dict[int, SurfaceLayoutLabeled]:
    """
    Automatically label surface layouts using their IDs directly as labels.
    """
    labeled: Dict[int, SurfaceLayoutLabeled] = {}
    for idx, layout in layouts.items():
        # Use the surface ID directly as the label
        auto_label = layout.id

        labeled[idx] = SurfaceLayoutLabeled(
            id=layout.id,
            tags=layout.tags,
            size=layout.size,
            label=auto_label
        )

    return labeled


async def execute_mock(args: argparse.Namespace):
    """
    Execute the mock command with the parsed arguments.
    """
    # Discover and setup surface layouts
    print("🔍 Discovering surface layouts...")
    layouts = discover_all_surface_layouts(args.directory)

    if not layouts:
        print("❌ No surface layouts found. Please generate at least one surface layout first.")
        return

    if args.auto_label_surface:
        print("🤖 Auto-labeling surface layouts...")
        labeled_surface_layouts = await auto_label_surface_layouts(layouts)
        print(f"📋 Auto-labeled {len(labeled_surface_layouts)} surface layouts:")
        for idx, layout in labeled_surface_layouts.items():
            print(f"  [{idx}] {layout.label} -> {layout.id}")
    else:
        labeled_surface_layouts = await setup_labeled_surface_layouts_cli(args.directory)
        print(f"📋 Found {len(labeled_surface_layouts)} labeled surface layouts: {list(labeled_surface_layouts.keys())}")

    if len(labeled_surface_layouts) == 0:
        print("❌ No labeled surface layouts found. Please generate or label at least one surface layout first.")
        return

    # Setup mock device
    print("🎭 Setting up mock device...")
    mock_devices = await setup_mock_device_cli()
    if len(mock_devices) == 0:
        print("❌ No mock device labeled.")
        return

    # Start WebSocket server
    print("🚀 Starting WebSocket server on ws://localhost:8765")
    server, broadcaster_task = await start_ws_server(host="localhost", port=8765)

    try:
        # Start mock tracking
        print(f"🎯 Starting mock tracking at {args.frequency} Hz with ±{args.noise_level}px noise...")
        # Get the device label from the mock devices
        device_label = list(mock_devices.values())[0].label
        tracker = await start_mock_tracking(labeled_surface_layouts.values(), noise_level=args.noise_level, device_label=device_label, frequency=args.frequency)

        print("Mock stream started!")
        print("🖱️  Click left mouse button to update gaze position")
        print(f"📊 Emitting at {args.frequency} Hz to all surfaces with random noise")
        print("Press Ctrl+C to stop")

        # Keep running until interrupted
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n❌ KeyboardInterrupt: Stopping mock stream")

    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("🧹 Cleaning up...")
        await stop_mock_tracking()
        await stop_ws_server(server, broadcaster_task)
        print("The mock streaming task has stopped")
