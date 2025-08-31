# gazedeck/cli/command_stream.py

# python
from __future__ import annotations

# external
import argparse

from gazedeck.cli.setup_labeled_devices import setup_labeled_devices_cli
from gazedeck.cli.setup_labeled_surface_layouts import setup_labeled_surface_layouts_cli

def add_stream_parser(subparsers) -> argparse.ArgumentParser:
    """
    Add the stream subparser to the main parser.
    """
    stream_parser = subparsers.add_parser(
        "stream",
        help="Stream gaze data and map it to surfaces from multiple selected devices with discovery steps."
    )

    # it must have surface layouts arguments
    stream_parser.add_argument(
        "--directory",
        type=str,
        default=".",
        help="Directory to search for surface layouts (default: current directory).",
    )

    # it must have duration arguments
    stream_parser.add_argument(
        "--duration",
        type=float,
        default=3.0,
        help="Device discovery window in seconds (default: 3.0).",
    )
    return stream_parser


async def execute_stream(args: argparse.Namespace):
    """
    Execute the stream command with the parsed arguments.
    """
    try:
        # discover and setup surface layouts
        labeled_surface_layouts = await setup_labeled_surface_layouts_cli(args.directory)
        if len(labeled_surface_layouts) == 0:
            print("No labeled surface layouts found. Please generate or label at least one surface layout first.")
            return
        
        # discover and setup devices
        labeled_devices = await setup_labeled_devices_cli(args.duration)
        if len(labeled_devices) == 0:
            print("No labeled devices found. Please discover and label at least one device first.")
            return

        pass # TODO: implement the stream command
    except ValueError as e:
        print(f"❌ ValueError: {e}")
        return
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return