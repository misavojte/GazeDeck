"""Pupil Labs gaze data adapter with reconnection support."""

import logging
from typing import AsyncIterator, Optional

try:
    from pupil_labs_realtime_api.simple import receive_gaze_data
except ImportError:
    receive_gaze_data = None

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
        if receive_gaze_data is None:
            raise ImportError("pupil-labs-realtime-api package is required for PupilLabsGazeStreamer")

    async def _stream_once(self) -> AsyncIterator[GazeSample]:
        """Stream gaze data from a single connection attempt.

        Yields:
            GazeSample: Validated gaze data

        Raises:
            ConnectionLostError: When connection is lost
        """
        try:
            logger.debug(f"Starting gaze data stream from {self.url}")
            async for gaze_datum in receive_gaze_data(self.url, run_loop=True):
                try:
                    # Validate and extract gaze data
                    gaze_sample = self._process_gaze_datum(gaze_datum)
                    if gaze_sample:
                        yield gaze_sample

                except Exception as e:
                    logger.warning(f"Failed to process gaze datum: {e}")
                    continue

        except Exception as e:
            # Wrap connection errors appropriately
            raise self._wrap_streaming_error(e) from e

    def _process_gaze_datum(self, gaze_datum) -> Optional[GazeSample]:
        """Process and validate a single gaze datum.

        Args:
            gaze_datum: Raw gaze data from Pupil Labs API

        Returns:
            GazeSample if valid, None if should be skipped
        """
        # Extract timestamp
        timestamp_ms = int(gaze_datum.timestamp_unix_seconds * 1000)

        # Extract coordinates
        x = gaze_datum.x
        y = gaze_datum.y

        # Validate coordinates are in expected range for normalized coordinates
        if not (0.0 <= x <= 1.0 and 0.0 <= y <= 1.0):
            logger.warning(f"Gaze coordinates out of range: x={x}, y={y}")
            return None

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
            frame="scene_norm",  # Pupil Labs provides normalized coordinates
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
