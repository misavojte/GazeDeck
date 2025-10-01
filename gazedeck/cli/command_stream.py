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
from gazedeck.core.websocket_server import start_ws_server, stop_ws_server, broadcast_gaze_data

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
    labeled_devices = await setup_labeled_devices_cli(args.duration)
    print(f"[INIT] Found {len(labeled_devices)} labeled devices: {list(labeled_devices.keys())}")
    if len(labeled_devices) == 0:
        print("[ERR] No labeled devices found. Please discover and label at least one device first.")
        return

    # Start WebSocket server
    print("[INIT] Starting WebSocket server on ws://localhost:8765")
    server, broadcaster_task = await start_ws_server(host="localhost", port=8765)

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
                    apriltag_params, args.gaze_filter_alpha, shutdown_event
                )
            )
            stream_tasks.append(task)

        # Add CV visualization as parallel task if requested
        if args.cv:
            if len(labeled_devices) > 1:
                print("[WARN] CV visualization currently supports single device only. Using first device.")
            first_device = next(iter(labeled_devices.values()))
            cv_task = asyncio.create_task(
                stream_cv_visualization(first_device, labeled_surface_layouts, apriltag_params, layouts, shutdown_event)
            )
            stream_tasks.append(cv_task)

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
            await stop_ws_server(server, broadcaster_task)
        except (Exception, asyncio.CancelledError):
            pass

        # Devices already closed in KeyboardInterrupt handler

        print("[STOP] Streaming stopped gracefully")



async def stream_gaze_mapped_data_to_ws(labeled_device: LabeledDevice, labeled_surface_layouts: Dict[int, SurfaceLayoutLabeled], apriltag_params: Dict[str, Any], gaze_filter_alpha: float, shutdown_event: asyncio.Event):
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
                        broadcast_gaze_data(device_id, surface_id, x, y, result.timestamp)
                        
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


async def stream_cv_visualization(labeled_device: LabeledDevice, labeled_surface_layouts: Dict[int, SurfaceLayoutLabeled], apriltag_params: Dict[str, Any], surface_layouts: Dict[int, SurfaceLayout], shutdown_event: asyncio.Event):
    """
    CV visualization with proper async patterns and graceful shutdown.
    
    Uses asyncio.Event for async coordination, proper exception handling
    and resource cleanup, better integration with asyncio task management,
    and maintains performance optimizations.
    """
    import threading
    from gazedeck.core.cv_visualizer import CVVisualizer
    from gazedeck.core.camera_distortion import CameraDistortion
    from gazedeck.core.device_senzors import get_sensor_urls
    from gazedeck.core.queues import get_most_recent_item
    from gazedeck.core.marker_detection import SimpleMarkerDetector
    from gazedeck.core.streaming_gaze_mapping import enqueue_sensor_data
    from pupil_labs.realtime_api import receive_video_frames
    from pupil_labs.realtime_api.streaming import VideoFrame

    try:
        print(f"[INIT] Starting CV visualization for device: {labeled_device.emission_id} {labeled_device.label}")
        print("[INFO] Press ESC to stop visualization")

        # Get sensor URLs
        _, sensor_video_url, _ = await get_sensor_urls(labeled_device)

        # Initialize lightweight video queue (smaller for CV)
        MAX_QUEUE_VIDEO_SIZE = 3  # Smaller queue for faster processing
        queue_video: asyncio.Queue[VideoFrame] = asyncio.Queue(maxsize=MAX_QUEUE_VIDEO_SIZE)

        # Use the passed shutdown_event for coordination

        # Start video collection task with shutdown support
        video_task = asyncio.create_task(
            enqueue_sensor_data(
                receive_video_frames(sensor_video_url, run_loop=True),
                queue_video,
                shutdown_event,
                f"CV video (device: {labeled_device.emission_id})"
            )
        )

        # Initialize lightweight components for CV only
        camera_distortion = CameraDistortion(labeled_device.camera_calibration)
        detector = SimpleMarkerDetector(apriltag_params)

        # Thread-safe queue for passing frames to GUI thread
        frame_queue: queue.Queue = queue.Queue(maxsize=2)  # Small queue to prevent memory buildup
        stop_event = threading.Event()  # Still use threading.Event for GUI thread coordination

        print("[INIT] Starting CV visualization loop...")

        def gui_thread():
            """Separate thread for all OpenCV GUI operations - completely non-blocking."""
            visualizer = CVVisualizer()

            try:
                while not stop_event.is_set():
                    try:
                        # Non-blocking frame retrieval with timeout
                        frame_data = frame_queue.get(timeout=0.1)

                        if frame_data is None:  # Sentinel value to stop
                            break

                        frame_bgr, detected_markers = frame_data

                        # Show visualization in GUI thread (blocking is OK here)
                        visualizer.show_frame(frame_bgr, detected_markers)

                        # Check for ESC key in GUI thread
                        if visualizer.should_close():
                            print("[STOP] Closing CV visualization")
                            break

                    except queue.Empty:
                        # No new frames, continue GUI event loop
                        continue
                    except Exception as e:
                        print(f"[WARN] GUI thread error: {e}")
                        break

            finally:
                visualizer.cleanup()

        # Start GUI thread
        gui_thread_instance = threading.Thread(target=gui_thread, daemon=True, name=f"CV-GUI-{labeled_device.emission_id}")
        gui_thread_instance.start()

        frame_count = 0
        try:
            while not shutdown_event.is_set():
                try:
                    # Get latest video frame (non-blocking with timeout)
                    _, video_frame = await get_most_recent_item(queue_video, timeout=0.1)

                    frame_count += 1

                    # Process every 2nd frame to reduce CPU load (15 FPS instead of 30)
                    if frame_count % 2 != 0:
                        continue

                    # Get frame data for visualization
                    if hasattr(video_frame, 'bgr_pixels'):
                        frame_bgr = video_frame.bgr_pixels
                    elif hasattr(video_frame, 'bgr_buffer'):
                        frame_bgr = video_frame.bgr_buffer()
                    else:
                        continue

                    # Lightweight marker detection for visualization only (in thread pool)
                    detected_markers = await asyncio.to_thread(
                        detector.detect_markers, frame_bgr, camera_distortion
                    )

                    # Put frame in GUI queue (non-blocking)
                    try:
                        # Remove old frame if queue is full
                        while frame_queue.full():
                            try:
                                frame_queue.get_nowait()
                            except queue.Empty:
                                break

                        frame_queue.put_nowait((frame_bgr, detected_markers))
                    except queue.Full:
                        # Drop frame if queue is full (maintains performance)
                        pass

                except asyncio.TimeoutError:
                    # No new frame available, continue processing
                    pass
                except asyncio.CancelledError:
                    print("[STOP] CV visualization cancelled")
                    break
                except Exception as e:
                    print(f"[WARN] CV frame processing error: {e}")

                # Small sleep to prevent busy waiting
                await asyncio.sleep(0.01)  # Very short sleep for responsiveness

        finally:
            # Graceful shutdown sequence
            print("[CLEAN] Cleaning up CV visualization...")
            
            # Signal async tasks to stop
            shutdown_event.set()
            
            # Cancel video task
            if not video_task.done():
                video_task.cancel()
                try:
                    await asyncio.wait_for(video_task, timeout=1.0)
                except (asyncio.CancelledError, asyncio.TimeoutError):
                    pass
            
            # Signal GUI thread to stop
            stop_event.set()
            try:
                frame_queue.put(None, timeout=0.5)  # Sentinel value
            except queue.Full:
                pass

            # Wait for GUI thread to finish
            gui_thread_instance.join(timeout=1.0)

    except asyncio.CancelledError:
        print(f"[STOP] CV visualization cancelled for device {labeled_device.emission_id}")
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ERR] Unexpected error in CV visualization: {e}")
        raise


