"""Pupil Labs frame data adapter with reconnection support."""

import logging
from typing import AsyncIterator, Tuple, Optional

import numpy as np

try:
    from pupil_labs_realtime_api.simple import receive_video_frames
except ImportError:
    receive_video_frames = None

from .device import PupilLabsDevice
from .streaming import BaseStreamer, ReconnectionConfig, ConnectionLostError
from ...ports.device_provider import SensorURLs
from ...core.types import SceneFrame
from ...ports.frame_provider import IFrameProvider

logger = logging.getLogger(__name__)


class PupilLabsFrameStreamer(BaseStreamer):
    """Pupil Labs frame data streamer with reconnection support."""

    def __init__(self, url: str, config: Optional[ReconnectionConfig] = None):
        """Initialize the frame streamer.

        Args:
            url: World sensor URL
            config: Reconnection configuration
        """
        super().__init__(url, config)
        if receive_video_frames is None:
            raise ImportError("pupil-labs-realtime-api package is required for PupilLabsFrameStreamer")

    async def _stream_once(self) -> AsyncIterator[Tuple[SceneFrame, np.ndarray]]:
        """Stream frame data from a single connection attempt.

        Yields:
            Tuple of (SceneFrame metadata, BGR pixel array)

        Raises:
            ConnectionLostError: When connection is lost
        """
        try:
            logger.debug(f"Starting video frame stream from {self.url}")
            async for frame in receive_video_frames(self.url, run_loop=True):
                try:
                    # Process and validate frame data
                    frame_data = self._process_frame(frame)
                    if frame_data:
                        yield frame_data

                except Exception as e:
                    logger.warning(f"Failed to process frame: {e}")
                    continue

        except Exception as e:
            # Wrap connection errors appropriately
            raise self._wrap_streaming_error(e) from e

    def _process_frame(self, frame) -> Optional[Tuple[SceneFrame, np.ndarray]]:
        """Process and validate a single frame.

        Args:
            frame: Raw frame data from Pupil Labs API

        Returns:
            Tuple of (SceneFrame, frame_array) if valid, None if should be skipped
        """
        # Extract frame metadata
        timestamp_ms = int(frame.timestamp_unix_seconds * 1000)

        # Convert numpy scalars to Python native types
        width = int(frame.width.item() if hasattr(frame.width, 'item') else frame.width)
        height = int(frame.height.item() if hasattr(frame.height, 'item') else frame.height)

        # Validate dimensions
        if width <= 0 or height <= 0:
            logger.warning(f"Invalid frame dimensions: {width}x{height}")
            return None

        # Extract pixel data with improved error handling
        frame_bgr = self._extract_pixel_data(frame, width, height)
        if frame_bgr is None:
            return None

        scene_frame = SceneFrame(
            ts_ms=timestamp_ms,
            w=width,
            h=height,
        )

        return scene_frame, frame_bgr

    def _extract_pixel_data(self, frame, width: int, height: int) -> Optional[np.ndarray]:
        """Extract pixel data from frame with robust error handling.

        Args:
            frame: Raw frame object
            width: Frame width
            height: Frame height

        Returns:
            BGR pixel array or None if extraction fails
        """
        # Try multiple methods to extract pixel data
        if hasattr(frame, 'bgr_pixels') and frame.bgr_pixels is not None:
            try:
                return np.array(frame.bgr_pixels, dtype=np.uint8).reshape(height, width, 3)
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to process bgr_pixels: {e}")

        if hasattr(frame, 'pixels') and frame.pixels is not None:
            try:
                pixels = np.array(frame.pixels, dtype=np.uint8)
                expected_size = width * height * 3

                if pixels.size == expected_size:
                    return pixels.reshape(height, width, 3)
                else:
                    logger.warning(f"Pixel data size mismatch: got {pixels.size}, expected {expected_size}")
            except (ValueError, TypeError) as e:
                logger.warning(f"Failed to process pixels: {e}")

        logger.warning("Frame object missing valid pixel data")
        return None


class PupilLabsFrameProvider(IFrameProvider):
    """Pupil Labs frame provider with reconnection support."""

    def __init__(self, device_provider: PupilLabsDevice,
                 reconnection_config: Optional[ReconnectionConfig] = None) -> None:
        """Initialize Pupil Labs frame provider.

        Args:
            device_provider: Shared device provider instance
            reconnection_config: Configuration for reconnection behavior
        """
        self._device_provider = device_provider
        self._reconnection_config = reconnection_config or ReconnectionConfig()

    async def stream(self) -> AsyncIterator[Tuple[SceneFrame, np.ndarray]]:
        """Stream scene frames from Pupil Labs device with reconnection support.

        Yields:
            Tuple of (SceneFrame metadata, BGR pixel array)

        Note:
            Uses shared device provider for sensor URL retrieval and includes
            automatic reconnection on connection failures.
        """
        # Get sensor URLs from shared device provider
        sensor_urls = await self._device_provider.get_sensor_urls()

        logger.info(f"Connecting to world sensor at {sensor_urls.world_url}")

        # Create streamer with reconnection support
        streamer = PupilLabsFrameStreamer(
            url=sensor_urls.world_url,
            config=self._reconnection_config
        )

        try:
            async for frame_data in streamer.stream_with_reconnect():
                yield frame_data
        finally:
            await streamer.shutdown()
