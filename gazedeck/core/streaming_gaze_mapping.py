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
from typing import Dict, TypeVar, Tuple, Optional, AsyncIterator
from asyncio import QueueEmpty, QueueFull
from datetime import datetime
from dataclasses import dataclass

# internal
from gazedeck.core.device_labeling import LabeledDevice
from gazedeck.core.gaze_mapper import GazeMapper
from gazedeck.core.surface_layout_labeling import SurfaceLayoutLabeled

# Generic type for sensor data items
T = TypeVar('T')

@dataclass(frozen=True)
class GazeMappedSurfaceResult:
    x: float
    y: float
    is_on_surface: bool

@dataclass(frozen=True)
class GazeMappedResult:
    timestamp: datetime
    surface_gaze: Dict[str, Optional[GazeMappedSurfaceResult]]

async def stream_gaze_mapped_data(labeled_device: LabeledDevice, surface_layouts: Dict[int, SurfaceLayoutLabeled]) -> asyncio.Queue[GazeMappedResult]:

    status = await labeled_device.device.get_status()
    sensor_gaze = status.direct_gaze_sensor()
    if not sensor_gaze.connected:
        raise RuntimeError("Could not connect to direct gaze sensor for device labeled as %s", labeled_device.label)
    
    sensor_video = status.direct_world_sensor()
    if not sensor_video.connected:
        raise RuntimeError("Could not connect to direct world sensor (FPV camera) for device labeled as %s", labeled_device.label)

    restart_on_disconnect = True
    
    queue_video: asyncio.Queue[VideoFrame] = asyncio.Queue()
    queue_gaze: asyncio.Queue[GazeData] = asyncio.Queue()
    # this will be consumed by the caller and we need to pass it to the caller
    queue_result: asyncio.Queue[GazeMappedResult] = asyncio.Queue()
    
    process_video = asyncio.create_task(
        enqueue_sensor_data(
            receive_video_frames(sensor_video.url, run_loop=restart_on_disconnect),
            queue_video,
            f"Incoming video (device: {labeled_device.label})",
        )
    )
    process_gaze = asyncio.create_task(
        enqueue_sensor_data(
            receive_gaze_data(sensor_gaze.url, run_loop=restart_on_disconnect),
            queue_gaze,
            f"Incoming gaze (device: {labeled_device.label})",
        )
    )
    try:
        await match_and_map_gaze(queue_video, queue_gaze, queue_result, labeled_device.camera_calibration, surface_layouts)
    finally:
        process_video.cancel()
        process_gaze.cancel()

    return queue_result

async def enqueue_sensor_data(sensor: AsyncIterator[T], queue: asyncio.Queue[T], label: str) -> None:
    async for datum in sensor:
        try:
            queue.put_nowait((datum.datetime, datum))
        except QueueFull:
            print(f"Queue for {label} is full, dropping {datum}")

async def get_most_recent_item(queue: asyncio.Queue[T]) -> Tuple[datetime, T]:
    item = await queue.get()
    while True:
        try:
            next_item = queue.get_nowait()
        except QueueEmpty:
            return item
        else:
            item = next_item

async def get_closest_item(queue: asyncio.Queue[T], timestamp: datetime) -> Tuple[datetime, T]:
    item_ts, item = await queue.get()
    # assumes monotonically increasing timestamps
    if item_ts > timestamp:
        return item_ts, item
    while True:
        try:
            next_item_ts, next_item = queue.get_nowait()
        except QueueEmpty:
            return item_ts, item
        else:
            if next_item_ts > timestamp:
                return next_item_ts, next_item
            item_ts, item = next_item_ts, next_item


async def match_and_map_gaze(queue_video: asyncio.Queue[VideoFrame], queue_gaze: asyncio.Queue[GazeData], output_queue: asyncio.Queue[GazeMappedResult], calibration: Calibration, surface_layouts: Dict[int, SurfaceLayoutLabeled]) -> None:
    
    # initialize gaze mapper
    gaze_mapper = GazeMapper(calibration) # init without surfaces, we need to use .add_surface()

    # key is gaze_mapper surface id, value is surface_layout label
    surface_uid_dict = {}
    for surface_layout in surface_layouts.values():
        created_surface = gaze_mapper.add_surface(surface_layout.tags, surface_layout.size, surface_layout.label)
        surface_uid_dict[created_surface.uid] = surface_layout.label
    
    # process gaze and video data
    while True:
        video_ts, video_item = await get_most_recent_item(queue_video)
        gaze_ts, gaze_item = await get_closest_item(queue_gaze, video_ts)

        # process the frame and gaze data
        # add this to the asyncio thread pool
        gaze_mapped_result = await asyncio.to_thread(gaze_mapper.process_frame, video_item, gaze_item)
        
        # create result to put into queue (TODO: RIGHT NOW DISTORTED, NEED TO UNDISTORT IN FUTURE)
        # for each surface, add the gaze mapped result
        if gaze_mapped_result is None:
            # no surfaces detected, emit None for each surface
            surface_gaze: Dict[str, Optional[GazeMappedSurfaceResult]] = {surface_label: None for surface_label in surface_uid_dict.values()}
        else:
            # surfaces detected, map gaze to each surface
            surface_gaze: Dict[str, Optional[GazeMappedSurfaceResult]] = {}
            for surface_uid, surface_label in surface_uid_dict.items():
                if surface_uid in gaze_mapped_result.mapped_gaze and gaze_mapped_result.mapped_gaze[surface_uid]:
                    mapped_data = gaze_mapped_result.mapped_gaze[surface_uid][0]
                    surface_gaze[surface_label] = GazeMappedSurfaceResult(
                        x=mapped_data.x,
                        y=mapped_data.y,
                        is_on_surface=mapped_data.is_on_aoi
                    )
                else:
                    surface_gaze[surface_label] = None
        
        result: GazeMappedResult = {
            "timestamp": gaze_ts,
            "surface_gaze": surface_gaze,
        }
        
        output_queue.put_nowait(result)

