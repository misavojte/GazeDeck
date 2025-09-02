# gazedeck/cli/command_stream.py

# python
from __future__ import annotations

# external
import argparse
import asyncio
import json
from typing import Dict

from gazedeck.cli.setup_labeled_devices import setup_labeled_devices_cli
from gazedeck.cli.setup_labeled_surface_layouts import setup_labeled_surface_layouts_cli
from gazedeck.core.device_labeling import LabeledDevice
from gazedeck.core.streaming_gaze_mapping import stream_gaze_mapped_data
from gazedeck.core.surface_layout_labeling import SurfaceLayoutLabeled
from gazedeck.core.websocket_server import start_ws_server, stop_ws_server, broadcast_nowait

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
        default=10.0,
        help="Device discovery window in seconds (default: 10.0).",
    )
    return stream_parser


async def execute_stream(args: argparse.Namespace):
    """
    Execute the stream command with the parsed arguments.
    """
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

    # Start WebSocket server
    print("Starting WebSocket server on ws://localhost:8765")
    server, broadcaster_task = await start_ws_server(host="localhost", port=8765)

    try:
        stream_tasks = [
            asyncio.create_task(stream_gaze_mapped_data_to_ws(labeled_device, labeled_surface_layouts)) for labeled_device in labeled_devices.values()
        ]

        print("All streams started")
        print("Press Ctrl+C to stop the streams")

        await asyncio.gather(*stream_tasks) # wait for all streams to finish (should be infinite)
    except KeyboardInterrupt:
        print("❌ KeyboardInterrupt: Stopping the streams")
    except ValueError as e:
        print(f"❌ ValueError: {e}")
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
    finally:
        for task in stream_tasks:
            task.cancel()
        await stop_ws_server(server, broadcaster_task)
        print("The streaming task has stopped")



async def stream_gaze_mapped_data_to_ws(labeled_device: LabeledDevice, labeled_surface_layouts: Dict[int, SurfaceLayoutLabeled]):
    """
    Stream gaze mapped data from a single device to a WebSocket server.
    """
    try:
        queue_result = await stream_gaze_mapped_data(labeled_device, labeled_surface_layouts)
        while True:
            result = await queue_result.get()
            # convert to json safely (json.dumps is not enough for datetime objects)

            # Convert datetime to ISO format string for JSON serialization
            result_json = {
                "timestamp": result["timestamp"].isoformat(),
                "surface_gaze": result["surface_gaze"]
            }

            broadcast_nowait(json.dumps(result_json))
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Unexpected error in stream_gaze_mapped_data_to_ws: {e}")
        return
