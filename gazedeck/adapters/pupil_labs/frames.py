"""Pupil Labs frame data adapter."""

import logging
from typing import AsyncIterator, Tuple

import numpy as np

try:
    from pupil_labs.realtime_api.simple import receive_video_frames
except ImportError:
    # Fallback for when pupil-labs is not installed
    receive_video_frames = None

from ...core.types import SceneFrame
from ...ports.frame_provider import IFrameProvider

logger = logging.getLogger(__name__)


class PupilLabsFrameProvider(IFrameProvider):
    """Pupil Labs frame provider with auto-reconnect."""

    def __init__(self, url: str) -> None:
        """Initialize Pupil Labs frame provider.

        Args:
            url: Pupil Labs device URL
        """
        if receive_video_frames is None:
            raise ImportError("pupil-labs package is required for PupilLabsFrameProvider")

        self._url = url

    async def stream(self) -> AsyncIterator[Tuple[SceneFrame, np.ndarray]]:
        """Stream scene frames from Pupil Labs device.

        Yields:
            Tuple of (SceneFrame metadata, BGR pixel array)

        Note:
            Uses auto-reconnect with run_loop=True as specified in the API.
        """
        logger.info(f"Connecting to Pupil Labs device at {self._url}")

        async for frame in receive_video_frames(self._url, run_loop=True):
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
