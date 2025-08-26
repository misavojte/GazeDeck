"""Sink interface for outputting gaze events."""

from typing import Protocol

from ..core.types import GazeEvent


class ISink(Protocol):
    """Protocol for event sinks."""

    async def emit(self, msg: GazeEvent) -> None:
        """Emit a gaze event.

        Args:
            msg: Gaze event to emit
        """
        ...  # pragma: no cover
