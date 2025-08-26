"""Gaze provider interface."""

from typing import Protocol, AsyncIterator

from ..core.types import GazeSample


class IGazeProvider(Protocol):
    """Protocol for gaze data providers."""

    async def stream(self) -> AsyncIterator[GazeSample]:
        """Stream gaze samples.

        Yields:
            GazeSample: Raw gaze data with timestamp, coordinates, and confidence
        """
        ...  # pragma: no cover
