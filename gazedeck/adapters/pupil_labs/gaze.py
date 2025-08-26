"""Pupil Labs gaze data adapter."""

import logging
from typing import AsyncIterator

try:
    from pupil_labs_realtime_api.simple import receive_gaze_data
except ImportError:
    receive_gaze_data = None

from .device import PupilLabsDevice
from ...ports.device_provider import SensorURLs
from ...core.types import GazeSample
from ...ports.gaze_provider import IGazeProvider

logger = logging.getLogger(__name__)


class PupilLabsGazeProvider(IGazeProvider):
    """Pupil Labs gaze data provider using shared device provider."""

    def __init__(self, device_provider: PupilLabsDevice) -> None:
        """Initialize Pupil Labs gaze provider.

        Args:
            device_provider: Shared device provider instance
        """
        if receive_gaze_data is None:
            raise ImportError("pupil-labs-realtime-api package is required for PupilLabsGazeProvider")

        self._device_provider = device_provider

    async def stream(self) -> AsyncIterator[GazeSample]:
        """Stream gaze samples from Pupil Labs device.

        Yields:
            GazeSample: Raw gaze data with timestamp, coordinates, and confidence

        Note:
            Uses shared device provider for sensor URL retrieval.
        """
        # Get sensor URLs from shared device provider
        sensor_urls = await self._device_provider.get_sensor_urls()

        logger.info(f"Connecting to gaze sensor at {sensor_urls.gaze_url}")

        async for gaze_datum in receive_gaze_data(sensor_urls.gaze_url, run_loop=True):
            try:
                # Extract data from Pupil Labs gaze datum
                # Based on Pupil Labs Real-Time API structure
                timestamp_ms = int(gaze_datum.timestamp_unix_seconds * 1000)

                # Get gaze position (normalized coordinates)
                x = gaze_datum.x
                y = gaze_datum.y

                # Get confidence if available
                confidence = getattr(gaze_datum, 'confidence', 1.0)

                yield GazeSample(
                    ts_ms=timestamp_ms,
                    x=x,
                    y=y,
                    frame="scene_norm",  # Pupil Labs provides normalized coordinates
                    conf=confidence,
                )

            except Exception as e:
                logger.warning(f"Failed to process gaze datum: {e}")
                continue
