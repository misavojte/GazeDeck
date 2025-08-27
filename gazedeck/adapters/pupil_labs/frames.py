"""Pupil Labs frame data adapter with reconnection support."""

import logging
from typing import AsyncIterator, Tuple, Optional

import numpy as np

try:
    from pupil_labs.realtime_api.simple import discover_one_device
except ImportError:
    discover_one_device = None

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

    async def _stream_once(self) -> AsyncIterator[Tuple[SceneFrame, np.ndarray]]:
        """Stream frame data from a single connection attempt.

        Yields:
            Tuple of (SceneFrame metadata, BGR pixel array)

        Raises:
            ConnectionLostError: When connection is lost
        """
        if discover_one_device is None:
            raise self._wrap_streaming_error(RuntimeError(
                "Pupil Labs Simple API not available. Install 'pupil-labs-realtime-api' and try again."
            ))

        device = None
        try:
            logger.debug("Discovering Pupil Labs device for scene frames...")
            device = await self._discover_device()

            logger.debug("Receiving scene video frames...")
            while True:
                frame = await self._receive_scene_frame(device)
                try:
                    frame_data = self._process_frame(frame)
                    if frame_data:
                        yield frame_data
                except Exception as e:
                    logger.warning(f"Failed to process frame: {e}")
                    continue

        except Exception as e:
            raise self._wrap_streaming_error(e) from e
        finally:
            if device is not None:
                try:
                    device.close()
                except Exception:
                    pass

    async def _discover_device(self):
        """Discover and return a Simple API Device (runs in a thread)."""
        import asyncio
        loop = asyncio.get_running_loop()

        def _block_discover():
            return discover_one_device(max_search_duration_seconds=10)

        device = await loop.run_in_executor(None, _block_discover)
        if device is None:
            raise RuntimeError("No Pupil Labs device found")
        return device

    async def _receive_scene_frame(self, device):
        """Receive one scene frame from the device in a thread."""
        import asyncio
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, device.receive_scene_video_frame)

    def _process_frame(self, frame) -> Optional[Tuple[SceneFrame, np.ndarray]]:
        """Process and validate a single frame.

        Args:
            frame: Raw frame data from Pupil Labs API

        Returns:
            Tuple of (SceneFrame, frame_array) if valid, None if should be skipped
        """
        # Extract timestamp
        timestamp_ms = int(getattr(frame, 'timestamp_unix_seconds', 0.0) * 1000)

        # Try to extract pixel data first; infer width/height from array shape if possible
        frame_bgr = self._extract_pixel_data(frame)
        if frame_bgr is None:
            return None

        height, width = frame_bgr.shape[:2]

        scene_frame = SceneFrame(ts_ms=timestamp_ms, w=width, h=height)
        return scene_frame, frame_bgr

    def _extract_pixel_data(self, frame) -> Optional[np.ndarray]:
        """Extract pixel data from frame with robust attribute handling."""
        # Direct numpy-like attributes
        for attr in ('bgr_pixels', 'pixels', 'bgr', 'image_bgr', 'image'):
            if hasattr(frame, attr):
                data = getattr(frame, attr)
                if data is not None:
                    arr = np.array(data, dtype=np.uint8)
                    # If already shaped (H, W, 3), just return
                    if arr.ndim == 3 and arr.shape[2] in (3, 4):
                        if arr.shape[2] == 4:
                            # Drop alpha if present
                            arr = arr[:, :, :3]
                        return arr

                    # Otherwise, try to reshape using any width/height attributes
                    width = None
                    height = None
                    for w_attr in ('width', 'width_px', 'w', 'cols'):
                        if hasattr(frame, w_attr):
                            w_val = getattr(frame, w_attr)
                            try:
                                width = int(w_val.item() if hasattr(w_val, 'item') else w_val)
                                break
                            except Exception:
                                continue
                    for h_attr in ('height', 'height_px', 'h', 'rows'):
                        if hasattr(frame, h_attr):
                            h_val = getattr(frame, h_attr)
                            try:
                                height = int(h_val.item() if hasattr(h_val, 'item') else h_val)
                                break
                            except Exception:
                                continue

                    if width and height and arr.size == width * height * 3:
                        try:
                            return arr.reshape(height, width, 3)
                        except Exception as e:
                            logger.warning(f"Failed to reshape pixel data: {e}")

        logger.warning("Frame object missing usable pixel data attributes")
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
