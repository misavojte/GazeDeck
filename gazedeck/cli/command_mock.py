# gazedeck/cli/command_mock.py

# python
from __future__ import annotations

# external
import argparse
import asyncio
from typing import Dict
from typing import NamedTuple

from gazedeck.cli.setup_labeled_surface_layouts import setup_labeled_surface_layouts_cli
from gazedeck.core.surface_layout_labeling import SurfaceLayoutLabeled
from gazedeck.core.surface_layout_discovery import discover_all_surface_layouts, SurfaceLayout
from gazedeck.core.websocket_server import start_ws_server, stop_ws_server, broadcast_gaze_data
from gazedeck.core.device_mocking import start_mock_tracking, stop_mock_tracking, get_active_mock_devices


class MockLabeledDevice(NamedTuple):
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


async def setup_mock_devices_cli(num_devices: int = 1) -> Dict[int, MockLabeledDevice]:
    """
    Present mock devices for labeling using the same interface as real devices.

    Args:
        num_devices: Number of mock devices to create (1-3)
    """
    print(f"[INIT] Setting up {num_devices} mock device{'s' if num_devices > 1 else ''}...")

    labeled_devices = {}
    button_names = ["left", "right", "middle"]

    for device_idx in range(num_devices):
        # Create a mock device description
        button_name = button_names[device_idx]
        mock_device_description = f"Mock Tracker Device {device_idx} ({button_name} click) | IP: 127.0.0.1 | Battery: 100% | Sensors: ✓"

        def _prompt_for_device(idx: int, desc: str) -> str:
            try:
                import sys

                # Check if we have a TTY (interactive terminal)
                if not sys.stdin.isatty():
                    return str(idx)  # Use simple label for non-interactive

                # Simple input with basic timeout handling
                try:
                    result = input(f"Label for mock device [{idx}] [{desc}] (blank=skip): ")
                    if result.strip():
                        return result.strip()
                    return str(idx)  # Use index as default label
                except EOFError:
                    print(f"\n[ERR] EOF detected for device {idx}, using default label '{idx}'...")
                    return str(idx)
                except KeyboardInterrupt:
                    print(f"\n[ERR] Keyboard interrupt for device {idx}, using default label '{idx}'...")
                    return str(idx)

            except Exception as e:
                print(f"\n[ERR] Error getting input for device {idx}: {e}, using default label '{idx}'...")
                return str(idx)

        try:
            label = await asyncio.wait_for(asyncio.to_thread(_prompt_for_device, device_idx, mock_device_description), timeout=30.0)
        except asyncio.TimeoutError:
            print(f"\n[WARN] Timeout for device {device_idx}, using default label '{device_idx}'...")
            label = str(device_idx)

        if not label.strip():
            label = str(device_idx)

        # Create the mock labeled device
        mock_device = MockLabeledDevice(
            label=label.strip(),
            name=f"Mock Cursor Tracker {device_idx}",
            ip="127.0.0.1"
        )

        labeled_devices[device_idx] = mock_device

    print("[INIT] Labeled mock devices:")
    for idx, device in labeled_devices.items():
        button_name = button_names[idx]
        print(f"  [{idx}] {device.label} -> {device.name} ({device.ip}) - {button_name} click")

    return labeled_devices


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

    # Number of devices argument
    mock_parser.add_argument(
        "--devices",
        type=int,
        default=1,
        choices=[1, 2, 3],
        help="Number of mock devices to create (1-3, default: 1). Each device uses a different mouse button.",
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
            label=auto_label,
            emission_id=idx
        )

    return labeled


async def execute_mock(args: argparse.Namespace):
    """
    Execute the mock command with the parsed arguments.
    """
    # Discover and setup surface layouts
    print("[SEARCH] Discovering surface layouts...")
    layouts = discover_all_surface_layouts(args.directory)

    if not layouts:
        print("[ERR] No surface layouts found. Please generate at least one surface layout first.")
        return

    if args.auto_label_surface:
        print("🤖 Auto-labeling surface layouts...")
        labeled_surface_layouts = await auto_label_surface_layouts(layouts)
        print(f"[INIT] Auto-labeled {len(labeled_surface_layouts)} surface layouts:")
        for idx, layout in labeled_surface_layouts.items():
            print(f"  [{idx}] {layout.label} -> {layout.id}")
    else:
        labeled_surface_layouts = await setup_labeled_surface_layouts_cli(args.directory)
        print(f"[INIT] Found {len(labeled_surface_layouts)} labeled surface layouts: {list(labeled_surface_layouts.keys())}")

    if len(labeled_surface_layouts) == 0:
        print("[ERR] No labeled surface layouts found. Please generate or label at least one surface layout first.")
        return

    # Setup mock devices
    mock_devices = await setup_mock_devices_cli(num_devices=args.devices)
    if len(mock_devices) == 0:
        print("[ERR] No mock devices labeled.")
        return

    # Start WebSocket server
    print("[INIT] Starting WebSocket server on ws://localhost:8765")
    server, broadcaster_task = await start_ws_server(host="localhost", port=8765)

    try:
        # Start mock tracking for all devices
        print(f"[INIT] Starting mock tracking for {len(mock_devices)} device{'s' if len(mock_devices) > 1 else ''} at {args.frequency} Hz with ±{args.noise_level}px noise...")

        trackers = []
        for device_idx, mock_device in mock_devices.items():
            tracker = await start_mock_tracking(
                labeled_surface_layouts.values(),
                noise_level=args.noise_level,
                device_label=mock_device.label,
                frequency=args.frequency,
                device_index=device_idx
            )
            trackers.append(tracker)

        button_names = ["left", "right", "middle"]
        print("Mock stream started!")
        for i, device in enumerate(mock_devices.values()):
            button_name = button_names[i]
            print(f"🖱️  Device {i} ({device.label}): Click {button_name} mouse button to update gaze position")

        print(f"📊 Emitting at {args.frequency} Hz from {len(mock_devices)} device{'s' if len(mock_devices) > 1 else ''} to all surfaces with random noise")
        print("Press Ctrl+C to stop")

        # Keep running until interrupted
        try:
            while True:
                await asyncio.sleep(1)
        except KeyboardInterrupt:
            print("\n[ERR] KeyboardInterrupt: Stopping mock stream")

    except Exception as e:
        print(f"[ERR] Unexpected error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        print("[CLEAN] Cleaning up...")
        await stop_mock_tracking()  # Stop all trackers
        await stop_ws_server(server, broadcaster_task)
        print("The mock streaming task has stopped")
