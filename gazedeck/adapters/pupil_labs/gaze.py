"""Pupil Labs gaze data adapter."""

import logging
from typing import AsyncIterator

try:
    from pupil_labs.realtime_api.simple import receive_gaze_data
except ImportError:
    # Fallback for when pupil-labs is not installed
    receive_gaze_data = None

from ...core.types import GazeSample
from ...ports.gaze_provider import IGazeProvider

logger = logging.getLogger(__name__)


class PupilLabsGazeProvider(IGazeProvider):
    """Pupil Labs gaze data provider with auto-reconnect."""

    def __init__(self, url: str) -> None:
        """Initialize Pupil Labs gaze provider.

        Args:
            url: Pupil Labs device URL
        """
        if receive_gaze_data is None:
            raise ImportError("pupil-labs package is required for PupilLabsGazeProvider")

        self._url = url

    async def stream(self) -> AsyncIterator[GazeSample]:
        """Stream gaze samples from Pupil Labs device.

        Yields:
            GazeSample: Raw gaze data with timestamp, coordinates, and confidence

        Note:
            Uses auto-reconnect with run_loop=True as specified in the API.
        """
        logger.info(f"Connecting to Pupil Labs device at {self._url}")

        async for gaze_datum in receive_gaze_data(self._url, run_loop=True):
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
