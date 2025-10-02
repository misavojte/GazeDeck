# gazedeck/cli/command_test_device_discovery.py

from __future__ import annotations

import argparse
from typing import Dict

from gazedeck.cli.setup_labeled_devices import setup_labeled_devices_cli
from gazedeck.core.device_labeling import LabeledDevice


def add_test_device_discovery_parser(subparsers) -> argparse.ArgumentParser:
    """
    Add the test-device-discovery subparser to the main parser.

    Args:
        subparsers: The subparsers object from the main argument parser

    Returns:
        The configured subparser for test-device-discovery command
    """
    test_discovery_parser = subparsers.add_parser(
        "test-device-discovery",
        help="Run test of device discovery + labeling"
    )
    test_discovery_parser.add_argument(
        "--duration",
        type=float,
        default=10.0,
        help="Device discovery window in seconds (default: 10.0). "
             "In manual IP mode, this becomes the connection timeout.",
    )
    test_discovery_parser.add_argument(
        "--device-ips",
        nargs="+",
        help="Space-separated list of IP addresses to connect to directly. "
             "Skips automatic discovery and connects directly to these IPs. "
             "Example: --device-ips 192.168.1.100 10.0.0.50",
    )
    test_discovery_parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable detailed debug logging to troubleshoot discovery issues",
    )
    return test_discovery_parser


async def run_discovery_and_label(duration: float = 10.0, device_ips: List[str] = None) -> Dict[int, LabeledDevice]:
    """
    Run device discovery and labeling for the specified duration.

    Args:
        duration: Time in seconds to discover devices (mDNS mode) or connection timeout (manual mode)
        device_ips: Optional list of IP addresses for direct connection

    Returns:
        Dictionary of labeled devices indexed by their discovery order
    """
    labeled_devices = await setup_labeled_devices_cli(duration, device_ips)
    return labeled_devices


async def cleanup_devices(devices: Dict[int, LabeledDevice]):
    """
    Clean up all stored labeled devices by closing their connections.
    """
    for device in devices.values():
        await device.device.close()
    devices.clear()


async def execute_test_device_discovery(args: argparse.Namespace):
    """
    Execute the test-device-discovery command with the parsed arguments.

    Args:
        args: Parsed command line arguments
    """
    if args.debug:
        from gazedeck.core.device_discovery import enable_discovery_debug_logging
        enable_discovery_debug_logging()
        print("Debug logging enabled - you'll see detailed discovery information")
    
    labeled_devices = await run_discovery_and_label(args.duration, getattr(args, 'device_ips', None))

    if len(labeled_devices) > 0:
        print(f"[INIT] Stored {len(labeled_devices)} labeled device(s) in memory.")
    else:
        if getattr(args, 'device_ips', None):
            print(f"[ERR] No devices found at specified IP addresses: {args.device_ips}")
        else:
            print("[ERR] No labeled devices stored.")

    print("Finishing the test. Cleaning up devices...")
    await cleanup_devices(labeled_devices)
