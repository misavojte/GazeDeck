"""Pupil Labs gaze data adapter with reconnection support."""

import logging
from typing import AsyncIterator, Optional

try:
    from pupil_labs.realtime_api.simple import discover_one_device
except ImportError:
    discover_one_device = None

from .device import PupilLabsDevice
from .streaming import BaseStreamer, ReconnectionConfig, ConnectionLostError
from ...ports.device_provider import SensorURLs
from ...core.types import GazeSample
from ...ports.gaze_provider import IGazeProvider

logger = logging.getLogger(__name__)


class PupilLabsGazeStreamer(BaseStreamer):
    """Pupil Labs gaze data streamer with reconnection support."""

    def __init__(self, url: str, config: Optional[ReconnectionConfig] = None):
        """Initialize the gaze streamer.

        Args:
            url: Gaze sensor URL
            config: Reconnection configuration
        """
        super().__init__(url, config)

    async def _stream_once(self) -> AsyncIterator[GazeSample]:
        """Stream gaze data from a single connection attempt.

        Yields:
            GazeSample: Validated gaze data

        Raises:
            ConnectionLostError: When connection is lost
        """
        if discover_one_device is None:
            raise self._wrap_streaming_error(RuntimeError(
                "Pupil Labs Simple API not available. Install 'pupil-labs-realtime-api' and try again."
            ))

        device = None
        try:
            logger.debug("Discovering Pupil Labs device for gaze stream...")
            device = await self._discover_device()

            logger.debug("Receiving gaze data...")
            gaze_count = 0
            while True:
                gaze_datum = await self._receive_gaze_datum(device)
                gaze_count += 1
                if gaze_count % 100 == 0:
                    logger.info(f"Received {gaze_count} gaze data points")
                try:
                    gaze_sample = self._process_gaze_datum(gaze_datum)
                    if gaze_sample:
                        yield gaze_sample
                    else:
                        logger.debug("Gaze datum was filtered out")
                except Exception as e:
                    logger.warning(f"Failed to process gaze datum: {e}")
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

    async def _receive_gaze_datum(self, device):
        """Receive one gaze datum from the device in a thread."""
        import asyncio
        loop = asyncio.get_running_loop()
        return await loop.run_in_executor(None, device.receive_gaze_datum)

    def _process_gaze_datum(self, gaze_datum) -> Optional[GazeSample]:
        """Process and validate a single gaze datum.

        Args:
            gaze_datum: Raw gaze data from Pupil Labs API

        Returns:
            GazeSample if valid, None if should be skipped
        """
        # Extract timestamp
        timestamp_ms = int(gaze_datum.timestamp_unix_seconds * 1000)

        # Extract coordinates (Simple API provides scene pixel coordinates)
        x = gaze_datum.x
        y = gaze_datum.y

        # Extract confidence
        confidence = getattr(gaze_datum, 'confidence', 1.0)

        # Validate confidence
        if not (0.0 <= confidence <= 1.0):
            logger.warning(f"Invalid confidence value: {confidence}")
            return None

        return GazeSample(
            ts_ms=timestamp_ms,
            x=x,
            y=y,
            frame="scene_px",
            conf=confidence,
        )


class PupilLabsGazeProvider(IGazeProvider):
    """Pupil Labs gaze data provider with reconnection support."""

    def __init__(self, device_provider: PupilLabsDevice,
                 reconnection_config: Optional[ReconnectionConfig] = None) -> None:
        """Initialize Pupil Labs gaze provider.

        Args:
            device_provider: Shared device provider instance
            reconnection_config: Configuration for reconnection behavior
        """
        self._device_provider = device_provider
        self._reconnection_config = reconnection_config or ReconnectionConfig()

    async def stream(self) -> AsyncIterator[GazeSample]:
        """Stream gaze samples from Pupil Labs device with reconnection support.

        Yields:
            GazeSample: Validated gaze data with automatic reconnection

        Note:
            Uses shared device provider for sensor URL retrieval and includes
            automatic reconnection on connection failures.
        """
        # Get sensor URLs from shared device provider
        sensor_urls = await self._device_provider.get_sensor_urls()

        logger.info(f"Connecting to gaze sensor at {sensor_urls.gaze_url}")

        # Create streamer with reconnection support
        streamer = PupilLabsGazeStreamer(
            url=sensor_urls.gaze_url,
            config=self._reconnection_config
        )

        try:
            async for gaze_sample in streamer.stream_with_reconnect():
                yield gaze_sample
        finally:
            await streamer.shutdown()
