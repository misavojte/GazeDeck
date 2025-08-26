"""Pupil Labs frame data adapter."""

import logging
from typing import AsyncIterator, Tuple

import numpy as np

try:
    from pupil_labs_realtime_api.simple import receive_video_frames
except ImportError:
    receive_video_frames = None

from .device import PupilLabsDevice
from ...ports.device_provider import SensorURLs
from ...core.types import SceneFrame
from ...ports.frame_provider import IFrameProvider

logger = logging.getLogger(__name__)


class PupilLabsFrameProvider(IFrameProvider):
    """Pupil Labs frame provider using shared device provider."""

    def __init__(self, device_provider: PupilLabsDevice) -> None:
        """Initialize Pupil Labs frame provider.

        Args:
            device_provider: Shared device provider instance
        """
        if receive_video_frames is None:
            raise ImportError("pupil-labs-realtime-api package is required for PupilLabsFrameProvider")

        self._device_provider = device_provider

    async def stream(self) -> AsyncIterator[Tuple[SceneFrame, np.ndarray]]:
        """Stream scene frames from Pupil Labs device.

        Yields:
            Tuple of (SceneFrame metadata, BGR pixel array)

        Note:
            Uses shared device provider for sensor URL retrieval.
        """
        # Get sensor URLs from shared device provider
        sensor_urls = await self._device_provider.get_sensor_urls()

        logger.info(f"Connecting to world sensor at {sensor_urls.world_url}")

        async for frame in receive_video_frames(sensor_urls.world_url, run_loop=True):
            try:
                # Extract frame data from Pupil Labs frame object
                timestamp_ms = int(frame.timestamp_unix_seconds * 1000)
                width = frame.width
                height = frame.height

                # Convert to BGR ndarray
                # Assuming frame.bgr_pixels contains the pixel data
                if hasattr(frame, 'bgr_pixels'):
                    frame_bgr = np.array(frame.bgr_pixels, dtype=np.uint8).reshape(height, width, 3)
                elif hasattr(frame, 'pixels'):
                    # Fallback if pixels are in different format
                    pixels = np.array(frame.pixels, dtype=np.uint8)
                    if pixels.size == width * height * 3:
                        frame_bgr = pixels.reshape(height, width, 3)
                    else:
                        logger.warning(f"Unexpected pixel format: {pixels.size} bytes for {width}x{height}x3 expected")
                        continue
                else:
                    logger.warning("Frame object missing pixel data")
                    continue

                scene_frame = SceneFrame(
                    ts_ms=timestamp_ms,
                    w=width,
                    h=height,
                )

                yield scene_frame, frame_bgr

            except Exception as e:
                logger.warning(f"Failed to process frame: {e}")
                continue
