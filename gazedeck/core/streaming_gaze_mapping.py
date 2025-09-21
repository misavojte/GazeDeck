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

# internal
from gazedeck.core.device_labeling import LabeledDevice
from gazedeck.core.device_senzors import get_sensor_urls
from gazedeck.core.gaze_mapper import GazeMapper
from gazedeck.core.surface_layout_labeling import SurfaceLayoutLabeled
from gazedeck.core.queues import enqueue_sensor_data, get_most_recent_item, get_closest_item
from gazedeck.core.gaze_filter import ExponentialFilter
from pupil_labs.realtime_api.streaming import IMUData

class GazeMappedSurfaceResult(NamedTuple):
    x: float
    y: float

class GazeMappedResult(NamedTuple):
    timestamp: float
    surface_gaze: Dict[str, Optional[GazeMappedSurfaceResult]] # key is surface label, value is GazeMappedSurfaceResult

async def stream_gaze_mapped_data(labeled_device: LabeledDevice, surface_layouts: Dict[int, SurfaceLayoutLabeled], apriltag_params: Dict[str, Any], gaze_filter_alpha: float = 0.25) -> asyncio.Queue[GazeMappedResult]:

    sensor_gaze_url, sensor_video_url, sensor_imu_url = await get_sensor_urls(labeled_device)

    restart_on_disconnect = True
    
    # We must limit the queue size to avoid memory issues
    MAX_QUEUE_VIDEO_SIZE = 10
    MAX_QUEUE_GAZE_SIZE = 256

    queue_video: asyncio.Queue[VideoFrame] = asyncio.Queue(maxsize=MAX_QUEUE_VIDEO_SIZE)
    queue_gaze: asyncio.Queue[GazeData] = asyncio.Queue(maxsize=MAX_QUEUE_GAZE_SIZE)
    queue_imu: asyncio.Queue[IMUData] = asyncio.Queue(maxsize=MAX_QUEUE_GAZE_SIZE)
    # this will be consumed by the caller and we need to pass it to the caller
    queue_result: asyncio.Queue[GazeMappedResult] = asyncio.Queue(maxsize=MAX_QUEUE_GAZE_SIZE)
    
    # Start the video collection tasks
    asyncio.create_task(
        enqueue_sensor_data(
            receive_video_frames(sensor_video_url, run_loop=restart_on_disconnect),
            queue_video,
            f"Incoming video (device: {labeled_device.emission_id} {labeled_device.label})",
        )
    )

    # Start the gaze collection task
    asyncio.create_task(
        enqueue_sensor_data(
            receive_gaze_data(sensor_gaze_url, run_loop=restart_on_disconnect),
            queue_gaze,
            f"Incoming gaze (device: {labeled_device.emission_id} {labeled_device.label})",
        )
    )

    # Start the gaze mapping task but don't await it - it runs forever
    asyncio.create_task(
        match_and_map_gaze(queue_video, queue_gaze, queue_result, labeled_device.camera_calibration, surface_layouts, apriltag_params, gaze_filter_alpha)
    )
    
    print(f"✅ Gaze mapping task started for device {labeled_device.emission_id} {labeled_device.label}, returning queue")
    return queue_result

async def match_and_map_gaze(queue_video: asyncio.Queue[VideoFrame], queue_gaze: asyncio.Queue[GazeData], output_queue: asyncio.Queue[GazeMappedResult], camera_distortion: dict, surface_layouts: Dict[int, SurfaceLayoutLabeled], apriltag_params: Dict[str, Any], gaze_filter_alpha: float = 0.25) -> None:

    print(f"🗺️ Initializing gaze mapper with {len(surface_layouts)} surface layouts")

    # initialize gaze mapper with camera distortion
    gaze_mapper = GazeMapper(camera_distortion, apriltag_params)

    # Direct mapping using emission_ids - no UUID conversion needed
    for surface_layout in surface_layouts.values():
        gaze_mapper.add_surface(
            surface_layout.tags,
            surface_layout.size,
            surface_layout.emission_id  # Use emission_id directly
        )

    print(f"📋 Surface mapping complete")

    # Initialize gaze filter
    gaze_filter = ExponentialFilter(alpha=gaze_filter_alpha)

    print("🔄 Starting gaze mapping loop...")

    # SIMPLIFIED IMPLEMENTATION: No caching, immediate surface recalculation per gaze
    # This ensures no drifting during rapid head movements
    while True:
        # Get the most recent video frame and gaze data
        video_ts, video_item = await get_most_recent_item(queue_video)
        #gaze_ts, gaze_item = await get_most_recent_item(queue_gaze)
        gaze_ts, gaze_item = await get_closest_item(queue_gaze, video_ts)
        
        # Process video frame for surface detection (no caching)
        await asyncio.to_thread(gaze_mapper.process_scene, video_item)
        
        # Process gaze using fresh surface detection
        gaze_mapped_result = await asyncio.to_thread(gaze_mapper.process_gaze, gaze_item)

        if gaze_mapped_result is None or len(gaze_mapped_result.mapped_gaze) == 0:
            # No surface detected or no valid mapping, emit None for all surfaces
            surface_gaze: Dict[str, Optional[GazeMappedSurfaceResult]] = {layout.label: None for layout in surface_layouts.values()}
        else:
            surface_gaze: Dict[str, Optional[GazeMappedSurfaceResult]] = {}
            for surface_layout in surface_layouts.values():
                emission_id = surface_layout.emission_id
                surface_label = surface_layout.label

                if emission_id in gaze_mapped_result.mapped_gaze and gaze_mapped_result.mapped_gaze[emission_id]:
                    mapped_data = gaze_mapped_result.mapped_gaze[emission_id][0]

                    # Apply filter
                    smooth_x, smooth_y = gaze_filter.filter(mapped_data.x, mapped_data.y)

                    surface_gaze[surface_label] = GazeMappedSurfaceResult(
                        x=smooth_x,
                        y=smooth_y
                    )
                else:
                    surface_gaze[surface_label] = None

        result = GazeMappedResult(
            timestamp=gaze_ts,
            surface_gaze=surface_gaze,
        )
        output_queue.put_nowait(result)

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

