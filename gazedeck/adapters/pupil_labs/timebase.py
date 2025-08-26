"""Pupil Labs timebase adapter (stub implementation)."""

import time
from typing import Protocol


class ITimebase(Protocol):
    """Timebase interface."""

    def now_ms(self) -> int:
        """Get current timestamp in milliseconds."""
        ...


class SystemTimebase(ITimebase):
    """System timebase using host time."""

    def now_ms(self) -> int:
        """Get current system time in milliseconds."""
        return int(time.time() * 1000)


class PupilLabsTimebase(ITimebase):
    """Pupil Labs timebase adapter (stub).

    This is a stub implementation that uses system time.
    In a real implementation, this would sync with Pupil Labs device time.
    """

    def __init__(self) -> None:
        """Initialize Pupil Labs timebase."""
        self._system_timebase = SystemTimebase()

    def now_ms(self) -> int:
        """Get current timestamp in milliseconds.

        Returns:
            Current timestamp (currently uses system time as stub)
        """
        return self._system_timebase.now_ms()
