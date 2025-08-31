from __future__ import annotations

import argparse
import asyncio
from gazedeck.cli.setup_labeled_devices import setup_labeled_devices_cli
from gazedeck.core import state

async def run_discovery_and_label(duration: float = 3.0):
    labeled_devices = await setup_labeled_devices_cli(duration)
    state.LABELED_DEVICES.update(labeled_devices)

async def cleanup_devices():
    for device in state.LABELED_DEVICES.values():
        await device.device.close()
    state.LABELED_DEVICES.clear()


def main() -> None:
    parser = argparse.ArgumentParser(prog="gazedeck", description="Gazedeck setup utilities")

    # Create subcommands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Test discovery command
    test_discovery_parser = subparsers.add_parser("test-device-discovery", help="Run test of device discovery + labeling")
    test_discovery_parser.add_argument(
        "--duration",
        type=float,
        default=3.0,
        help="Device discovery window in seconds (default: 3.0).",
    )

    args = parser.parse_args()

    if args.command == "test-device-discovery":
        asyncio.run(run_discovery_and_label(args.duration))
        if len(state.LABELED_DEVICES) > 0:
            print(f"Stored {len(state.LABELED_DEVICES)} labeled device(s) in memory.")
        else:
            print("No labeled devices stored.")
        print("Finishing the test. Cleaning up devices...")
        asyncio.run(cleanup_devices())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
