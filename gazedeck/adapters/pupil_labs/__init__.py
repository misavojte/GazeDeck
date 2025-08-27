"""Pupil Labs adapters for gaze tracking and frame streaming."""

from .device import PupilLabsDevice
from .frames import PupilLabsFrameProvider
from .gaze import PupilLabsGazeProvider
from .streaming import (
    BaseStreamer,
    ReconnectionConfig,
    StreamingError,
    ConnectionLostError,
    MaxRetriesExceededError,
    ExponentialBackoff,
)

__all__ = [
    "PupilLabsDevice",
    "PupilLabsFrameProvider",
    "PupilLabsGazeProvider",
    "BaseStreamer",
    "ReconnectionConfig",
    "StreamingError",
    "ConnectionLostError",
    "MaxRetriesExceededError",
    "ExponentialBackoff",
]
