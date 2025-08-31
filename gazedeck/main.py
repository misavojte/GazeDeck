from __future__ import annotations

import argparse
import asyncio
from gazedeck.cli.setup_device_labeling import run_cli_discovery_and_label
from gazedeck.core import state

async def cleanup_devices():
    for device in state.LABELED_DEVICES.values():
        await device.device.close()
    state.LABELED_DEVICES.clear()


def main() -> None:
    parser = argparse.ArgumentParser(prog="gazedeck", description="Gazedeck setup utilities")
    parser.add_argument(
        "--test-discovery",
        action="store_true",
        help="Run device discovery + labeling (stores results in process memory).",
    )
    parser.add_argument(
        "--duration",
        type=float,
        default=3.0,
        help="Discovery window in seconds (default: 3.0).",
    )
    args = parser.parse_args()

    if args.test_discovery:
        asyncio.run(run_cli_discovery_and_label(args.duration))
        if state.LABELED_DEVICES:
            print(f"Stored {len(state.LABELED_DEVICES)} labeled device(s) in memory.")
        else:
            print("No labeled devices stored.")
        print("Finishing the test. Cleaning up devices...")
        asyncio.run(cleanup_devices())
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
