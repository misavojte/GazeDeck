# gazedeck/cli/command_stream.py

# python
from __future__ import annotations

# external
import argparse
import asyncio
import json
from typing import Dict, Any

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

    # AprilTag detector parameters
    stream_parser.add_argument(
        "--apriltag-nthreads",
        type=int,
        default=4,
        help="Number of threads for AprilTag detection (default: 1 - optimized for quality).",
    )
    stream_parser.add_argument(
        "--apriltag-quad-decimate",
        type=float,
        default=0.5,
        help="Quad decimation factor for AprilTag detection (default: 0.5 - higher resolution).",
    )
    stream_parser.add_argument(
        "--apriltag-decode-sharpening",
        type=float,
        default=0.25,
        help="Decode sharpening factor for AprilTag detection (default: 0.25 - enhanced detection).",
    )
    stream_parser.add_argument(
        "--apriltag-quad-sigma",
        type=float,
        default=0.5,
        help="Quad sigma factor for AprilTag detection (default: 0.5 - stability enhancement).",
    )
    stream_parser.add_argument(
        "--apriltag-debug",
        type=int,
        default=0,
        help="Debug level for AprilTag detection (default: 0).",
    )
    # PRECISION PARAMETERS:
    stream_parser.add_argument(
        "--apriltag-refine-edges",
        type=int,
        default=1,
        choices=[0, 1],
        help="Enable sub-pixel edge refinement for precise corner detection (default: 1).",
    )

    # Gaze filter parameters
    stream_parser.add_argument(
        "--gaze-filter-alpha",
        type=float,
        default=0.25,
        help="Exponential smoothing alpha for gaze filter (0.0-1.0, default: 0.25). Lower = smoother, higher = more responsive.",
    )
    return stream_parser


async def execute_stream(args: argparse.Namespace):
    """
    Execute the stream command with the parsed arguments.
    """
    # discover and setup surface layouts
    print("🔍 Discovering surface layouts...")
    labeled_surface_layouts = await setup_labeled_surface_layouts_cli(args.directory)
    print(f"📋 Found {len(labeled_surface_layouts)} labeled surface layouts: {list(labeled_surface_layouts.keys())}")
    if len(labeled_surface_layouts) == 0:
        print("❌ No labeled surface layouts found. Please generate or label at least one surface layout first.")
        return

    # discover and setup devices
    print(f"🔍 Discovering devices for {args.duration}s...")
    labeled_devices = await setup_labeled_devices_cli(args.duration)
    print(f"📋 Found {len(labeled_devices)} labeled devices: {list(labeled_devices.keys())}")
    if len(labeled_devices) == 0:
        print("❌ No labeled devices found. Please discover and label at least one device first.")
        return

    # Start WebSocket server
    print("🚀 Starting WebSocket server on ws://localhost:8765")
    server, broadcaster_task = await start_ws_server(host="localhost", port=8765)

    try:
        apriltag_params = {
            'nthreads': args.apriltag_nthreads,
            'quad_decimate': args.apriltag_quad_decimate,
            'decode_sharpening': args.apriltag_decode_sharpening,
            'quad_sigma': args.apriltag_quad_sigma,
            'debug': args.apriltag_debug,
            # PRECISION PARAMETERS:
            'refine_edges': args.apriltag_refine_edges,
        }

        stream_tasks = [
            asyncio.create_task(stream_gaze_mapped_data_to_ws(labeled_device, labeled_surface_layouts, apriltag_params, args.gaze_filter_alpha)) for labeled_device in labeled_devices.values()
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



async def stream_gaze_mapped_data_to_ws(labeled_device: LabeledDevice, labeled_surface_layouts: Dict[int, SurfaceLayoutLabeled], apriltag_params: Dict[str, Any], gaze_filter_alpha: float):
    """
    Stream gaze mapped data from a single device to a WebSocket server.
    """
    try:
        print(f"🎯 Starting gaze streaming for device: {labeled_device.label}")
        queue_result = await stream_gaze_mapped_data(labeled_device, labeled_surface_layouts, apriltag_params, gaze_filter_alpha)
        print(f"📡 Queue created for device {labeled_device.label}, waiting for gaze data...")

        message_count = 0
        while True:
            result = await queue_result.get()
            message_count += 1

            # convert to json safely (json.dumps is not enough for datetime objects)
            # Convert datetime to ISO format string for JSON serialization
            # Convert GazeMappedSurfaceResult dataclass objects to dictionaries
            surface_gaze_dict = {}
            for surface_name, surface_result in result.surface_gaze.items():
                if surface_result is None:
                    surface_gaze_dict[surface_name] = None
                else:
                    surface_gaze_dict[surface_name] = {
                        "x": surface_result.x,
                        "y": surface_result.y,
                        "is_on_surface": surface_result.is_on_surface
                    }

            result_json = {
                "timestamp": result.timestamp.isoformat(),
                "device": labeled_device.label,
                "surface_gaze": surface_gaze_dict
            }

            broadcast_nowait(json.dumps(result_json))

    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"❌ Unexpected error in stream_gaze_mapped_data_to_ws: {e}")
        return
