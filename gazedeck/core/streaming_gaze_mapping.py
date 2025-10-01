# gazedeck/core/streaming_gaze_mapping.py

# pupil labs realtime api
from pupil_labs.neon_recording.calib import Calibration
from pupil_labs.realtime_api.streaming import GazeData
from pupil_labs.realtime_api import (
    VideoFrame,
    receive_gaze_data,
    receive_video_frames,
)

# python
import asyncio
from typing import Dict, Optional, Any
from typing import NamedTuple
from contextlib import asynccontextmanager

# internal
from gazedeck.core.device_labeling import LabeledDevice
from gazedeck.core.device_senzors import get_sensor_urls
from gazedeck.core.gaze_mapper import GazeMapper
from gazedeck.core.surface_layout_labeling import SurfaceLayoutLabeled
from gazedeck.core.queues import get_most_recent_item, get_closest_item
from gazedeck.core.gaze_filter import ExponentialFilter
from pupil_labs.realtime_api.streaming import IMUData

class GazeMappedSurfaceResult(NamedTuple):
    x: float
    y: float

class GazeMappedResult(NamedTuple):
    timestamp: float
    surface_gaze: Dict[str, Optional[GazeMappedSurfaceResult]] # key is surface label, value is GazeMappedSurfaceResult

@asynccontextmanager
async def create_streaming_context(labeled_device: LabeledDevice, surface_layouts: Dict[int, SurfaceLayoutLabeled], apriltag_params: Dict[str, Any], gaze_filter_alpha: float = 0.25):
    """
    Async context manager for streaming gaze mapping resources.
    
    Ensures proper cleanup of tasks and queues when streaming stops.
    Best practice: Use context managers for resource lifecycle management.
    """
    sensor_gaze_url, sensor_video_url, sensor_imu_url = await get_sensor_urls(labeled_device)
    
    # Optimized queue sizes for real-time processing with backpressure
    MAX_QUEUE_VIDEO_SIZE = 5   # Smaller video queue for lower latency
    MAX_QUEUE_GAZE_SIZE = 64   # Reduced gaze queue size for real-time response
    MAX_QUEUE_RESULT_SIZE = 32 # Result queue with backpressure control
    
    # Create queues with proper sizing for real-time processing
    queue_video: asyncio.Queue[VideoFrame] = asyncio.Queue(maxsize=MAX_QUEUE_VIDEO_SIZE)
    queue_gaze: asyncio.Queue[GazeData] = asyncio.Queue(maxsize=MAX_QUEUE_GAZE_SIZE)
    queue_result: asyncio.Queue[GazeMappedResult] = asyncio.Queue(maxsize=MAX_QUEUE_RESULT_SIZE)
    
    # Shutdown coordination using asyncio.Event (not threading.Event)
    shutdown_event = asyncio.Event()
    
    tasks = []
    
    try:
        # Start sensor data collection tasks
        video_task = asyncio.create_task(
            enqueue_sensor_data(
                receive_video_frames(sensor_video_url, run_loop=True),
                queue_video,
                shutdown_event,
                f"Incoming video (device: {labeled_device.emission_id} {labeled_device.label})"
            )
        )
        
        gaze_task = asyncio.create_task(
            enqueue_sensor_data(
                receive_gaze_data(sensor_gaze_url, run_loop=True),
                queue_gaze,
                shutdown_event,
                f"Incoming gaze (device: {labeled_device.emission_id} {labeled_device.label})"
            )
        )
        
        # Start gaze mapping task
        mapping_task = asyncio.create_task(
            match_and_map_gaze(
                queue_video, queue_gaze, queue_result,
                labeled_device.camera_calibration, surface_layouts,
                apriltag_params, gaze_filter_alpha, shutdown_event
            )
        )
        
        tasks = [video_task, gaze_task, mapping_task]
        
        print(f"[INIT] Streaming context initialized for device {labeled_device.emission_id} {labeled_device.label}")
        
        yield queue_result, shutdown_event
        
    finally:
        # Graceful shutdown: signal all tasks to stop
        shutdown_event.set()
        
        # IMMEDIATELY close device to stop RTSP streams
        try:
            await labeled_device.device.close()
        except Exception:
            pass
        
        # Cancel all tasks with proper cleanup
        for task in tasks:
            if not task.done():
                task.cancel()
        
        # Wait for tasks to complete gracefully
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        
        print(f"[CLEAN] Streaming context cleaned up for device {labeled_device.emission_id} {labeled_device.label}")



async def enqueue_sensor_data(sensor_stream, queue: asyncio.Queue, shutdown_event: asyncio.Event, stream_name: str):
    """
    Sensor data enqueuing with graceful shutdown support.
    
    Uses asyncio.Event for proper async coordination instead of threading primitives.
    Implements backpressure handling to prevent memory issues in real-time processing.
    """
    try:
        async for data in sensor_stream:
            if shutdown_event.is_set():
                break
                
            # Implement backpressure: drop oldest items if queue is full
            # This prevents blocking in real-time scenarios
            while queue.full():
                try:
                    queue.get_nowait()  # Drop oldest item
                except asyncio.QueueEmpty:
                    break
            
            try:
                # Put tuple (timestamp, data) to match expected format
                queue.put_nowait((data.timestamp_unix_seconds, data))
            except asyncio.QueueFull:
                # Should not happen due to backpressure handling above,
                # but included for robustness
                pass
                
    except asyncio.CancelledError:
        print(f"[STOP] {stream_name} cancelled gracefully")
        raise
    except KeyboardInterrupt:
        # Swallow KeyboardInterrupt inside worker to allow single-pass Ctrl+C
        print(f"[STOP] {stream_name} interrupted")
        return
    except Exception as e:
        print(f"[ERR] Error in {stream_name}: {e}")
        raise


async def match_and_map_gaze(queue_video: asyncio.Queue[VideoFrame], queue_gaze: asyncio.Queue[GazeData], output_queue: asyncio.Queue[GazeMappedResult], camera_distortion: dict, surface_layouts: Dict[int, SurfaceLayoutLabeled], apriltag_params: Dict[str, Any], gaze_filter_alpha: float, shutdown_event: asyncio.Event) -> None:
    """
    Gaze mapping with proper async patterns and graceful shutdown.
    
    Uses asyncio.Event for shutdown coordination, implements proper exception handling,
    optimizes CPU-intensive operations with asyncio.to_thread, and adds backpressure 
    handling for output queue.
    """
    print(f"[INIT] Initializing gaze mapper with {len(surface_layouts)} surface layouts")
    
    try:
        # Initialize components
        gaze_mapper = GazeMapper(camera_distortion, apriltag_params)
        
        # Direct mapping using emission_ids - no UUID conversion needed
        for surface_layout in surface_layouts.values():
            gaze_mapper.add_surface(
                surface_layout.tags,
                surface_layout.size,
                surface_layout.emission_id
            )
        
        print(f"[INIT] Surface mapping setup complete")
        
        # Initialize gaze filter
        gaze_filter = ExponentialFilter(alpha=gaze_filter_alpha)
        
        print("[INIT] Starting gaze mapping loop...")
        
        # Real-time processing loop with proper async patterns
        while not shutdown_event.is_set():
            try:
                # Use timeout-based processing to prevent indefinite blocking
                # This allows graceful shutdown checks
                video_ts, video_item = await get_most_recent_item(queue_video, timeout=0.1)
                gaze_ts, gaze_item = await get_closest_item(queue_gaze, video_ts, timeout=0.1)
                
                # Process CPU-intensive operations in thread pool
                # This is the correct asyncio pattern for blocking operations
                scene_result = await asyncio.to_thread(gaze_mapper.process_scene, video_item)
                gaze_mapped_result = await asyncio.to_thread(gaze_mapper.process_gaze, gaze_item)
                
                # Build result structure efficiently
                surface_gaze: Dict[str, Optional[GazeMappedSurfaceResult]] = {}

                if gaze_mapped_result is not None:
                    # Pre-compute surface mappings for faster lookup
                    for surface_layout in surface_layouts.values():
                        emission_id = surface_layout.emission_id
                        surface_label = surface_layout.label

                        if emission_id in gaze_mapped_result.mapped_gaze and gaze_mapped_result.mapped_gaze[emission_id]:
                            mapped_data = gaze_mapped_result.mapped_gaze[emission_id][0]

                            # Apply smoothing filter
                            smooth_x, smooth_y = gaze_filter.filter(mapped_data.x, mapped_data.y)

                            surface_gaze[surface_label] = GazeMappedSurfaceResult(
                                x=smooth_x,
                                y=smooth_y
                            )
                        else:
                            surface_gaze[surface_label] = None
                else:
                    # No gaze data available - mark all surfaces as None
                    for surface_layout in surface_layouts.values():
                        surface_gaze[surface_layout.label] = None
                
                result = GazeMappedResult(
                    timestamp=gaze_ts,
                    surface_gaze=surface_gaze,
                )
                
                # Implement backpressure for output queue
                # Drop oldest results if queue is full to maintain real-time performance
                while output_queue.full():
                    try:
                        output_queue.get_nowait()
                    except asyncio.QueueEmpty:
                        break
                
                try:
                    output_queue.put_nowait(result)
                except asyncio.QueueFull:
                    # Should not happen due to backpressure handling
                    pass
                    
            except asyncio.TimeoutError:
                # No data available, continue processing
                # This allows the shutdown check to run periodically
                continue
            except asyncio.CancelledError:
                print("[STOP] Gaze mapping cancelled gracefully")
                break
            except KeyboardInterrupt:
                # Swallow KeyboardInterrupt inside worker to allow single-pass Ctrl+C
                print("[STOP] Gaze mapping interrupted")
                break
            except Exception as e:
                print(f"[WARN] Error in gaze mapping: {e}")
                # Continue processing despite errors
                await asyncio.sleep(0.01)
                
    except asyncio.CancelledError:
        print("[STOP] Gaze mapping task cancelled")
        raise
    except Exception as e:
        print(f"[ERR] Fatal error in gaze mapping: {e}")
        raise
    finally:
        print("[CLEAN] Gaze mapping cleanup complete")



    # ORIGINAL IMPLEMENTATION (commented out for reference):
    # # process gaze and video data
    # frame_count = 0
    # while True:
    #     frame_count += 1
    #     video_ts, video_item = await get_most_recent_item(queue_video)
    #     gaze_ts, gaze_item = await get_closest_item(queue_gaze, video_ts)
    #
    #     # process the frame and gaze data
    #     # add this to the asyncio thread pool
    #     gaze_mapped_result = await asyncio.to_thread(gaze_mapper.process_frame, video_item, gaze_item)
    #
    #     # create result to put into queue (TODO: RIGHT NOW DISTORTED, NEED TO UNDISTORT IN FUTURE)
    #     # for each surface, add the gaze mapped result
    #     if gaze_mapped_result is None:
    #         # no surfaces detected, emit None for each surface
    #         surface_gaze: Dict[str, Optional[GazeMappedSurfaceResult]] = {surface_label: None for surface_label in surface_uid_dict.values()}
    #     else:
    #         # surfaces detected, map gaze to each surface
    #         surface_gaze: Dict[str, Optional[GazeMappedSurfaceResult]] = {}
    #         for surface_uid, surface_label in surface_uid_dict.items():
    #             if surface_uid in gaze_mapped_result.mapped_gaze and gaze_mapped_result.mapped_gaze[surface_uid]:
    #                 mapped_data = gaze_mapped_result.mapped_gaze[surface_uid][0]
    #                 surface_gaze[surface_label] = GazeMappedSurfaceResult(
    #                     x=mapped_data.x,
    #                     y=mapped_data.y,
    #                 )
    #             else:
    #                 surface_gaze[surface_label] = None
    #
    #     result = GazeMappedResult(
    #         timestamp=gaze_ts,
    #         surface_gaze=surface_gaze,
    #     )
    #
    #     output_queue.put_nowait(result)

