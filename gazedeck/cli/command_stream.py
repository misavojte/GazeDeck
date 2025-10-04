# gazedeck/cli/command_stream.py

from __future__ import annotations
import argparse
import asyncio
import queue
from typing import Dict, Any

from gazedeck.cli.setup_labeled_devices import setup_labeled_devices_cli
from gazedeck.cli.setup_labeled_surface_layouts import setup_labeled_surface_layouts_cli
from gazedeck.core.device_labeling import LabeledDevice
from gazedeck.core.streaming_gaze_mapping import create_streaming_context
from gazedeck.core.surface_layout_labeling import SurfaceLayoutLabeled
from gazedeck.core.surface_layout_discovery import discover_all_surface_layouts, SurfaceLayout
from gazedeck.core.websocket_server import WebSocketServer

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
        help="Device discovery window in seconds (default: 3.0). "
             "In manual IP mode, this becomes the connection timeout.",
    )
    stream_parser.add_argument(
        "--device-ips",
        nargs="+",
        help="Space-separated list of IP addresses to connect to directly. "
             "Skips automatic discovery and connects directly to these IPs. "
             "Useful when mDNS discovery is blocked (e.g. mobile hotspots). "
             "Example: --device-ips 192.168.1.100 10.0.0.50",
    )

    # AprilTag detector parameters
    stream_parser.add_argument(
        "--threads",
        type=int,
        default=2,
        help="Number of threads for AprilTag detection (default: 2).",
    )
    stream_parser.add_argument(
        "--decimate",
        type=float,
        default=2,
        help="Quad decimation factor for AprilTag detection (default: 2 - high decimation for performance).",
    )
    stream_parser.add_argument(
        "--sharpening",
        type=float,
        default=0.5,
        help="Decode sharpening factor for AprilTag detection (default: 0.5 - enhanced detection).",
    )
    stream_parser.add_argument(
        "--apriltag-quad-sigma",
        type=float,
        default=0.0,
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
        default=0.8,
        help="Exponential smoothing alpha for gaze filter (0.0-1.0, default: 0.25). Lower = smoother, higher = more responsive.",
    )

    # Auto-label surface layouts
    stream_parser.add_argument(
        "--auto-label-surface",
        action="store_true",
        help="Automatically label surfaces based on their IDs instead of prompting for labels.",
    )
    
    # CV visualization
    stream_parser.add_argument(
        "--cv",
        action="store_true", 
        help="Enable live OpenCV visualization showing detected tags and surfaces.",
    )
    return stream_parser


async def auto_label_surface_layouts(layouts: Dict[int, SurfaceLayout]) -> Dict[int, SurfaceLayoutLabeled]:
    """
    Automatically label surface layouts using their IDs directly as labels.

    Args:
        layouts: Dictionary of discovered surface layouts {index -> SurfaceLayout}

    Returns:
        Dictionary of auto-labeled surface layouts {index -> SurfaceLayoutLabeled}
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


async def execute_stream(args: argparse.Namespace):
    """
    Execute the stream command with the parsed arguments.
    """
    # discover and setup surface layouts
    print("[SEARCH] Discovering surface layouts...")
    layouts = discover_all_surface_layouts(args.directory)

    if not layouts:
        print("[ERR] No surface layouts found. Please generate at least one surface layout first.")
        return

    if args.auto_label_surface:
        print("[INIT] Auto-labeling surface layouts...")
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

    # discover and setup devices
    labeled_devices = await setup_labeled_devices_cli(args.duration, getattr(args, 'device_ips', None))
    print(f"[INIT] Found {len(labeled_devices)} labeled devices: {list(labeled_devices.keys())}")
    if len(labeled_devices) == 0:
        print("[ERR] No labeled devices found. Please discover and label at least one device first.")
        return

    # Create and start WebSocket server with path-based routing
    print("[INIT] Starting WebSocket server on ws://localhost:8765")
    print("[INFO] Routes: / (gaze), /fpv/{deviceId} (video)")
    ws_server = WebSocketServer(host="localhost", port=8765)
    await ws_server.start()

    # Set up signal handling for graceful shutdown
    shutdown_event = asyncio.Event()

    try:
        apriltag_params = {
            'nthreads': args.threads,
            'quad_decimate': args.decimate,
            'decode_sharpening': args.sharpening,
            'quad_sigma': args.apriltag_quad_sigma,
            'debug': args.apriltag_debug,
            # PRECISION PARAMETERS:
            'refine_edges': args.apriltag_refine_edges,
        }

        # Create streaming tasks with proper async patterns
        stream_tasks = []

        # Create WebSocket streaming tasks for all devices
        for labeled_device in labeled_devices.values():
            task = asyncio.create_task(
                stream_gaze_mapped_data_to_ws(
                    labeled_device, labeled_surface_layouts,
                    apriltag_params, args.gaze_filter_alpha, shutdown_event, ws_server
                )
            )
            stream_tasks.append(task)

        # Add CV visualization as parallel task if requested
        if args.cv:
            if len(labeled_devices) > 1:
                print("[WARN] CV visualization currently supports single device only. Using first device.")
            first_device = next(iter(labeled_devices.values()))
            cv_task = asyncio.create_task(
                stream_cv_visualization(first_device, labeled_surface_layouts, apriltag_params, layouts, shutdown_event, ws_server)
            )
            stream_tasks.append(cv_task)
            print(f"[INFO] CV video available at ws://localhost:8765/fpv/{first_device.emission_id}")

        print("All streams started")
        print("Press Ctrl+C to stop the streams")

        # Use asyncio.gather with proper exception handling
        # This is the recommended pattern for managing multiple concurrent tasks
        try:
            await asyncio.gather(*stream_tasks, return_exceptions=True)
        except asyncio.CancelledError:
            # This is expected during shutdown - suppress it
            pass

    except KeyboardInterrupt:
        print("\n[STOP] Received keyboard interrupt, initiating graceful shutdown...")
        shutdown_event.set()
        
        # Device close is now handled in streaming context cleanup
    except ValueError as e:
        print(f"[ERR] ValueError: {e}")
        shutdown_event.set()
    except Exception as e:
        print(f"[ERR] Unexpected error: {e}")
        shutdown_event.set()
    finally:
        # Graceful shutdown with proper task cancellation
        print("[STOP] Initiating graceful shutdown...")

        # Cancel all tasks (fire-and-forget)
        for task in stream_tasks:
            if not task.done():
                task.cancel()

        # Short, non-blocking wait for tasks to acknowledge cancellation
        if stream_tasks:
            try:
                await asyncio.wait_for(
                    asyncio.gather(*stream_tasks, return_exceptions=True),
                    timeout=0.3
                )
            except (asyncio.TimeoutError, asyncio.CancelledError):
                pass

        # Stop WebSocket server
        try:
            await ws_server.stop()
        except (Exception, asyncio.CancelledError):
            pass

        # Devices already closed in KeyboardInterrupt handler

        print("[STOP] Streaming stopped gracefully")



async def stream_gaze_mapped_data_to_ws(labeled_device: LabeledDevice, labeled_surface_layouts: Dict[int, SurfaceLayoutLabeled], apriltag_params: Dict[str, Any], gaze_filter_alpha: float, shutdown_event: asyncio.Event, ws_server: WebSocketServer):
    """
    WebSocket streaming with proper async context management.
    
    Uses streaming context manager for better resource cleanup
    and implements proper async patterns for real-time processing.
    
    Performance optimized for high-frequency gaze tracking:
    - Binary serialization: 30x faster than JSON
    - One message per surface: eliminates nested structures
    - NaN for invalid data: mathematical correctness with minimal overhead
    - Proper async context management for resource cleanup
    """
    try:
        print(f"[INIT] Starting gaze streaming for device: {labeled_device.emission_id} {labeled_device.label}")
        
        # Use the new context manager for proper resource management
        async with create_streaming_context(
            labeled_device, labeled_surface_layouts,
            apriltag_params, gaze_filter_alpha
        ) as (queue_result, context_shutdown):
            
            print(f"[INIT] Streaming context created for device {labeled_device.emission_id} {labeled_device.label}")

            # Pre-compute surface ID mapping for performance
            device_id = labeled_device.emission_id
            surface_id_map = {
                surface_layout.label: surface_layout.emission_id
                for surface_layout in labeled_surface_layouts.values()
            }

            message_count = 0
            
            # Real-time processing loop with proper async patterns
            while not shutdown_event.is_set() and not context_shutdown.is_set():
                try:
                    # Use timeout to allow periodic shutdown checks
                    result = await asyncio.wait_for(queue_result.get(), timeout=0.1)
                    message_count += 1
                    
                    # Send one binary message per surface (not nested JSON)
                    for surface_label, surface_result in result.surface_gaze.items():
                        surface_id = surface_id_map.get(surface_label, 0)
                        
                        if surface_result is None:
                            # Surface not detected - use NaN coordinates
                            x, y = float('nan'), float('nan')
                        else:
                            # Valid surface detection
                            x, y = surface_result.x, surface_result.y
                        
                        # Binary serialization - massively more efficient than JSON
                        ws_server.broadcast_gaze_data(device_id, surface_id, x, y, result.timestamp)
                        
                except asyncio.TimeoutError:
                    # No data available, continue to check shutdown
                    continue
                except asyncio.CancelledError:
                    print(f"[STOP] WebSocket streaming cancelled for device {labeled_device.emission_id}")
                    break
                    
            print(f"[STOP] Processed {message_count} messages for device {labeled_device.emission_id}")
            
    except asyncio.CancelledError:
        print(f"[STOP] WebSocket streaming task cancelled for device {labeled_device.emission_id}")
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ERR] Unexpected error in WebSocket streaming: {e}")
        raise


async def stream_cv_visualization(labeled_device: LabeledDevice, labeled_surface_layouts: Dict[int, SurfaceLayoutLabeled], apriltag_params: Dict[str, Any], surface_layouts: Dict[int, SurfaceLayout], shutdown_event: asyncio.Event, ws_server: WebSocketServer):
    """
    HighGUI-free CV visualization:
    - Detect AprilTags on device video
    - Overlay with draw_tag_visualization
    - JPEG-encode and broadcast over WebSocket on path /video/{deviceEmissionId}
    """
    import cv2
    import contextlib
    from gazedeck.core.cv_visualizer import draw_tag_visualization
    from gazedeck.core.camera_distortion import CameraDistortion
    from gazedeck.core.device_senzors import get_sensor_urls
    from gazedeck.core.queues import get_most_recent_item
    from gazedeck.core.marker_detection import SimpleMarkerDetector
    from gazedeck.core.streaming_gaze_mapping import enqueue_sensor_data
    from pupil_labs.realtime_api import receive_video_frames
    from pupil_labs.realtime_api.streaming import VideoFrame

    try:
        device_path = f"/video/{labeled_device.emission_id}"
        print(f"[INIT] Starting CV stream at ws://{ws_server.host}:{ws_server.port}{device_path} for device: {labeled_device.emission_id} {labeled_device.label}")

        _, sensor_video_url, _ = await get_sensor_urls(labeled_device)

        queue_video: asyncio.Queue[VideoFrame] = asyncio.Queue(maxsize=3)
        video_task = asyncio.create_task(
            enqueue_sensor_data(
                receive_video_frames(sensor_video_url, run_loop=True),
                queue_video,
                shutdown_event,
                f"CV video (device: {labeled_device.emission_id})"
            )
        )

        camera_distortion = CameraDistortion(labeled_device.camera_calibration)
        detector = SimpleMarkerDetector(apriltag_params)

        frame_idx = 0
        try:
            while not shutdown_event.is_set():
                try:
                    _, video_frame = await get_most_recent_item(queue_video, timeout=0.1)
                except asyncio.TimeoutError:
                    continue

                frame_idx += 1
                if frame_idx % 2 != 0:
                    continue  # ~15 FPS

                if hasattr(video_frame, "bgr_pixels"):
                    frame_bgr = video_frame.bgr_pixels
                elif hasattr(video_frame, "bgr_buffer"):
                    frame_bgr = video_frame.bgr_buffer()
                else:
                    continue

                detected_markers = await asyncio.to_thread(
                    detector.detect_markers, frame_bgr, camera_distortion
                )

                vis_frame = draw_tag_visualization(frame_bgr, detected_markers)

                # JPEG encode and broadcast
                ok, buf = cv2.imencode(".jpg", vis_frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
                if ok and buf is not None and len(buf) > 0:
                    jpeg_bytes = buf.tobytes()
                    fpv_path = f"/fpv/{labeled_device.emission_id}"
                    ws_server.broadcast_nowait(jpeg_bytes, path=fpv_path)

                await asyncio.sleep(0.005)
        finally:
            shutdown_event.set()
            if not video_task.done():
                video_task.cancel()
                with contextlib.suppress(asyncio.CancelledError, asyncio.TimeoutError):
                    await asyncio.wait_for(video_task, timeout=1.0)

    except asyncio.CancelledError:
        print(f"[STOP] CV JPEG stream cancelled for device {labeled_device.emission_id}")
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ERR] Unexpected error in CV JPEG stream: {e}")
        raise


